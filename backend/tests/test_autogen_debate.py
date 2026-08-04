"""Integration tests for AutoGen-powered debate controller.

Tests cover:
  - GalileoModelClient adapter (BUG-1 tool_choice, BUG-4 function_calling)
  - GalileoModelClient cancellation & timeout safety-net
  - JSON parsing helper (_try_parse_json)
  - Full debate runs (converging / diverging / fallback)
  - Early-stop logic on parsed JSON dicts
  - SharedMemo builder on parsed JSON dicts
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

import pytest

from autogen_core import CancellationToken
from autogen_core.models import (
    AssistantMessage,
    SystemMessage,
    UserMessage,
)

from app.core.domain.schemas import DebateRole
from app.infra.debate.autogen_debate_flow import (
    AutoGenDebateController,
    _try_parse_json,
    _extract_content,
)
from app.infra.debate.schemas import (
    DebateMessage,
    DebatePhase,
    DebateResult,
    MessageEvent,
    PhaseEvent,
)
from app.infra.llm.autogen_model_client import GalileoModelClient, _DEFAULT_CREATE_TIMEOUT
from app.infra.llm.base import LLMResponse


# ---------------------------------------------------------------------------
# Mock LLM client that satisfies BaseLLMClient Protocol
# ---------------------------------------------------------------------------

class MockBaseLLMClient:
    """Deterministic LLM mock returning canned responses."""

    def __init__(self, responses: list[str] | None = None) -> None:
        self._responses = list(responses) if responses else []
        self._idx = 0
        self.call_count = 0

    async def complete(
        self,
        prompt: str,
        *,
        json_schema: Optional[dict[str, Any]] = None,
        temperature: float = 0.0,
        timeout: int = 60,
        retries: int = 3,
    ) -> LLMResponse:
        self.call_count += 1
        if self._idx < len(self._responses):
            text = self._responses[self._idx]
            self._idx += 1
        else:
            # Default: return a valid JSON judge verdict
            text = _judge_json()
        return LLMResponse(text=text, latency_ms=10, cost_estimate=0.001)


class HangingMockLLMClient:
    """Mock that hangs forever on ``complete()`` — used to test timeouts."""

    def __init__(self) -> None:
        self.call_count = 0

    async def complete(
        self,
        prompt: str,
        *,
        json_schema: Optional[dict[str, Any]] = None,
        temperature: float = 0.0,
        timeout: int = 60,
        retries: int = 3,
    ) -> LLMResponse:
        self.call_count += 1
        await asyncio.sleep(3600)  # hang for 1 hour (will be cancelled)
        return LLMResponse(text="unreachable", latency_ms=0, cost_estimate=0.0)


class SlowMockLLMClient:
    """Mock that takes ``delay`` seconds per call — used to test safety-net timeout."""

    def __init__(self, delay: float = 5.0) -> None:
        self._delay = delay
        self.call_count = 0

    async def complete(
        self,
        prompt: str,
        *,
        json_schema: Optional[dict[str, Any]] = None,
        temperature: float = 0.0,
        timeout: int = 60,
        retries: int = 3,
    ) -> LLMResponse:
        self.call_count += 1
        await asyncio.sleep(self._delay)
        return LLMResponse(text="slow response", latency_ms=int(self._delay * 1000), cost_estimate=0.001)


# ---------------------------------------------------------------------------
# Canned JSON responses
# ---------------------------------------------------------------------------

def _proposal_json(verdict: str = "SUPPORTED") -> str:
    """JSON matching the Proposal schema."""
    return json.dumps({
        "proposed_verdict": verdict,
        "evidence_used": ["E1", "E2"],
        "key_points": ["Evidence supports this position"],
        "uncertainties": ["Sample size limited"],
        "what_would_change_my_mind": ["Counter-evidence"],
    })


def _revision_json(verdict: str = "SUPPORTED") -> str:
    """JSON matching the Revision schema."""
    return json.dumps({
        "final_proposed_verdict": verdict,
        "evidence_used": ["E1", "E2"],
        "what_i_changed": [],
        "remaining_disagreements": [],
        "confidence": 0.85,
    })


def _judge_json() -> str:
    """JSON matching the judge verdict schema."""
    return json.dumps({
        "verdict": "SUPPORTED",
        "confidence": 0.85,
        "evidence_used": ["E1", "E2"],
        "reasoning": "Evidence supports the claim based on E1 and E2.",
    })


def _build_responses_converging() -> list[str]:
    """Build responses where all agents agree -> dispute skipped."""
    return [
        # Phase 1: 3 proposals (parallel, JSON)
        _proposal_json("SUPPORTED"),
        _proposal_json("SUPPORTED"),
        _proposal_json("SUPPORTED"),
        # Phase 2: 7 cross-exam turns (conversational free text)
        "Orthodox questions Heretic about E1. [E1]",
        "Heretic responds: E1 supports the claim. [E1]",
        "Heretic questions Orthodox about E2. [E2]",
        "Orthodox responds: E2 is consistent. [E2]",
        "Skeptic challenges both: What about gaps in E1? [E1]",
        "Orthodox answers Skeptic: No gaps identified. [E1]",
        "Heretic answers Skeptic: E1 is solid. [E1]",
        # Phase 3: 3 revisions (parallel, JSON)
        _revision_json("SUPPORTED"),
        _revision_json("SUPPORTED"),
        _revision_json("SUPPORTED"),
        # Phase 4: Judge (JSON)
        _judge_json(),
    ]


def _build_responses_diverging() -> list[str]:
    """Build responses where agents disagree -> dispute runs."""
    return [
        # Phase 1: 3 proposals (JSON)
        _proposal_json("SUPPORTED"),
        _proposal_json("REFUTED"),
        _proposal_json("INSUFFICIENT"),
        # Phase 2: 7 cross-exam turns (free text)
        "Orthodox questions Heretic about E1.",
        "Heretic responds: E1 is inconclusive.",
        "Heretic questions Orthodox about E2.",
        "Orthodox responds: E2 strongly supports.",
        "Skeptic challenges both sides.",
        "Orthodox answers Skeptic.",
        "Heretic answers Skeptic.",
        # Phase 3: 3 revisions (JSON, still disagree)
        _revision_json("SUPPORTED"),
        _revision_json("REFUTED"),
        _revision_json("INSUFFICIENT"),
        # Phase 3.5: 3 dispute messages (free text)
        "Skeptic's decisive question about E1.",
        "Orthodox's final answer with E1.",
        "Heretic's final answer with E2.",
        # Phase 4: Judge (JSON)
        _judge_json(),
    ]


EVIDENCE_PACKETS = [
    {"eid": "E1", "summary": "Main evidence", "source": "Source A", "date": "2024-01-01"},
    {"eid": "E2", "summary": "Supporting evidence", "source": "Source B", "date": "2024-02-01"},
    {"eid": "E3", "summary": "Contradicting evidence", "source": "Source C", "date": "2024-03-01"},
]


# ---------------------------------------------------------------------------
# Tests: GalileoModelClient adapter
# ---------------------------------------------------------------------------

class TestGalileoModelClient:
    """Unit tests for the adapter (BUG-1, BUG-4)."""

    def test_model_info_function_calling_off(self):
        mock = MockBaseLLMClient()
        client = GalileoModelClient(mock, enable_function_calling=False)
        assert client.model_info["function_calling"] is False

    def test_model_info_function_calling_on(self):
        mock = MockBaseLLMClient()
        client = GalileoModelClient(mock, enable_function_calling=True)
        assert client.model_info["function_calling"] is True

    @pytest.mark.asyncio
    async def test_create_with_tool_choice(self):
        """BUG-1: tool_choice must be accepted without TypeError."""
        mock = MockBaseLLMClient(["Hello world"])
        client = GalileoModelClient(mock)

        result = await client.create(
            [UserMessage(content="test", source="user")],
            tool_choice="auto",
        )
        assert result.content == "Hello world"
        assert result.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_cost_accumulation(self):
        mock = MockBaseLLMClient(["Response 1", "Response 2"])
        client = GalileoModelClient(mock)

        await client.create([UserMessage(content="q1", source="user")])
        await client.create([UserMessage(content="q2", source="user")])

        assert client.accumulated_cost == pytest.approx(0.002)
        assert client.total_usage.prompt_tokens > 0
        assert client.total_usage.completion_tokens > 0

    @pytest.mark.asyncio
    async def test_message_flattening(self):
        """System + User + Assistant messages are flattened into a single prompt."""
        mock = MockBaseLLMClient(["OK"])
        client = GalileoModelClient(mock)

        await client.create([
            SystemMessage(content="Be helpful"),
            UserMessage(content="Hello", source="user"),
            AssistantMessage(content="Hi there", source="assistant"),
            UserMessage(content="Follow up", source="user"),
        ])

        assert mock.call_count == 1


# ---------------------------------------------------------------------------
# Tests: _try_parse_json helper
# ---------------------------------------------------------------------------

class TestTryParseJson:
    """Robust JSON parsing from LLM output."""

    def test_valid_json(self):
        text = '{"verdict": "SUPPORTED", "confidence": 0.9}'
        result = _try_parse_json(text)
        assert result["verdict"] == "SUPPORTED"

    def test_fenced_json(self):
        text = '```json\n{"verdict": "REFUTED"}\n```'
        result = _try_parse_json(text)
        assert result["verdict"] == "REFUTED"

    def test_fenced_no_lang_tag(self):
        text = '```\n{"verdict": "INSUFFICIENT"}\n```'
        result = _try_parse_json(text)
        assert result["verdict"] == "INSUFFICIENT"

    def test_json_with_preamble(self):
        text = 'Here is my analysis:\n{"verdict": "SUPPORTED", "confidence": 0.8}'
        result = _try_parse_json(text)
        assert result["verdict"] == "SUPPORTED"

    def test_invalid_falls_back(self):
        text = "This is not JSON at all {{{ invalid"
        fallback = {"verdict": "INSUFFICIENT"}
        result = _try_parse_json(text, fallback=fallback)
        assert result["verdict"] == "INSUFFICIENT"

    def test_empty_text_falls_back(self):
        result = _try_parse_json("", fallback={"x": 1})
        assert result == {"x": 1}

    def test_no_fallback_returns_empty_dict(self):
        result = _try_parse_json("not json")
        assert result == {}


# ---------------------------------------------------------------------------
# Tests: Full debate runs
# ---------------------------------------------------------------------------

class TestAutoGenDebateConverging:
    """Full debate run where agents agree -> dispute skipped."""

    @pytest.mark.asyncio
    async def test_converging_debate(self):
        mock_llm = MockBaseLLMClient(_build_responses_converging())
        client = GalileoModelClient(mock_llm)
        # 7 cross-exam responses in the mock data
        controller = AutoGenDebateController(client, "test/model", max_cross_exam_messages=7)

        phases_seen: list[str] = []
        messages_seen: list[tuple[str, str, int]] = []

        async def on_phase(evt: PhaseEvent) -> None:
            phases_seen.append(evt.phase)

        async def on_msg(evt: MessageEvent) -> None:
            messages_seen.append((evt.role, evt.phase, evt.round))

        result = await controller.run(
            case_id="T01",
            claim="Test claim",
            topic="Test topic",
            evidence_packets=EVIDENCE_PACKETS,
            on_message=on_msg,
            on_phase=on_phase,
        )

        # Dispute should be skipped (all SUPPORTED)
        assert "dispute" not in phases_seen
        assert phases_seen == [
            "setup", "independent", "cross_exam", "revision", "judge",
        ]
        assert result.judge_json["verdict"] == "SUPPORTED"
        assert result.total_cost > 0
        assert result.total_latency_ms > 0

    @pytest.mark.asyncio
    async def test_all_messages_have_phase_and_round(self):
        mock_llm = MockBaseLLMClient(_build_responses_converging())
        client = GalileoModelClient(mock_llm)
        controller = AutoGenDebateController(client, "test/model", max_cross_exam_messages=7)

        result = await controller.run(
            case_id="T02",
            claim="Test claim",
            topic="Test topic",
            evidence_packets=EVIDENCE_PACKETS,
        )

        for msg in result.messages:
            assert msg.phase != "", f"Message from {msg.role} has empty phase"
            assert msg.round > 0, f"Message from {msg.role} has round=0"

    @pytest.mark.asyncio
    async def test_proposal_content_is_parseable_json(self):
        """Proposals in DebateMessage.content must be clean JSON for frontend rendering."""
        mock_llm = MockBaseLLMClient(_build_responses_converging())
        client = GalileoModelClient(mock_llm)
        controller = AutoGenDebateController(client, "test/model", max_cross_exam_messages=7)

        result = await controller.run(
            case_id="T05",
            claim="Test claim",
            topic="Test topic",
            evidence_packets=EVIDENCE_PACKETS,
        )

        proposal_msgs = [m for m in result.messages if m.phase == "independent"]
        assert len(proposal_msgs) == 3
        for msg in proposal_msgs:
            parsed = json.loads(msg.content)
            assert "proposed_verdict" in parsed
            assert "key_points" in parsed
            assert "evidence_used" in parsed

    @pytest.mark.asyncio
    async def test_revision_content_is_parseable_json(self):
        """Revisions in DebateMessage.content must be clean JSON for frontend rendering."""
        mock_llm = MockBaseLLMClient(_build_responses_converging())
        client = GalileoModelClient(mock_llm)
        controller = AutoGenDebateController(client, "test/model", max_cross_exam_messages=7)

        result = await controller.run(
            case_id="T06",
            claim="Test claim",
            topic="Test topic",
            evidence_packets=EVIDENCE_PACKETS,
        )

        revision_msgs = [m for m in result.messages if m.phase == "revision"]
        assert len(revision_msgs) == 3
        for msg in revision_msgs:
            parsed = json.loads(msg.content)
            assert "final_proposed_verdict" in parsed
            assert "confidence" in parsed


class TestAutoGenDebateDiverging:
    """Full debate run where agents disagree -> dispute runs."""

    @pytest.mark.asyncio
    async def test_diverging_debate(self):
        mock_llm = MockBaseLLMClient(_build_responses_diverging())
        client = GalileoModelClient(mock_llm)
        # 7 cross-exam responses in the mock data
        controller = AutoGenDebateController(client, "test/model", max_cross_exam_messages=7)

        phases_seen: list[str] = []

        async def on_phase(evt: PhaseEvent) -> None:
            phases_seen.append(evt.phase)

        result = await controller.run(
            case_id="T03",
            claim="Test claim",
            topic="Test topic",
            evidence_packets=EVIDENCE_PACKETS,
            on_phase=on_phase,
        )

        # Dispute should run (agents disagree)
        assert "dispute" in phases_seen
        assert phases_seen == [
            "setup", "independent", "cross_exam", "revision", "dispute", "judge",
        ]
        assert result.judge_json["verdict"] == "SUPPORTED"


class TestAutoGenDebateFallback:
    """Judge produces invalid output -> fallback verdict used."""

    @pytest.mark.asyncio
    async def test_fallback_judge_output(self):
        responses = _build_responses_converging()
        # Replace the last response (judge) with invalid output
        responses[-1] = "This is not valid TOML or JSON {{{invalid"

        mock_llm = MockBaseLLMClient(responses)
        client = GalileoModelClient(mock_llm)
        controller = AutoGenDebateController(client, "test/model", max_cross_exam_messages=7)

        result = await controller.run(
            case_id="T04",
            claim="Test claim",
            topic="Test topic",
            evidence_packets=EVIDENCE_PACKETS,
        )

        # Fallback verdict should be INSUFFICIENT
        assert result.judge_json["verdict"] == "INSUFFICIENT"
        assert result.judge_json["confidence"] == 0.0


# ---------------------------------------------------------------------------
# Tests: Early-stop logic (parsed JSON dicts)
# ---------------------------------------------------------------------------

class TestEarlyStopLogic:
    """Verdict extraction from parsed revision dicts."""

    def test_should_skip_dispute_all_agree(self):
        revisions = {
            DebateRole.ORTHODOX: {"final_proposed_verdict": "SUPPORTED", "evidence_used": ["E1"], "confidence": 0.9},
            DebateRole.HERETIC: {"final_proposed_verdict": "SUPPORTED", "evidence_used": ["E2"], "confidence": 0.8},
            DebateRole.SKEPTIC: {"final_proposed_verdict": "SUPPORTED", "evidence_used": ["E1"], "confidence": 0.85},
        }
        assert AutoGenDebateController._should_skip_dispute(revisions) is True

    def test_should_not_skip_dispute_disagree(self):
        revisions = {
            DebateRole.ORTHODOX: {"final_proposed_verdict": "SUPPORTED", "confidence": 0.9},
            DebateRole.HERETIC: {"final_proposed_verdict": "REFUTED", "confidence": 0.8},
            DebateRole.SKEPTIC: {"final_proposed_verdict": "INSUFFICIENT", "confidence": 0.5},
        }
        assert AutoGenDebateController._should_skip_dispute(revisions) is False

    def test_should_not_skip_when_empty_verdict(self):
        revisions = {
            DebateRole.ORTHODOX: {"final_proposed_verdict": "", "confidence": 0.5},
            DebateRole.HERETIC: {"final_proposed_verdict": "", "confidence": 0.5},
            DebateRole.SKEPTIC: {"final_proposed_verdict": "", "confidence": 0.5},
        }
        # Empty verdicts -> no consensus detected -> don't skip
        assert AutoGenDebateController._should_skip_dispute(revisions) is False

    def test_should_not_skip_when_missing_verdict_key(self):
        revisions = {
            DebateRole.ORTHODOX: {"confidence": 0.5},
            DebateRole.HERETIC: {"confidence": 0.5},
            DebateRole.SKEPTIC: {"confidence": 0.5},
        }
        assert AutoGenDebateController._should_skip_dispute(revisions) is False


# ---------------------------------------------------------------------------
# Tests: SharedMemo builder (parsed JSON dicts)
# ---------------------------------------------------------------------------

class TestBuildMemo:
    """SharedMemo from parsed proposal dicts."""

    def test_memo_with_verdicts_and_evidence(self):
        proposals = {
            DebateRole.ORTHODOX: {"proposed_verdict": "SUPPORTED", "evidence_used": ["E1"]},
            DebateRole.HERETIC: {"proposed_verdict": "REFUTED", "evidence_used": ["E2"]},
        }
        memo = AutoGenDebateController._build_memo(proposals)
        assert "Shared Memo" in memo
        assert "SUPPORTED" in memo
        assert "REFUTED" in memo
        assert "Contested" in memo
        assert "E1" in memo
        assert "E2" in memo

    def test_memo_agreement(self):
        proposals = {
            DebateRole.ORTHODOX: {"proposed_verdict": "SUPPORTED", "evidence_used": ["E1"]},
            DebateRole.HERETIC: {"proposed_verdict": "SUPPORTED", "evidence_used": ["E1"]},
        }
        memo = AutoGenDebateController._build_memo(proposals)
        assert "Contested" not in memo

    def test_memo_with_empty_proposal(self):
        proposals = {
            DebateRole.ORTHODOX: {},
        }
        memo = AutoGenDebateController._build_memo(proposals)
        assert "Shared Memo" in memo


# ---------------------------------------------------------------------------
# Tests: GalileoModelClient cancellation & timeout
# ---------------------------------------------------------------------------

class TestGalileoModelClientCancellation:
    """Verify that GalileoModelClient honours CancellationToken and
    has a safety-net timeout."""

    @pytest.mark.asyncio
    async def test_cancellation_token_aborts_call(self):
        """A cancelled token must abort a hanging LLM call promptly."""
        mock = HangingMockLLMClient()
        client = GalileoModelClient(mock)

        cancel = CancellationToken()
        # Schedule cancellation after 0.2 seconds
        loop = asyncio.get_event_loop()
        loop.call_later(0.2, cancel.cancel)

        with pytest.raises((asyncio.CancelledError, Exception)):
            await client.create(
                [UserMessage(content="test", source="user")],
                cancellation_token=cancel,
            )

    @pytest.mark.asyncio
    async def test_safety_net_timeout_fires(self):
        """The safety-net timeout must abort a call that exceeds the budget."""
        import app.infra.llm.autogen_model_client as mc
        original = mc._DEFAULT_CREATE_TIMEOUT
        mc._DEFAULT_CREATE_TIMEOUT = 1  # 1 second for test speed

        try:
            mock = HangingMockLLMClient()
            client = GalileoModelClient(mock)

            with pytest.raises(asyncio.TimeoutError):
                await client.create(
                    [UserMessage(content="test", source="user")],
                )
        finally:
            mc._DEFAULT_CREATE_TIMEOUT = original

    @pytest.mark.asyncio
    async def test_normal_call_unaffected_by_timeout(self):
        """A fast LLM call should succeed normally despite the timeout wrapper."""
        mock = MockBaseLLMClient(["Hello"])
        client = GalileoModelClient(mock)

        result = await client.create(
            [UserMessage(content="test", source="user")],
        )
        assert result.content == "Hello"
        assert mock.call_count == 1


# ---------------------------------------------------------------------------
# Tests: Cross-exam phase timeout
# ---------------------------------------------------------------------------

class TestCrossExamTimeout:
    """Verify that a hanging cross-exam phase does not block the debate."""

    @pytest.mark.asyncio
    async def test_cross_exam_timeout_does_not_block_debate(self):
        """When the LLM hangs during cross-exam, the phase should time out
        and the debate should continue to revision and judge phases."""
        import app.infra.debate.autogen_debate_flow as df
        original_timeout = df._PER_TURN_TIMEOUT
        df._PER_TURN_TIMEOUT = 1  # 1 second per turn for test speed

        try:
            # First 3 responses are proposals (fast mock), then cross-exam hangs
            responses = [
                _proposal_json("SUPPORTED"),
                _proposal_json("SUPPORTED"),
                _proposal_json("SUPPORTED"),
            ]
            # After proposals, the cross-exam calls will hang, triggering timeout.
            # Post-timeout, revision + judge phases need responses.
            # We supply revision + judge responses; cross-exam will time out.
            responses.extend([
                # Revision (3 responses)
                _revision_json("SUPPORTED"),
                _revision_json("SUPPORTED"),
                _revision_json("SUPPORTED"),
                # Judge
                _judge_json(),
            ])

            class ProposalThenHangClient:
                """Returns canned responses for the first N calls, then hangs."""

                def __init__(self, fast_responses: list[str]) -> None:
                    self._fast = list(fast_responses)
                    self._idx = 0
                    self.call_count = 0

                async def complete(
                    self,
                    prompt: str,
                    *,
                    json_schema: Optional[dict[str, Any]] = None,
                    temperature: float = 0.0,
                    timeout: int = 60,
                    retries: int = 3,
                ) -> LLMResponse:
                    self.call_count += 1
                    if self._idx < len(self._fast):
                        text = self._fast[self._idx]
                        self._idx += 1
                        return LLMResponse(text=text, latency_ms=10, cost_estimate=0.001)
                    # After fast responses exhausted, hang (simulates stuck API)
                    await asyncio.sleep(3600)
                    return LLMResponse(text="unreachable", latency_ms=0, cost_estimate=0.0)

            mock = ProposalThenHangClient(responses)
            client = GalileoModelClient(mock)
            controller = AutoGenDebateController(
                client, "test/model", max_cross_exam_messages=3,
            )

            phases_seen: list[str] = []

            async def on_phase(evt: PhaseEvent) -> None:
                phases_seen.append(evt.phase)

            result = await controller.run(
                case_id="T-timeout",
                claim="Test claim",
                topic="Test topic",
                evidence_packets=EVIDENCE_PACKETS,
                on_phase=on_phase,
            )

            # The cross-exam phase should have been entered (and timed out)
            assert "cross_exam" in phases_seen
            # The debate should still produce a judge verdict
            assert result.judge_json is not None
        finally:
            df._PER_TURN_TIMEOUT = original_timeout
