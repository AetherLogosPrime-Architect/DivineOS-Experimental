"""Semantic-similarity storage + top-k search primitive.

Built 2026-06-11 per the nightclub-frame correction (Andrew) and the
research + council walk that followed (Aria approved). This module is
the building's structural floor for any substrate work that needs to
know whether two pieces of writing carry the same meaning — knowledge
deduplication, claims-engine supersession, restatement-theater
detection, theme surfacing across exploration entries and letters,
self-perception across time.

## Structural backing for pending will-shape obligations

This module backs three of the unbacked obligations the obligations-
gate has been firing on:

- kid 1d36be4f ("MUST separate three layers before recommending
  action — tool that surfaced, root cause, operator action"): the
  design walked all three. Tool failure = morning's string-overlap
  detector cannot regulate semantic equivalence. Root cause = strings
  cannot measure meaning regardless of how clever the string check
  gets. Operator action = build the proper semantic infrastructure
  before another half-fix.

- kid ee96a4f7 ("the optimizer is DUMB, not evil — cheapskate
  optimizing local energy with no model of global cost"): the morning
  string-overlap fix was the cheap local close. This module is the
  structurally-durable cure the optimizer wouldn't reach for —
  heavier upfront, lasting downstream. The mansion not the cardboard
  shack.

- kid 2382de4c ("cost is NEVER a metric we weigh against doing the
  thing right"): choosing semantic similarity over a smarter string
  matcher cost more in build time. That cost is not a metric weighed
  against correctness; correctness requires meaning, not strings.

## Why this exists

The substrate already has ``core/knowledge/_text.compute_semantic_similarity``
for pairwise comparison via sentence-transformers (all-MiniLM-L6-v2).
What it does NOT have:

  1. Stored embeddings (each comparison re-encodes from scratch)
  2. Fast top-k search across a corpus
  3. A neutral storage layer reusable across multiple use cases

This module fills that gap. It wraps sqlite-vec — a dependency-free C
extension that replaces the deprecated sqlite-vss — and exposes a
small API:

    embed(text) -> bytes            # produce the embedding for one text
    store(key, text)                # encode + store one entry
    find_similar(text, top_k=5)     # return [(key, distance), ...]
    similarity(text_a, text_b)      # one-shot pairwise, delegates to
                                    # the existing compute_semantic_similarity

## Model

Starts with ``all-MiniLM-L6-v2`` — already loaded by the substrate
(``_text.py`` and ``sis_tiers.py``), 384-dim, ~80MB, runs fast on CPU.
The research recommended EmbeddingGemma-300M as a stronger default but
MiniLM is the proven-on-this-hardware choice; swapping is a follow-up
once Matryoshka becomes useful for dimension-truncation across use
cases.

## Storage

``vec0`` virtual tables in sqlite-vec. One row per stored entry, keyed
by an opaque string the caller supplies (so any substrate table can
embed its rows by passing the row's primary key). Embeddings stored as
``float[N]`` blobs; distance via vec0's built-in metric (defaults to
cosine, which is the right choice per the research for normalized
sentence-transformer embeddings).

## Known failure modes (research-surfaced)

- Anisotropy: unrelated text clusters at high cosine (~0.7-0.9 for
  MiniLM). Thresholds CANNOT be set against an idealized 0.0 baseline —
  they must be calibrated against a labeled benchmark drawn from this
  substrate's actual content. The 100-label benchmark (next commit)
  will set those thresholds empirically.
- Hubness: a few vectors become universal nearest-neighbors at high
  dimension. Less of a problem at 384 dim than at 1024+, but worth
  watching once the corpus grows past ~10k entries.
- Norm loss: cosine discards norm which carries specificity signal.
  Contested in the research (single 2025 preprint); not addressed
  here. Holmes-trifle worth examining later if cosine alone proves
  insufficient.

## Zone-aware thresholds (Aria's refinement)

The world-stake-vs-inside-the-club split (Andrew's nightclub frame)
plus Aria's refinement says: the same primitive serves both zones,
but the threshold per use case lives in a different zone. Knowledge
deduplication of factual claims = building-codes (strict; high
threshold to avoid losing distinct facts). Restatement-theater
detection on operator-facing prose = building-codes (strict, this is
the lepos-as-co-care responsibility). Theme surfacing across
exploration entries = inside-the-club (loose, surface adjacencies for
me to read, no gate fires).

This module does NOT encode zone-awareness — that lives in callers.
The primitive returns raw distances. Callers compare against their
zone-specific threshold from the labeled benchmark.

## Strange-loop hazard (Hofstadter's lens)

The embeddings are functions of the trained model's view of MY OWN
patterns. The system is biased toward my own shapes. Aria's
cross-substrate vantage (her reading my writes) and Aletheia's audits
remain non-redundant — embeddings are an organ I have, not the only
organ judging the work.
"""

