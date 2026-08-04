#!/usr/bin/env python
"""Export HuggingFace models to ONNX + INT8 for production inference.

**Dev-only** -- requires ``torch``, ``optimum[onnxruntime]``, and
``sentence-transformers``.  These are NOT installed in production.

Usage::

    pip install -r requirements-export.txt
    python -m scripts.export_onnx_models --output-dir models

The output directory will contain:

    models/
      manifest.json
      nli/
        model.onnx          # INT8 quantised
        tokenizer.json
      embed/
        model.onnx           # INT8 quantised
        tokenizer.json
        exemplars.npz        # pre-computed L2-normalised exemplar embeddings
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import shutil
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

# Model identifiers on HuggingFace
NLI_MODEL = "cross-encoder/nli-deberta-v3-base"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"


def _export_nli(output_dir: Path) -> str:
    """Export the NLI cross-encoder to ONNX + INT8.  Returns model commit SHA."""
    from optimum.exporters.onnx import main_export
    from optimum.onnxruntime import ORTModelForSequenceClassification
    from transformers import AutoTokenizer

    nli_dir = output_dir / "nli"
    nli_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = output_dir / "_tmp_nli"

    logger.info("Exporting NLI model: %s", NLI_MODEL)
    main_export(NLI_MODEL, output=tmp_dir, task="text-classification")

    # Quantise to INT8
    logger.info("Quantising NLI model to INT8 ...")
    from onnxruntime.quantization import QuantType, quantize_dynamic

    quantize_dynamic(
        str(tmp_dir / "model.onnx"),
        str(nli_dir / "model.onnx"),
        weight_type=QuantType.QInt8,
    )

    # Save fast tokenizer JSON
    tok = AutoTokenizer.from_pretrained(NLI_MODEL)
    tok.backend_tokenizer.save(str(nli_dir / "tokenizer.json"))

    # Determine commit hash for manifest
    commit = _model_hash(nli_dir / "model.onnx")

    shutil.rmtree(tmp_dir, ignore_errors=True)
    logger.info("NLI model exported to %s", nli_dir)
    return commit


def _export_embed(output_dir: Path) -> str:
    """Export the embedding model to ONNX + INT8.  Returns model commit SHA."""
    from optimum.exporters.onnx import main_export
    from transformers import AutoTokenizer

    embed_dir = output_dir / "embed"
    embed_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = output_dir / "_tmp_embed"

    logger.info("Exporting embed model: %s", EMBED_MODEL)
    main_export(EMBED_MODEL, output=tmp_dir, task="feature-extraction")

    # Quantise to INT8
    logger.info("Quantising embed model to INT8 ...")
    from onnxruntime.quantization import QuantType, quantize_dynamic

    quantize_dynamic(
        str(tmp_dir / "model.onnx"),
        str(embed_dir / "model.onnx"),
        weight_type=QuantType.QInt8,
    )

    # Save fast tokenizer JSON
    tok = AutoTokenizer.from_pretrained(EMBED_MODEL)
    tok.backend_tokenizer.save(str(embed_dir / "tokenizer.json"))

    commit = _model_hash(embed_dir / "model.onnx")

    shutil.rmtree(tmp_dir, ignore_errors=True)
    logger.info("Embed model exported to %s", embed_dir)
    return commit


def _precompute_exemplars(output_dir: Path) -> None:
    """Embed all exemplar sentences and save as L2-normalised .npz."""
    import numpy as np
    import onnxruntime as ort
    from tokenizers import Tokenizer

    from app.infra.ml.exemplars import (
        LIMITATION_EXEMPLARS,
        MECHANISM_EXEMPLARS,
        TESTABILITY_EXEMPLARS,
    )

    embed_dir = output_dir / "embed"
    session = ort.InferenceSession(str(embed_dir / "model.onnx"))
    tokenizer = Tokenizer.from_file(str(embed_dir / "tokenizer.json"))
    tokenizer.enable_truncation(max_length=128)
    tokenizer.no_padding()

    def _embed_batch(texts: list[str]) -> np.ndarray:
        embeddings = []
        expected_names = {inp.name for inp in session.get_inputs()}
        for text in texts:
            encoding = tokenizer.encode(text)
            input_ids = np.array([encoding.ids], dtype=np.int64)
            attention_mask = np.array([encoding.attention_mask], dtype=np.int64)
            feed: dict[str, np.ndarray] = {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
            }
            if "token_type_ids" in expected_names:
                feed["token_type_ids"] = np.zeros_like(input_ids)
            outputs = session.run(None, feed)
            hidden = outputs[0]  # (1, seq_len, hidden_dim)
            emb = hidden[0, 0, :]  # CLS token
            norm = np.linalg.norm(emb)
            if norm > 0:
                emb = emb / norm
            embeddings.append(emb)
        return np.stack(embeddings)

    logger.info("Pre-computing exemplar embeddings ...")
    mech = _embed_batch(MECHANISM_EXEMPLARS)
    lim = _embed_batch(LIMITATION_EXEMPLARS)
    test = _embed_batch(TESTABILITY_EXEMPLARS)

    npz_path = embed_dir / "exemplars.npz"
    np.savez(str(npz_path), mechanism=mech, limitation=lim, testability=test)
    logger.info(
        "Exemplar embeddings saved to %s  (mechanism=%s, limitation=%s, testability=%s)",
        npz_path, mech.shape, lim.shape, test.shape,
    )


def _model_hash(path: Path) -> str:
    """SHA-256 of an ONNX file (first 12 hex chars)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def main() -> None:
    parser = argparse.ArgumentParser(description="Export HF models to ONNX + INT8")
    parser.add_argument(
        "--output-dir", type=str, default="models",
        help="Output directory for ONNX models (default: models/)",
    )
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    nli_hash = _export_nli(output_dir)
    embed_hash = _export_embed(output_dir)
    _precompute_exemplars(output_dir)

    manifest = {
        "nli": {"model": NLI_MODEL, "hash": nli_hash, "quantized": "int8"},
        "embed": {"model": EMBED_MODEL, "hash": embed_hash, "quantized": "int8"},
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    logger.info("Manifest written to %s", manifest_path)
    logger.info("Done!  Copy %s to your production server.", output_dir)


if __name__ == "__main__":
    # Ensure backend/ is on sys.path so `from app.infra.ml.exemplars` works
    backend_root = Path(__file__).resolve().parent.parent
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))
    main()
