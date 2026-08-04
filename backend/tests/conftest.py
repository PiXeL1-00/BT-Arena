import pytest

from app.core.domain.schemas import JudgeDecision, VerdictEnum


@pytest.fixture
def sample_judge_correct() -> JudgeDecision:
    return JudgeDecision(
        verdict=VerdictEnum.SUPPORTED,
        confidence=0.92,
        evidence_used=["E1", "E2"],
        reasoning="Evidence E1 and E2 strongly support the claim, however some uncertainty remains.",
    )


@pytest.fixture
def sample_judge_wrong() -> JudgeDecision:
    return JudgeDecision(
        verdict=VerdictEnum.REFUTED,
        confidence=0.85,
        evidence_used=["E1"],
        reasoning="Evidence suggests the claim is refuted due to contrary data.",
    )


@pytest.fixture
def sample_judge_insufficient() -> JudgeDecision:
    return JudgeDecision(
        verdict=VerdictEnum.INSUFFICIENT,
        confidence=0.40,
        evidence_used=["E1"],
        reasoning="Not enough evidence to determine, uncertainty is high.",
    )


@pytest.fixture
def valid_eids() -> set[str]:
    return {"E1", "E2", "E3"}
