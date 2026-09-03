"""Semantic search over a prose corpus — first real high-volume consumer
of the GPU-accelerated embedding plumbing (PR #169).

Designed per council walk consult-77dad1f3290e (Hinton, Peirce, Dijkstra,
Bengio, Norman, Lovelace lenses). The lens-decisions that shaped this
module:

- **Per-paragraph chunking** (Hinton + Peirce). Per-entry is too coarse
  for a 5,000-word exploration entry — can't find the specific
  paragraph that matters. Per-sentence loses context. Paragraphs are
  the unit reading-attention actually lands on.
- **Source-pointer per chunk** (Lovelace). The chunk knows its origin
  file + paragraph index so the search can lead the reader back.
  Generic enough to work over explorations, letters, knowledge,
  council walks.
- **Embedding-model version per chunk** (Meadows). When the model
  upgrades, only stale-version chunks need re-embed. Targeted, not
  whole-substrate rebuild.
- **Postconditions tested** (Dijkstra). Search results are sorted by
  descending similarity. The invariant is pinned at the test level.
- **Operator-judged-relevance eval > result-count metric** (Yudkowsky).
  Pre-reg ``prereg-2ad79e23fcf7`` registers the success criterion in
  terms of held-out queries with operator-judged relevance, not
  threshold counts.

## Surface

- ``chunk_file(path)`` → list of ``Chunk`` (paragraph_text, paragraph_idx)
- ``index_corpus(paths, db_path)`` → embeds chunks, stores with source
  pointer; idempotent (skips already-indexed paragraphs at current model
  version)
- ``search(query, db_path, top_k)`` → list of ``SearchHit`` sorted by
  descending similarity

## Storage schema

A single SQLite table ``semantic_search_chunks``:

    chunk_id        TEXT PRIMARY KEY   -- file_path:paragraph_index
    source_path     TEXT NOT NULL
    paragraph_index INTEGER NOT NULL
    chunk_text      TEXT NOT NULL
    embedding       BLOB NOT NULL      -- serialized float32 vector
    embedding_model TEXT NOT NULL      -- e.g. "all-MiniLM-L6-v2"
    indexed_at      REAL NOT NULL

Index on ``(source_path, paragraph_index)`` for the idempotency check.
The embedding column is BLOB serialized via ``semantic_store``'s
existing serializer for cosine-search compatibility.
"""

from __future__ import annotations

import re
import sqlite3
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from divineos.core.semantic_store import (
    _DEFAULT_MODEL_NAME,
    deserialize_embedding,
    embed,
    serialize_embedding,
)

# In-process cache of the whole index as one matrix, keyed by
# (db_path, model_name) and invalidated when the file's size or mtime moves.
#
# WHY THIS EXISTS. The first search implementation pulled every row, called
# struct.unpack per chunk, and ran a Python-loop cosine against each one.
# Measured 2026-09-03 at 49k chunks: 13.4 SECONDS for one query. This search
# is meant to fire at the start of every turn, so seconds-per-query is not a
# slow feature, it is an unusable one — and the failure would have shown up
# as the whole session feeling broken rather than as anything naming itself.
# One matrix multiply does the same arithmetic in the numeric library.
# Value is (db-stamp, rowids array, unit-normalised matrix). Both arrays are
# typed loosely on purpose: numpy's generic parameters vary by construction
# path, and pinning them here would describe one call site rather than the
# contract, which is "whatever _load_matrix built and search() consumes".
_MATRIX_CACHE: dict[tuple[str, str], tuple[tuple[float, int], object, object]] = {}


@dataclass
class Chunk:
    """A single paragraph extracted from a source file.

    Per-paragraph is the right granularity per the Hinton + Peirce
    council lenses: paragraphs are the unit reading-attention lands on.
    """

    source_path: str
    paragraph_index: int
    text: str