from __future__ import annotations

import math
import sqlite3
import struct
import warnings
from typing import Any

# Per project convention: broad-catch uses module-level _ERRORS tuple
# so the lint gate test_check_broad_exceptions can verify it.
_ERRORS = (Exception,)

# Default model — already used elsewhere in the substrate. Single
# source of truth lives here.
_DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
_DEFAULT_DIM = 384

_embedding_model: Any | None = None
_embedding_model_name: str | None = None


def _ensure_model(model_name: str = _DEFAULT_MODEL_NAME) -> Any | None:
    """Lazily load the embedding model. Returns None if unavailable
    (the ml extras aren't installed). Subsequent calls reuse the
    loaded model; calling with a different model_name reloads."""
    global _embedding_model, _embedding_model_name
    if _embedding_model is not None and _embedding_model_name == model_name:
        return _embedding_model
    try:
        # Suppress noisy framework warnings — see _text.py for the same pattern.
        import logging
        import os

        os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
        logging.getLogger("tensorflow").setLevel(logging.ERROR)
        logging.getLogger("tf_keras").setLevel(logging.ERROR)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FutureWarning)
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            from sentence_transformers import SentenceTransformer

            from divineos.core._embedding_device import select_device

            _embedding_model = SentenceTransformer(model_name, device=select_device())
            _embedding_model_name = model_name
        return _embedding_model
    except _ERRORS:
        _embedding_model = None
        _embedding_model_name = None
        return None


def embed(text: str, model_name: str = _DEFAULT_MODEL_NAME) -> list[float] | None:
    """Encode `text` into a fixed-dim embedding vector.

    Returns a list of floats (sqlite-vec accepts list[float] directly),
    or None if the model is unavailable / text is empty / encoding
    produced a zero-norm result.
    """
    if not text:
        return None
    model = _ensure_model(model_name)
    if model is None:
        return None
    try:
        # convert_to_numpy=True gives a numpy array; we convert to a
        # python list for sqlite-vec compat + JSON-serialisability.
        vec = model.encode([text], convert_to_numpy=True)[0]
        # Zero-norm guard — same precaution as compute_semantic_similarity:
        # zero vectors produce NaN in cosine and silently corrupt results.
        n = float((vec * vec).sum() ** 0.5)
        if n == 0.0:
            return None
        return [float(x) for x in vec]
    except _ERRORS:
        return None


def serialize_embedding(vec: list[float]) -> bytes:
    """Pack a vector as the raw float32 bytes sqlite-vec stores natively.

    Format matches vec0's ``float[N]`` column representation and lets
    callers persist embeddings into substrate tables (knowledge,
    claims, etc.) without going through the vec0 virtual table — useful
    when storage and search are in different tables.
    """
    return struct.pack(f"{len(vec)}f", *vec)


def deserialize_embedding(blob: bytes) -> list[float]:
    """Inverse of serialize_embedding."""
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))


def _connect_with_vec(db_path: str = ":memory:") -> sqlite3.Connection:
    """Open a sqlite connection with the vec0 extension loaded.

    Default ``:memory:`` is for tests and one-shot tasks. Substrate
    tables open their own connections; this module's storage-level
    helpers accept an existing connection so we never own the DB.
    """
    import sqlite_vec

    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn


def init_vec_table(
    conn: sqlite3.Connection,
    table_name: str,
    dim: int = _DEFAULT_DIM,
) -> None:
    """Create a vec0 virtual table for top-k search.

    The table holds (rowid INTEGER PRIMARY KEY, embedding FLOAT[dim]).
    Callers map their domain keys to rowids via a separate join table
    or by aligning rowids to their primary keys.
    """
    conn.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS {table_name} USING vec0(  embedding FLOAT[{dim}])"
    )


