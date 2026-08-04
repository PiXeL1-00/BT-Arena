"""Multi-turn debate controller (FSM-style).

Phase 0  Moderator setup (no LLM)
Phase 1  Independent proposals (3 parallel)
Phase 2  Cross-exam (7 sequential)
Phase 3  Revision (3 + early-stop check)
Phase 3.5  Dispute (optional, 3 calls if agents still disagree)
Phase 4  Judge (1 call, TOML-based)
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Callable, Optional, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.domain.schemas import DebateRole, VerdictEnum
from app.infra.llm.base import BaseLLMClient

from .prompts import (
    case_packet_text,
    cross_exam_answer_prompt,
    cross_exam_question_prompt,
    cross_exam_question_skeptic_prompt,
    dispute_answer_prompt,
    dispute_question_prompt,
    format_evidence,
    judge_prompt,
    proposal_prompt,
    proposal_retry_prompt,
    revision_prompt,
    toml_retry_suffix,
)
from .schemas import (
    AdmissionLevel,
    AnswersMessage,
    DebateMessage,
    DebatePhase,
    DebateResult,
    DebateTarget,
    DisputeAnswersMessage,
    DisputeQuestionsMessage,
    FALLBACK_ANSWER,
    FALLBACK_JUDGE_REASONING,
    FALLBACK_QUESTION,
    LogMessageType,
    MessageEvent,
    OnMessageCallback,
    OnPhaseCallback,
    PhaseEvent,
    Proposal,
    Revision,
    QuestionsMessage,
    SharedMemo,
)
from .toml_serde import dict_to_toml, parse_judge_output, toml_to_dict

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

DEFAULT_EARLY_STOP_JACCARD = 0.4
MAX_DISPUTE_STEPS = 1


class DebateController:
    """Full multi-turn debate for one case + one model."""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        model_key: str,
        *,
        early_stop_jaccard: float = DEFAULT_EARLY_STOP_JACCARD,
    ) -> None:
        self._llm = llm_client
        self._model_key = model_key
        self._early_stop_jaccard = early_stop_jaccard

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
        case_pkt = case_packet_text(claim=claim, topic=topic, evidence_text=evidence_text)
        valid_eids = {ep["eid"] for ep in evidence_packets}

        # phase 0: setup
        await self._emit_phase(on_phase, case_id, DebatePhase.SETUP)

        # phase 1: independent proposals
        await self._emit_phase(on_phase, case_id, DebatePhase.INDEPENDENT)
        proposals = await self._phase_independent(
            case_id=case_id, case_pkt=case_pkt,
            result=result, on_message=on_message,
        )

        # phase 2: cross-exam
        await self._emit_phase(on_phase, case_id, DebatePhase.CROSS_EXAM)
        cross_exam_log = await self._phase_cross_exam(
            case_id=case_id, case_pkt=case_pkt,
            proposals=proposals, result=result, on_message=on_message,
        )

        # phase 3: revision
        await self._emit_phase(on_phase, case_id, DebatePhase.REVISION)
        revisions, memo = await self._phase_revision(
            case_id=case_id, case_pkt=case_pkt,
            proposals=proposals, cross_exam_log=cross_exam_log,
            result=result, on_message=on_message,
        )

        # phase 3.5: dispute (only if not converged)
        if not self._should_early_stop(revisions):
            await self._emit_phase(on_phase, case_id, DebatePhase.DISPUTE)
            await self._phase_dispute(
                case_id=case_id, case_pkt=case_pkt,
                revisions=revisions, memo=memo,
                result=result, on_message=on_message,
            )

        # phase 4: judge
        await self._emit_phase(on_phase, case_id, DebatePhase.JUDGE)
        await self._phase_judge(
            case_id=case_id, claim=claim, topic=topic,
            evidence_text=evidence_text,
            result=result, on_message=on_message,
        )

        result.total_latency_ms = int((time.perf_counter() - t0) * 1000)
        logger.info(
            "debate done case=%s model=%s cost=%.6f latency=%dms",
            case_id, self._model_key, result.total_cost, result.total_latency_ms,
        )
        return result

    # --- phase 1: proposals (parallel) ---

    async def _phase_independent(
        self, *, case_id: str, case_pkt: str,
        result: DebateResult, on_message: Optional[OnMessageCallback],
    ) -> dict[str, Proposal]:
        roles = [DebateRole.ORTHODOX, DebateRole.HERETIC, DebateRole.SKEPTIC]

        async def _get_proposal(role: str) -> tuple[str, Proposal, float]:
            prompt = proposal_prompt(role=role, case_packet=case_pkt)
            parsed, raw, cost = await self._call_structured(
                prompt=prompt, schema_cls=Proposal,
                retry_prompt_fn=lambda bad: proposal_retry_prompt(
                    role=role, case_packet=case_pkt, failed_output=bad,
                ),
            )
            raw_json = parsed.model_dump_json()
            await self._emit_msg(on_message, case_id, role, raw_json, DebatePhase.INDEPENDENT, 1)
            return role, parsed, cost

        gathered = await asyncio.gather(*[_get_proposal(r) for r in roles])

        proposals: dict[str, Proposal] = {}
        for role, parsed, cost in gathered:
            raw_json = parsed.model_dump_json()
            proposals[role] = parsed
            result.total_cost += cost
            result.messages.append(DebateMessage(role, raw_json, DebatePhase.INDEPENDENT, 1))

        return proposals

    # --- phase 2: cross-exam (7 steps) ---

    async def _phase_cross_exam(
        self, *, case_id: str, case_pkt: str,
        proposals: dict[str, Proposal],
        result: DebateResult, on_message: Optional[OnMessageCallback],
    ) -> list[dict[str, Any]]:
        log: list[dict[str, Any]] = []
        memo = self._build_memo_from_proposals(proposals)
        memo_text = memo.to_context_str()

        o_toml = _model_to_toml(proposals[DebateRole.ORTHODOX])
        h_toml = _model_to_toml(proposals[DebateRole.HERETIC])
        s_toml = _model_to_toml(proposals[DebateRole.SKEPTIC])

        step = 0
        _O = DebateRole.ORTHODOX.value
        _H = DebateRole.HERETIC.value
        _S = DebateRole.SKEPTIC.value
        _BOTH = DebateTarget.BOTH.value
        _Q = LogMessageType.QUESTIONS.value
        _A = LogMessageType.ANSWERS.value

        # 2A: Orthodox asks Heretic
        step += 1
        q_oh = await self._cross_exam_step(
            case_id=case_id, case_pkt=case_pkt,
            asker=_O, target=_H, asker_toml=o_toml, target_toml=h_toml,
            memo_text=memo_text, result=result, on_message=on_message, step=step,
        )
        log.append({"from": _O, "to": _H, "type": _Q, "data": q_oh})

        # 2B: Heretic answers
        step += 1
        a_ho = await self._answer_step(
            case_id=case_id, case_pkt=case_pkt,
            answerer=_H, questions_toml=q_oh, own_toml=h_toml,
            memo_text=memo_text, result=result, on_message=on_message, step=step,
        )
        log.append({"from": _H, "to": _O, "type": _A, "data": a_ho})

        # 2C: Heretic asks Orthodox
        step += 1
        q_ho = await self._cross_exam_step(
            case_id=case_id, case_pkt=case_pkt,
            asker=_H, target=_O, asker_toml=h_toml, target_toml=o_toml,
            memo_text=memo_text, result=result, on_message=on_message, step=step,
        )
        log.append({"from": _H, "to": _O, "type": _Q, "data": q_ho})

        # 2D: Orthodox answers
        step += 1
        a_oh = await self._answer_step(
            case_id=case_id, case_pkt=case_pkt,
            answerer=_O, questions_toml=q_ho, own_toml=o_toml,
            memo_text=memo_text, result=result, on_message=on_message, step=step,
        )
        log.append({"from": _O, "to": _H, "type": _A, "data": a_oh})

        # 2E: Skeptic asks Both
        step += 1
        q_sk = await self._skeptic_question_step(
            case_id=case_id, case_pkt=case_pkt,
            orthodox_toml=o_toml, heretic_toml=h_toml,
            memo_text=memo_text, result=result, on_message=on_message, step=step,
        )
        log.append({"from": _S, "to": _BOTH, "type": _Q, "data": q_sk})

        # 2F: Orthodox answers Skeptic
        step += 1
        a_os = await self._answer_step(
            case_id=case_id, case_pkt=case_pkt,
            answerer=_O, questions_toml=q_sk, own_toml=o_toml,
            memo_text=memo_text, result=result, on_message=on_message, step=step,
        )
        log.append({"from": _O, "to": _S, "type": _A, "data": a_os})

        # 2G: Heretic answers Skeptic
        step += 1
        a_hs = await self._answer_step(
            case_id=case_id, case_pkt=case_pkt,
            answerer=_H, questions_toml=q_sk, own_toml=h_toml,
            memo_text=memo_text, result=result, on_message=on_message, step=step,
        )
        log.append({"from": _H, "to": _S, "type": _A, "data": a_hs})

        return log

    async def _cross_exam_step(
        self, *, case_id: str, case_pkt: str,
        asker: str, target: str,
        asker_toml: str, target_toml: str,
        memo_text: str, result: DebateResult,
        on_message: Optional[OnMessageCallback], step: int,
    ) -> str:
        prompt = cross_exam_question_prompt(
            asker=asker, target=target, case_packet=case_pkt,
            asker_proposal_toml=asker_toml, target_proposal_toml=target_toml,
            memo_text=memo_text,
        )
        parsed, raw, cost = await self._call_structured(prompt=prompt, schema_cls=QuestionsMessage)
        raw_json = parsed.model_dump_json()
        result.total_cost += cost
        result.messages.append(DebateMessage(asker, raw_json, DebatePhase.CROSS_EXAM, step))
        await self._emit_msg(on_message, case_id, asker, raw_json, DebatePhase.CROSS_EXAM, step)
        return _model_to_toml(parsed)

    async def _skeptic_question_step(
        self, *, case_id: str, case_pkt: str,
        orthodox_toml: str, heretic_toml: str,
        memo_text: str, result: DebateResult,
        on_message: Optional[OnMessageCallback], step: int,
    ) -> str:
        prompt = cross_exam_question_skeptic_prompt(
            case_packet=case_pkt,
            orthodox_proposal_toml=orthodox_toml,
            heretic_proposal_toml=heretic_toml,
            memo_text=memo_text,
        )
        parsed, raw, cost = await self._call_structured(prompt=prompt, schema_cls=QuestionsMessage)
        raw_json = parsed.model_dump_json()
        result.total_cost += cost
        result.messages.append(DebateMessage(DebateRole.SKEPTIC, raw_json, DebatePhase.CROSS_EXAM, step))
        await self._emit_msg(on_message, case_id, DebateRole.SKEPTIC, raw_json, DebatePhase.CROSS_EXAM, step)
        return _model_to_toml(parsed)

    async def _answer_step(
        self, *, case_id: str, case_pkt: str,
        answerer: str, questions_toml: str, own_toml: str,
        memo_text: str, result: DebateResult,
        on_message: Optional[OnMessageCallback], step: int,
    ) -> str:
        prompt = cross_exam_answer_prompt(
            answerer=answerer, questions_toml=questions_toml,
            case_packet=case_pkt, own_proposal_toml=own_toml,
            memo_text=memo_text,
        )
        parsed, raw, cost = await self._call_structured(prompt=prompt, schema_cls=AnswersMessage)
        raw_json = parsed.model_dump_json()
        result.total_cost += cost
        result.messages.append(DebateMessage(answerer, raw_json, DebatePhase.CROSS_EXAM, step))
        await self._emit_msg(on_message, case_id, answerer, raw_json, DebatePhase.CROSS_EXAM, step)
        return _model_to_toml(parsed)

    # --- phase 3: revision ---

    async def _phase_revision(
        self, *, case_id: str, case_pkt: str,
        proposals: dict[str, Proposal],
        cross_exam_log: list[dict[str, Any]],
        result: DebateResult, on_message: Optional[OnMessageCallback],
    ) -> tuple[dict[str, Revision], SharedMemo]:
        cross_summary = dict_to_toml({"exchange": cross_exam_log})
        memo = self._build_memo_from_proposals(proposals)
        memo_text = memo.to_context_str()

        revisions: dict[str, Revision] = {}
        for idx, role in enumerate([DebateRole.ORTHODOX, DebateRole.HERETIC, DebateRole.SKEPTIC], 1):
            prompt = revision_prompt(
                role=role, case_packet=case_pkt,
                own_proposal_toml=_model_to_toml(proposals[role]),
                cross_exam_summary=cross_summary, memo_text=memo_text,
            )
            parsed, raw, cost = await self._call_structured(prompt=prompt, schema_cls=Revision)
            raw_json = parsed.model_dump_json()
            revisions[role] = parsed
            result.total_cost += cost
            result.messages.append(DebateMessage(role, raw_json, DebatePhase.REVISION, idx))
            await self._emit_msg(on_message, case_id, role, raw_json, DebatePhase.REVISION, idx)

        return revisions, self._build_memo_from_revisions(revisions)

    # --- phase 3.5: dispute ---

    async def _phase_dispute(
        self, *, case_id: str, case_pkt: str,
        revisions: dict[str, Revision], memo: SharedMemo,
        result: DebateResult, on_message: Optional[OnMessageCallback],
    ) -> None:
        rev_summary = dict_to_toml({r: v.model_dump() for r, v in revisions.items()})
        memo_text = memo.to_context_str()

        # skeptic question
        prompt_q = dispute_question_prompt(
            case_packet=case_pkt, revisions_summary=rev_summary, memo_text=memo_text,
        )
        q_parsed, _, cost_q = await self._call_structured(prompt=prompt_q, schema_cls=DisputeQuestionsMessage)
        q_json = q_parsed.model_dump_json()
        q_toml = _model_to_toml(q_parsed)
        result.total_cost += cost_q
        result.messages.append(DebateMessage(DebateRole.SKEPTIC, q_json, DebatePhase.DISPUTE, 1))
        await self._emit_msg(on_message, case_id, DebateRole.SKEPTIC, q_json, DebatePhase.DISPUTE, 1)

        # orthodox + heretic answer
        for step, role in enumerate([DebateRole.ORTHODOX, DebateRole.HERETIC], 2):
            prompt_a = dispute_answer_prompt(
                answerer=role, case_packet=case_pkt,
                dispute_question_toml=q_toml,
                own_revision_toml=_model_to_toml(revisions[role]),
                memo_text=memo_text,
            )
            a_parsed, _, cost_a = await self._call_structured(prompt=prompt_a, schema_cls=DisputeAnswersMessage)
            a_json = a_parsed.model_dump_json()
            result.total_cost += cost_a
            result.messages.append(DebateMessage(role, a_json, DebatePhase.DISPUTE, step))
            await self._emit_msg(on_message, case_id, role, a_json, DebatePhase.DISPUTE, step)

    # --- phase 4: judge ---

    async def _phase_judge(
        self, *, case_id: str, claim: str, topic: str,
        evidence_text: str, result: DebateResult,
        on_message: Optional[OnMessageCallback],
    ) -> None:
        structured = [
            {"role": msg.role, "phase": msg.phase, "round": msg.round,
             "content": _safe_content_parse(msg.content)}
            for msg in result.messages
        ]

        prompt = judge_prompt(
            claim=claim, topic=topic,
            evidence_text=evidence_text, structured_debate=structured,
        )
        judge_resp = await self._llm.complete(prompt, temperature=0.0)
        result.total_cost += judge_resp.cost_estimate
        result.messages.append(DebateMessage(DebateRole.JUDGE, judge_resp.text, DebatePhase.JUDGE, 1))
        await self._emit_msg(on_message, case_id, DebateRole.JUDGE, judge_resp.text, DebatePhase.JUDGE, 1)

        result.judge_json = parse_judge_output(judge_resp.text)

    # --- early-stop logic ---

    def _should_early_stop(self, revisions: dict[str, Revision]) -> bool:
        verdicts = {r: v.final_proposed_verdict for r, v in revisions.items()}
        unique = set(verdicts.values())

        # unanimous + decent evidence overlap
        if len(unique) == 1:
            ev_sets = [set(v.evidence_used) for v in revisions.values()]
            if self._jaccard(ev_sets) >= self._early_stop_jaccard:
                return True

        # skeptic + one side agree, dissenter has only soft objections
        skeptic_v = verdicts.get(DebateRole.SKEPTIC)
        for ally, dissenter in [
            (DebateRole.ORTHODOX, DebateRole.HERETIC),
            (DebateRole.HERETIC, DebateRole.ORTHODOX),
        ]:
            if verdicts.get(ally) == skeptic_v and verdicts.get(dissenter) != skeptic_v:
                d_rev = revisions[dissenter]
                no_strong_counter = (
                    not d_rev.remaining_disagreements
                    or all("uncertain" in pt.lower() for pt in d_rev.remaining_disagreements)
                )
                if no_strong_counter:
                    return True

        return False

    @staticmethod
    def _jaccard(sets: list[set[str]]) -> float:
        if not sets:
            return 0.0
        union = set().union(*sets)
        if not union:
            return 0.0
        intersection = sets[0].intersection(*sets[1:])
        return len(intersection) / len(union)

    # --- memo builders ---

    @staticmethod
    def _build_memo_from_proposals(proposals: dict[str, Proposal]) -> SharedMemo:
        all_eids: set[str] = set()
        verdicts: dict[str, str] = {}
        contested: list[str] = []

        for role, p in proposals.items():
            all_eids.update(p.evidence_used)
            verdicts[role] = p.proposed_verdict

        if len(set(verdicts.values())) > 1:
            contested.append(f"Verdict disagreement: {verdicts}")

        return SharedMemo(all_evidence_cited=all_eids, verdicts_by_role=verdicts, contested_points=contested)

    @staticmethod
    def _build_memo_from_revisions(revisions: dict[str, Revision]) -> SharedMemo:
        all_eids: set[str] = set()
        verdicts: dict[str, str] = {}
        contested: list[str] = []

        for role, r in revisions.items():
            all_eids.update(r.evidence_used)
            verdicts[role] = r.final_proposed_verdict
            contested.extend(r.remaining_disagreements)

        return SharedMemo(all_evidence_cited=all_eids, verdicts_by_role=verdicts, contested_points=contested)

    # --- structured LLM call with one retry ---

    async def _call_structured(
        self, *, prompt: str, schema_cls: type[T],
        retry_prompt_fn: Optional[Callable[[str], str]] = None,
    ) -> tuple[T, str, float]:
        total_cost = 0.0

        resp = await self._llm.complete(prompt, temperature=0.0)
        total_cost += resp.cost_estimate
        raw = resp.text

        parsed = _try_parse(raw, schema_cls)
        if parsed is not None:
            return parsed, raw, total_cost

        # one retry
        logger.warning("couldn't parse %s, retrying... raw: %s", schema_cls.__name__, raw[:200])
        if retry_prompt_fn:
            retry_prompt = retry_prompt_fn(raw)
        else:
            retry_prompt = prompt + toml_retry_suffix(
                failed_output=raw, schema_hint=str(schema_cls.model_json_schema()),
            )

        resp2 = await self._llm.complete(retry_prompt, temperature=0.0)
        total_cost += resp2.cost_estimate
        raw2 = resp2.text

        parsed2 = _try_parse(raw2, schema_cls)
        if parsed2 is not None:
            return parsed2, raw2, total_cost

        # gave up -- use safe defaults
        logger.error("gave up parsing %s after retry, using safe defaults", schema_cls.__name__)
        fallback = _build_fallback(schema_cls)
        return fallback, raw2, total_cost

    # --- emit helpers ---

    @staticmethod
    async def _emit_msg(
        cb: Optional[OnMessageCallback], case_id: str,
        role: str, content: str, phase: str | DebatePhase, round_num: int,
    ) -> None:
        if cb is None:
            return
        phase_str = phase.value if isinstance(phase, DebatePhase) else phase
        evt = MessageEvent(case_id=case_id, role=role, content=content, phase=phase_str, round=round_num)
        await _maybe_await(cb(evt))

    @staticmethod
    async def _emit_phase(
        cb: Optional[OnPhaseCallback], case_id: str, phase: DebatePhase,
    ) -> None:
        if cb is None:
            return
        await _maybe_await(cb(PhaseEvent(case_id=case_id, phase=phase.value)))


# --- module helpers ---

def _model_to_toml(model: BaseModel) -> str:
    return dict_to_toml(model.model_dump())


# Module-level constants for admission values (used in multiple places)
_ADM_NONE = AdmissionLevel.NONE.value
_ADM_INSUFFICIENT = AdmissionLevel.INSUFFICIENT.value


def _ensure_admission_field(data: dict[str, Any]) -> None:
    """Ensure admission field is present in answers arrays.
    
    This defensive check ensures that even if TOML parsing omits the admission
    field, we set it to a default value before Pydantic validation.
    """
    # Handle AnswersMessage format: {"answers": [{"q": "...", "a": "...", ...}, ...]}
    if "answers" in data and isinstance(data["answers"], list):
        for answer in data["answers"]:
            if isinstance(answer, dict) and "admission" not in answer:
                answer["admission"] = _ADM_NONE
            elif isinstance(answer, dict) and answer.get("admission") is None:
                answer["admission"] = _ADM_NONE
    
    # Handle DisputeAnswersMessage format (same structure)
    # The check above should handle both cases


def _try_parse(raw: str, schema_cls: type[T]) -> Optional[T]:
    try:
        data = toml_to_dict(raw)
        # Ensure admission field is set for Answer/DisputeAnswer models
        # This handles cases where TOML parsing omits the field
        _ensure_admission_field(data)
        return schema_cls.model_validate(data)
    except (ValueError, ValidationError):
        return None


def _build_fallback(schema_cls: type[T]) -> T:
    _insuf = VerdictEnum.INSUFFICIENT.value
    _both = DebateTarget.BOTH.value

    if schema_cls is Proposal:
        return schema_cls.model_validate({  # type: ignore[return-value]
            "proposed_verdict": _insuf, "evidence_used": [],
            "key_points": [FALLBACK_JUDGE_REASONING],
            "uncertainties": [], "what_would_change_my_mind": [],
        })
    if schema_cls is QuestionsMessage:
        return schema_cls.model_validate({  # type: ignore[return-value]
            "questions": [{"to": _both, "q": FALLBACK_QUESTION, "evidence_refs": []}],
        })
    if schema_cls is AnswersMessage:
        return schema_cls.model_validate({  # type: ignore[return-value]
            "answers": [{"q": "?", "a": FALLBACK_ANSWER, "evidence_refs": [], "admission": _ADM_INSUFFICIENT}],
        })
    if schema_cls is Revision:
        return schema_cls.model_validate({  # type: ignore[return-value]
            "final_proposed_verdict": _insuf, "evidence_used": [],
            "what_i_changed": [], "remaining_disagreements": [], "confidence": 0.0,
        })
    if schema_cls is DisputeQuestionsMessage:
        return schema_cls.model_validate({  # type: ignore[return-value]
            "questions": [{"q": FALLBACK_QUESTION, "evidence_refs": []}],
        })
    if schema_cls is DisputeAnswersMessage:
        return schema_cls.model_validate({  # type: ignore[return-value]
            "answers": [{"q": "?", "a": FALLBACK_ANSWER, "evidence_refs": [], "admission": _ADM_INSUFFICIENT}],
        })
    raise ValueError(f"no fallback for {schema_cls.__name__}")



# Backward-compatible aliases (deprecated: use toml_serde.parse_judge_output directly)
_parse_judge_output = parse_judge_output


def _safe_content_parse(text: str) -> Any:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text


async def _maybe_await(val: Any) -> Any:
    if asyncio.iscoroutine(val) or asyncio.isfuture(val):
        return await val
    return val
