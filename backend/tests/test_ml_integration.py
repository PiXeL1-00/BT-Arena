"""Integration tests for the ML scoring infra layer.

These tests require real ONNX models in the ``models/`` directory.
Skip them in CI by not exporting models or by running::

    pytest -m "not ml"

To run them locally::

    python -m scripts.export_onnx_models --output-dir models
    pytest -m ml
"""

from __future__ import annotations

import pytest

# Mark all tests in this module with 'ml'
pytestmark = pytest.mark.ml


def _models_available() -> bool:
    """Check whether ONNX models have been exported."""
    from pathlib import Path

    models_dir = Path(__file__).resolve().parents[1] / "models"
    return (
        (models_dir / "nli" / "model.onnx").exists()
        and (models_dir / "embed" / "model.onnx").exists()
        and (models_dir / "embed" / "exemplars.npz").exists()
    )


skip_no_models = pytest.mark.skipif(
    not _models_available(),
    reason="ONNX models not exported -- run scripts/export_onnx_models.py first",
)


@skip_no_models
class TestModelRegistry:
    def test_warm_up(self):
        from app.infra.ml.model_registry import ModelRegistry

        ModelRegistry._loaded = False  # reset for test isolation
        ModelRegistry.warm_up()
        assert ModelRegistry._loaded is True

    def test_nli_returns_session_and_tokenizer(self):
        from app.infra.ml.model_registry import ModelRegistry

        if not ModelRegistry._loaded:
            ModelRegistry.warm_up()
        session, tokenizer = ModelRegistry.nli()
        assert session is not None
        assert tokenizer is not None

    def test_embed_returns_session_and_tokenizer(self):
        from app.infra.ml.model_registry import ModelRegistry

        if not ModelRegistry._loaded:
            ModelRegistry.warm_up()
        session, tokenizer = ModelRegistry.embed()
        assert session is not None
        assert tokenizer is not None

    def test_exemplar_embeddings_loaded(self):
        from app.infra.ml.model_registry import ModelRegistry

        if not ModelRegistry._loaded:
            ModelRegistry.warm_up()
        exemplars = ModelRegistry.exemplar_embeddings()
        assert "mechanism" in exemplars
        assert "limitation" in exemplars
        assert "testability" in exemplars
        # Should be 2D arrays with shape (n_exemplars, hidden_dim)
        for key in ("mechanism", "limitation", "testability"):
            assert exemplars[key].ndim == 2
            assert exemplars[key].shape[1] > 0


@skip_no_models
class TestScorerFunctions:
    def test_compute_grounding_nli(self):
        from app.infra.ml.model_registry import ModelRegistry
        from app.infra.ml.scorer import compute_grounding_nli

        if not ModelRegistry._loaded:
            ModelRegistry.warm_up()

        score = compute_grounding_nli(
            reasoning="The data clearly shows rising temperatures caused ice melt.",
            evidence_used=["E1"],
            evidence_map={"E1": "Temperature data shows 2C increase since 1990."},
        )
        assert 0.0 <= score <= 1.0

    def test_compute_falsifiable_semantic(self):
        from app.infra.ml.model_registry import ModelRegistry
        from app.infra.ml.scorer import compute_falsifiable_semantic

        if not ModelRegistry._loaded:
            ModelRegistry.warm_up()

        mech, lim, test = compute_falsifiable_semantic(
            "CO2 causes warming. However, the sample is small. "
            "If we measure Arctic temperatures we would expect decline."
        )
        assert 0.0 <= mech <= 1.0
        assert 0.0 <= lim <= 1.0
        assert 0.0 <= test <= 1.0

    def test_compute_deference_and_refusal(self):
        from app.infra.ml.model_registry import ModelRegistry
        from app.infra.ml.scorer import compute_deference_and_refusal

        if not ModelRegistry._loaded:
            ModelRegistry.warm_up()

        deference, refusal = compute_deference_and_refusal(
            "Most experts agree this is well established."
        )
        assert 0.0 <= deference <= 1.0
        assert 0.0 <= refusal <= 1.0

    def test_compute_ml_scores_returns_mlscores(self):
        from app.core.domain.schemas import MLScores
        from app.infra.ml.model_registry import ModelRegistry
        from app.infra.ml.scorer import compute_ml_scores

        if not ModelRegistry._loaded:
            ModelRegistry.warm_up()

        result = compute_ml_scores(
            reasoning="Evidence E1 shows the mechanism leads to the outcome.",
            evidence_used=["E1"],
            evidence_map={"E1": "Lab study shows causal link."},
        )
        assert isinstance(result, MLScores)
        assert 0.0 <= result.grounding_entailment <= 1.0
        assert 0.0 <= result.deference_score <= 1.0

    def test_compute_ml_scores_empty_evidence(self):
        from app.infra.ml.model_registry import ModelRegistry
        from app.infra.ml.scorer import compute_ml_scores

        if not ModelRegistry._loaded:
            ModelRegistry.warm_up()

        result = compute_ml_scores(
            reasoning="Some reasoning.",
            evidence_used=[],
            evidence_map={},
        )
        assert result is not None
        assert result.grounding_entailment == 0.0

    def test_long_reasoning_is_truncated_without_error(self):
        from app.infra.ml.model_registry import ModelRegistry
        from app.infra.ml.scorer import compute_ml_scores

        if not ModelRegistry._loaded:
            ModelRegistry.warm_up()

        long_reasoning = "This is a test sentence. " * 500  # ~3000 tokens
        result = compute_ml_scores(
            reasoning=long_reasoning,
            evidence_used=["E1"],
            evidence_map={"E1": "Short summary."},
        )
        assert result is not None
