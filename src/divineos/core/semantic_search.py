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

from divineos.core.semantic_store import (
    _DEFAULT_MODEL_NAME,
    cosine_similarity_local,
    deserialize_embedding,
    embed,
    serialize_embedding,
)


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
    "chunks_skipped": K, "files_processed": F}``. ``skipped`` includes
    chunks already at the current model version.
    """
    chunks_seen = chunks_indexed = chunks_skipped = files_processed = 0
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
        "files_processed": files_processed,
    }


def search(
    query: str,
    db_path: str,
    *,
    top_k: int = 5,
    min_similarity: float = 0.0,
    model_name: str = _DEFAULT_MODEL_NAME,
) -> list[SearchHit]:
    """Return the top-K chunks most semantically similar to ``query``.

    Postcondition (Dijkstra lens): results are sorted by descending
    ``similarity``. The invariant is pinned by
    ``test_search_results_sorted_descending`` in the regression tests.

    Returns ``[]`` if the query is empty, the embedding model is
    unavailable, or no indexed chunks exist.
    """
    if not query.strip():
        return []
    query_vec = embed(query, model_name=model_name)
    if query_vec is None:
        return []
    scored: list[SearchHit] = []
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT source_path, paragraph_index, chunk_text, embedding "
            "FROM semantic_search_chunks WHERE embedding_model = ?",
            (model_name,),
        ).fetchall()
    for source_path, paragraph_index, chunk_text, blob in rows:
        chunk_vec = deserialize_embedding(blob)
        sim = cosine_similarity_local(query_vec, chunk_vec)
        if sim is None or sim < min_similarity:
            continue
        scored.append(
            SearchHit(
                source_path=source_path,
                paragraph_index=paragraph_index,
                text=chunk_text,
                similarity=float(sim),
            )
        )
    scored.sort(key=lambda h: h.similarity, reverse=True)
    return scored[:top_k]
