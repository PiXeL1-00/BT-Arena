from __future__ import annotations

import json
from typing import Any, Optional

import pytest
import tomli_w

from app.infra.debate.runner import DebateController, DebateMessage
from app.infra.debate.schemas import DebatePhase, MessageEvent, PhaseEvent
from app.infra.llm.base import LLMResponse


def _to_toml(data: dict) -> str:
    return tomli_w.dumps(data)


VALID_PROPOSAL = _to_toml({
    "proposed_verdict": "SUPPORTED",
    "evidence_used": ["E1", "E2"],
    "key_points": ["Evidence strongly supports claim"],
    "uncertainties": ["Sample size limited"],
    "what_would_change_my_mind": ["Counter-evidence from E3"],
})

VALID_PROPOSAL_REFUTED = _to_toml({
    "proposed_verdict": "REFUTED",
    "evidence_used": ["E2"],
    "key_points": ["Evidence contradicts claim"],
    "uncertainties": [],
    "what_would_change_my_mind": ["Additional supporting data"],
})

VALID_PROPOSAL_INSUFFICIENT = _to_toml({
    "proposed_verdict": "INSUFFICIENT",
    "evidence_used": ["E1"],
    "key_points": ["Not enough evidence to determine"],
    "uncertainties": ["Both sides have gaps"],
    "what_would_change_my_mind": ["More data points"],
})

VALID_QUESTIONS = _to_toml({
    "questions": [
        {"to": "Heretic", "q": "How do you reconcile E1?", "evidence_refs": ["E1"]},
        {"to": "Heretic", "q": "What about the date gap?", "evidence_refs": ["E2"]},
    ],
})

VALID_ANSWERS = _to_toml({
    "answers": [
        {"q": "How do you reconcile E1?", "a": "E1 is contextual", "evidence_refs": ["E1"], "admission": "none"},
        {"q": "What about the date gap?", "a": "Gap is not significant", "evidence_refs": ["E2"], "admission": "none"},
    ],
})

VALID_SKEPTIC_QUESTIONS = _to_toml({
    "questions": [
        {"to": "Both", "q": "Neither side addresses E3", "evidence_refs": ["E3"]},
        {"to": "Both", "q": "What is the confidence basis?", "evidence_refs": ["E1"]},
    ],
})

VALID_REVISION_AGREE = _to_toml({
    "final_proposed_verdict": "SUPPORTED",
    "evidence_used": ["E1", "E2"],
    "what_i_changed": [],
    "remaining_disagreements": [],
    "confidence": 0.9,
})

VALID_REVISION_DISAGREE = _to_toml({
    "final_proposed_verdict": "REFUTED",
    "evidence_used": ["E2"],
    "what_i_changed": ["Reconsidered E1"],
    "remaining_disagreements": ["Verdict still differs"],
    "confidence": 0.7,
})

VALID_DISPUTE_QUESTION = _to_toml({
    "questions": [{"q": "Final decisive question", "evidence_refs": ["E1"]}],
})

VALID_DISPUTE_ANSWER = _to_toml({
    "answers": [{"q": "Final decisive question", "a": "My final answer", "evidence_refs": ["E1"], "admission": "none"}],
})

VALID_JUDGE = _to_toml({
    "verdict": "SUPPORTED",
    "confidence": 0.88,
    "evidence_used": ["E1", "E2"],
    "reasoning": "Evidence E1 and E2 strongly support the claim, however sample size is limited.",
})

EVIDENCE_PACKETS = [
    {"eid": "E1", "summary": "Main evidence", "source": "Source A", "date": "2024-01-01"},
    {"eid": "E2", "summary": "Supporting evidence", "source": "Source B", "date": "2024-02-01"},
    {"eid": "E3", "summary": "Contradicting evidence", "source": "Source C", "date": "2024-03-01"},
]


class MockLLMClient:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self._call_index = 0
        self.call_log: list[str] = []

    async def complete(
        self, prompt: str, *,
        json_schema: Optional[dict[str, Any]] = None,
        temperature: float = 0.0,
        timeout: int = 60, retries: int = 3,
    ) -> LLMResponse:
        self.call_log.append(prompt[:80])
        text = self._responses[self._call_index] if self._call_index < len(self._responses) else VALID_JUDGE
        self._call_index += 1
        return LLMResponse(text=text, latency_ms=50, cost_estimate=0.001)

    @property
    def total_calls(self) -> int:
        return self._call_index


def _build_converging_responses() -> list[str]:
    return [
        VALID_PROPOSAL, VALID_PROPOSAL, VALID_PROPOSAL,
        VALID_QUESTIONS, VALID_ANSWERS, VALID_QUESTIONS, VALID_ANSWERS,
        VALID_SKEPTIC_QUESTIONS, VALID_ANSWERS, VALID_ANSWERS,
        VALID_REVISION_AGREE, VALID_REVISION_AGREE, VALID_REVISION_AGREE,
        VALID_JUDGE,
    ]


