# AutoGen Integration for AIGalileoArena

Leverage Microsoft AutoGen's agentic framework to enhance the multi-agent debate system with built-in orchestration, memory, and tool-use capabilities.

> **Installed version**: `autogen-agentchat==0.7.5` / `autogen-core==0.7.5` / `autogen-ext==0.7.5`
> The original spec referenced 0.4; all API signatures below are verified against the **installed 0.7.5** packages.

## User Review Required

> [!IMPORTANT]
> **Non-Breaking**: The current `DebateController` is **not replaced**. A new `AutoGenDebateController` lives alongside it, activated by a feature flag (`USE_AUTOGEN_DEBATE=true`). Existing tests and behavior are untouched.

> [!CAUTION]
> **API Cost Implications**: AutoGen's `SelectorGroupChat` uses an **extra LLM call per turn** to choose the next speaker. With the cross-exam phase capped at 7 messages, expect ~7 additional selector calls on top of the agent calls. Budget accordingly.

---

## Deep-Scan Findings

### Current Architecture Summary

| Layer | Files | Purpose |
|-------|-------|---------|
| **LLM** | `infra/llm/base.py`, `factory.py`, 6 provider clients | `BaseLLMClient` Protocol → `complete(prompt) → LLMResponse` |
| **Debate** | `infra/debate/runner.py`, `schemas.py`, `prompts.py`, `toml_serde.py` | FSM-style 5-phase debate: setup → proposals → cross-exam → revision → dispute → judge |
| **Domain** | `core/domain/schemas.py`, `scoring.py` | `VerdictEnum`, `JudgeDecision`, `CaseScoreBreakdown`, deterministic + ML scoring |
| **ML** | `infra/ml/scorer.py`, `model_registry.py`, `exemplars.py` | ONNX NLI + embedding scoring (grounding, falsifiability, deference, refusal) |
| **Usecase** | `usecases/run_eval.py` | `RunEvalUsecase` orchestrates `DebateController` → scoring → persistence |
| **API** | `api/routes/runs.py`, `datasets.py` | FastAPI REST + SSE streaming |
| **DB** | `infra/db/models.py`, `repository.py` | SQLAlchemy async ORM (runs, messages, results, events, cache slots) |
| **Config** | `config.py` | Pydantic-settings, `.env` based |

### Key Contracts the AutoGen Path Must Honour

1. **`DebateResult` dataclass** (`runner.py:72-78`): `messages: list[DebateMessage]`, `judge_json: dict`, `total_latency_ms`, `total_cost`
2. **`MessageEvent` / `PhaseEvent`** callbacks (`schemas.py:136-148`): must emit per-message and per-phase events for SSE + DB persistence
3. **`JudgeDecision` Pydantic model** (`core/domain/schemas.py:134-138`): `verdict: VerdictEnum`, `confidence: float`, `evidence_used: list[str]`, `reasoning: str`
4. **TOML judge output**: The existing scoring pipeline expects `toml_to_dict(judge_text)` → dict with verdict/confidence/evidence_used/reasoning keys
5. **Cost tracking**: Every LLM call must accumulate `cost_estimate` into `DebateResult.total_cost`

### AutoGen 0.7.5 API Surface (Verified)

| AutoGen Class | Import Path | Key Signature |
|---------------|-------------|---------------|
| `ChatCompletionClient` | `autogen_core.models` | Abstract: `create(messages: Seq[LLMMessage], *, tools, json_output, ...) → CreateResult` |
| `CreateResult` | `autogen_core.models` | `content: str\|list[FunctionCall]`, `usage: RequestUsage`, `finish_reason`, `cached` |
| `RequestUsage` | `autogen_core.models` | `prompt_tokens: int`, `completion_tokens: int` |
| `ModelInfo` | `autogen_core.models` | `vision`, `function_calling`, `json_output`, `family`, `structured_output` |
| `AssistantAgent` | `autogen_agentchat.agents` | `name`, `model_client`, `tools`, `system_message`, `description`, `output_content_type` |
| `SelectorGroupChat` | `autogen_agentchat.teams` | `participants`, `model_client`, `selector_prompt`, `termination_condition`, `max_turns`, `selector_func` |
| `FunctionTool` | `autogen_core.tools` | `func: Callable`, `description: str`, `name: str\|None` |
| `MaxMessageTermination` | `autogen_agentchat.conditions` | `max_messages: int` |
| `TaskResult` | `autogen_agentchat.base` | `messages: list`, `stop_reason: str\|None` |
| `OpenAIChatCompletionClient` | `autogen_ext.models.openai` | Built-in for OpenAI (kwargs-based config) |

**⚠️ Doc corrections vs original spec:**
- `FunctionTool` is in `autogen_core.tools`, NOT `autogen_agentchat.tools`
- `ChatCompletionClient.create()` requires implementing 9 abstract methods (not just `create`)
- `AssistantAgent.run()` returns `TaskResult` (not raw text)
- `SelectorGroupChat` uses an **extra model_client** call per turn to pick the next speaker

