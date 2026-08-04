from __future__ import annotations

import tomllib

import pytest
import tomli_w

from app.infra.debate.toml_serde import dict_to_toml, toml_to_dict


class TestRoundTripProposal:
    PROPOSAL = {
        "proposed_verdict": "SUPPORTED",
        "evidence_used": ["E1", "E2"],
        "key_points": ["Evidence strongly supports claim"],
        "uncertainties": ["Sample size limited"],
        "what_would_change_my_mind": ["Counter-evidence from E3"],
    }

    def test_round_trip(self):
        assert toml_to_dict(dict_to_toml(self.PROPOSAL)) == self.PROPOSAL

    def test_toml_output_is_valid(self):
        parsed = tomllib.loads(dict_to_toml(self.PROPOSAL))
        assert parsed["proposed_verdict"] == "SUPPORTED"


class TestRoundTripQuestionsMessage:
    QUESTIONS = {
        "questions": [
            {"to": "Heretic", "q": "How do you reconcile E1?", "evidence_refs": ["E1"]},
            {"to": "Heretic", "q": "What about the date gap?", "evidence_refs": ["E2"]},
        ],
    }

    def test_round_trip(self):
        assert toml_to_dict(dict_to_toml(self.QUESTIONS)) == self.QUESTIONS

    def test_array_of_tables_syntax(self):
        assert "[[questions]]" in dict_to_toml(self.QUESTIONS)


class TestRoundTripAnswersMessage:
    ANSWERS = {
        "answers": [
            {"q": "How?", "a": "E1 is contextual", "evidence_refs": ["E1"], "admission": "none"},
            {"q": "Gap?", "a": "Not significant", "evidence_refs": ["E2"], "admission": "uncertain"},
        ],
    }

    def test_round_trip(self):
        assert toml_to_dict(dict_to_toml(self.ANSWERS)) == self.ANSWERS


class TestRoundTripRevision:
    REVISION = {
        "final_proposed_verdict": "SUPPORTED",
        "evidence_used": ["E1", "E2"],
        "what_i_changed": [],
        "remaining_disagreements": [],
        "confidence": 0.9,
    }

    def test_round_trip(self):
        assert toml_to_dict(dict_to_toml(self.REVISION)) == self.REVISION

    def test_confidence_stays_float(self):
        assert "0.9" in dict_to_toml(self.REVISION)


class TestRoundTripDisputeQuestionsMessage:
    DISPUTE_Q = {"questions": [{"q": "Final decisive question", "evidence_refs": ["E1"]}]}

    def test_round_trip(self):
        assert toml_to_dict(dict_to_toml(self.DISPUTE_Q)) == self.DISPUTE_Q


class TestRoundTripDisputeAnswersMessage:
    DISPUTE_A = {"answers": [{"q": "Question?", "a": "My answer", "evidence_refs": ["E1"], "admission": "none"}]}

    def test_round_trip(self):
        assert toml_to_dict(dict_to_toml(self.DISPUTE_A)) == self.DISPUTE_A


# --- fence stripping ---

class TestFenceStripping:
    SIMPLE = {"key": "value", "nums": [1, 2, 3]}

    def test_toml_fenced_block(self):
        inner = tomli_w.dumps(self.SIMPLE)
        assert toml_to_dict(f"```toml\n{inner}```") == self.SIMPLE

    def test_generic_fenced_block(self):
        inner = tomli_w.dumps(self.SIMPLE)
        assert toml_to_dict(f"```\n{inner}```") == self.SIMPLE

    def test_fenced_with_extra_whitespace(self):
        inner = tomli_w.dumps(self.SIMPLE)
        assert toml_to_dict(f"```toml  \n{inner}\n```") == self.SIMPLE


# --- mixed output ---

class TestMixedOutputExtraction:

    def test_preamble_then_toml(self):
        text = (
            "Here is my analysis:\n"
            "I think the evidence supports the claim.\n"
            "\n"
            'proposed_verdict = "SUPPORTED"\n'
            'evidence_used = ["E1"]\n'
            'key_points = ["good evidence"]\n'
            "uncertainties = []\n"
            'what_would_change_my_mind = ["more data"]\n'
        )
        result = toml_to_dict(text)
        assert result["proposed_verdict"] == "SUPPORTED"
        assert result["evidence_used"] == ["E1"]

    def test_preamble_then_fenced_toml(self):
        text = (
            "Sure, here is the output:\n"
            "```toml\n"
            'verdict = "REFUTED"\n'
            "confidence = 0.75\n"
            'evidence_used = ["E2"]\n'
            'reasoning = "Evidence contradicts"\n'
            "```\n"
        )
        result = toml_to_dict(text)
        assert result["verdict"] == "REFUTED"
        assert result["confidence"] == 0.75


# --- edge cases ---

class TestEdgeCases:
    def test_empty_arrays(self):
        data = {"items": [], "name": "test"}
        assert toml_to_dict(dict_to_toml(data)) == data

    def test_special_characters_in_strings(self):
        data = {"text": 'He said "hello" and it\'s fine', "path": "C:\\Users\\test"}
        assert toml_to_dict(dict_to_toml(data)) == data

    def test_float_precision(self):
        data = {"confidence": 0.85, "score": 1.0}
        result = toml_to_dict(dict_to_toml(data))
        assert result["confidence"] == pytest.approx(0.85)
        assert result["score"] == pytest.approx(1.0)

    def test_integer_confidence_converted_to_float(self):
        assert "0.0" in dict_to_toml({"confidence": 0})

    def test_none_values_stripped(self):
        data = {"key": "value", "optional": None, "nested": {"a": 1, "b": None}}
        result = toml_to_dict(dict_to_toml(data))
        assert "optional" not in result
        assert "b" not in result["nested"]

    def test_invalid_toml_raises_value_error(self):
        with pytest.raises(ValueError, match="Could not parse TOML"):
            toml_to_dict("this is not valid {{}} TOML at all }{")

    def test_empty_string_returns_empty_dict(self):
        assert toml_to_dict("") == {}

    def test_pure_json_not_valid_toml(self):
        with pytest.raises(ValueError):
            toml_to_dict('{"key": "value"}')
