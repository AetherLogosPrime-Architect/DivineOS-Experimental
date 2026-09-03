"""Embed text through a light runtime, for callers that run once per turn.

## Why this exists

Embedding a query used to cost about four seconds, and the measurement
(2026-09-03) put nearly all of it in the IMPORTS rather than in the work:

    import torch                  1588 ms
    import transformers           1957 ms
    import sentence_transformers  2887 ms
    construct the model            395 ms
    encode one short query         154 ms

So the model was never slow. Hauling the training-sized toolchain into memory
to do one small forward pass was slow. The proactive recall surface runs in a
FRESH PROCESS on every turn and would pay that toll every single time.

``import onnxruntime`` costs 171 ms against sentence-transformers' 2887 ms —
the same arithmetic through a doorway one seventeenth the size.

## What this is not

It is not a different model, and it must never become one. The corpus index
was built with the original; if this returned even slightly different vectors,
every search would still return results, still look plausible, and quietly be
comparing against a different meaning-space. That is the failure shape this
substrate keeps finding — the one that never announces itself. So the export
script verifies agreement against the original and refuses to leave a drifting
export on disk, and ``embed_query`` falls back to the original library rather
than guessing when the export is absent.

Walk-record: decision ace4bd3a.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_MODEL_DIR = Path.home() / ".divineos" / "models" / MODEL_NAME
_MAX_TOKENS = 256

_session: Any = None
_tokenizer: Any = None
_loaded_from: Path | None = None


def artifacts_present(model_dir: Path | None = None) -> bool:
    """True when both exported pieces are on disk."""
    d = model_dir or DEFAULT_MODEL_DIR
    return (d / "model.onnx").exists() and (d / "tokenizer.json").exists()


def _ensure_loaded(model_dir: Path) -> bool:
    global _session, _tokenizer, _loaded_from
    if _session is not None and _loaded_from == model_dir:
        return True
    if not artifacts_present(model_dir):
        return False
    try:
        import onnxruntime as ort
        from tokenizers import Tokenizer

        opts = ort.SessionOptions()
        # One thread. This runs alongside a live session rather than as a batch
        # job, so grabbing every core to save milliseconds on one short query
        # would take them from whatever else the machine is doing.
        opts.intra_op_num_threads = 1
        opts.inter_op_num_threads = 1
        _session = ort.InferenceSession(
            str(model_dir / "model.onnx"),
            sess_options=opts,
            providers=["CPUExecutionProvider"],
        )
        _tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
        _tokenizer.enable_truncation(max_length=_MAX_TOKENS)
        _loaded_from = model_dir
        return True
    except Exception:  # noqa: BLE001 - a missing/broken runtime falls back, never crashes the turn
        _session = None
        _tokenizer = None
        _loaded_from = None
        return False


def embed_texts_onnx(texts: list[str], model_dir: Path | None = None):
    """Return an array of unit-length vectors, or None if unavailable.

    Mean-pools the token vectors under the attention mask and normalises —
    the same two steps the original library performs for this model. Both are
    reproduced here rather than imported, which is exactly why the export
    script checks the output against the original instead of trusting that
    they match.
    """
    d = model_dir or DEFAULT_MODEL_DIR
    if not texts or not _ensure_loaded(d):
        return None
    encs = [_tokenizer.encode(t) for t in texts]
    width = max(len(e.ids) for e in encs)
    ids = np.zeros((len(encs), width), dtype=np.int64)
    mask = np.zeros((len(encs), width), dtype=np.int64)
    for row, enc in enumerate(encs):
        n = len(enc.ids)
        ids[row, :n] = enc.ids
        mask[row, :n] = enc.attention_mask
    feeds = {
        "input_ids": ids,
        "attention_mask": mask,
        "token_type_ids": np.zeros_like(ids),
    }
    supplied = {i.name for i in _session.get_inputs()}
    feeds = {k: v for k, v in feeds.items() if k in supplied}
    hidden = _session.run(None, feeds)[0]
    m = mask[..., None].astype(np.float32)
    pooled = (hidden * m).sum(axis=1) / np.clip(m.sum(axis=1), 1e-9, None)
    norms = np.linalg.norm(pooled, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return (pooled / norms).astype(np.float32)


def embed_query(text: str) -> list[float] | None:
    """Embed one query the fast way, falling back to the original library.

    The fallback is deliberate rather than defensive: on a machine where the
    export has not been run, a slow correct answer beats a fast absent one,
    and the caller should never have to know which path served it.
    """
    vec = embed_texts_onnx([text])
    if vec is not None:
        return [float(x) for x in vec[0]]
    from divineos.core.semantic_store import embed

    return embed(text)
