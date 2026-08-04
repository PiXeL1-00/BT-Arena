"""Singleton ONNX model registry -- loads 2 models once at startup.

Models
------
* **nli** – ``cross-encoder/nli-deberta-v3-base`` for grounding entailment
  and deference / refusal detection (via constructed NLI hypotheses).
* **embed** – ``BAAI/bge-small-en-v1.5`` for semantic similarity against
  falsifiability exemplars.

Thread-safety
-------------
Tokenizer truncation is configured once in :meth:`warm_up`.  After that
call, all shared state is read-only -- ``Tokenizer.encode()`` produces a
fresh ``Encoding`` per call and ``InferenceSession.run()`` is thread-safe.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import ClassVar, Optional

import numpy as np

try:
    import onnxruntime as ort
except ImportError:  # pragma: no cover
    ort = None  # type: ignore[assignment]

try:
    from tokenizers import Tokenizer
except ImportError:  # pragma: no cover
    Tokenizer = None  # type: ignore[assignment, misc]

from app.config import settings

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Process-wide singleton managing 2 ONNX sessions + tokenizers."""

    _nli_session: ClassVar[Optional["ort.InferenceSession"]] = None
    _nli_tokenizer: ClassVar[Optional["Tokenizer"]] = None

    _embed_session: ClassVar[Optional["ort.InferenceSession"]] = None
    _embed_tokenizer: ClassVar[Optional["Tokenizer"]] = None

    _exemplar_embeddings: ClassVar[Optional[dict[str, np.ndarray]]] = None

    _loaded: ClassVar[bool] = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def warm_up(cls) -> None:
        """Load both models + pre-computed exemplar embeddings.

        Must be called once at app startup (e.g. in FastAPI lifespan).
        Raises ``FileNotFoundError`` if the models directory is missing.
        """
        if cls._loaded:
            return

        assert ort is not None, "onnxruntime is not installed"
        assert Tokenizer is not None, "tokenizers is not installed"

        models_dir = Path(settings.ml_models_dir)
        if not models_dir.is_absolute():
            # Resolve relative to the backend root (parent of app/)
            models_dir = Path(__file__).resolve().parents[3] / models_dir

        nli_dir = models_dir / "nli"
        embed_dir = models_dir / "embed"

        # Validate paths exist before loading
        for p in (nli_dir / "model.onnx", nli_dir / "tokenizer.json",
                  embed_dir / "model.onnx", embed_dir / "tokenizer.json",
                  embed_dir / "exemplars.npz"):
            if not p.exists():
                raise FileNotFoundError(str(p))

        # ONNX session options
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = settings.onnx_intra_threads
        opts.inter_op_num_threads = 1

        # --- NLI cross-encoder ---
        cls._nli_tokenizer = Tokenizer.from_file(str(nli_dir / "tokenizer.json"))
        cls._nli_tokenizer.enable_truncation(max_length=settings.ml_nli_max_tokens)
        cls._nli_tokenizer.no_padding()

        cls._nli_session = ort.InferenceSession(str(nli_dir / "model.onnx"), opts)

        # --- Embedding model ---
        cls._embed_tokenizer = Tokenizer.from_file(str(embed_dir / "tokenizer.json"))
        cls._embed_tokenizer.enable_truncation(max_length=128)
        cls._embed_tokenizer.no_padding()

        cls._embed_session = ort.InferenceSession(str(embed_dir / "model.onnx"), opts)

        # --- Pre-computed exemplar embeddings (L2-normalised) ---
        npz = np.load(str(embed_dir / "exemplars.npz"))
        cls._exemplar_embeddings = {k: npz[k] for k in npz.files}

        cls._loaded = True
        logger.info(
            "ML models loaded from %s  (NLI inputs: %s, Embed inputs: %s)",
            models_dir,
            [i.name for i in cls._nli_session.get_inputs()],
            [i.name for i in cls._embed_session.get_inputs()],
        )

    @classmethod
    def nli(cls) -> tuple["ort.InferenceSession", "Tokenizer"]:
        """Return (session, tokenizer) for the NLI cross-encoder."""
        assert cls._loaded, "ModelRegistry.warm_up() not called"
        assert cls._nli_session is not None
        assert cls._nli_tokenizer is not None
        return cls._nli_session, cls._nli_tokenizer

    @classmethod
    def embed(cls) -> tuple["ort.InferenceSession", "Tokenizer"]:
        """Return (session, tokenizer) for the embedding model."""
        assert cls._loaded, "ModelRegistry.warm_up() not called"
        assert cls._embed_session is not None
        assert cls._embed_tokenizer is not None
        return cls._embed_session, cls._embed_tokenizer

    @classmethod
    def exemplar_embeddings(cls) -> dict[str, np.ndarray]:
        """Return pre-computed exemplar embeddings keyed by dimension name."""
        assert cls._loaded, "ModelRegistry.warm_up() not called"
        assert cls._exemplar_embeddings is not None
        return cls._exemplar_embeddings