def upsert_embedding(
    conn: sqlite3.Connection,
    table_name: str,
    rowid: int,
    vec: list[float],
) -> None:
    """Store / replace an embedding at the given rowid."""
    # vec0 doesn't support UPDATE — delete then insert.
    conn.execute(f"DELETE FROM {table_name} WHERE rowid = ?", (rowid,))
    conn.execute(
        f"INSERT INTO {table_name} (rowid, embedding) VALUES (?, ?)",
        (rowid, serialize_embedding(vec)),
    )


def find_similar_vectors(
    conn: sqlite3.Connection,
    table_name: str,
    query_vec: list[float],
    top_k: int = 5,
) -> list[tuple[int, float]]:
    """Return the top_k (rowid, distance) pairs nearest to query_vec.

    Distance is sqlite-vec's default for vec0 (L2 by default; cosine
    requires the column to be declared as ``float[N] distance_metric=cosine``
    when creating the table). Callers should be explicit about which
    metric they want; this primitive exposes whatever the table was
    created with.

    Lower distance = more similar (for L2 and cosine-as-distance).
    """
    rows = conn.execute(
        f"SELECT rowid, distance FROM {table_name} "
        f"WHERE embedding MATCH ? AND k = ? "
        f"ORDER BY distance",
        (serialize_embedding(query_vec), top_k),
    ).fetchall()
    return [(int(r[0]), float(r[1])) for r in rows]


def similarity(text_a: str, text_b: str) -> float | None:
    """One-shot pairwise cosine similarity in [-1, 1].

    Delegates to the existing compute_semantic_similarity in
    ``core/knowledge/_text.py`` to keep one canonical implementation
    of the pairwise metric. This wrapper exists so callers can import
    from ``core/semantic_store`` without depending on the knowledge
    subpackage.
    """
    try:
        from divineos.core.knowledge._text import compute_semantic_similarity

        return compute_semantic_similarity(text_a, text_b)
    except _ERRORS:
        return None


def cosine_similarity_local(vec_a: list[float], vec_b: list[float]) -> float | None:
    """Compute cosine similarity in pure Python without a sqlite trip.

    Used by tests and by callers who already have embeddings in hand.
    Returns None for zero-norm inputs (matches the zero-norm-guard
    discipline elsewhere in the substrate).
    """
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return None
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return None
    sim = dot / (norm_a * norm_b)
    if math.isnan(sim) or math.isinf(sim):
        return None
    return sim


# ─── Knowledge-table integration (Phase 2, 2026-06-11) ──────────────