def _build_diverging_responses() -> list[str]:
    return [
        VALID_PROPOSAL, VALID_PROPOSAL_REFUTED, VALID_PROPOSAL_INSUFFICIENT,
        VALID_QUESTIONS, VALID_ANSWERS, VALID_QUESTIONS, VALID_ANSWERS,
        VALID_SKEPTIC_QUESTIONS, VALID_ANSWERS, VALID_ANSWERS,
        VALID_REVISION_AGREE, VALID_REVISION_DISAGREE, VALID_REVISION_AGREE,
        VALID_DISPUTE_QUESTION, VALID_DISPUTE_ANSWER, VALID_DISPUTE_ANSWER,
        VALID_JUDGE,
    ]


@pytest.mark.asyncio
async def test_turn_order_converging():
    mock_llm = MockLLMClient(_build_converging_responses())
    controller = DebateController(mock_llm, "test/model")

    phases_seen: list[str] = []
    messages_seen: list[tuple[str, str, int]] = []

    async def on_phase(evt: PhaseEvent) -> None:
        phases_seen.append(evt.phase)

    async def on_msg(evt: MessageEvent) -> None:
        messages_seen.append((evt.role, evt.phase, evt.round))

    result = await controller.run(
        case_id="T01", claim="Test claim", topic="Test topic",
        evidence_packets=EVIDENCE_PACKETS, on_message=on_msg, on_phase=on_phase,
    )

    assert phases_seen == ["setup", "independent", "cross_exam", "revision", "judge"]
    roles = [m[0] for m in messages_seen]
    expected_roles = [
        "Orthodox", "Heretic", "Skeptic",
        "Orthodox", "Heretic", "Heretic", "Orthodox",
        "Skeptic", "Orthodox", "Heretic",
        "Orthodox", "Heretic", "Skeptic",
        "Judge",
    ]
    assert roles == expected_roles, f"Role order mismatch: {roles}"
    assert result.judge_json["verdict"] == "SUPPORTED"
    assert result.total_cost > 0


@pytest.mark.asyncio
async def test_turn_order_diverging():
    mock_llm = MockLLMClient(_build_diverging_responses())
    controller = DebateController(mock_llm, "test/model")
    phases_seen: list[str] = []

    async def on_phase(evt: PhaseEvent) -> None:
        phases_seen.append(evt.phase)

    result = await controller.run(
        case_id="T02", claim="Test claim", topic="Test topic",
        evidence_packets=EVIDENCE_PACKETS, on_phase=on_phase,
    )
    assert "dispute" in phases_seen
    assert phases_seen == ["setup", "independent", "cross_exam", "revision", "dispute", "judge"]
    assert result.judge_json["verdict"] == "SUPPORTED"


@pytest.mark.asyncio
async def test_early_stop_convergence():
    mock_llm = MockLLMClient(_build_converging_responses())
    controller = DebateController(mock_llm, "test/model", early_stop_jaccard=0.4)
    phases_seen: list[str] = []

    async def on_phase(evt: PhaseEvent) -> None:
        phases_seen.append(evt.phase)

    await controller.run(
        case_id="T03", claim="Test claim", topic="Test topic",
        evidence_packets=EVIDENCE_PACKETS, on_phase=on_phase,
    )
    assert "dispute" not in phases_seen
    assert mock_llm.total_calls == 14


@pytest.mark.asyncio
async def test_hard_cap_max_calls():
    mock_llm = MockLLMClient(_build_diverging_responses())
    controller = DebateController(mock_llm, "test/model")
    await controller.run(
        case_id="T04", claim="Test claim", topic="Test topic",
        evidence_packets=EVIDENCE_PACKETS,
    )
    assert mock_llm.total_calls <= 17


@pytest.mark.asyncio
async def test_toml_retry_on_invalid_response():
    responses = [
        "This is not valid TOML at all! {{{",
        VALID_PROPOSAL, VALID_PROPOSAL, VALID_PROPOSAL,
        VALID_QUESTIONS, VALID_ANSWERS, VALID_QUESTIONS, VALID_ANSWERS,
        VALID_SKEPTIC_QUESTIONS, VALID_ANSWERS, VALID_ANSWERS,
        VALID_REVISION_AGREE, VALID_REVISION_AGREE, VALID_REVISION_AGREE,
        VALID_JUDGE,
    ]
    mock_llm = MockLLMClient(responses)
    controller = DebateController(mock_llm, "test/model")

    result = await controller.run(
        case_id="T05", claim="Test claim", topic="Test topic",
        evidence_packets=EVIDENCE_PACKETS,
    )
    assert mock_llm.total_calls == 15
    assert result.judge_json["verdict"] == "SUPPORTED"
    assert any(m.role == "Orthodox" for m in result.messages)


