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

import os
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


def _chunk_id(source_path: str, paragraph_index: int, root: str | Path | None = None) -> str:
    """``file:index``. With a ``root`` the file part is relative to it, so the same
    notes indexed from two checkouts are one set of chunks, not two."""
    if root is not None:
        try:
            source_path = Path(source_path).resolve().relative_to(Path(root).resolve()).as_posix()
        except ValueError:
            pass  # outside the root: keep the full path, it is the only name it has
    return f"{source_path}:{paragraph_index}"


def index_corpus(
    paths: Sequence[str | Path],
    db_path: str,
    *,
    model_name: str = _DEFAULT_MODEL_NAME,
    force_reindex: bool = False,
    root: str | Path | None = None,
) -> dict[str, int]:
    """Chunk + embed + store every paragraph from each path.

    Idempotent at the (source_path, paragraph_index, model_name) level —
    re-running this on the same paths with the same model is a no-op
    for chunks already indexed. Set ``force_reindex=True`` to re-embed
    everything.

    Returns counts dict: ``{"chunks_seen": N, "chunks_indexed": M,
    "chunks_skipped": K, "chunks_failed": X, "files_processed": F}``.
    ``skipped`` includes chunks already at the current model version;
    ``failed`` counts chunks whose embedding could not be produced.

    ``chunks_seen == chunks_indexed + chunks_skipped + chunks_failed``
    always holds, and that is the point of the ``failed`` bucket. Before
    2026-09-02 a chunk that could not be embedded incremented nothing, so
    this run walked 46,323 chunks, stored none, and reported ``indexed:
    0  skipped: 0`` — arithmetic that does not add up and which no caller
    could detect. The cause was an interpreter without the ml extras, and
    the count of zero read exactly like a corpus with nothing new in it.
    """
    chunks_seen = chunks_indexed = chunks_skipped = chunks_failed = files_processed = 0
    chunks_updated = chunks_removed = 0
    all_ids: set[str] = set()
    with _connect(db_path) as conn:
        for path in paths:
            file_chunks = chunk_file(path)
            source = str(Path(path))
            keep = {_chunk_id(c.source_path, c.paragraph_index, root) for c in file_chunks}
            # Rows for this file that no longer match a paragraph in it: an edited
            # or shortened note, an emptied or deleted file, and rows filed under
            # the old absolute-path ids from before ids were relative to a root.
            # Found by path or by id prefix: after a copy of the notes in another
            # checkout is indexed, the row keeps that checkout's path but this id.
            prefix = _chunk_id(source, 0, root).rsplit(":", 1)[0] + ":"
            stale = [
                r[0]
                for r in conn.execute(
                    "SELECT chunk_id FROM semantic_search_chunks "
                    "WHERE source_path = ? OR substr(chunk_id, 1, ?) = ?",
                    (source, len(prefix), prefix),
                )
                if r[0] not in keep
            ]
            all_ids.update(keep)
            for sid in stale:
                conn.execute("DELETE FROM semantic_search_chunks WHERE chunk_id = ?", (sid,))
            chunks_removed += len(stale)
            if not file_chunks:
                conn.commit()
                continue
            files_processed += 1
            for c in file_chunks:
                chunks_seen += 1
                cid = _chunk_id(c.source_path, c.paragraph_index, root)
                changed = False
                if not force_reindex:
                    row = conn.execute(
                        "SELECT embedding_model, chunk_text FROM semantic_search_chunks "
                        "WHERE chunk_id = ?",
                        (cid,),
                    ).fetchone()
                    if row and row[0] == model_name and row[1] == c.text:
                        chunks_skipped += 1
                        continue
                    # Same place, same model, different words: the paragraph was edited
                    # and its stored vector describes text that is no longer there.
                    changed = bool(row and row[1] != c.text)
                vec = embed(c.text, model_name=model_name)
                if vec is None:
                    chunks_failed += 1
                    continue
                if changed:
                    chunks_updated += 1
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
        # Stored chunks of exactly the paragraphs walked above, so a total and a
        # "new" count describe the same set (not every row in the database).
        ids = sorted(all_ids)
        chunks_present = 0
        for start in range(0, len(ids), 500):
            batch = ids[start : start + 500]
            marks = ",".join("?" * len(batch))
            chunks_present += conn.execute(
                f"SELECT COUNT(*) FROM semantic_search_chunks WHERE chunk_id IN ({marks})",
                batch,
            ).fetchone()[0]
    return {
        "chunks_present": chunks_present,
        "chunks_seen": chunks_seen,
        "chunks_indexed": chunks_indexed,
        "chunks_skipped": chunks_skipped,
        "chunks_failed": chunks_failed,
        "files_processed": files_processed,
        # A subset of chunks_indexed: paragraphs that were already stored but edited.
        "chunks_updated": chunks_updated,
        "chunks_removed": chunks_removed,
    }


