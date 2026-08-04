"""AutoGen-powered adversarial debate flow with phased execution.

Maintains the same ``DebateResult`` contract as ``DebateController`` so the
scoring / persistence pipeline in ``run_eval.py`` works identically for both.

Key design choices (all verified against AutoGen 0.7.5 source):
  - Phase isolation: each phase is a separate AutoGen interaction
  - ``max_turns`` (not ``MaxMessageTermination``) to avoid off-by-one
  - Deterministic ``selector_func`` that never returns None
  - Structured JSON output for proposals, revisions, and judge verdict
  - ``on_reset()`` between phases to avoid context duplication
  - ``output_task_messages=False`` to keep TaskResult clean
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any, Optional

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import StopMessage, TextMessage
from autogen_agentchat.teams import SelectorGroupChat
from autogen_core import CancellationToken

from app.core.domain.schemas import DebateRole
from app.infra.debate.prompts import format_evidence
from app.infra.debate.schemas import (
    DebateMessage,
    DebatePhase,
    DebateResult,
    MessageEvent,
    OnMessageCallback,
    OnPhaseCallback,
    PhaseEvent,
)
from app.infra.debate.toml_serde import parse_judge_output
from app.infra.llm.autogen_model_client import GalileoModelClient

from .autogen_agents import create_debate_agents

logger = logging.getLogger(__name__)

# Per-turn timeout budget (seconds).  Each agent turn in a group-chat
# phase (cross-exam / dispute) gets this many seconds before the whole
# phase is cancelled.  Generous enough for slow providers; tight enough
# to avoid multi-minute hangs.
_PER_TURN_TIMEOUT: int = 120

# Deterministic cross-exam turn order (mirrors the existing FSM)
_CROSS_EXAM_ORDER = [
    DebateRole.ORTHODOX,   # Ask Heretic
    DebateRole.HERETIC,    # Answer
    DebateRole.HERETIC,    # Ask Orthodox
    DebateRole.ORTHODOX,   # Answer
    DebateRole.SKEPTIC,    # Ask Both
    DebateRole.ORTHODOX,   # Answer Skeptic
    DebateRole.HERETIC,    # Answer Skeptic
]

# Metadata for each cross-exam turn: whether it is a "question" or "answer"
# turn, and the target role for question turns.
_CROSS_EXAM_TURN_META: list[dict[str, str]] = [
    {"type": "question", "target": DebateRole.HERETIC.value},
    {"type": "answer"},
    {"type": "question", "target": DebateRole.ORTHODOX.value},
    {"type": "answer"},
    {"type": "question", "target": "Both"},
    {"type": "answer"},
    {"type": "answer"},
]

# Regex for evidence IDs in free text (e.g. E1, E2, HY01-E1, CL02-E3)
_EVIDENCE_REF_RE = re.compile(r"\b(?:[A-Z]{2,}\d{2}-)?E\d+\b")

# --- JSON schema instructions appended to task prompts ---

_PROPOSAL_JSON_SCHEMA = (
    "\n\nOutput ONLY valid JSON matching this schema:\n"
    '{"proposed_verdict": "SUPPORTED or REFUTED or INSUFFICIENT", '
    '"evidence_used": ["E1", "E2"], '
    '"key_points": ["point 1", "point 2"], '
    '"uncertainties": ["..."], '
    '"what_would_change_my_mind": ["..."]}\n'
    "No extra text outside the JSON."
)

_REVISION_JSON_SCHEMA = (
    "\n\nOutput ONLY valid JSON matching this schema:\n"
    '{"final_proposed_verdict": "SUPPORTED or REFUTED or INSUFFICIENT", '
    '"evidence_used": ["E1"], '
    '"what_i_changed": ["..."], '
    '"remaining_disagreements": ["..."], '
    '"confidence": 0.85}\n'
    "No extra text outside the JSON."
)

_JUDGE_JSON_SCHEMA = (
    "Output ONLY valid JSON matching this schema:\n"
    '{"verdict": "SUPPORTED or REFUTED or INSUFFICIENT", '
    '"confidence": 0.85, '
    '"evidence_used": ["E1", "E2"], '
    '"reasoning": "brief explanation (1-3 sentences)"}\n'
    "No extra text outside the JSON."
)

# --- Fallback dicts when JSON parsing fails ---

_PROPOSAL_FALLBACK: dict[str, Any] = {
    "proposed_verdict": "INSUFFICIENT",
    "evidence_used": [],
    "key_points": ["Unable to parse proposal"],
    "uncertainties": [],
    "what_would_change_my_mind": [],
}

_REVISION_FALLBACK: dict[str, Any] = {
    "final_proposed_verdict": "INSUFFICIENT",
    "evidence_used": [],
    "what_i_changed": [],
    "remaining_disagreements": [],
    "confidence": 0.0,
}


class AutoGenDebateController:
    """AutoGen-powered debate orchestrator.

    Drop-in alternative to ``DebateController`` — same ``.run()`` signature
    and ``DebateResult`` output, activated via the ``use_autogen_debate``
    feature flag.
    """

    def __init__(
        self,
        model_client: GalileoModelClient,
        model_key: str,
        *,
        max_cross_exam_messages: int = 3,
        enable_tools: bool = False,
    ) -> None:
        self._model_client = model_client
        self._model_key = model_key
        self._max_cross_exam = max_cross_exam_messages
        self._enable_tools = enable_tools

    # ------------------------------------------------------------------
    # Public API (same contract as DebateController.run)
    # ------------------------------------------------------------------

    async def run(
        self,
        *,
        case_id: str,
        claim: str,
        topic: str,
        evidence_packets: list[dict],
        on_message: Optional[OnMessageCallback] = None,
        on_phase: Optional[OnPhaseCallback] = None,
    ) -> DebateResult:
        result = DebateResult()
        t0 = time.perf_counter()
        evidence_text = format_evidence(evidence_packets)

        # Build tools (optional)
        tools = None
        if self._enable_tools:
            from .autogen_tools import build_evidence_tools
            tools = build_evidence_tools(evidence_packets)

        # Create agents (all share the same model_client)
        agents = create_debate_agents(
            self._model_client,
            claim=claim,
            topic=topic,
            evidence_packets=evidence_packets,
            tools=tools,
        )
        orthodox = agents[DebateRole.ORTHODOX]
        heretic = agents[DebateRole.HERETIC]
        skeptic = agents[DebateRole.SKEPTIC]
        judge = agents[DebateRole.JUDGE]
        debaters = [orthodox, heretic, skeptic]

        try:
            # Phase 0: Setup
            await _emit_phase(on_phase, case_id, DebatePhase.SETUP)

            # Phase 1: Independent proposals (parallel, JSON output)
            await _emit_phase(on_phase, case_id, DebatePhase.INDEPENDENT)
            proposals = await self._phase_proposals(
                case_id, claim, agents, result, on_message,
            )

            # Reset agents between phases (Strategy A: explicit context injection)
            await _reset_agents(debaters)

            # Phase 2: Cross-examination (SelectorGroupChat, conversational)
            await _emit_phase(on_phase, case_id, DebatePhase.CROSS_EXAM)
            await self._phase_cross_exam(
                case_id, claim, proposals, agents, result, on_message,
            )

            # Reset agents between phases
            await _reset_agents(debaters)

            # Phase 3: Revision (parallel, JSON output)
            await _emit_phase(on_phase, case_id, DebatePhase.REVISION)
            revisions = await self._phase_revision(
                case_id, claim, proposals, result, agents, on_message,
            )

            # Early-stop check
            if not self._should_skip_dispute(revisions):
                await _reset_agents(debaters)

                # Phase 3.5: Dispute (conversational)
                await _emit_phase(on_phase, case_id, DebatePhase.DISPUTE)
                await self._phase_dispute(
                    case_id, claim, agents, result, on_message,
                )

            # Phase 4: Judge (JSON output)
            await _emit_phase(on_phase, case_id, DebatePhase.JUDGE)
            await self._phase_judge(
                case_id, claim, topic, evidence_text,
                judge, result, on_message,
            )

        finally:
            await self._model_client.close()

        result.total_latency_ms = int((time.perf_counter() - t0) * 1000)
        result.total_cost = self._model_client.accumulated_cost
        logger.info(
            "autogen debate done case=%s model=%s cost=%.6f latency=%dms",
            case_id, self._model_key, result.total_cost, result.total_latency_ms,
        )
        return result

    # ------------------------------------------------------------------
    # Phase 1: Independent proposals (parallel, JSON)
    # ------------------------------------------------------------------

    async def _phase_proposals(
        self,
        case_id: str,
        claim: str,
        agents: dict[str, AssistantAgent],
        result: DebateResult,
        on_message: Optional[OnMessageCallback],
    ) -> dict[str, dict]:
        tasks = {
            DebateRole.ORTHODOX: (
                f"Argue FOR this claim: {claim}\n"
                f"Cite evidence IDs.{_PROPOSAL_JSON_SCHEMA}"
            ),
            DebateRole.HERETIC: (
                f"Argue AGAINST this claim: {claim}\n"
                f"Cite evidence IDs.{_PROPOSAL_JSON_SCHEMA}"
            ),
            DebateRole.SKEPTIC: (
                f"Challenge BOTH sides on: {claim}\n"
                f"Cite evidence IDs.{_PROPOSAL_JSON_SCHEMA}"
            ),
        }
        proposals: dict[str, dict] = {}
        task_results = await asyncio.gather(*[
            agents[role].run(task=task, output_task_messages=False)
            for role, task in tasks.items()
        ])
        for idx, (role, _) in enumerate(tasks.items()):
            content = _extract_content(task_results[idx])
            parsed = _try_parse_json(content, fallback=_PROPOSAL_FALLBACK)
            proposals[role] = parsed
            clean_json = json.dumps(parsed)
            result.messages.append(
                DebateMessage(role.value, clean_json, DebatePhase.INDEPENDENT, idx + 1),
            )
            await _emit_msg(
                on_message, case_id, role.value, clean_json,
                DebatePhase.INDEPENDENT, idx + 1,
            )
        return proposals

    # ------------------------------------------------------------------
    # Phase 2: Cross-examination (SelectorGroupChat, conversational)
    # ------------------------------------------------------------------

    async def _phase_cross_exam(
        self,
        case_id: str,
        claim: str,
        proposals: dict[str, dict],
        agents: dict[str, AssistantAgent],
        result: DebateResult,
        on_message: Optional[OnMessageCallback],
    ) -> None:
        debate_agents = [
            agents[DebateRole.ORTHODOX],
            agents[DebateRole.HERETIC],
            agents[DebateRole.SKEPTIC],
        ]

        # Build context from parsed proposal dicts (JSON format)
        proposals_json = {
            role.value: data for role, data in proposals.items()
        }
        proposal_summary = json.dumps(proposals_json, indent=2, ensure_ascii=False)

        # Deterministic turn order — never returns None (DESIGN-1 fix)
        turn_idx = 0

        def deterministic_selector(messages: Any) -> str:
            nonlocal turn_idx
            if turn_idx < len(_CROSS_EXAM_ORDER):
                role = _CROSS_EXAM_ORDER[turn_idx]
                turn_idx += 1
                return role.value
            # Safe fallback — max_turns terminates before this runs
            return _CROSS_EXAM_ORDER[0].value

        # Use max_turns (not MaxMessageTermination) to avoid off-by-one (BUG-6 fix)
        cross_exam_team = SelectorGroupChat(
            participants=debate_agents,
            model_client=self._model_client,
            max_turns=self._max_cross_exam,
            selector_func=deterministic_selector,
        )

        task = (
            f"Cross-examine each other's positions on: {claim}\n\n"
            f"Proposals (JSON):\n{proposal_summary}\n\n"
            "Ask probing questions and challenge weak arguments. Cite evidence IDs."
        )

        # Wrap in a CancellationToken + asyncio timeout so a hung LLM
        # call cannot block the entire debate indefinitely.
        cancel = CancellationToken()
        phase_timeout = self._max_cross_exam * _PER_TURN_TIMEOUT
        try:
            chat_result = await asyncio.wait_for(
                cross_exam_team.run(
                    task=task,
                    output_task_messages=False,
                    cancellation_token=cancel,
                ),
                timeout=phase_timeout,
            )
        except (asyncio.TimeoutError, asyncio.CancelledError):
            cancel.cancel()
            logger.warning(
                "cross-exam phase timed out after %ds (max_turns=%d)",
                phase_timeout, self._max_cross_exam,
            )
            return

        # Filter out StopMessage and task messages, then wrap each agent
        # turn in the structured JSON envelope the frontend expects
        # (QuestionsMessage or AnswersMessage).
        agent_msg_idx = 0
        for msg in chat_result.messages:
            if isinstance(msg, StopMessage):
                continue
            if hasattr(msg, "source") and msg.source == "user":
                continue
            raw = msg.content if hasattr(msg, "content") else str(msg)
            source = msg.source if hasattr(msg, "source") else "Unknown"
            content = _wrap_cross_exam_message(agent_msg_idx, raw, source)
            agent_msg_idx += 1
            result.messages.append(
                DebateMessage(source, content, DebatePhase.CROSS_EXAM, agent_msg_idx),
            )
            await _emit_msg(
                on_message, case_id, source, content,
                DebatePhase.CROSS_EXAM, agent_msg_idx,
            )

    # ------------------------------------------------------------------
    # Phase 3: Revision (parallel, JSON)
    # ------------------------------------------------------------------

    async def _phase_revision(
        self,
        case_id: str,
        claim: str,
        proposals: dict[str, dict],
        result: DebateResult,
        agents: dict[str, AssistantAgent],
        on_message: Optional[OnMessageCallback],
    ) -> dict[str, dict]:
        # Build debate history for context injection
        debate_history = "\n".join(
            f"[{m.role}] {m.content[:2000]}" for m in result.messages
        )

        # Build lightweight SharedMemo from parsed proposals
        memo = self._build_memo(proposals)

        task_template = (
            "The cross-examination is complete. Revise your stance on: {claim}\n\n"
            "Debate so far:\n{history}\n\n"
            "{memo}\n\n"
            "State your FINAL verdict, evidence used, what you changed, "
            "remaining disagreements, and confidence (0.0-1.0)."
            "{schema}"
        )

        roles = [DebateRole.ORTHODOX, DebateRole.HERETIC, DebateRole.SKEPTIC]
        revisions: dict[str, dict] = {}
        results_list = await asyncio.gather(*[
            agents[role].run(
                task=task_template.format(
                    claim=claim,
                    history=debate_history[-8000:],
                    memo=memo,
                    schema=_REVISION_JSON_SCHEMA,
                ),
                output_task_messages=False,
            )
            for role in roles
        ])
        for idx, role in enumerate(roles):
            content = _extract_content(results_list[idx])
            parsed = _try_parse_json(content, fallback=_REVISION_FALLBACK)
            revisions[role] = parsed
            clean_json = json.dumps(parsed)
            result.messages.append(
                DebateMessage(role.value, clean_json, DebatePhase.REVISION, idx + 1),
            )
            await _emit_msg(
                on_message, case_id, role.value, clean_json,
                DebatePhase.REVISION, idx + 1,
            )
        return revisions

    # ------------------------------------------------------------------
    # Phase 3.5: Dispute (conversational)
    # ------------------------------------------------------------------

    async def _phase_dispute(
        self,
        case_id: str,
        claim: str,
        agents: dict[str, AssistantAgent],
        result: DebateResult,
        on_message: Optional[OnMessageCallback],
    ) -> None:
        debate_history = "\n".join(
            f"[{m.role}] {m.content[:2000]}" for m in result.messages
        )

        # 3 agent calls (Skeptic question + 2 answers) — budget accordingly
        phase_timeout = 3 * _PER_TURN_TIMEOUT

        try:
            await asyncio.wait_for(
                self._dispute_inner(
                    case_id, claim, debate_history, agents, result, on_message,
                ),
                timeout=phase_timeout,
            )
        except (asyncio.TimeoutError, asyncio.CancelledError):
            logger.warning(
                "dispute phase timed out after %ds", phase_timeout,
            )

    async def _dispute_inner(
        self,
        case_id: str,
        claim: str,
        debate_history: str,
        agents: dict[str, AssistantAgent],
        result: DebateResult,
        on_message: Optional[OnMessageCallback],
    ) -> None:
        """Inner logic for the dispute phase, separated for timeout wrapping."""
        # Skeptic question → DisputeQuestionsMessage envelope
        q_result = await agents[DebateRole.SKEPTIC].run(
            task=(
                f"Agents still disagree on: {claim}\n\n"
                f"Debate so far:\n{debate_history[-6000:]}\n\n"
                "Ask exactly 1 final decisive question that could resolve the "
                "disagreement. Reference specific evidence."
            ),
            output_task_messages=False,
        )
        q_raw = _extract_content(q_result)
        q_content = _wrap_dispute_question(q_raw)
        result.messages.append(
            DebateMessage(DebateRole.SKEPTIC.value, q_content, DebatePhase.DISPUTE, 1),
        )
        await _emit_msg(
            on_message, case_id, DebateRole.SKEPTIC.value,
            q_content, DebatePhase.DISPUTE, 1,
        )

        # Orthodox + Heretic answer → DisputeAnswersMessage envelope
        for step, role in enumerate([DebateRole.ORTHODOX, DebateRole.HERETIC], 2):
            a_result = await agents[role].run(
                task=f"Answer the Skeptic's question:\n{q_raw}\n\nCite evidence.",
                output_task_messages=False,
            )
            a_raw = _extract_content(a_result)
            a_content = _wrap_dispute_answer(a_raw)
            result.messages.append(
                DebateMessage(role.value, a_content, DebatePhase.DISPUTE, step),
            )
            await _emit_msg(
                on_message, case_id, role.value,
                a_content, DebatePhase.DISPUTE, step,
            )

    # ------------------------------------------------------------------
    # Phase 4: Judge (JSON)
    # ------------------------------------------------------------------

    async def _phase_judge(
        self,
        case_id: str,
        claim: str,
        topic: str,
        evidence_text: str,
        judge: AssistantAgent,
        result: DebateResult,
        on_message: Optional[OnMessageCallback],
    ) -> None:
        structured = [
            {
                "role": msg.role,
                "phase": msg.phase,
                "round": msg.round,
                "content": _safe_content_parse(msg.content),
            }
            for msg in result.messages
        ]
        debate_block = json.dumps(structured, indent=2, ensure_ascii=False)

        judge_task = (
            f"You are the Judge. Render a FINAL verdict on the claim.\n\n"
            f"Topic: {topic}\nClaim: {claim}\n\n{evidence_text}\n\n"
            f"Structured debate transcript (JSON):\n{debate_block}\n\n"
            "Evaluate ALL positions, cross-examination results, and revisions.\n"
            "Use ONLY the evidence IDs from the evidence pack above.\n\n"
            f"{_JUDGE_JSON_SCHEMA}"
        )

        judge_result = await judge.run(task=judge_task, output_task_messages=False)
        judge_text = _extract_content(judge_result)
        result.messages.append(
            DebateMessage(DebateRole.JUDGE.value, judge_text, DebatePhase.JUDGE, 1),
        )
        await _emit_msg(
            on_message, case_id, DebateRole.JUDGE.value,
            judge_text, DebatePhase.JUDGE, 1,
        )
        result.judge_json = parse_judge_output(judge_text)

    # ------------------------------------------------------------------
    # Early-stop logic (operates on parsed JSON dicts)
    # ------------------------------------------------------------------

    @staticmethod
    def _should_skip_dispute(revisions: dict[str, dict]) -> bool:
        """Check consensus by reading ``final_proposed_verdict`` from parsed revision dicts."""
        verdicts: set[str] = set()
        for data in revisions.values():
            v = data.get("final_proposed_verdict", "")
            if v:
                verdicts.add(v.upper())
        # Skip dispute only when all 3 agents agree on the same verdict
        return len(verdicts) == 1 and len(revisions) > 0

    # ------------------------------------------------------------------
    # SharedMemo builder (operates on parsed JSON dicts)
    # ------------------------------------------------------------------

    @staticmethod
    def _build_memo(proposals: dict[str, dict]) -> str:
        """Build a lightweight SharedMemo string from parsed proposal dicts."""
        verdicts: dict[str, str] = {}
        evidence_cited: set[str] = set()

        for role, data in proposals.items():
            role_name = role.value if hasattr(role, "value") else str(role)
            v = data.get("proposed_verdict", "")
            if v:
                verdicts[role_name] = v.upper()
            for eid in data.get("evidence_used", []):
                evidence_cited.add(eid)

        lines = ["=== Shared Memo ==="]
        if evidence_cited:
            lines.append(f"Evidence cited so far: {sorted(evidence_cited)}")
        if verdicts:
            lines.append(f"Current verdicts: {verdicts}")
        if len(set(verdicts.values())) > 1:
            lines.append("Contested: Agents disagree on the verdict.")
        return "\n".join(lines)


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------

def _extract_evidence_refs(text: str) -> list[str]:
    """Extract unique evidence IDs from free text (e.g. E1, HY01-E2)."""
    return sorted(set(_EVIDENCE_REF_RE.findall(text)))


def _wrap_cross_exam_message(
    turn_index: int,
    raw_text: str,
    source: str,
) -> str:
    """Wrap a raw cross-exam turn in the structured JSON envelope the
    frontend expects (``QuestionsMessage`` or ``AnswersMessage``).
    """
    refs = _extract_evidence_refs(raw_text)
    meta = _CROSS_EXAM_TURN_META[turn_index] if turn_index < len(_CROSS_EXAM_TURN_META) else {"type": "answer"}

    if meta["type"] == "question":
        envelope: dict[str, Any] = {
            "questions": [{
                "to": meta.get("target", source),
                "q": raw_text,
                "evidence_refs": refs,
            }],
        }
    else:
        envelope = {
            "answers": [{
                "q": "(cross-exam)",
                "a": raw_text,
                "evidence_refs": refs,
                "admission": "none",
            }],
        }
    return json.dumps(envelope, ensure_ascii=False)


def _wrap_dispute_question(raw_text: str) -> str:
    """Wrap a Skeptic dispute question in ``DisputeQuestionsMessage`` JSON."""
    return json.dumps({
        "questions": [{
            "q": raw_text,
            "evidence_refs": _extract_evidence_refs(raw_text),
        }],
    }, ensure_ascii=False)


def _wrap_dispute_answer(raw_text: str) -> str:
    """Wrap an Orthodox/Heretic dispute answer in ``DisputeAnswersMessage`` JSON."""
    return json.dumps({
        "answers": [{
            "q": "(dispute)",
            "a": raw_text,
            "evidence_refs": _extract_evidence_refs(raw_text),
            "admission": "none",
        }],
    }, ensure_ascii=False)


def _safe_content_parse(text: str) -> Any:
    """Try to parse JSON; return parsed dict on success or raw string on failure.

    Identical to ``runner.py``'s helper so the judge receives the same
    clean structure regardless of which controller produced the messages.
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text