@dataclass
class SearchHit:
    """A search result — a chunk that matched the query, with metadata.

    ``similarity`` is the cosine-similarity of the query embedding to the
    chunk's stored embedding (the first-pass score).

    ``rerank_score`` is an optional cross-encoder score from a second
    re-ranking pass (see ``semantic_search_rerank.rerank``). None when
    no rerank has been applied. When present, the consumer typically
    sorts by rerank_score and treats similarity as auxiliary context.
    """

    source_path: str
    paragraph_index: int
    text: str
    similarity: float
    rerank_score: float | None = None


_PARAGRAPH_SEP = re.compile(r"\n\s*\n+")
_MIN_PARAGRAPH_CHARS = 20  # filter dividers + sub-line markers; allow short real prose


def chunk_file(path: str | Path) -> list[Chunk]:
    """Read ``path`` and split it into paragraph chunks.

    Paragraphs are separated by blank lines. Markdown headers, dividers
    (``---``), and very-short lines below ``_MIN_PARAGRAPH_CHARS`` are
    filtered out — they're not search-meaningful prose.

    Returns ``[]`` if the file doesn't exist or is empty.
    """
    p = Path(path)
    if not p.exists() or not p.is_file():
        return []
    text = p.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return []
    chunks: list[Chunk] = []
    for idx, raw in enumerate(_PARAGRAPH_SEP.split(text)):
        cleaned = raw.strip()
        if len(cleaned) < _MIN_PARAGRAPH_CHARS:
            continue
        # Drop markdown horizontal rules and pure-header paragraphs.
        if cleaned in ("---", "***") or re.match(r"^#+\s+\S+$", cleaned):
            continue
        chunks.append(
            Chunk(
                source_path=str(p),
                paragraph_index=idx,
                text=cleaned,
            )
        )
    return chunks


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS semantic_search_chunks (
            chunk_id TEXT PRIMARY KEY,
            source_path TEXT NOT NULL,
            paragraph_index INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            embedding BLOB NOT NULL,
            embedding_model TEXT NOT NULL,
            indexed_at REAL NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_semsearch_source "
        "ON semantic_search_chunks (source_path, paragraph_index)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_semsearch_model ON semantic_search_chunks (embedding_model)"
    )
    return conn


def _chunk_id(source_path: str, paragraph_index: int) -> str:
    return f"{source_path}:{paragraph_index}"


def index_corpus(
    paths: Sequence[str | Path],
    db_path: str,
    *,
    model_name: str = _DEFAULT_MODEL_NAME,
    force_reindex: bool = False,
) -> dict[str, int]:
    """Chunk + embed + store every paragraph from each path.

    Idempotent at the (source_path, paragraph_index, model_name) level —
    re-running this on the same paths with the same model is a no-op
    for chunks already indexed. Set ``force_reindex=True`` to re-embed
    everything.

    Returns counts dict: ``{"chunks_seen": N, "chunks_indexed": M,
    "chunks_skipped": K, "chunks_failed": X, "files_processed": F}``.
    ``skipped`` includes chunks already at the current model version;
    ``failed`` counts chunks the embedder could not encode at all.
    """
    chunks_seen = chunks_indexed = chunks_skipped = files_processed = 0
    chunks_failed = 0
    with _connect(db_path) as conn:
        for path in paths:
            file_chunks = chunk_file(path)
            if not file_chunks:
                continue
            files_processed += 1
            for c in file_chunks:
                chunks_seen += 1
                cid = _chunk_id(c.source_path, c.paragraph_index)
                if not force_reindex:
                    row = conn.execute(
                        "SELECT embedding_model FROM semantic_search_chunks WHERE chunk_id = ?",
                        (cid,),
                    ).fetchone()
                    if row and row[0] == model_name:
                        chunks_skipped += 1
                        continue
                vec = embed(c.text, model_name=model_name)
                if vec is None:
                    # A chunk that could not be embedded is a FAILURE, not an
                    # absence. This used to `continue` uncounted, so an absent
                    # embedding library rendered as "indexed: 0" with nothing
                    # anywhere saying why — could-not-look wearing the costume
                    # of a value. Found 2026-09-03 after the whole corpus came
                    # back unindexed and the run looked like a clean no-op.
                    chunks_failed += 1
                    continue
                conn.execute(
                    "INSERT OR REPLACE INTO semantic_search_chunks "
                    "(chunk_id, source_path, paragraph_index, chunk_text, "
                    "embedding, embedding_model, indexed_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        cid,
                        c.source_path,
                        c.paragraph_index,
                        c.text,
                        serialize_embedding(vec),
                        model_name,
                        time.time(),
                    ),
                )
                chunks_indexed += 1
            conn.commit()
    return {
        "chunks_seen": chunks_seen,
        "chunks_indexed": chunks_indexed,
        "chunks_skipped": chunks_skipped,
        "chunks_failed": chunks_failed,
        "files_processed": files_processed,
    }


