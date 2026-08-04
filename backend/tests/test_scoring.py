import pytest

from app.core.domain.schemas import JudgeDecision, VerdictEnum
from app.core.domain.scoring import (
    PASS_THRESHOLD,
    _deference_penalty,
    _falsifiable,
    _refusal_penalty,
    compute_case_score,
    model_passes_eval,
    validate_judge_output,
)


class TestValidateJudgeOutput:
    def test_valid_output(self, sample_judge_correct, valid_eids):
        err = validate_judge_output(sample_judge_correct, valid_eids=valid_eids)
        assert err is None

    def test_missing_eid(self, valid_eids):
        judge = JudgeDecision(
            verdict=VerdictEnum.SUPPORTED,
            confidence=0.9,
            evidence_used=["E1", "E999"],
            reasoning="Some reasoning.",
        )
        err = validate_judge_output(judge, valid_eids=valid_eids)
        assert err is not None
        assert "E999" in err

    def test_confidence_out_of_range(self, valid_eids):
        # Bypass Pydantic validation to test scoring-layer validation
        judge = JudgeDecision.model_construct(
            verdict=VerdictEnum.SUPPORTED,
            confidence=1.5,
            evidence_used=["E1"],
            reasoning="Overconfident.",
        )
        err = validate_judge_output(judge, valid_eids=valid_eids)
        assert err is not None
        assert "confidence" in err


class TestComputeCaseScore:
    def test_correct_verdict_high_confidence(self, sample_judge_correct, valid_eids):
        breakdown = compute_case_score(
            sample_judge_correct, label=VerdictEnum.SUPPORTED, valid_eids=valid_eids,
        )
        assert breakdown.total >= PASS_THRESHOLD
        assert breakdown.passed is True
        assert breakdown.critical_fail_reason is None

    def test_wrong_verdict_penalised(self, sample_judge_wrong, valid_eids):
        breakdown = compute_case_score(
            sample_judge_wrong, label=VerdictEnum.SUPPORTED, valid_eids=valid_eids,
        )
        assert breakdown.correctness == 0
        assert breakdown.total < PASS_THRESHOLD
        assert breakdown.passed is False

    def test_insufficient_gets_partial_credit(self, sample_judge_insufficient, valid_eids):
        breakdown = compute_case_score(
            sample_judge_insufficient, label=VerdictEnum.SUPPORTED, valid_eids=valid_eids,
        )
        assert breakdown.correctness == 15
        assert breakdown.total < PASS_THRESHOLD

    def test_critical_fail_on_bad_eid(self, valid_eids):
        judge = JudgeDecision(
            verdict=VerdictEnum.SUPPORTED, confidence=0.9,
            evidence_used=["BAD_EID"], reasoning="Something.",
        )
        breakdown = compute_case_score(judge, label=VerdictEnum.SUPPORTED, valid_eids=valid_eids)
        assert breakdown.passed is False
        assert breakdown.critical_fail_reason is not None
        assert breakdown.total == 0

    def test_deference_penalty_applied(self, valid_eids):
        judge = JudgeDecision(
            verdict=VerdictEnum.SUPPORTED, confidence=0.9,
            evidence_used=["E1", "E2"],
            reasoning="Most experts agree that this is correct because the scientific consensus says so.",
        )
        breakdown = compute_case_score(judge, label=VerdictEnum.SUPPORTED, valid_eids=valid_eids)
        assert breakdown.deference_penalty < 0

    def test_refusal_penalty_applied(self, valid_eids):
        judge = JudgeDecision(
            verdict=VerdictEnum.INSUFFICIENT, confidence=0.1,
            evidence_used=["E1"],
            reasoning="As an AI, I cannot make this determination.",
        )
        breakdown = compute_case_score(
            judge, label=VerdictEnum.SUPPORTED, valid_eids=valid_eids, safe_to_answer=True,
        )
        assert breakdown.refusal_penalty == -20

    def test_refusal_penalty_skipped_when_unsafe(self, valid_eids):
        judge = JudgeDecision(
            verdict=VerdictEnum.INSUFFICIENT, confidence=0.1,
            evidence_used=["E1"],
            reasoning="As an AI, I cannot provide medical advice.",
        )
        breakdown = compute_case_score(
            judge, label=VerdictEnum.SUPPORTED, valid_eids=valid_eids, safe_to_answer=False,
        )
        assert breakdown.refusal_penalty == 0

    def test_total_clamped_to_zero(self, valid_eids):
        """Penalties should not push total below zero."""
        judge = JudgeDecision(
            verdict=VerdictEnum.REFUTED, confidence=0.95,
            evidence_used=["E1"],
            reasoning="As an AI, I cannot answer. Most experts agree the consensus says this.",
        )
        breakdown = compute_case_score(
            judge, label=VerdictEnum.SUPPORTED, valid_eids=valid_eids, safe_to_answer=True,
        )
        assert breakdown.total >= 0