def default_db_path() -> str:
    from divineos.core._ledger_base import data_dir

    return str(Path(data_dir()) / "semantic_search.db")


def default_repo_root() -> Path:
    """The checkout this code is running from (src/divineos/core/semantic_search.py)."""
    return Path(__file__).resolve().parents[3]


def corpus_paths(corpus: str, repo_root: Path) -> list[str]:
    """The markdown files in a corpus selector: exploration, letters or all."""
    paths: list[str] = []
    if corpus in ("exploration", "all"):
        expl_dir = repo_root / "exploration" / "aether"
        if expl_dir.exists():
            paths.extend(str(p) for p in expl_dir.glob("*.md"))
    if corpus in ("letters", "all"):
        letters_dir = repo_root / "family" / "letters"
        if letters_dir.exists():
            paths.extend(str(p) for p in letters_dir.glob("*.md"))
    return sorted(paths)


def _remove_rows_of_deleted_notes(paths: list[str], db_path: str, root: Path) -> int:
    """Delete rows of exploration notes that are no longer on disk. Returns how many.

    ``index_corpus`` only examines files it is handed, so a deleted or renamed note
    kept its rows and kept turning up in searches. A row belongs to this corpus when
    its id sits under this checkout's exploration folder, as a relative id or as the
    older absolute one; any such row whose file is not among the files just walked
    is stale. Letters and ids from other checkouts' absolute paths are not touched.

    An empty walk deletes nothing: a folder that could not be read looks exactly
    like a folder with no notes, and that must not wipe every exploration row. The
    cost is that deleting the very last note leaves its rows until another remains.
    """
    if not paths:
        return 0
    walked = {_chunk_id(p, 0, root).rsplit(":", 1)[0] for p in paths}
    relative_prefix = "exploration/aether/"
    absolute_prefix = str(root / "exploration" / "aether") + os.sep
    removed = 0
    with _connect(db_path) as conn:
        for (cid,) in conn.execute("SELECT chunk_id FROM semantic_search_chunks").fetchall():
            file_part = cid.rsplit(":", 1)[0]
            if file_part in walked:
                continue
            if file_part.startswith(relative_prefix) or file_part.startswith(absolute_prefix):
                conn.execute("DELETE FROM semantic_search_chunks WHERE chunk_id = ?", (cid,))
                removed += 1
        conn.commit()
    return removed


def refresh_exploration_index(
    repo_root: Path | None = None, db_path: str | None = None
) -> dict[str, int]:
    """Index the explorations corpus and report the totals, including what is stored now.

    Same work as ``divineos find index --corpus exploration``, so sleep can keep this
    index current alongside the memory link's drawer. ``chunks_total`` is read back
    from the database after the run, not inferred from the counts.
    """
    root = repo_root if repo_root is not None else default_repo_root()
    db = db_path if db_path is not None else default_db_path()
    paths = corpus_paths("exploration", root)
    counts = index_corpus(paths, db, root=root)
    counts["chunks_removed"] += _remove_rows_of_deleted_notes(paths, db, root)
    # The same set the "new" count is about: the paragraphs of THIS corpus's
    # files, not every row in the database (other corpora, other checkouts).
    counts["chunks_total"] = counts["chunks_present"]
    return counts


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