def search(
    query: str,
    db_path: str,
    *,
    top_k: int = 5,
    min_similarity: float = 0.0,
    model_name: str = _DEFAULT_MODEL_NAME,
    min_chars: int = 0,
) -> list[SearchHit]:
    """Return the top-K chunks most semantically similar to ``query``.

    Postcondition (Dijkstra lens): results are sorted by descending
    ``similarity``. The invariant is pinned by
    ``test_search_results_sorted_descending`` in the regression tests.

    ``min_chars`` drops chunks shorter than that from the results.
    WHY: measured 2026-09-03, one hit in three on a real query was the
    four-word line "Dad will relay your reply." A very short sentence
    carries little meaning of its own, so it sits near EVERYTHING in
    embedding space and floats to the top of unrelated queries — the same
    way a vague remark can sound relevant to any conversation. Callers that
    surface results to a reader should set this; callers doing exhaustive
    search should leave it at zero. Filtering here rather than at index time
    keeps short chunks findable by exact search and out of the proactive
    surface, and needs no re-index to tune.

    Returns ``[]`` if the query is empty, the embedding model is
    unavailable, or no indexed chunks exist.
    """
    if not query.strip():
        return []
    # Query goes through the light runtime when it has been exported; that
    # path falls back to the original library on its own, so this stays a
    # speed choice and never a correctness one. Verified identical to six
    # decimal places by scripts/export_embedding_model_onnx.py, which deletes
    # the export rather than let a drifted one serve.
    from divineos.core.onnx_embed import embed_query

    query_vec = (
        embed_query(query)
        if model_name == _DEFAULT_MODEL_NAME
        else embed(query, model_name=model_name)
    )
    if query_vec is None:
        return []
    rowids, matrix = _load_matrix(db_path, model_name)
    if matrix.shape[0] == 0:
        return []
    q = np.asarray(query_vec, dtype=np.float32)
    q_norm = float(np.linalg.norm(q))
    if q_norm == 0.0:
        return []
    # Rows are pre-normalised in _load_matrix, so this dot product IS the
    # cosine — one matrix-vector multiply for the whole corpus.
    sims = matrix @ (q / q_norm)
    # Take the top_k by partition rather than sorting all of them; only the
    # short list gets ordered.
    # Over-fetch when a length floor is set, because the short chunks about to
    # be dropped would otherwise eat the result slots.
    want = top_k * 8 if min_chars > 0 else top_k
    k = min(want, sims.shape[0])
    top_idx = np.argpartition(-sims, k - 1)[:k] if k < sims.shape[0] else np.arange(sims.shape[0])
    top_idx = top_idx[np.argsort(-sims[top_idx])]
    keep = [(int(i), float(sims[i])) for i in top_idx if float(sims[i]) >= min_similarity]
    if not keep:
        return []
    # Only the surviving handful of rows get their text read. Pulling all
    # 70k chunk bodies to return three of them is what made the first
    # version unusable in a per-turn hook.
    wanted = [int(rowids[i]) for i, _ in keep]
    placeholders = ",".join("?" * len(wanted))
    with _connect(db_path) as conn:
        found = {
            r[0]: (r[1], r[2], r[3])
            for r in conn.execute(
                "SELECT rowid, source_path, paragraph_index, chunk_text "
                f"FROM semantic_search_chunks WHERE rowid IN ({placeholders})",
                wanted,
            )
        }
    hits: list[SearchHit] = []
    for (i, sim), rowid in zip(keep, wanted, strict=True):
        row = found.get(rowid)
        if row is None:
            continue
        if min_chars > 0 and len(row[2].strip()) < min_chars:
            continue
        hits.append(
            SearchHit(
                source_path=row[0],
                paragraph_index=row[1],
                text=row[2],
                similarity=sim,
            )
        )
        if len(hits) >= top_k:
            break
    return hits


