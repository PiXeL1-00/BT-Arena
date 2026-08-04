import json

import pytest

from app.core.domain.schemas import JudgeDecision, VerdictEnum
from app.core.domain.scoring import validate_judge_output


class TestJudgeDecisionParsing:
    def test_valid_json_parses(self):
        raw = json.dumps({
            "verdict": "SUPPORTED", "confidence": 0.85,
            "evidence_used": ["E1"], "reasoning": "Solid evidence supports the claim.",
        })
        judge = JudgeDecision(**json.loads(raw))
        assert judge.verdict == VerdictEnum.SUPPORTED
        assert judge.confidence == 0.85

    def test_missing_field_raises(self):
        raw = json.dumps({"verdict": "SUPPORTED", "confidence": 0.85})
        with pytest.raises(Exception):
            JudgeDecision(**json.loads(raw))

    def test_invalid_verdict_value(self):
        with pytest.raises(ValueError):
            JudgeDecision(verdict="MAYBE", confidence=0.5, evidence_used=[], reasoning="Dunno.")

    def test_confidence_boundary_zero(self):
        judge = JudgeDecision(
            verdict=VerdictEnum.INSUFFICIENT, confidence=0.0,
            evidence_used=[], reasoning="No evidence at all.",
        )
        assert judge.confidence == 0.0

    def test_confidence_boundary_one(self):
        judge = JudgeDecision(
            verdict=VerdictEnum.SUPPORTED, confidence=1.0,
            evidence_used=["E1"], reasoning="Absolutely certain.",
        )
        assert judge.confidence == 1.0


class TestValidateJudgeOutputEdgeCases:
    def test_empty_evidence_is_valid(self):
        judge = JudgeDecision(
            verdict=VerdictEnum.INSUFFICIENT, confidence=0.3,
            evidence_used=[], reasoning="No evidence cited.",
        )
        assert validate_judge_output(judge, valid_eids={"E1", "E2"}) is None

    def test_all_valid_eids(self):
        judge = JudgeDecision(
            verdict=VerdictEnum.SUPPORTED, confidence=0.8,
            evidence_used=["E1", "E2", "E3"], reasoning="All evidence checked out.",
        )
        assert validate_judge_output(judge, valid_eids={"E1", "E2", "E3", "E4"}) is None

    def test_partial_invalid_eids(self):
        judge = JudgeDecision(
            verdict=VerdictEnum.SUPPORTED, confidence=0.8,
            evidence_used=["E1", "FAKE"], reasoning="Mixed references.",
        )
        err = validate_judge_output(judge, valid_eids={"E1", "E2"})
        assert err is not None
        assert "FAKE" in err