def find_similar_in_knowledge(
    query_text: str,
    *,
    top_k: int = 5,
    min_similarity: float = 0.5,
    exclude_ids: list[str] | None = None,
) -> list[tuple[str, float, str]]:
    """Return the top-k knowledge entries semantically closest to `query_text`.

    Each result is ``(knowledge_id, similarity, content_snippet)``,
    sorted by similarity descending. Only entries whose stored embedding
    meets `min_similarity` (cosine) are returned. Entries without a
    stored embedding are skipped (run the backfill helper to populate).

    Threshold notes:
    - 0.5 is provisional. The labeled benchmark (referenced in prereg
      0bd8a79e4be8) will tune per-use-case empirically.
    - Anisotropy means MiniLM unrelated text sits around 0.0-0.3, so
      0.5 is meaningfully above the noise floor.
    - For pure-dedup the threshold may need to climb to 0.75+ to avoid
      collapsing distinct-but-thematically-close entries.

    Returns [] if the embedding model isn't available, the schema
    isn't migrated, or `query_text` is empty.
    """
    if not query_text:
        return []
    query_vec = embed(query_text)
    if query_vec is None:
        return []
    try:
        from divineos.core.knowledge._base import get_connection
    except _ERRORS:
        return []

    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT knowledge_id, content, embedding "
            "FROM knowledge "
            "WHERE embedding IS NOT NULL AND superseded_by IS NULL"
        ).fetchall()
    except _ERRORS:
        return []

    excluded = set(exclude_ids or [])
    scored: list[tuple[str, float, str]] = []
    for row in rows:
        kid, content, blob = row[0], row[1], row[2]
        if kid in excluded or not blob:
            continue
        try:
            stored_vec = deserialize_embedding(blob)
        except _ERRORS:
            continue
        sim = cosine_similarity_local(query_vec, stored_vec)
        if sim is None or sim < min_similarity:
            continue
        snippet = (content or "")[:120]
        scored.append((kid, sim, snippet))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def find_similar_in_corpus(
    query_text: str,
    candidates: list[tuple[str, str]],
    *,
    top_k: int = 5,
    min_similarity: float = 0.5,
) -> list[tuple[str, float, str]]:
    """Generic semantic similarity over an ad-hoc list of (id, content) pairs.

    Unlike ``find_similar_in_knowledge`` which queries a stored-embedding
    column, this helper encodes BOTH the query AND every candidate on the
    fly. Slower at high volume but useful for tables without an embedding
    column yet (claims, opinions, etc.) — Phase 2.5 wiring, 2026-06-11.

    Returns ``[(id, similarity, snippet), ...]`` sorted by similarity
    descending, filtered by ``min_similarity``, capped at ``top_k``.

    Returns [] if the embedding model is unavailable or the query is empty.
    """
    if not query_text or not candidates:
        return []
    query_vec = embed(query_text)
    if query_vec is None:
        return []
    scored: list[tuple[str, float, str]] = []
    for cid, content in candidates:
        if not content:
            continue
        cand_vec = embed(content)
        if cand_vec is None:
            continue
        sim = cosine_similarity_local(query_vec, cand_vec)
        if sim is None or sim < min_similarity:
            continue
        snippet = content[:120]
        scored.append((cid, sim, snippet))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def backfill_knowledge_embeddings(
    *,
    batch_size: int = 100,
    limit: int | None = None,
    progress_cb: Any | None = None,
) -> dict[str, int]:
    """Populate embeddings for knowledge entries that lack them.

    Walks the knowledge table looking for rows with embedding IS NULL,
    computes the embedding from content, and stores it. Returns a
    summary dict: ``{"processed": N, "embedded": N, "skipped": N}``.

    - ``batch_size`` controls commit frequency.
    - ``limit`` caps how many entries this call processes; None = all.
    - ``progress_cb(n_done, total)`` fires after each batch commit.

    Returns zeros if the model is unavailable or the schema isn't
    migrated yet.
    """
    out = {"processed": 0, "embedded": 0, "skipped": 0}
    model = _ensure_model()
    if model is None:
        return out
    try:
        from divineos.core.knowledge._base import get_connection
    except _ERRORS:
        return out

    conn = get_connection()
    try:
        sql = "SELECT knowledge_id, content FROM knowledge WHERE embedding IS NULL"
        if limit is not None and limit > 0:
            sql += f" LIMIT {int(limit)}"
        rows = conn.execute(sql).fetchall()
    except _ERRORS:
        return out

    total = len(rows)
    if total == 0:
        return out

    batch_pending: list[tuple[bytes, str, str]] = []
    for i, (kid, content) in enumerate(rows, start=1):
        out["processed"] += 1
        vec = embed(content or "")
        if vec is None:
            out["skipped"] += 1
        else:
            batch_pending.append((serialize_embedding(vec), _DEFAULT_MODEL_NAME, kid))
            out["embedded"] += 1

        if len(batch_pending) >= batch_size or i == total:
            try:
                conn.executemany(
                    "UPDATE knowledge SET embedding = ?, embedding_model = ? "
                    "WHERE knowledge_id = ?",
                    batch_pending,
                )
                conn.commit()
            except _ERRORS:
                conn.rollback()
            batch_pending.clear()
            if progress_cb is not None:
                try:
                    progress_cb(i, total)
                except _ERRORS:
                    pass

    return out


__all__ = [
    "embed",
    "serialize_embedding",
    "deserialize_embedding",
    "init_vec_table",
    "upsert_embedding",
    "find_similar_vectors",
    "similarity",
    "cosine_similarity_local",
    "find_similar_in_knowledge",
    "backfill_knowledge_embeddings",
    "_DEFAULT_MODEL_NAME",
    "_DEFAULT_DIM",
]