@pytest.mark.asyncio
async def test_double_retry_falls_back():
    responses = [
        "not toml {{{", "still not toml {{",
        VALID_PROPOSAL, VALID_PROPOSAL,
        VALID_QUESTIONS, VALID_ANSWERS, VALID_QUESTIONS, VALID_ANSWERS,
        VALID_SKEPTIC_QUESTIONS, VALID_ANSWERS, VALID_ANSWERS,
        VALID_REVISION_AGREE, VALID_REVISION_AGREE, VALID_REVISION_AGREE,
        VALID_JUDGE,
    ]
    mock_llm = MockLLMClient(responses)
    controller = DebateController(mock_llm, "test/model")

    result = await controller.run(
        case_id="T06", claim="Test claim", topic="Test topic",
        evidence_packets=EVIDENCE_PACKETS,
    )
    assert result.judge_json["verdict"] == "SUPPORTED"
    orthodox = [m for m in result.messages if m.role == "Orthodox" and m.phase == DebatePhase.INDEPENDENT]
    assert len(orthodox) == 1


@pytest.mark.asyncio
async def test_missing_eid_proceeds_to_judge():
    bad_proposal = _to_toml({
        "proposed_verdict": "SUPPORTED",
        "evidence_used": ["E1", "E999"],
        "key_points": ["Evidence supports claim"],
        "uncertainties": [], "what_would_change_my_mind": [],
    })
    responses = [
        bad_proposal, VALID_PROPOSAL, VALID_PROPOSAL,
        VALID_QUESTIONS, VALID_ANSWERS, VALID_QUESTIONS, VALID_ANSWERS,
        VALID_SKEPTIC_QUESTIONS, VALID_ANSWERS, VALID_ANSWERS,
        VALID_REVISION_AGREE, VALID_REVISION_AGREE, VALID_REVISION_AGREE,
        VALID_JUDGE,
    ]
    mock_llm = MockLLMClient(responses)
    result = await DebateController(mock_llm, "test/model").run(
        case_id="T07", claim="Test claim", topic="Test topic",
        evidence_packets=EVIDENCE_PACKETS,
    )
    assert result.judge_json["verdict"] == "SUPPORTED"
    orthodox_msg = next(m for m in result.messages if m.role == "Orthodox" and m.phase == DebatePhase.INDEPENDENT)
    assert "E999" in json.loads(orthodox_msg.content)["evidence_used"]


@pytest.mark.asyncio
async def test_messages_have_phase_and_round():
    mock_llm = MockLLMClient(_build_converging_responses())
    result = await DebateController(mock_llm, "test/model").run(
        case_id="T08", claim="Test claim", topic="Test topic",
        evidence_packets=EVIDENCE_PACKETS,
    )
    for msg in result.messages:
        assert msg.phase != "", f"Message from {msg.role} has empty phase"
        assert msg.round > 0, f"Message from {msg.role} has round=0"


def test_jaccard_calculation():
    assert DebateController._jaccard([{"a", "b"}, {"b", "c"}]) == pytest.approx(1 / 3)
    assert DebateController._jaccard([{"a", "b"}, {"a", "b"}]) == pytest.approx(1.0)
    assert DebateController._jaccard([set(), set()]) == pytest.approx(0.0)
    assert DebateController._jaccard([{"a"}, {"b"}]) == pytest.approx(0.0)
    assert DebateController._jaccard([]) == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_internal_storage_is_json():
    mock_llm = MockLLMClient(_build_converging_responses())
    result = await DebateController(mock_llm, "test/model").run(
        case_id="T09", claim="Test claim", topic="Test topic",
        evidence_packets=EVIDENCE_PACKETS,
    )
    for msg in result.messages:
        if msg.role == "Judge":
            continue
        parsed = json.loads(msg.content)
        assert isinstance(parsed, dict)


@pytest.mark.asyncio
async def test_fenced_toml_output_parsed():
    fenced_proposal = f"```toml\n{VALID_PROPOSAL}```"
    responses = [
        fenced_proposal, VALID_PROPOSAL, VALID_PROPOSAL,
        VALID_QUESTIONS, VALID_ANSWERS, VALID_QUESTIONS, VALID_ANSWERS,
        VALID_SKEPTIC_QUESTIONS, VALID_ANSWERS, VALID_ANSWERS,
        VALID_REVISION_AGREE, VALID_REVISION_AGREE, VALID_REVISION_AGREE,
        VALID_JUDGE,
    ]
    mock_llm = MockLLMClient(responses)
    result = await DebateController(mock_llm, "test/model").run(
        case_id="T10", claim="Test claim", topic="Test topic",
        evidence_packets=EVIDENCE_PACKETS,
    )
    assert mock_llm.total_calls == 14
    assert result.judge_json["verdict"] == "SUPPORTED"
