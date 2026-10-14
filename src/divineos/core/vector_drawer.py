"""A drawer of sentence vectors, so nothing is embedded twice.

The memory link needs a vector for every letter, correction, knowledge entry,
exploration and wall line it might surface: about 7900 of them, measured
2026-09-24, and about 50ms each to compute. Computed afresh in the compose hook
that was minutes per turn, and the hook is a fresh process every time, so an
in-memory cache never survived to the second turn (6e72eb15).

So vectors live here, keyed by what they are a vector OF: a hash of the model
name and the exact text. Same text, same model, same vector; a changed text is
a new key and the old row is simply never asked for again. The drawer is filled
ahead of time (``fill``), never from inside the compose hook, where a missing
vector is counted and skipped rather than computed on the spot.

Not ``semantic_search``'s index, which was the nearest existing part: that one
is keyed by file and paragraph, and most of what the memory link embeds is a
database row with no file.

Per seat, under the data home: vectors of a seat's private knowledge are
derived from it and stay with it.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from divineos.core import light_embedder

_OVERRIDE_ENV = "DIVINEOS_VECTOR_DRAWER"


def drawer_path() -> Path:
    override = os.environ.get(_OVERRIDE_ENV)
    if override:
        return Path(override)
    from divineos.core.paths import divineos_home

    return divineos_home() / "data" / "vectors.db"


def key(text: str, model: str = light_embedder.MODEL_ID) -> str:
    return hashlib.sha256(f"{model}\x00{text}".encode()).hexdigest()


def _conn() -> sqlite3.Connection:
    path = drawer_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS vectors (key TEXT PRIMARY KEY, model TEXT NOT NULL, "
        "dim INTEGER NOT NULL, vec BLOB NOT NULL)"
    )
    return conn


def lookup(texts: Iterable[str]) -> dict[str, Any]:
    """Stored vectors for these texts, by text. Texts with no vector are absent.

    Raises sqlite3.Error when the drawer cannot be read. The caller decides
    what that means, and an unreadable drawer must never look like an empty one.
    """
    import numpy as np

    wanted = {key(t): t for t in texts if t and t.strip()}
    if not wanted:
        return {}
    found: dict[str, Any] = {}
    conn = _conn()
    try:
        keys = list(wanted)
        for start in range(0, len(keys), 500):
            chunk = keys[start : start + 500]
            marks = ",".join("?" * len(chunk))
            rows = conn.execute(
                f"SELECT key, vec FROM vectors WHERE key IN ({marks})",  # nosec B608 -- placeholders only
                chunk,
            ).fetchall()
            for k, blob in rows:
                found[wanted[k]] = np.frombuffer(blob, dtype=np.float32)
    finally:
        conn.close()
    return found


_READER: sqlite3.Connection | None = None
_READER_PATH: Path | None = None


def get(text: str) -> Any:
    """The stored vector for one text, or None. One connection per process.

    The memory link asks for thousands of items in one load; opening the
    database for each would cost more than the lookups themselves.
    """
    global _READER, _READER_PATH
    import numpy as np

    if not text or not text.strip():
        return None
    path = drawer_path()
    if _READER is None or _READER_PATH != path:
        _READER = _conn()
        _READER_PATH = path
    row = _READER.execute("SELECT vec FROM vectors WHERE key = ?", (key(text),)).fetchone()
    return None if row is None else np.frombuffer(row[0], dtype=np.float32)


_BATCH = 256


def _bulk_encoder() -> Callable[[list[str]], Any]:
    """The same model through sentence-transformers, batched, on the GPU if any.

    The ONE place the heavy toolkit is used, and only for bulk filling, where
    its 17s import is paid once and batching on the GPU (Andrew 2026-06-13:
    embedding work should run on the GPU when there is one) turns an hour of
    one-at-a-time numpy into seconds. Its vectors match the light embedder's to
    about 1e-7, pinned in tests, so the drawer and the query agree.
    """
    import numpy as np
    from sentence_transformers import SentenceTransformer

    from divineos.core._embedding_device import select_device

    snap = light_embedder.model_dir()
    if snap is None:
        raise light_embedder.EmbedderUnavailable("the model is not in the local cache")
    model = SentenceTransformer(str(snap), device=select_device())

    def encode_many(batch: list[str]) -> Any:
        return np.asarray(
            model.encode(batch, batch_size=64, convert_to_numpy=True), dtype=np.float32
        )

    return encode_many


def fill(
    texts: Iterable[str],
    progress: Callable[[int, int], None] | None = None,
    encode_many: Callable[[list[str]], Any] | None = None,
) -> dict[str, int]:
    """Compute and store every vector not already in the drawer.

    Offline work, for a command or sleep, never the compose hook. Commits each
    batch so an interrupted fill keeps what it finished.
    """
    unique = list(dict.fromkeys(t for t in texts if t and t.strip()))
    have = lookup(unique)
    todo = [t for t in unique if t not in have]
    out = {"asked": len(unique), "already": len(have), "computed": 0}
    if not todo:
        return out
    encode = encode_many or _bulk_encoder()
    conn = _conn()
    try:
        for start in range(0, len(todo), _BATCH):
            chunk = todo[start : start + _BATCH]
            vecs = encode(chunk)
            conn.executemany(
                "INSERT OR REPLACE INTO vectors (key, model, dim, vec) VALUES (?, ?, ?, ?)",
                [
                    (key(t), light_embedder.MODEL_ID, int(v.shape[0]), v.tobytes())
                    for t, v in zip(chunk, vecs, strict=True)
                ],
            )
            conn.commit()
            out["computed"] += len(chunk)
            if progress is not None:
                progress(out["computed"], len(todo))
    finally:
        conn.close()
    return out