def _try_parse_json(
    text: str,
    fallback: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Parse JSON from LLM output, handling fences and preamble.

    Tries in order:
      1. Direct ``json.loads(text)``
      2. Strip markdown ```` ```json ... ``` ```` fences
      3. Extract first ``{...}`` block from text
      4. Return *fallback* (or empty dict)
    """
    # 1. Direct parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # 2. Strip markdown fences
    stripped = text.strip()
    if stripped.startswith("```"):
        first_nl = stripped.find("\n")
        last_fence = stripped.rfind("```", first_nl)
        if first_nl != -1 and last_fence > first_nl:
            inner = stripped[first_nl + 1 : last_fence].strip()
            try:
                return json.loads(inner)
            except (json.JSONDecodeError, TypeError):
                pass

    # 3. Find first {...} block
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except (json.JSONDecodeError, TypeError):
            pass

    # 4. Fallback
    return dict(fallback) if fallback is not None else {}


def _extract_content(task_result: Any) -> str:
    """Extract text content from a TaskResult.

    For standalone ``agent.run()``, the last message is always the
    agent's ``chat_message`` (a ``TextMessage``), never a ``StopMessage``.
    """
    if hasattr(task_result, "messages") and task_result.messages:
        last = task_result.messages[-1]
        if hasattr(last, "content") and isinstance(last.content, str):
            return last.content
    return str(task_result)


async def _reset_agents(agents: list[AssistantAgent]) -> None:
    """Reset agent model contexts between phases."""
    ct = CancellationToken()
    for agent in agents:
        await agent.on_reset(ct)


async def _emit_msg(
    cb: Optional[OnMessageCallback],
    case_id: str,
    role: str,
    content: str,
    phase: str | DebatePhase,
    round_num: int,
) -> None:
    if cb is None:
        return
    phase_str = phase.value if isinstance(phase, DebatePhase) else phase
    evt = MessageEvent(
        case_id=case_id, role=role, content=content,
        phase=phase_str, round=round_num,
    )
    result = cb(evt)
    if asyncio.iscoroutine(result):
        await result


async def _emit_phase(
    cb: Optional[OnPhaseCallback],
    case_id: str,
    phase: DebatePhase,
) -> None:
    if cb is None:
        return
    result = cb(PhaseEvent(case_id=case_id, phase=phase.value))
    if asyncio.iscoroutine(result):
        await result
