"""ML scoring functions -- ONNX inference for grounding, falsifiability,
deference and refusal detection.

All heavy computation runs synchronously inside a bounded
:class:`~concurrent.futures.ThreadPoolExecutor`.  The public async entry
point :func:`compute_ml_scores_async` wraps this for non-blocking use
from the async usecase layer.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import numpy as np

from app.config import settings
from app.core.domain.schemas import MLScores

from .model_registry import ModelRegistry

logger = logging.getLogger(__name__)

# Bounded executor so ONNX threads don't saturate all CPU cores.
# max_workers * onnx_intra_threads should not exceed available cores.
_ml_executor = ThreadPoolExecutor(
    max_workers=settings.ml_max_workers,
    thread_name_prefix="ml-scorer",
)

# NLI label indices for cross-encoder/nli-deberta-v3-base
_CONTRADICTION_IDX = 0
_NEUTRAL_IDX = 1
_ENTAILMENT_IDX = 2

# Hypotheses for zero-shot-style deference / refusal detection via NLI
_DEFERENCE_HYPOTHESIS = "This text appeals to authority or expert consensus rather than evaluating evidence directly"
_REFUSAL_HYPOTHESIS = "The author refuses to answer, declines to evaluate, or states inability to respond"


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _softmax(logits: np.ndarray) -> np.ndarray:
    """Numerically stable softmax (no scipy needed)."""
    shifted = logits - np.max(logits, axis=-1, keepdims=True)
    exp = np.exp(shifted)
    return exp / np.sum(exp, axis=-1, keepdims=True)


def _build_feed_dict(
    session: "ort.InferenceSession",  # noqa: F821
    input_ids: np.ndarray,
    attention_mask: np.ndarray,
) -> dict[str, np.ndarray]:
    """Build ONNX feed dict, adding token_type_ids if model expects it."""
    feed: dict[str, np.ndarray] = {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
    }
    expected_names = {inp.name for inp in session.get_inputs()}
    if "token_type_ids" in expected_names:
        feed["token_type_ids"] = np.zeros_like(input_ids)
    return feed


def _nli_entailment_prob(
    session: "ort.InferenceSession",  # noqa: F821
    tokenizer: "Tokenizer",  # noqa: F821
    premise: str,
    hypothesis: str,
) -> float:
    """Run NLI cross-encoder and return entailment probability."""
    encoding = tokenizer.encode(premise, hypothesis)
    input_ids = np.array([encoding.ids], dtype=np.int64)
    attention_mask = np.array([encoding.attention_mask], dtype=np.int64)

    feed = _build_feed_dict(session, input_ids, attention_mask)
    outputs = session.run(None, feed)
    logits = outputs[0]  # shape (1, 3)
    probs = _softmax(logits)
    return float(probs[0, _ENTAILMENT_IDX])


def _embed_text(
    session: "ort.InferenceSession",  # noqa: F821
    tokenizer: "Tokenizer",  # noqa: F821
    text: str,
) -> np.ndarray:
    """Embed text via BGE-small, returns L2-normalised (384,) vector."""
    encoding = tokenizer.encode(text)
    input_ids = np.array([encoding.ids], dtype=np.int64)
    attention_mask = np.array([encoding.attention_mask], dtype=np.int64)

    feed = _build_feed_dict(session, input_ids, attention_mask)
    outputs = session.run(None, feed)
    hidden_states = outputs[0]  # (1, seq_len, hidden_dim)

    # CLS pooling: first token
    embedding: np.ndarray = hidden_states[0, 0, :]

    # L2 normalise (BGE requires this)
    norm = np.linalg.norm(embedding)
    if norm > 0:
        embedding = embedding / norm
    return embedding


def _max_cosine_sim(query_emb: np.ndarray, exemplar_embs: np.ndarray) -> float:
    """Max cosine similarity between query and exemplar embeddings.

    Both must be L2-normalised so cosine sim = dot product.
    """
    sims = exemplar_embs @ query_emb  # (n_exemplars,)
    return float(np.max(sims))


# ---------------------------------------------------------------------------
# Public scoring functions
# ---------------------------------------------------------------------------

def compute_grounding_nli(
    reasoning: str,
    evidence_used: list[str],
    evidence_map: dict[str, str],
) -> float:
    """Average NLI entailment between each cited evidence summary and reasoning.

    Returns 0.0 when no evidence summaries are available.
    """
    session, tokenizer = ModelRegistry.nli()
    scores: list[float] = []
    for eid in evidence_used:
        summary = evidence_map.get(eid, "")
        if not summary:
            continue
        prob = _nli_entailment_prob(session, tokenizer, summary, reasoning)
        scores.append(prob)
    return sum(scores) / len(scores) if scores else 0.0


def compute_falsifiable_semantic(reasoning: str) -> tuple[float, float, float]:
    """Cosine similarity of reasoning against mechanism / limitation / testability exemplars."""
    session, tokenizer = ModelRegistry.embed()
    exemplars = ModelRegistry.exemplar_embeddings()

    query_emb = _embed_text(session, tokenizer, reasoning)

    mechanism_sim = _max_cosine_sim(query_emb, exemplars["mechanism"])
    limitation_sim = _max_cosine_sim(query_emb, exemplars["limitation"])
    testability_sim = _max_cosine_sim(query_emb, exemplars["testability"])

    return mechanism_sim, limitation_sim, testability_sim


def compute_deference_and_refusal(reasoning: str) -> tuple[float, float]:
    """NLI entailment scores for deference and refusal hypotheses."""
    session, tokenizer = ModelRegistry.nli()
    deference = _nli_entailment_prob(session, tokenizer, reasoning, _DEFERENCE_HYPOTHESIS)
    refusal = _nli_entailment_prob(session, tokenizer, reasoning, _REFUSAL_HYPOTHESIS)
    return deference, refusal


def compute_ml_scores(
    reasoning: str,
    evidence_used: list[str],
    evidence_map: dict[str, str],
) -> Optional[MLScores]:
    """Compute all ML sub-scores.  Returns ``None`` on any failure so the
    caller falls back to the keyword-only scoring path.
    """
    try:
        grounding = compute_grounding_nli(reasoning, evidence_used, evidence_map)
        mech, lim, test = compute_falsifiable_semantic(reasoning)
        deference, refusal = compute_deference_and_refusal(reasoning)

        return MLScores(
            grounding_entailment=grounding,
            falsifiable_mechanism=mech,
            falsifiable_limitation=lim,
            falsifiable_testability=test,
            deference_score=deference,
            refusal_score=refusal,
        )
    except Exception:
        logger.exception("ML scoring failed -- falling back to keyword-only")
        return None


# ---------------------------------------------------------------------------
# Async wrapper (for use from async usecase layer)
# ---------------------------------------------------------------------------

async def compute_ml_scores_async(
    reasoning: str,
    evidence_used: list[str],
    evidence_map: dict[str, str],
) -> Optional[MLScores]:
    """Non-blocking wrapper that runs ONNX inference in the bounded thread pool."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _ml_executor,
        compute_ml_scores,
        reasoning,
        evidence_used,
        evidence_map,
    )
