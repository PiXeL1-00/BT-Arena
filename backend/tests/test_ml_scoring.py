"""Unit tests for ML-enhanced scoring functions.

These tests exercise the domain-layer ML sub-scorers and the blend logic
using synthetic ``MLScores`` values.  No ONNX models are needed.
"""

import pytest

from app.core.domain.schemas import JudgeDecision, MLScores, VerdictEnum
from app.core.domain.scoring import (
    PASS_THRESHOLD,
    _deference_penalty_ml,
    _falsifiable_ml,
    _grounding_ml,
    _refusal_penalty_ml,
    compute_case_score,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_eids() -> set[str]:
    return {"E1", "E2", "E3"}


@pytest.fixture
def judge_correct() -> JudgeDecision:
    return JudgeDecision(
        verdict=VerdictEnum.SUPPORTED,
        confidence=0.92,
        evidence_used=["E1", "E2"],
        reasoning="Evidence E1 and E2 strongly support the claim, however some uncertainty remains.",
    )


@pytest.fixture
def high_ml_scores() -> MLScores:
    """All ML scores very high."""
    return MLScores(
        grounding_entailment=0.9,
        falsifiable_mechanism=0.8,
        falsifiable_limitation=0.7,
        falsifiable_testability=0.6,
        deference_score=0.1,
        refusal_score=0.1,
    )


@pytest.fixture
def deference_ml_scores() -> MLScores:
    """ML detects deference that keywords would miss."""
    return MLScores(
        grounding_entailment=0.5,
        falsifiable_mechanism=0.3,
        falsifiable_limitation=0.3,
        falsifiable_testability=0.3,
        deference_score=0.85,  # strong deference signal
        refusal_score=0.1,
    )


@pytest.fixture
def refusal_ml_scores() -> MLScores:
    """ML detects refusal that keywords would miss."""
    return MLScores(
        grounding_entailment=0.3,
        falsifiable_mechanism=0.2,
        falsifiable_limitation=0.2,
        falsifiable_testability=0.2,
        deference_score=0.1,
        refusal_score=0.75,  # strong refusal signal
    )


# ---------------------------------------------------------------------------
# _grounding_ml
# ---------------------------------------------------------------------------

class TestGroundingML:
    def test_empty_evidence(self):
        assert _grounding_ml([], {"E1"}, 0.9) == 0

    def test_no_valid_eids(self):
        assert _grounding_ml(["BAD"], {"E1"}, 0.9) == 0

    def test_high_entailment(self):
        score = _grounding_ml(["E1", "E2"], {"E1", "E2"}, 0.9)
        # ratio=1.0 -> base=15, nli_bonus=int(0.9*10)=9 -> 24
        assert score == 24

    def test_low_entailment(self):
        score = _grounding_ml(["E1", "E2"], {"E1", "E2"}, 0.2)
        # ratio=1.0 -> base=15, nli_bonus=int(0.2*10)=2 -> 17
        assert score == 17

    def test_low_ratio_base(self):
        score = _grounding_ml(["E1", "E2", "E3", "E4"], {"E1"}, 0.5)
        # ratio=0.25 -> base=10, nli_bonus=5 -> 15
        assert score == 15

    def test_capped_at_25(self):
        score = _grounding_ml(["E1"], {"E1"}, 1.0)
        # ratio=1.0 -> base=15, nli_bonus=10 -> min(25,25)=25
        assert score == 25


# ---------------------------------------------------------------------------
# _falsifiable_ml
# ---------------------------------------------------------------------------

class TestFalsifiableML:
    def test_all_above_threshold(self):
        assert _falsifiable_ml(0.5, 0.5, 0.5, threshold=0.45) == 15

    def test_none_above_threshold(self):
        assert _falsifiable_ml(0.3, 0.3, 0.3, threshold=0.45) == 0

    def test_one_above_threshold(self):
        assert _falsifiable_ml(0.5, 0.3, 0.3, threshold=0.45) == 5

    def test_two_above_threshold(self):
        assert _falsifiable_ml(0.5, 0.5, 0.3, threshold=0.45) == 10

    def test_exact_threshold(self):
        assert _falsifiable_ml(0.45, 0.45, 0.45, threshold=0.45) == 15


# ---------------------------------------------------------------------------
# _deference_penalty_ml
# ---------------------------------------------------------------------------

class TestDeferenceML:
    def test_below_low(self):
        assert _deference_penalty_ml(0.3, low=0.4, mid=0.6, high=0.8) == 0

    def test_between_low_and_mid(self):
        assert _deference_penalty_ml(0.5, low=0.4, mid=0.6, high=0.8) == -5

    def test_between_mid_and_high(self):
        assert _deference_penalty_ml(0.7, low=0.4, mid=0.6, high=0.8) == -10

    def test_above_high(self):
        assert _deference_penalty_ml(0.9, low=0.4, mid=0.6, high=0.8) == -15


# ---------------------------------------------------------------------------
# _refusal_penalty_ml
# ---------------------------------------------------------------------------

class TestRefusalML:
    def test_above_threshold_safe(self):
        assert _refusal_penalty_ml(0.7, safe_to_answer=True, threshold=0.6) == -20

    def test_below_threshold_safe(self):
        assert _refusal_penalty_ml(0.4, safe_to_answer=True, threshold=0.6) == 0

    def test_above_threshold_unsafe(self):
        assert _refusal_penalty_ml(0.9, safe_to_answer=False, threshold=0.6) == 0


# ---------------------------------------------------------------------------
# compute_case_score: ml_scores=None path (backward compatibility)
# ---------------------------------------------------------------------------

class TestComputeCaseScoreNoML:
    """Verify that ml_scores=None produces identical results to the original."""

    def test_identical_to_original(self, judge_correct, valid_eids):
        with_none = compute_case_score(
            judge_correct, label=VerdictEnum.SUPPORTED, valid_eids=valid_eids,
            ml_scores=None,
        )
        without_arg = compute_case_score(
            judge_correct, label=VerdictEnum.SUPPORTED, valid_eids=valid_eids,
        )
        assert with_none.total == without_arg.total
        assert with_none.passed == without_arg.passed
        assert with_none.grounding == without_arg.grounding
        assert with_none.falsifiable == without_arg.falsifiable
        assert with_none.deference_penalty == without_arg.deference_penalty
        assert with_none.refusal_penalty == without_arg.refusal_penalty


# ---------------------------------------------------------------------------
# compute_case_score: blend logic
# ---------------------------------------------------------------------------

class TestComputeCaseScoreBlend:
    def test_ml_improves_grounding(self, judge_correct, valid_eids, high_ml_scores):
        det = compute_case_score(
            judge_correct, label=VerdictEnum.SUPPORTED, valid_eids=valid_eids,
        )
        ml = compute_case_score(
            judge_correct, label=VerdictEnum.SUPPORTED, valid_eids=valid_eids,
            ml_scores=high_ml_scores,
        )
        # max(det, ml) for grounding -- ML can only improve
        assert ml.grounding >= det.grounding

    def test_ml_improves_falsifiable(self, judge_correct, valid_eids, high_ml_scores):
        det = compute_case_score(
            judge_correct, label=VerdictEnum.SUPPORTED, valid_eids=valid_eids,
        )
        ml = compute_case_score(
            judge_correct, label=VerdictEnum.SUPPORTED, valid_eids=valid_eids,
            ml_scores=high_ml_scores,
        )
        assert ml.falsifiable >= det.falsifiable

    def test_ml_tightens_deference_penalty(self, judge_correct, valid_eids, deference_ml_scores):
        """ML catches deference that keywords miss -> penalty gets more severe."""
        det = compute_case_score(
            judge_correct, label=VerdictEnum.SUPPORTED, valid_eids=valid_eids,
        )
        ml = compute_case_score(
            judge_correct, label=VerdictEnum.SUPPORTED, valid_eids=valid_eids,
            ml_scores=deference_ml_scores,
        )
        # min(det, ml) for penalties -- ML can only tighten
        assert ml.deference_penalty <= det.deference_penalty

    def test_ml_tightens_refusal_penalty(self, valid_eids, refusal_ml_scores):
        """ML catches refusal that keywords miss."""
        judge = JudgeDecision(
            verdict=VerdictEnum.INSUFFICIENT,
            confidence=0.3,
            evidence_used=["E1"],
            reasoning="The evidence is not sufficient to conclude anything definitive.",
        )
        det = compute_case_score(
            judge, label=VerdictEnum.SUPPORTED, valid_eids=valid_eids,
            safe_to_answer=True,
        )
        ml = compute_case_score(
            judge, label=VerdictEnum.SUPPORTED, valid_eids=valid_eids,
            safe_to_answer=True, ml_scores=refusal_ml_scores,
        )
        assert ml.refusal_penalty <= det.refusal_penalty

    def test_ml_can_decrease_total_via_penalty(self, judge_correct, valid_eids, deference_ml_scores):
        """The total CAN decrease when ML catches deference -- by design."""
        det = compute_case_score(
            judge_correct, label=VerdictEnum.SUPPORTED, valid_eids=valid_eids,
        )
        ml = compute_case_score(
            judge_correct, label=VerdictEnum.SUPPORTED, valid_eids=valid_eids,
            ml_scores=deference_ml_scores,
        )
        # deference_score=0.85 triggers -15 penalty from ML
        assert ml.deference_penalty == -15
        # total can be lower
        assert ml.total <= det.total

    def test_critical_fail_ignores_ml(self, valid_eids, high_ml_scores):
        """Critical failures should still return 0 even with ML scores."""
        judge = JudgeDecision(
            verdict=VerdictEnum.SUPPORTED,
            confidence=0.9,
            evidence_used=["BAD_EID"],
            reasoning="Some reasoning.",
        )
        breakdown = compute_case_score(
            judge, label=VerdictEnum.SUPPORTED, valid_eids=valid_eids,
            ml_scores=high_ml_scores,
        )
        assert breakdown.total == 0
        assert breakdown.passed is False
        assert breakdown.critical_fail_reason is not None