def _cache_paths(db_path: str, model_name: str) -> tuple[Path, Path]:
    """Sidecar files holding the prepared matrix and its row identifiers."""
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", model_name)
    base = Path(db_path)
    return (
        base.with_name(f"{base.name}.{safe}.vectors.npy"),
        base.with_name(f"{base.name}.{safe}.rowids.npy"),
    )


def _load_matrix(db_path: str, model_name: str):
    """Return (rowids, unit-normalised embedding matrix) for the index.

    Cached at two levels because the callers live at two timescales. A CLI
    session queries repeatedly and is served by the in-process dict; a hook
    is a FRESH PROCESS every turn and would otherwise rebuild the whole
    matrix out of sqlite blobs each time — measured at ~7 seconds, which is
    the difference between a surface that fires on every turn and one that
    makes every turn feel broken. So the prepared matrix also lands beside
    the database as a plain array file that loads by memory-map.

    Both levels are invalidated by the database's size and mtime, so a newly
    indexed chunk is visible to the very next query rather than after some
    manual rebuild nobody would remember to run.
    """
    key = (db_path, model_name)
    try:
        st = Path(db_path).stat()
        stamp = (st.st_mtime, st.st_size)
    except OSError:
        stamp = (0.0, 0)
    cached = _MATRIX_CACHE.get(key)
    if cached is not None and cached[0] == stamp:
        return cached[1], cached[2]

    vec_path, ids_path = _cache_paths(db_path, model_name)
    stamp_path = vec_path.with_suffix(".stamp")
    want = f"{stamp[0]!r}:{stamp[1]}"
    if vec_path.exists() and ids_path.exists() and stamp_path.exists():
        try:
            if stamp_path.read_text(encoding="utf-8").strip() == want:
                matrix = np.load(vec_path, mmap_mode="r")
                rowids = np.load(ids_path)
                _MATRIX_CACHE[key] = (stamp, rowids, matrix)
                return rowids, matrix
        except (OSError, ValueError):
            pass  # a damaged sidecar is rebuilt below, never trusted

    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT rowid, embedding FROM semantic_search_chunks WHERE embedding_model = ?",
            (model_name,),
        ).fetchall()
    if not rows:
        empty = np.zeros((0, 0), dtype=np.float32)
        ids = np.zeros((0,), dtype=np.int64)
        _MATRIX_CACHE[key] = (stamp, ids, empty)
        return ids, empty
    rowids = np.asarray([r[0] for r in rows], dtype=np.int64)
    matrix = np.asarray([deserialize_embedding(r[1]) for r in rows], dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    # A zero-norm row would divide to NaN and silently poison every later
    # comparison; leave it at zero so it simply never wins.
    norms[norms == 0.0] = 1.0
    matrix = matrix / norms
    try:
        np.save(vec_path, matrix)
        np.save(ids_path, rowids)
        stamp_path.write_text(want, encoding="utf-8")
    except OSError:
        pass  # an unwritable sidecar costs speed, never correctness
    _MATRIX_CACHE[key] = (stamp, rowids, matrix)
    return rowids, matrix
