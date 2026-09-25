"""The same sentence vectors, without the seventeen-second import.

Measured 2026-09-24: loading sentence-transformers costs 17s in every fresh
process (16.4s of it is the import itself, by ``python -X importtime``), and
the compose hook is a fresh process every turn. That cost is why the memory
link was unwired on 2026-09-20 (6e72eb15): the hook stopped returning and, being
fail-open, looked exactly like an ordinary quiet turn.

This runs the same model, all-MiniLM-L6-v2, as plain numpy over the weights
already in the local Hugging Face cache: BERT with exact GELU, mean pooling over
the attention mask, L2-normalised, truncated at the model's own 256 tokens.
Against sentence-transformers on the same sentences the largest difference
measured was 1.3e-7 (cosine 1.0000000). It loads in about 0.3s.

One code path. If the cached weights are missing this raises
``EmbedderUnavailable`` and says why; it never reaches for the heavy toolkit,
because that fallback is the outage this module exists to end. Nothing is ever
downloaded from here.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MODEL_ID = "all-MiniLM-L6-v2"
_REPO_DIR = "models--sentence-transformers--all-MiniLM-L6-v2"
_REQUIRED = (
    "model.safetensors",
    "config.json",
    "tokenizer.json",
    "sentence_bert_config.json",
    "1_Pooling/config.json",
    "modules.json",
)


class EmbedderUnavailable(RuntimeError):
    """The model cannot be run here. Its message says what is missing."""


def _hub_cache() -> Path:
    explicit = os.environ.get("HUGGINGFACE_HUB_CACHE") or os.environ.get("HF_HUB_CACHE")
    if explicit:
        return Path(explicit)
    home = os.environ.get("HF_HOME")
    return (Path(home) if home else Path.home() / ".cache" / "huggingface") / "hub"


def model_dir() -> Path | None:
    """The cached snapshot holding every file the model needs, or None.

    The snapshot ``refs/main`` names comes first; any other complete one is
    accepted, since a snapshot is content-addressed and the weights are what
    they are.
    """
    repo = _hub_cache() / _REPO_DIR
    snapshots = repo / "snapshots"
    if not snapshots.is_dir():
        return None
    ordered: list[Path] = []
    ref = repo / "refs" / "main"
    if ref.is_file():
        named = snapshots / ref.read_text(encoding="utf-8").strip()
        ordered.append(named)
    ordered += sorted(p for p in snapshots.iterdir() if p.is_dir() and p not in ordered)
    for snap in ordered:
        if all((snap / name).is_file() for name in _REQUIRED):
            return snap
    return None


@dataclass
class _Model:
    weights: dict[str, Any]
    tokenizer: Any
    layers: int
    heads: int
    hidden: int
    eps: float
    prefix: str
    normalize: bool


_LOCK = threading.Lock()
_LOADED: _Model | None = None


def _load() -> _Model:
    global _LOADED
    with _LOCK:
        if _LOADED is not None:
            return _LOADED
        snap = model_dir()
        if snap is None:
            raise EmbedderUnavailable(
                f"{MODEL_ID} is not in the local model cache at {_hub_cache() / _REPO_DIR}; "
                "nothing is downloaded from here"
            )
        try:
            from safetensors.numpy import load_file
            from tokenizers import Tokenizer
        except ImportError as exc:
            raise EmbedderUnavailable(f"a runtime piece is missing: {exc}") from exc
        pooling = json.loads((snap / "1_Pooling" / "config.json").read_text(encoding="utf-8"))
        if not pooling.get("pooling_mode_mean_tokens"):
            raise EmbedderUnavailable(f"the cached model does not use mean pooling: {pooling}")
        modules = json.loads((snap / "modules.json").read_text(encoding="utf-8"))
        cfg = json.loads((snap / "config.json").read_text(encoding="utf-8"))
        if cfg.get("hidden_act") != "gelu" or cfg.get("model_type") != "bert":
            raise EmbedderUnavailable(f"unexpected architecture: {cfg.get('model_type')}")
        st_cfg = json.loads((snap / "sentence_bert_config.json").read_text(encoding="utf-8"))
        tokenizer = Tokenizer.from_file(str(snap / "tokenizer.json"))
        tokenizer.enable_truncation(max_length=int(st_cfg["max_seq_length"]))
        tokenizer.no_padding()
        weights = load_file(str(snap / "model.safetensors"))
        prefix = "" if "embeddings.word_embeddings.weight" in weights else "bert."
        _LOADED = _Model(
            weights=weights,
            tokenizer=tokenizer,
            layers=int(cfg["num_hidden_layers"]),
            heads=int(cfg["num_attention_heads"]),
            hidden=int(cfg["hidden_size"]),
            eps=float(cfg.get("layer_norm_eps", 1e-12)),
            prefix=prefix,
            normalize=any(m.get("type", "").endswith("Normalize") for m in modules),
        )
        return _LOADED


def available() -> tuple[bool, str]:
    """Whether the model can run here, and why not when it cannot."""
    try:
        _load()
    except EmbedderUnavailable as exc:
        return False, str(exc)
    return True, "ok"


def encode(text: str) -> Any:
    """The sentence vector for ``text``, as a float32 numpy array.

    Raises EmbedderUnavailable when the model cannot run, and ValueError for
    empty text: an empty string has no meaning to embed, and a zero vector
    would quietly match nothing.
    """
    if not text or not text.strip():
        raise ValueError("there is no text to embed")
    import numpy as np
    from scipy.special import erf

    m = _load()
    w, p = m.weights, m.prefix
    enc = m.tokenizer.encode(text)
    ids = np.asarray(enc.ids)
    types = np.asarray(enc.type_ids)
    n = len(ids)
    head_dim = m.hidden // m.heads

    def norm(x: Any, name: str) -> Any:
        mu = x.mean(-1, keepdims=True)
        var = ((x - mu) ** 2).mean(-1, keepdims=True)
        return (x - mu) / np.sqrt(var + m.eps) * w[name + ".weight"] + w[name + ".bias"]

    def dense(x: Any, name: str) -> Any:
        return x @ w[name + ".weight"].T + w[name + ".bias"]

    x = (
        w[p + "embeddings.word_embeddings.weight"][ids]
        + w[p + "embeddings.position_embeddings.weight"][:n]
        + w[p + "embeddings.token_type_embeddings.weight"][types]
    )
    x = norm(x, p + "embeddings.LayerNorm")
    for i in range(m.layers):
        layer = f"{p}encoder.layer.{i}."
        q, k, v = (
            dense(x, layer + f"attention.self.{part}")
            .reshape(n, m.heads, head_dim)
            .transpose(1, 0, 2)
            for part in ("query", "key", "value")
        )
        scores = q @ k.transpose(0, 2, 1) / np.sqrt(head_dim)
        scores = np.exp(scores - scores.max(-1, keepdims=True))
        scores /= scores.sum(-1, keepdims=True)
        attended = (scores @ v).transpose(1, 0, 2).reshape(n, m.hidden)
        x = norm(
            dense(attended, layer + "attention.output.dense") + x,
            layer + "attention.output.LayerNorm",
        )
        inner = dense(x, layer + "intermediate.dense")
        inner = 0.5 * inner * (1.0 + erf(inner / np.sqrt(2.0)))
        x = norm(dense(inner, layer + "output.dense") + x, layer + "output.LayerNorm")
    # No padding and a full attention mask, so the mean over tokens IS the
    # masked mean sentence-transformers computes.
    pooled = x.mean(0)
    if m.normalize:
        pooled = pooled / np.linalg.norm(pooled)
    return pooled.astype(np.float32)