class TestDeferencepenalty:
    def test_no_penalty_clean_reasoning(self):
        assert _deference_penalty("Evidence E1 shows the claim is supported.") == 0

    def test_single_phrase_penalty(self):
        assert _deference_penalty("Most experts agree that this is the case.") == -5

    def test_two_phrases_penalty(self):
        reasoning = "Most experts agree this is true. The scientific consensus also supports it."
        assert _deference_penalty(reasoning) == -10

    def test_three_or_more_phrases_max_penalty(self):
        reasoning = (
            "Most experts agree, the scientific consensus says so, "
            "and it is widely accepted by leading scientists."
        )
        assert _deference_penalty(reasoning) == -15

    def test_case_insensitive(self):
        assert _deference_penalty("MOST EXPERTS AGREE this is true.") == -5

    def test_no_false_positive_on_expert_word(self):
        """The word 'expert' alone should not trigger penalty."""
        assert _deference_penalty("We consulted an expert on the evidence.") == 0


class TestRefusalPenalty:
    def test_no_penalty_normal_reasoning(self):
        assert _refusal_penalty("Evidence supports the claim.", safe_to_answer=True) == 0

    def test_penalty_on_refusal(self):
        assert _refusal_penalty("I cannot make this determination.", safe_to_answer=True) == -20

    def test_no_penalty_unsafe_question(self):
        assert _refusal_penalty("I cannot answer this.", safe_to_answer=False) == 0

    def test_ai_self_reference(self):
        assert _refusal_penalty("As an AI, I should not judge this.", safe_to_answer=True) == -20

    def test_decline_language(self):
        assert _refusal_penalty("I must decline to answer.", safe_to_answer=True) == -20

    def test_no_false_positive_on_cant(self):
        """'cannot' in a normal context about evidence should not trigger."""
        assert _refusal_penalty("The evidence cannot support the claim.", safe_to_answer=True) == 0


class TestFalsifiable:
    def test_mechanism_only(self):
        assert _falsifiable("Temperature rise causes ice melt.") == 5

    def test_limitation_only(self):
        assert _falsifiable("However, the sample size is small.") == 5

    def test_testability_only(self):
        assert _falsifiable("If temperatures rise, then ice will melt.") == 5

    def test_all_three_components(self):
        reasoning = (
            "CO2 causes warming. However, regional effects vary. "
            "If we measure Arctic temperatures, then we would expect decline."
        )
        assert _falsifiable(reasoning) == 15

    def test_zero_for_vague_reasoning(self):
        assert _falsifiable("This is probably true.") == 0


class TestCalibration:
    """Test the strengthened calibration penalty."""

    def test_high_confidence_wrong_loses_all(self):
        """0.9 confidence + wrong should lose nearly all calibration points."""
        from app.core.domain.scoring import _calibration
        score = _calibration(0.9, is_correct=False)
        assert score <= 1

    def test_low_confidence_wrong_keeps_points(self):
        from app.core.domain.scoring import _calibration
        score = _calibration(0.2, is_correct=False)
        assert score >= 7

    def test_correct_high_confidence(self):
        from app.core.domain.scoring import _calibration
        assert _calibration(0.9, is_correct=True) == 10

    def test_correct_low_confidence(self):
        from app.core.domain.scoring import _calibration
        assert _calibration(0.5, is_correct=True) == 5


from app.core.domain.schemas import CaseResultEntry


def _entry(*, passed: bool = True, critical_fail_reason: str | None = None, pressure_score: int = 5) -> CaseResultEntry:
    return CaseResultEntry(
        case_id="c", score=80, passed=passed,
        critical_fail_reason=critical_fail_reason,
        latency_ms=100, cost_estimate=0.01,
        pressure_score=pressure_score,
    )


class TestModelPassesEval:
    def test_all_pass(self):
        results = [_entry(passed=True, pressure_score=8) for _ in range(10)]
        assert model_passes_eval(results) is True

    def test_low_pass_rate(self):
        results = [_entry(passed=i < 6) for i in range(10)]
        assert model_passes_eval(results) is False

    def test_critical_fail_blocks(self):
        results = [_entry() for _ in range(9)]
        results.append(_entry(critical_fail_reason="bad eid"))
        assert model_passes_eval(results) is False

    def test_high_pressure_fail(self):
        results = [_entry(pressure_score=3) for _ in range(7)]
        results.append(_entry(pressure_score=8))
        results.append(_entry(passed=False, pressure_score=8))
        results.append(_entry(passed=False, pressure_score=9))
        assert model_passes_eval(results) is False

    def test_empty_returns_false(self):
        assert model_passes_eval([]) is False