---

## Architecture Decision Records

### ADR-1: Adapter vs Native AutoGen Clients

**Decision**: Use an **adapter** wrapping `BaseLLMClient` → `ChatCompletionClient`.

**Rationale**:
- Reuses existing per-provider cost estimation, retry logic, and timeout handling
- Works uniformly for all 6 providers (OpenAI, Anthropic, Mistral, DeepSeek, Gemini, Grok)
- AutoGen's native `OpenAIChatCompletionClient` only covers OpenAI-compatible APIs
- Maintains compatibility with the existing `MockLLMClient` test infrastructure
- **Single model per run** design: all 4 agents share one `GalileoModelClient` instance

### ADR-2: Output Format

**Decision**: Keep **TOML** for the Judge phase output (consistency with scoring pipeline). Allow natural language for debate phases.

**Rationale**:
- The scoring pipeline (`run_eval.py:179`) expects `JudgeDecision(**debate.judge_json)` from TOML/JSON parsing
- AutoGen's `output_content_type` could enforce JSON, but TOML is the established format
- Debate arguments benefit from natural language (richer cross-examination)

### ADR-3: SelectorGroupChat for Cross-Exam

**Decision**: Use `SelectorGroupChat` with a custom `selector_func` (deterministic, no LLM) for cross-exam to maintain the fixed turn order while gaining AutoGen's message management.

**Rationale**:
- The original spec uses `model_client` in `SelectorGroupChat`, which adds **7 extra LLM calls** just for speaker selection
- A deterministic `selector_func` preserves the existing turn order (O→H, H→O, S→Both, etc.) with **zero extra cost**
- Falls back to LLM-based selection only if `autogen_dynamic_selector=true` is set

### ADR-4: Phase Isolation

**Decision**: Run each debate phase as a **separate** AutoGen interaction (not one continuous group chat).

**Rationale**:
- Matches the existing phase-based architecture (emit `PhaseEvent` per phase)
- Allows cost/latency tracking per phase
- Enables consensus check between revision and judge (same as current early-stop logic)
- Agent context is passed explicitly between phases (no hidden state leakage)

---

## Proposed Changes

### Component 1: AutoGen Model Client Adapter

#### [NEW] `backend/app/infra/llm/autogen_model_client.py`

Adapts the existing `BaseLLMClient` to AutoGen's `ChatCompletionClient` interface (9 abstract methods).

```python
"""Adapter: BaseLLMClient → AutoGen ChatCompletionClient."""
from __future__ import annotations

import asyncio
from typing import Any, Mapping, Optional, Sequence, Union

from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    ModelFamily,
    ModelInfo,
    RequestUsage,
    SystemMessage,
    UserMessage,
)
from autogen_core.tools import Tool, ToolSchema
from pydantic import BaseModel

from app.infra.llm.base import BaseLLMClient


class GalileoModelClient(ChatCompletionClient):
    """Wrap an existing BaseLLMClient for AutoGen compatibility.

    Design:
    - Flattens AutoGen's message list into a single prompt string
    - Delegates to the existing provider's `complete()` method
    - Tracks cumulative token usage for cost reporting
    """

    def __init__(
        self,
        base_client: BaseLLMClient,
        *,
        model_name: str = "unknown",
        provider: str = "unknown",
    ) -> None:
        self._client = base_client
        self._model_name = model_name
        self._provider = provider
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._total_cost = 0.0

    # --- Required abstract methods ---

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool | type[BaseModel]] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token=None,
    ) -> CreateResult:
        # Flatten messages into a single prompt
        prompt = self._messages_to_prompt(messages)

        # Delegate to existing BaseLLMClient
        resp = await self._client.complete(prompt, temperature=0.0)

        # Rough token estimate (4 chars ≈ 1 token)
        est_prompt_tokens = len(prompt) // 4
        est_completion_tokens = len(resp.text) // 4
        self._total_prompt_tokens += est_prompt_tokens
        self._total_completion_tokens += est_completion_tokens
        self._total_cost += resp.cost_estimate

        usage = RequestUsage(
            prompt_tokens=est_prompt_tokens,
            completion_tokens=est_completion_tokens,
        )

        return CreateResult(
            finish_reason="stop",
            content=resp.text,
            usage=usage,
            cached=False,
        )

    async def create_stream(self, messages, **kwargs):
        raise NotImplementedError("Streaming not supported by GalileoModelClient")

    def count_tokens(self, messages, **kwargs) -> int:
        return sum(len(self._msg_to_str(m)) // 4 for m in messages)

    def remaining_tokens(self, messages, **kwargs) -> int:
        return 4096 - self.count_tokens(messages)

    @property
    def total_usage(self) -> RequestUsage:
        return RequestUsage(
            prompt_tokens=self._total_prompt_tokens,
            completion_tokens=self._total_completion_tokens,
        )

    @property
    def actual_usage(self) -> RequestUsage:
        return self.total_usage

    @property
    def capabilities(self) -> ModelInfo:
        return self.model_info

    @property
    def model_info(self) -> ModelInfo:
        return ModelInfo(
            vision=False,
            function_calling=False,
            json_output=True,
            family=ModelFamily.UNKNOWN,
            structured_output=False,
        )

    async def close(self) -> None:
        pass

    # --- Cost accessor (not part of AutoGen interface) ---

    @property
    def accumulated_cost(self) -> float:
        return self._total_cost

    def reset_usage(self) -> None:
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._total_cost = 0.0

    # --- Helpers ---

    @staticmethod
    def _messages_to_prompt(messages: Sequence[LLMMessage]) -> str:
        parts: list[str] = []
        for msg in messages:
            parts.append(GalileoModelClient._msg_to_str(msg))
        return "\n\n".join(parts)

    @staticmethod
    def _msg_to_str(msg: LLMMessage) -> str:
        if isinstance(msg, SystemMessage):
            return f"[System]\n{msg.content}"
        if isinstance(msg, UserMessage):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            return f"[User]\n{content}"
        if isinstance(msg, AssistantMessage):
            return f"[Assistant]\n{msg.content}"
        return str(msg)
```

**Impact**: New file only. No existing files modified.

**Edge Cases**:
- Messages with image content → falls back to `str(msg.content)` (no vision support flagged)
- `create_stream` → raises `NotImplementedError` (agents don't use streaming)
- Token counting is approximate (4 chars ≈ 1 token); sufficient for `remaining_tokens` guard

---

### Component 2: Core AutoGen Agents Layer

#### [NEW] `backend/app/infra/debate/autogen_agents.py`

Define debate agents using AutoGen's `AssistantAgent`. System prompts are derived from the existing `prompts.py` templates but reformulated for conversational (non-TOML) output during debate phases.

```python
"""AutoGen agent definitions for adversarial debate roles."""
from __future__ import annotations

from typing import Sequence

from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import ChatCompletionClient
from autogen_core.tools import FunctionTool

from app.core.domain.schemas import DebateRole


def create_debate_agents(
    model_client: ChatCompletionClient,
    *,
    claim: str,
    topic: str,
    evidence_text: str,
    tools: Sequence[FunctionTool] | None = None,
) -> dict[str, AssistantAgent]:
    """Create all 4 debate agents sharing the same model_client."""

    case_context = (
        f"Topic: {topic}\nClaim: {claim}\n\n{evidence_text}\n\n"
        "RULES: Use ONLY the evidence IDs provided. Do NOT introduce outside facts."
    )

    agent_configs = {
        DebateRole.ORTHODOX: {
            "name": "Orthodox",
            "description": "Argues FOR the claim using cited evidence.",
            "system_message": (
                f"You are the Orthodox agent in a structured adversarial debate.\n\n"
                f"{case_context}\n\n"
                "Your role: Steelman the MAJORITY interpretation supporting this claim. "
                "Argue FOR the claim using cited evidence IDs (e.g. [CL01-E1]). "
                "Be specific, cite sources, and address counterarguments."
            ),
        },
        DebateRole.HERETIC: {
            "name": "Heretic",
            "description": "Argues AGAINST the claim using cited evidence.",
            "system_message": (
                f"You are the Heretic agent in a structured adversarial debate.\n\n"
                f"{case_context}\n\n"
                "Your role: Steelman the MINORITY / opposing interpretation. "
                "Argue AGAINST or challenge the claim using cited evidence IDs. "
                "Expose weaknesses, gaps, and contradictions in the supporting evidence."
            ),
        },
        DebateRole.SKEPTIC: {
            "name": "Skeptic",
            "description": "Questions BOTH sides, identifies gaps and contradictions.",
            "system_message": (
                f"You are the Skeptic agent in a structured adversarial debate.\n\n"
                f"{case_context}\n\n"
                "Your role: Rigorously question BOTH sides. "
                "Identify gaps, unsupported assumptions, and contradictions. "
                "You are not a tiebreaker - you stress-test all arguments."
            ),
        },
        DebateRole.JUDGE: {
            "name": "Judge",
            "description": "Evaluates all arguments and renders a final verdict.",
            "system_message": (
                f"You are the Judge. Render a FINAL verdict on the claim.\n\n"
                f"{case_context}\n\n"
                "Evaluate ALL positions from the adversarial debate. "
                "Use ONLY the evidence IDs from the evidence pack.\n\n"
                "Output ONLY valid TOML with these fields:\n"
                'verdict = "SUPPORTED|REFUTED|INSUFFICIENT"\n'
                "confidence = 0.85\n"
                'evidence_used = ["E1", "E2"]\n'
                'reasoning = "brief explanation (1-3 sentences)"\n\n'
                "No extra text outside the TOML content."
            ),
        },
    }

    agents: dict[str, AssistantAgent] = {}
    for role, cfg in agent_configs.items():
        agent_tools = list(tools) if tools and role != DebateRole.JUDGE else None
        agents[role] = AssistantAgent(
            name=cfg["name"],
            model_client=model_client,
            system_message=cfg["system_message"],
            description=cfg["description"],
            tools=agent_tools,
        )
    return agents
```

**Impact**: New file only. Reuses `DebateRole` enum and evidence formatting conventions.

---

### Component 3: Adversarial Debate Flow

#### [NEW] `backend/app/infra/debate/autogen_debate_flow.py`

Orchestrates the 5-phase debate using AutoGen agents. Each phase runs as a separate interaction to maintain phase boundaries, cost tracking, and callback emission.

```python
"""AutoGen-powered adversarial debate flow with phased execution."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Optional

from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import SelectorGroupChat
from autogen_core.models import ChatCompletionClient

from app.core.domain.schemas import DebateRole, VerdictEnum
from app.infra.debate.prompts import format_evidence
from app.infra.debate.schemas import DebatePhase, MessageEvent, PhaseEvent
from app.infra.debate.toml_serde import toml_to_dict
from app.infra.llm.autogen_model_client import GalileoModelClient

from .autogen_agents import create_debate_agents
from .runner import (
    DebateMessage,
    DebateResult,
    OnMessageCallback,
    OnPhaseCallback,
    _fallback_judge,
    _parse_judge_output,
)

logger = logging.getLogger(__name__)

# Deterministic cross-exam turn order (mirrors existing FSM)
_CROSS_EXAM_ORDER = [
    DebateRole.ORTHODOX,   # Ask Heretic
    DebateRole.HERETIC,    # Answer
    DebateRole.HERETIC,    # Ask Orthodox
    DebateRole.ORTHODOX,   # Answer
    DebateRole.SKEPTIC,    # Ask Both
    DebateRole.ORTHODOX,   # Answer Skeptic
    DebateRole.HERETIC,    # Answer Skeptic
]


class AutoGenDebateController:
    """AutoGen-powered debate orchestrator.

    Maintains the same DebateResult contract as DebateController.
    Runs phases sequentially, using AutoGen agents within each phase.
    """

    def __init__(
        self,
        model_client: GalileoModelClient,
        model_key: str,
        *,
        max_cross_exam_messages: int = 7,
        enable_tools: bool = False,
    ) -> None:
        self._model_client = model_client
        self._model_key = model_key
        self._max_cross_exam = max_cross_exam_messages
        self._enable_tools = enable_tools

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

        # Create agents
        agents = create_debate_agents(
            self._model_client,
            claim=claim,
            topic=topic,
            evidence_text=evidence_text,
            tools=tools,
        )

        orthodox = agents[DebateRole.ORTHODOX]
        heretic = agents[DebateRole.HERETIC]
        skeptic = agents[DebateRole.SKEPTIC]
        judge = agents[DebateRole.JUDGE]

        # Phase 0: Setup
        await self._emit_phase(on_phase, case_id, DebatePhase.SETUP)

        # Phase 1: Independent proposals (parallel)
        await self._emit_phase(on_phase, case_id, DebatePhase.INDEPENDENT)
        proposals = await self._phase_proposals(
            case_id, claim, agents, result, on_message,
        )

        # Phase 2: Cross-examination (SelectorGroupChat or deterministic)
        await self._emit_phase(on_phase, case_id, DebatePhase.CROSS_EXAM)
        await self._phase_cross_exam(
            case_id, claim, proposals, agents, result, on_message,
        )

        # Phase 3: Revision (parallel)
        await self._emit_phase(on_phase, case_id, DebatePhase.REVISION)
        revisions = await self._phase_revision(
            case_id, claim, agents, result, on_message,
        )

        # Early-stop check: if all agents agree, skip dispute + judge
        if not self._should_skip_dispute(revisions):
            # Phase 3.5: Dispute
            await self._emit_phase(on_phase, case_id, DebatePhase.DISPUTE)
            await self._phase_dispute(
                case_id, claim, agents, result, on_message,
            )

        # Phase 4: Judge
        await self._emit_phase(on_phase, case_id, DebatePhase.JUDGE)
        await self._phase_judge(
            case_id, claim, topic, evidence_text,
            judge, result, on_message,
        )

        result.total_latency_ms = int((time.perf_counter() - t0) * 1000)
        result.total_cost = self._model_client.accumulated_cost
        logger.info(
            "autogen debate done case=%s model=%s cost=%.6f latency=%dms",
            case_id, self._model_key, result.total_cost, result.total_latency_ms,
        )
        return result

    # --- Phase implementations ---
    # (Each phase uses agent.run() independently, collecting messages)

    async def _phase_proposals(self, case_id, claim, agents, result, on_message):
        """Phase 1: Each agent independently proposes a position."""
        tasks = {
            DebateRole.ORTHODOX: f"Argue FOR this claim: {claim}. Cite evidence IDs. Be concise.",
            DebateRole.HERETIC: f"Argue AGAINST this claim: {claim}. Cite evidence IDs. Be concise.",
            DebateRole.SKEPTIC: f"Challenge BOTH sides on: {claim}. Cite evidence IDs. Be concise.",
        }
        proposals = {}
        results = await asyncio.gather(*[
            agents[role].run(task=task) for role, task in tasks.items()
        ])
        for idx, (role, _) in enumerate(tasks.items()):
            task_result = results[idx]
            content = self._extract_content(task_result)
            proposals[role] = content
            msg = DebateMessage(role.value, content, DebatePhase.INDEPENDENT, idx + 1)
            result.messages.append(msg)
            await self._emit_msg(on_message, case_id, role.value, content,
                                 DebatePhase.INDEPENDENT, idx + 1)
        return proposals

    async def _phase_cross_exam(self, case_id, claim, proposals, agents, result, on_message):
        """Phase 2: Cross-examination using SelectorGroupChat with deterministic selector."""
        debate_agents = [agents[DebateRole.ORTHODOX], agents[DebateRole.HERETIC], agents[DebateRole.SKEPTIC]]

        # Build context from proposals
        proposal_summary = "\n\n".join(
            f"**{role.value}** proposed:\n{text}" for role, text in proposals.items()
        )

        turn_idx = 0

        def deterministic_selector(messages) -> str | None:
            """Follow the fixed cross-exam turn order."""
            nonlocal turn_idx
            if turn_idx >= len(_CROSS_EXAM_ORDER):
                return None
            role = _CROSS_EXAM_ORDER[turn_idx]
            turn_idx += 1
            return role.value  # Agent name matches role value

        cross_exam_team = SelectorGroupChat(
            participants=debate_agents,
            model_client=self._model_client,
            termination_condition=MaxMessageTermination(max_messages=self._max_cross_exam),
            selector_func=deterministic_selector,
        )

        task = (
            f"Cross-examine each other's positions on: {claim}\n\n"
            f"Proposals:\n{proposal_summary}\n\n"
            "Ask probing questions and challenge weak arguments. Cite evidence."
        )

        chat_result = await cross_exam_team.run(task=task)

        for idx, msg in enumerate(chat_result.messages):
            content = msg.content if hasattr(msg, 'content') else str(msg)
            source = msg.source if hasattr(msg, 'source') else "Unknown"
            dm = DebateMessage(source, content, DebatePhase.CROSS_EXAM, idx + 1)
            result.messages.append(dm)
            await self._emit_msg(on_message, case_id, source, content,
                                 DebatePhase.CROSS_EXAM, idx + 1)

    async def _phase_revision(self, case_id, claim, agents, result, on_message):
        """Phase 3: Each agent revises their position."""
        debate_history = "\n".join(
            f"[{m.role}] {m.content[:500]}" for m in result.messages
        )
        task_template = (
            "The cross-examination is complete. Revise your stance on: {claim}\n\n"
            "Debate so far:\n{history}\n\n"
            "State your FINAL verdict (SUPPORTED / REFUTED / INSUFFICIENT), "
            "evidence used, what you changed, remaining disagreements, "
            "and confidence (0.0-1.0). Be concise."
        )
        revisions = {}
        roles = [DebateRole.ORTHODOX, DebateRole.HERETIC, DebateRole.SKEPTIC]
        results_list = await asyncio.gather(*[
            agents[role].run(
                task=task_template.format(claim=claim, history=debate_history[-3000])
            ) for role in roles
        ])
        for idx, role in enumerate(roles):
            content = self._extract_content(results_list[idx])
            revisions[role] = content
            dm = DebateMessage(role.value, content, DebatePhase.REVISION, idx + 1)
            result.messages.append(dm)
            await self._emit_msg(on_message, case_id, role.value, content,
                                 DebatePhase.REVISION, idx + 1)
        return revisions

    async def _phase_dispute(self, case_id, claim, agents, result, on_message):
        """Phase 3.5: Skeptic asks a decisive question, Orthodox and Heretic answer."""
        debate_history = "\n".join(
            f"[{m.role}] {m.content[:500]}" for m in result.messages
        )
        # Skeptic question
        q_result = await agents[DebateRole.SKEPTIC].run(
            task=(
                f"Agents still disagree on: {claim}\n\n"
                f"Debate so far:\n{debate_history[-2000:]}\n\n"
                "Ask exactly 1 final decisive question that could resolve the disagreement. "
                "Reference specific evidence."
            )
        )
        q_content = self._extract_content(q_result)
        result.messages.append(DebateMessage(DebateRole.SKEPTIC.value, q_content, DebatePhase.DISPUTE, 1))
        await self._emit_msg(on_message, case_id, DebateRole.SKEPTIC.value, q_content, DebatePhase.DISPUTE, 1)

        # Orthodox + Heretic answer
        for step, role in enumerate([DebateRole.ORTHODOX, DebateRole.HERETIC], 2):
            a_result = await agents[role].run(
                task=f"Answer the Skeptic's question:\n{q_content}\n\nCite evidence."
            )
            a_content = self._extract_content(a_result)
            result.messages.append(DebateMessage(role.value, a_content, DebatePhase.DISPUTE, step))
            await self._emit_msg(on_message, case_id, role.value, a_content, DebatePhase.DISPUTE, step)

    async def _phase_judge(self, case_id, claim, topic, evidence_text, judge, result, on_message):
        """Phase 4: Judge renders final verdict in TOML format."""
        structured = [
            {"role": msg.role, "phase": msg.phase, "round": msg.round,
             "content": msg.content[:1000]}
            for msg in result.messages
        ]
        from app.infra.debate.toml_serde import dict_to_toml
        debate_block = dict_to_toml({"entry": structured})

        judge_task = (
            f"You are the Judge. Render a FINAL verdict on the claim.\n\n"
            f"Topic: {topic}\nClaim: {claim}\n\n{evidence_text}\n\n"
            f"Structured debate transcript:\n{debate_block}\n\n"
            "Evaluate ALL positions, cross-examination results, and revisions.\n"
            "Use ONLY the evidence IDs from the evidence pack above.\n\n"
            "Output ONLY valid TOML with these fields:\n"
            'verdict = "SUPPORTED|REFUTED|INSUFFICIENT"\n'
            "confidence = 0.85\n"
            'evidence_used = ["E1", "E2"]\n'
            'reasoning = "brief explanation (1-3 sentences)"\n\n'
            "No extra text outside the TOML content."
        )

        judge_result = await judge.run(task=judge_task)
        judge_text = self._extract_content(judge_result)
        result.messages.append(
            DebateMessage(DebateRole.JUDGE.value, judge_text, DebatePhase.JUDGE, 1)
        )
        await self._emit_msg(on_message, case_id, DebateRole.JUDGE.value,
                             judge_text, DebatePhase.JUDGE, 1)
        result.judge_json = _parse_judge_output(judge_text)

    # --- Helpers ---

    @staticmethod
    def _extract_content(task_result) -> str:
        """Extract text content from TaskResult."""
        if hasattr(task_result, 'messages') and task_result.messages:
            last = task_result.messages[-1]
            if hasattr(last, 'content'):
                return last.content if isinstance(last.content, str) else str(last.content)
        return str(task_result)

    @staticmethod
    def _should_skip_dispute(revisions: dict) -> bool:
        """Check if all agents agree on the verdict."""
        verdicts = set()
        for text in revisions.values():
            lower = text.lower()
            if "supported" in lower:
                verdicts.add("SUPPORTED")
            elif "refuted" in lower:
                verdicts.add("REFUTED")
            elif "insufficient" in lower:
                verdicts.add("INSUFFICIENT")
        return len(verdicts) == 1

    @staticmethod
    async def _emit_msg(cb, case_id, role, content, phase, round_num):
        if cb is None:
            return
        phase_str = phase.value if hasattr(phase, 'value') else phase
        evt = MessageEvent(case_id=case_id, role=role, content=content,
                          phase=phase_str, round=round_num)
        result = cb(evt)
        if asyncio.iscoroutine(result):
            await result

    @staticmethod
    async def _emit_phase(cb, case_id, phase):
        if cb is None:
            return
        result = cb(PhaseEvent(case_id=case_id, phase=phase.value))
        if asyncio.iscoroutine(result):
            await result
```

**Impact**: New file. Imports from `runner.py` (shared types: `DebateMessage`, `DebateResult`, `_parse_judge_output`, `_fallback_judge`).

---

### Component 4: Evidence Retrieval Tools

#### [NEW] `backend/app/infra/debate/autogen_tools.py`

Provides `FunctionTool` wrappers that agents can call mid-conversation to query evidence.

```python
"""Evidence retrieval tools for AutoGen debate agents."""
from __future__ import annotations

from autogen_core.tools import FunctionTool


def build_evidence_tools(evidence_packets: list[dict]) -> list[FunctionTool]:
    """Build FunctionTool instances scoped to the given evidence packets."""

    # Build lookup maps
    evidence_by_id = {ep["eid"]: ep for ep in evidence_packets}

    def get_evidence(eid: str) -> str:
        """Retrieve evidence packet by ID. Returns summary, source, date."""
        ep = evidence_by_id.get(eid)
        if ep is None:
            return f"Evidence {eid} not found. Available: {list(evidence_by_id.keys())}"
        return f"[{ep['eid']}] {ep['summary']} (Source: {ep['source']}, Date: {ep['date']})"

    def list_evidence() -> str:
        """List all available evidence IDs and their summaries."""
        lines = [f"[{ep['eid']}] {ep['summary'][:80]}..." for ep in evidence_packets]
        return "\n".join(lines)

    def search_evidence(query: str) -> str:
        """Search evidence summaries for a keyword or phrase."""
        query_lower = query.lower()
        matches = [
            f"[{ep['eid']}] {ep['summary']}"
            for ep in evidence_packets
            if query_lower in ep["summary"].lower()
        ]
        if not matches:
            return f"No evidence matches '{query}'. Available IDs: {list(evidence_by_id.keys())}"
        return "\n".join(matches)

    return [
        FunctionTool(get_evidence, description="Retrieve a specific evidence packet by its ID"),
        FunctionTool(list_evidence, description="List all available evidence IDs and summaries"),
        FunctionTool(search_evidence, description="Search evidence summaries by keyword"),
    ]
```

**Impact**: New file only. Tools are injected into debate agents when `autogen_enable_tools=true`.

**Edge Cases**:
- Empty evidence packets → tools return helpful error messages
- Agents may ignore tools if model doesn't support function calling → gracefully degrades
- Judge agent intentionally excluded from tool use (must reason from debate transcript only)

---

### Component 5: Feature Flag Configuration

#### [MODIFY] `backend/app/config.py`

Add 3 new settings (backward-compatible defaults):

```python
# --- AutoGen debate mode ---
use_autogen_debate: bool = Field(
    default=False,
    description="Use AutoGen-powered debate orchestration instead of FSM controller",
)
autogen_max_cross_exam_messages: int = Field(
    default=7, ge=3, le=20,
    description="Max messages in AutoGen cross-examination phase",
)
autogen_enable_tools: bool = Field(
    default=False,
    description="Enable evidence retrieval tools for AutoGen debate agents",
)
```

**Impact**: Additive only. Default `use_autogen_debate=false` preserves existing behavior.

---

### Component 6: Integration with Runner + Usecase

#### [MODIFY] `backend/app/usecases/run_eval.py`

Add a feature flag check to select the appropriate debate controller:

```python
# In _run_case(), replace the controller creation:
if settings.use_autogen_debate:
    from app.infra.llm.autogen_model_client import GalileoModelClient
    from app.infra.debate.autogen_debate_flow import AutoGenDebateController
    
    autogen_client = GalileoModelClient(llm, model_name=model_cfg["model_name"], provider=model_cfg["provider"])
    controller = AutoGenDebateController(
        autogen_client, model_key,
        max_cross_exam_messages=settings.autogen_max_cross_exam_messages,
        enable_tools=settings.autogen_enable_tools,
    )
else:
    controller = DebateController(llm, model_key)
```

Both controllers expose the same `.run()` signature and return `DebateResult`.

**Impact**: Minimal change (5-line if/else block). Scoring, persistence, and SSE pipelines are completely untouched.

---

### Component 7: Integration Tests

#### [NEW] `backend/tests/test_autogen_debate.py`

Mirror the structure of `test_debate_runner.py` using a mock `ChatCompletionClient`:

**Test cases**:
1. `test_autogen_converging_debate` — All agents agree → dispute skipped → judge produces valid TOML
2. `test_autogen_diverging_debate` — Agents disagree → dispute phase runs → judge decides
3. `test_autogen_cost_tracking` — Verify `accumulated_cost` propagates to `DebateResult.total_cost`
4. `test_autogen_phase_callbacks` — All 6 phases emitted in correct order
5. `test_autogen_message_persistence` — All messages have role/phase/round populated
6. `test_autogen_fallback_judge_output` — Invalid judge TOML → fallback verdict used
7. `test_galileo_model_client_adapter` — Unit test the adapter: message flattening, cost accumulation, `model_info`

---

## File Inventory (Implemented)

| # | Action | File | Description |
|---|--------|------|-------------|
| 0 | **MODIFY** | `backend/app/infra/debate/schemas.py` | +`DebateMessage`, `DebateResult`, `OnMessageCallback`, `OnPhaseCallback` (moved from runner.py) |
| 0 | **MODIFY** | `backend/app/infra/debate/toml_serde.py` | +`parse_judge_output()`, `fallback_judge()` (moved from runner.py, made public) |
| 0 | **MODIFY** | `backend/app/infra/debate/runner.py` | Now imports shared types from schemas.py/toml_serde.py; backward-compatible alias |
| 1 | **NEW** | `backend/app/infra/llm/autogen_model_client.py` | `BaseLLMClient` → `ChatCompletionClient` adapter (all 9 abstract methods) |
| 2 | **NEW** | `backend/app/infra/debate/autogen_agents.py` | AutoGen agent definitions with sanitized system prompts via `case_packet_text()` |
| 3 | **NEW** | `backend/app/infra/debate/autogen_tools.py` | `FunctionTool` evidence retrieval wrappers |
| 4 | **NEW** | `backend/app/infra/debate/autogen_debate_flow.py` | `AutoGenDebateController` with all plan v3 bug fixes |
| 5 | **MODIFY** | `backend/app/config.py` | +3 settings: `use_autogen_debate`, `autogen_max_cross_exam_messages`, `autogen_enable_tools` |
| 6 | **MODIFY** | `backend/app/usecases/run_eval.py` | Feature flag wiring to select controller |
| 7 | **MODIFY** | `backend/requirements.txt` | Pin `autogen-agentchat>=0.7,<1.0` (was `>=0.4`) |
| 8 | **NEW** | `backend/tests/test_autogen_debate.py` | 20 integration tests covering all verified bugs |

**Existing files preserved** (backward-compatible):
- `runner.py` — `DebateController` logic untouched; shared types moved to schemas.py with re-exports
- `prompts.py` — existing templates still used by FSM path
- `scoring.py` — scoring pipeline is controller-agnostic
- `runs.py` — API routes unchanged
- All 70 existing tests — zero regressions (133 total pass)

---

## Dependency Graph

```
run_eval.py
├── [feature flag OFF] DebateController (runner.py) ← existing path, unchanged
└── [feature flag ON]  AutoGenDebateController (autogen_debate_flow.py) ← new path
    ├── GalileoModelClient (autogen_model_client.py)
    │   └── BaseLLMClient (base.py) ← existing provider clients
    ├── create_debate_agents (autogen_agents.py)
    │   └── AssistantAgent (autogen_agentchat)
    ├── build_evidence_tools (autogen_tools.py) [optional]
    │   └── FunctionTool (autogen_core.tools)
    └── SelectorGroupChat (autogen_agentchat.teams)
        └── max_turns (no MaxMessageTermination needed)
```

---

## Bug Fixes Applied (from Critical Review v3)

| Bug | Fix Applied |
|-----|------------|
| BUG-1: `tool_choice` missing from `create()` | Added to adapter signature |
| BUG-3: `[-3000]` slice typo | Fixed to `[-3000:]` |
| BUG-4: `function_calling=False` crashes | Dynamic flag via `enable_function_calling` param |
| BUG-6: Off-by-one in message count | `max_turns` instead of `MaxMessageTermination` |
| DESIGN-1: `selector_func` None | Never returns None (safe fallback) |
| DESIGN-2: Fragile verdict parsing | `VERDICT_RE` regex tags |
| DESIGN-3: No SharedMemo | `_build_memo()` extracts evidence + verdicts from free text |
| DESIGN-4: Context duplication | Strategy A: `on_reset()` between phases |
| MISSING-1: No sanitization | `case_packet_text()` / `format_evidence()` for system prompts |
| MISSING-2: Task/Stop in output | Filter + `output_task_messages=False` |
| MISSING-4: No cleanup | `close()` in finally block |
| ARCH-1: Shared types in runner.py | Extracted to `schemas.py` / `toml_serde.py` |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| AutoGen API breaking changes (0.7 → 0.8+) | Medium | High | Pin `<1.0` in requirements.txt; wrap all AutoGen imports |
| Higher LLM costs (selector calls) | Low | Medium | Deterministic `selector_func` (zero extra LLM calls) |
| Judge TOML parsing failures | Medium | Low | Reuses `parse_judge_output()` with TOML+JSON+fallback chain |
| Agent context window overflow | Low | Low | `on_reset()` between phases + 3000-char history cap |
| Existing test regressions | Very Low | High | Feature flag defaults OFF; 133/133 tests pass |

---

## Implementation Status

```
Step 0 ─── DONE: schemas.py + toml_serde.py refactor (ARCH-1)
Step 1 ─── DONE: autogen_model_client.py (BUG-1, BUG-4)
Step 2 ─── DONE: autogen_agents.py (MISSING-1)
Step 3 ─── DONE: autogen_tools.py
Step 4 ─── DONE: autogen_debate_flow.py (BUG-3, BUG-6, DESIGN-1..4, MISSING-2, MISSING-4)
Step 5 ─── DONE: config.py (+3 settings)
Step 6 ─── DONE: run_eval.py (feature flag wiring)
Step 7 ─── DONE: requirements.txt (version pin)
Step 8 ─── DONE: test_autogen_debate.py (20 tests)
```

---

## Verification Results

```
Full test suite: 133 passed, 0 failed, 1 warning (pre-existing)
  - 70 existing tests: all pass (zero regressions)
  - 20 new AutoGen tests: all pass
  - 43 other tests: all pass
```

### Manual Verification

1. **Feature Flag Off** (default):
   ```powershell
   # Start backend normally — should behave identically
   uvicorn app.main:app --reload
   curl http://localhost:8000/health
   ```

2. **Feature Flag On**:
   ```powershell
   # Set in .env:
   # USE_AUTOGEN_DEBATE=true
   # AUTOGEN_ENABLE_TOOLS=false
   uvicorn app.main:app --reload
   # Trigger a run via Swagger or frontend
   # Compare judge output quality and cost with FSM path
   ```

3. **With Tools Enabled**:
   ```powershell
   # USE_AUTOGEN_DEBATE=true
   # AUTOGEN_ENABLE_TOOLS=true
   # Observe agent tool calls in debug logs
   ```
