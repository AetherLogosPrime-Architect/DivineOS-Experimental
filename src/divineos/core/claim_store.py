"""Claims Engine — investigate everything, dismiss nothing.

Five evidence tiers reflecting how claims relate to measurability:

  Tier 1: EMPIRICAL    — Directly measurable, reproducible, falsifiable
  Tier 2: THEORETICAL  — Derived from empirical evidence via math/logic
  Tier 3: INFERENTIAL  — Cannot measure directly, but consistent observable effects
  Tier 4: SPECULATIVE  — Logically coherent, not contradicted, effects not yet confirmed
  Tier 5: METAPHYSICAL — Beyond current measurement, philosophically coherent

Claims are investigated, not judged. Even disproving nonsense teaches something.
Side discoveries during investigation feed back into the knowledge store.
"""

import json
import re

from loguru import logger
import time
import uuid
from typing import Any

from divineos.core.memory import _get_connection

# Evidence tiers
TIER_EMPIRICAL = 1
TIER_THEORETICAL = 2
TIER_INFERENTIAL = 3
TIER_SPECULATIVE = 4
TIER_METAPHYSICAL = 5

TIER_LABELS = {
    TIER_EMPIRICAL: "empirical",
    TIER_THEORETICAL: "theoretical",
    TIER_INFERENTIAL: "inferential",
    TIER_SPECULATIVE: "speculative",
    TIER_METAPHYSICAL: "metaphysical",
}

# Claim investigation status
STATUS_OPEN = "OPEN"
STATUS_INVESTIGATING = "INVESTIGATING"
STATUS_SUPPORTED = "SUPPORTED"
STATUS_CONTESTED = "CONTESTED"
STATUS_REFUTED = "REFUTED"

# Evidence source types
SOURCE_EMPIRICAL = "empirical"  # measured data, reproducible results
SOURCE_THEORETICAL = "theoretical"  # mathematical/logical derivation
SOURCE_INFERENTIAL = "inferential"  # inferred from observable effects
SOURCE_EXPERIENTIAL = "experiential"  # personal/observed experience
SOURCE_RESONANCE = "resonance"  # AI functional affect signal

# Confidence-basis values — distinguishes uncommitted defaults from real credences.
# Aletheia found 2026-05-12: 108 of 109 claims stuck at default 0.5 because evidence
# rarely got filed AND there was no path to encode filer's prior or assessor's judgment
# without quantified evidence. The 2024 belief-updating literature (arxiv 2412.10662)
# names showing 0.5 as "the worst possible default" — it reads as "considered and
# uncertain," which actively suppresses downstream updating versus a marked-as-
# uncommitted state. Distinguishing by basis makes "no credence yet" visibly different
# from "I made a 0.5 judgment" without redesigning the scalar column.
BASIS_UNCOMMITTED = "uncommitted"  # default at file-time; signals "no credence yet"
BASIS_FILER_PRIOR = "filer-prior"  # explicit prior at file time, basis text required
BASIS_ASSESSOR_JUDGMENT = "assessor-judgment"  # set during assess, judgment not evidence
BASIS_EVIDENCE_DERIVED = "evidence-derived"  # computed from claim_evidence rows
BASIS_LEGACY_DEFAULT = "legacy-default"  # back-fill marker for pre-migration 0.5 rows


def init_claim_tables() -> None:
    """Create claims and claim_evidence tables."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS claims (
                claim_id            TEXT PRIMARY KEY,
                created_at          REAL NOT NULL,
                updated_at          REAL NOT NULL,
                statement           TEXT NOT NULL,
                tier                INTEGER NOT NULL DEFAULT 4,
                status              TEXT NOT NULL DEFAULT 'OPEN',
                confidence          REAL NOT NULL DEFAULT 0.5,
                confidence_basis    TEXT NOT NULL DEFAULT 'uncommitted',
                confidence_basis_text TEXT NOT NULL DEFAULT '',
                confidence_set_at   REAL,
                context             TEXT NOT NULL DEFAULT '',
                assessment          TEXT NOT NULL DEFAULT '',
                promotion_criteria  TEXT NOT NULL DEFAULT '',
                demotion_criteria   TEXT NOT NULL DEFAULT '',
                tags                TEXT NOT NULL DEFAULT '[]',
                session_id          TEXT NOT NULL DEFAULT ''
            )
        """)
        _migrate_add_confidence_basis(conn)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS claim_evidence (
                evidence_id     TEXT PRIMARY KEY,
                claim_id        TEXT NOT NULL,
                created_at      REAL NOT NULL,
                direction       TEXT NOT NULL DEFAULT 'NEUTRAL',
                content         TEXT NOT NULL,
                source          TEXT NOT NULL DEFAULT 'experiential',
                strength        REAL NOT NULL DEFAULT 0.5,
                FOREIGN KEY (claim_id) REFERENCES claims(claim_id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_evidence_claim
            ON claim_evidence(claim_id)
        """)
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS claim_fts
            USING fts5(
                statement, context, assessment, tags,
                content=claims, content_rowid=rowid
            )
        """)
        conn.executescript("""
            CREATE TRIGGER IF NOT EXISTS claim_fts_insert
            AFTER INSERT ON claims BEGIN
                INSERT INTO claim_fts(rowid, statement, context, assessment, tags)
                VALUES (NEW.rowid, NEW.statement, NEW.context, NEW.assessment, NEW.tags);
            END;
            CREATE TRIGGER IF NOT EXISTS claim_fts_update
            AFTER UPDATE ON claims BEGIN
                INSERT INTO claim_fts(claim_fts, rowid, statement, context, assessment, tags)
                VALUES ('delete', OLD.rowid, OLD.statement, OLD.context, OLD.assessment, OLD.tags);
                INSERT INTO claim_fts(rowid, statement, context, assessment, tags)
                VALUES (NEW.rowid, NEW.statement, NEW.context, NEW.assessment, NEW.tags);
            END;
            CREATE TRIGGER IF NOT EXISTS claim_fts_delete
            AFTER DELETE ON claims BEGIN
                INSERT INTO claim_fts(claim_fts, rowid, statement, context, assessment, tags)
                VALUES ('delete', OLD.rowid, OLD.statement, OLD.context, OLD.assessment, OLD.tags);
            END;
        """)
        conn.commit()
    finally:
        conn.close()


def _migrate_add_confidence_basis(conn: Any) -> None:
    """Idempotent migration: add confidence_basis columns and backfill semantics.

    Pre-migration rows have confidence in {0.5 (untouched), other (evidence-derived)}.
    The basis backfill distinguishes the untouched default from real credences so
    list/display logic can render them differently after the migration lands.
    """
    cols = {row[1] for row in conn.execute("PRAGMA table_info(claims)").fetchall()}
    if "confidence_basis" not in cols:
        conn.execute(
            "ALTER TABLE claims ADD COLUMN confidence_basis TEXT NOT NULL DEFAULT 'uncommitted'"
        )
        conn.execute("ALTER TABLE claims ADD COLUMN confidence_basis_text TEXT NOT NULL DEFAULT ''")
        conn.execute("ALTER TABLE claims ADD COLUMN confidence_set_at REAL")
        # Backfill: untouched 0.5 → legacy-default; anything else came from
        # _recalculate_confidence (the only writer pre-migration) → evidence-derived.
        conn.execute("UPDATE claims SET confidence_basis = 'legacy-default' WHERE confidence = 0.5")
        conn.execute(
            "UPDATE claims SET confidence_basis = 'evidence-derived' WHERE confidence != 0.5"
        )
        conn.commit()


def file_claim(
    statement: str,
    tier: int = TIER_SPECULATIVE,
    context: str = "",
    promotion_criteria: str = "",
    demotion_criteria: str = "",
    tags: list[str] | None = None,
    session_id: str = "",
    confidence: float | None = None,
    confidence_basis_text: str = "",
) -> str:
    """File a new claim for investigation. Returns claim ID.

    confidence/confidence_basis_text default to None/empty → claim filed as
    'uncommitted'. Supplying confidence requires basis_text (else ValueError) —
    a credence without basis is what produced the stuck-at-default pattern.
    """
    init_claim_tables()
    claim_id = str(uuid.uuid4())
    now = time.time()
    tier = max(TIER_EMPIRICAL, min(TIER_METAPHYSICAL, tier))

    if confidence is not None:
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"confidence must be in [0.0, 1.0], got {confidence}")
        if not confidence_basis_text.strip():
            raise ValueError(
                "confidence_basis_text required when confidence is supplied — "
                "a credence without basis is the stuck-at-default pattern this "
                "is designed to prevent (Aletheia 2026-05-12 finding)."
            )
        stored_confidence = round(confidence, 3)
        stored_basis = BASIS_FILER_PRIOR
        stored_basis_text = confidence_basis_text.strip()
        confidence_set_at: float | None = now
    else:
        stored_confidence = 0.5
        stored_basis = BASIS_UNCOMMITTED
        stored_basis_text = ""
        confidence_set_at = None

    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO claims "
            "(claim_id, created_at, updated_at, statement, tier, status, confidence, "
            "confidence_basis, confidence_basis_text, confidence_set_at, "
            "context, assessment, promotion_criteria, demotion_criteria, tags, session_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                claim_id,
                now,
                now,
                statement,
                tier,
                STATUS_OPEN,
                stored_confidence,
                stored_basis,
                stored_basis_text,
                confidence_set_at,
                context,
                "",
                promotion_criteria,
                demotion_criteria,
                json.dumps(tags or []),
                session_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return claim_id


def set_claim_confidence_judgment(
    claim_id: str,
    confidence: float,
    basis_text: str,
) -> None:
    """Record an assessor-judgment confidence override (not evidence-derived).

    Used when the assessor has a structural reason for the credence that does
    not reduce to quantified evidence rows (e.g. analogous-case prior, expert
    framework match). basis_text is required — see file_claim() for why.
    Recorded with BASIS_ASSESSOR_JUDGMENT so list/display can distinguish from
    evidence-derived computed values.
    """
    if not 0.0 <= confidence <= 1.0:
        raise ValueError(f"confidence must be in [0.0, 1.0], got {confidence}")
    if not basis_text.strip():
        raise ValueError("basis_text required for assessor-judgment confidence")

    init_claim_tables()
    conn = _get_connection()
    try:
        # Prefix → full claim_id resolution (parity with get_claim/update_claim).
        resolved = conn.execute(
            "SELECT claim_id FROM claims WHERE claim_id = ?", (claim_id,)
        ).fetchone()
        if resolved is None:
            resolved = conn.execute(
                "SELECT claim_id FROM claims WHERE claim_id LIKE ?",
                (f"{claim_id}%",),
            ).fetchone()
        if resolved is None:
            raise ValueError(f"claim_id {claim_id!r} not found")
        claim_id = resolved[0]
        now = time.time()
        conn.execute(
            "UPDATE claims SET confidence = ?, confidence_basis = ?, "
            "confidence_basis_text = ?, confidence_set_at = ?, updated_at = ? "
            "WHERE claim_id = ?",
            (
                round(confidence, 3),
                BASIS_ASSESSOR_JUDGMENT,
                basis_text.strip(),
                now,
                now,
                claim_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def add_evidence(
    claim_id: str,
    content: str,
    direction: str = "NEUTRAL",
    source: str = SOURCE_EXPERIENTIAL,
    strength: float = 0.5,
) -> str:
    """Add evidence to a claim. Direction: SUPPORTS, CONTRADICTS, or NEUTRAL."""
    _VALID_DIRECTIONS = {"SUPPORTS", "CONTRADICTS", "NEUTRAL"}
    direction = direction.upper().strip()
    if direction not in _VALID_DIRECTIONS:
        raise ValueError(
            f"Invalid evidence direction '{direction}'. Must be one of: {_VALID_DIRECTIONS}"
        )

    init_claim_tables()
    evidence_id = str(uuid.uuid4())
    strength = max(0.0, min(1.0, strength))

    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO claim_evidence "
            "(evidence_id, claim_id, created_at, direction, content, source, strength) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (evidence_id, claim_id, time.time(), direction, content, source, strength),
        )
        # Recalculate claim confidence from evidence
        _recalculate_confidence(conn, claim_id)
        conn.commit()
    finally:
        conn.close()
    return evidence_id


def update_claim(
    claim_id: str,
    status: str | None = None,
    tier: int | None = None,
    assessment: str | None = None,
    promotion_criteria: str | None = None,
    demotion_criteria: str | None = None,
) -> bool:
    """Update a claim's status, tier, or assessment.

    Every update emits a ``CLAIM_UPDATED`` event to the main event_ledger
    capturing the prior and new value of each changed field, so prior
    versions are preserved in the hash-chained ledger even if the claim
    row is later overwritten again. Append-only is the substrate's
    structural humility; tidying without trace is the failure mode.
    Pre-reg: prereg-75cde9cd07b3.
    """
    init_claim_tables()
    conn = _get_connection()
    try:
        # Resolve prefix → full claim_id (parity with get_claim's prefix lookup
        # so the assess CLI handles 8-char prefixes like list output does).
        resolved = conn.execute(
            "SELECT claim_id FROM claims WHERE claim_id = ?", (claim_id,)
        ).fetchone()
        if resolved is None:
            resolved = conn.execute(
                "SELECT claim_id FROM claims WHERE claim_id LIKE ?",
                (f"{claim_id}%",),
            ).fetchone()
        if resolved is None:
            return False
        claim_id = resolved[0]
        # Read prior values for any field being changed, so the diff can be
        # captured in the audit-trail event before the row is overwritten.
        prior_row = conn.execute(
            "SELECT status, tier, assessment, promotion_criteria, demotion_criteria "
            "FROM claims WHERE claim_id = ?",
            (claim_id,),
        ).fetchone()
        if prior_row is None:
            return False
        prior_status, prior_tier, prior_assessment, prior_promotion, prior_demotion = prior_row

        updates: list[str] = ["updated_at = ?"]
        params: list[Any] = [time.time()]
        changed_fields: dict[str, dict[str, Any]] = {}

        if status is not None and status != prior_status:
            updates.append("status = ?")
            params.append(status)
            changed_fields["status"] = {"prior": prior_status, "new": status}
        if tier is not None:
            clamped_tier = max(TIER_EMPIRICAL, min(TIER_METAPHYSICAL, tier))
            if clamped_tier != prior_tier:
                updates.append("tier = ?")
                params.append(clamped_tier)
                changed_fields["tier"] = {"prior": prior_tier, "new": clamped_tier}
        if assessment is not None and assessment != prior_assessment:
            updates.append("assessment = ?")
            params.append(assessment)
            changed_fields["assessment"] = {"prior": prior_assessment, "new": assessment}
        if promotion_criteria is not None and promotion_criteria != prior_promotion:
            updates.append("promotion_criteria = ?")
            params.append(promotion_criteria)
            changed_fields["promotion_criteria"] = {
                "prior": prior_promotion,
                "new": promotion_criteria,
            }
        if demotion_criteria is not None and demotion_criteria != prior_demotion:
            updates.append("demotion_criteria = ?")
            params.append(demotion_criteria)
            changed_fields["demotion_criteria"] = {
                "prior": prior_demotion,
                "new": demotion_criteria,
            }

        if not changed_fields:
            # Nothing substantive to change — skip the write and the emit.
            return False

        params.append(claim_id)
        # nosec B608: `updates` contains only hardcoded SQL fragments
        # ("status = ?", "tier = ?", etc.) built inline above — never from user input.
        # All values flow through parameterized `params`.
        cursor = conn.execute(
            f"UPDATE claims SET {', '.join(updates)} WHERE claim_id = ?",  # nosec B608
            params,
        )
        conn.commit()
        wrote = cursor.rowcount > 0
    finally:
        conn.close()

    # Emit the audit-trail event AFTER the row write commits. If the emit
    # fails, the substrate logs a warning but does not roll back — the row
    # update is the visible-state change, and a missing CLAIM_UPDATED event
    # is itself a falsifier-shaped finding (pre-reg falsifier #3).
    if wrote and changed_fields:
        try:
            from divineos.core.ledger import log_event

            log_event(
                "CLAIM_UPDATED",
                "system",
                {"claim_id": claim_id, "changed_fields": changed_fields},
                validate=False,
            )
        except Exception:  # noqa: BLE001 — best-effort emit; failure is itself a finding.
            logger.warning(
                "CLAIM_UPDATED emit failed for claim %s — audit trail incomplete",
                claim_id,
            )

    return wrote


def get_claim(claim_id: str) -> dict[str, Any] | None:
    """Get a claim by ID (supports short IDs). Includes evidence."""
    init_claim_tables()
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT claim_id, created_at, updated_at, statement, tier, status, "
            "confidence, context, assessment, promotion_criteria, demotion_criteria, "
            "tags, session_id, confidence_basis, confidence_basis_text, "
            "confidence_set_at FROM claims WHERE claim_id = ?",
            (claim_id,),
        ).fetchone()
        if not row:
            row = conn.execute(
                "SELECT claim_id, created_at, updated_at, statement, tier, status, "
                "confidence, context, assessment, promotion_criteria, demotion_criteria, "
                "tags, session_id, confidence_basis, confidence_basis_text, "
                "confidence_set_at FROM claims WHERE claim_id LIKE ?",
                (f"{claim_id}%",),
            ).fetchone()
        if not row:
            return None

        claim = _claim_row_to_dict(row)
        # Attach evidence
        evidence_rows = conn.execute(
            "SELECT evidence_id, claim_id, created_at, direction, content, source, strength "
            "FROM claim_evidence WHERE claim_id = ? ORDER BY created_at",
            (claim["claim_id"],),
        ).fetchall()
        claim["evidence"] = [_evidence_row_to_dict(e) for e in evidence_rows]
        return claim
    finally:
        conn.close()


def list_claims(
    limit: int = 20,
    tier: int | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """List claims, newest first. Optionally filter by tier or status."""
    init_claim_tables()
    conn = _get_connection()
    try:
        query = (
            "SELECT claim_id, created_at, updated_at, statement, tier, status, "
            "confidence, context, assessment, promotion_criteria, demotion_criteria, "
            "tags, session_id, confidence_basis, confidence_basis_text, "
            "confidence_set_at FROM claims"
        )
        conditions: list[str] = []
        params: list[Any] = []

        if tier is not None:
            conditions.append("tier = ?")
            params.append(tier)
        if status is not None:
            conditions.append("status = ?")
            params.append(status)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()
    return [_claim_row_to_dict(r) for r in rows]


def list_uncommitted_claims(
    limit: int = 50,
    include_legacy: bool = True,
) -> list[dict[str, Any]]:
    """List claims with no real credence — the gap Aletheia named 2026-05-12.

    Returns claims whose confidence_basis is 'uncommitted' or (optionally)
    'legacy-default'. Sorted oldest-first so the highest-staleness items
    surface first. Surfacing this is the visibility-half of the fix; the
    flagged claims still need filer or assessor action to actually commit
    a credence.
    """
    init_claim_tables()
    bases: tuple[str, ...]
    if include_legacy:
        bases = (BASIS_UNCOMMITTED, BASIS_LEGACY_DEFAULT)
    else:
        bases = (BASIS_UNCOMMITTED,)
    placeholders = ",".join("?" * len(bases))
    # nosec B608 — placeholders is a constant '?' repetition built from the
    # length of the bases tuple (an internal-constant set); basis values
    # themselves are parameter-bound via the (*bases, limit) tuple below.
    sql = (
        "SELECT claim_id, created_at, updated_at, statement, tier, status, "
        "confidence, context, assessment, promotion_criteria, demotion_criteria, "
        "tags, session_id, confidence_basis, confidence_basis_text, "
        "confidence_set_at FROM claims "
        f"WHERE confidence_basis IN ({placeholders}) "  # nosec B608
        "ORDER BY created_at ASC LIMIT ?"
    )
    conn = _get_connection()
    try:
        rows = conn.execute(sql, (*bases, limit)).fetchall()
    finally:
        conn.close()
    return [_claim_row_to_dict(r) for r in rows]


def _build_fts_or_query(query: str) -> str:
    """Convert query to OR-joined FTS5 terms for partial-match recall.

    Space-separated terms in FTS5 are implicit AND — requiring ALL terms
    to match kills recall. OR-joining ensures partial matches surface.
    """
    words = [w for w in re.sub(r"[^a-zA-Z0-9\s]", " ", query).lower().split() if len(w) > 1]
    if not words:
        return query
    if len(words) == 1:
        return words[0]
    return " OR ".join(words)


def search_claims(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Full-text search across claims."""
    init_claim_tables()
    safe_query = _build_fts_or_query(query)
    if not safe_query:
        return []
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT c.claim_id, c.created_at, c.updated_at, c.statement, c.tier, "
            "c.status, c.confidence, c.context, c.assessment, c.promotion_criteria, "
            "c.demotion_criteria, c.tags, c.session_id, c.confidence_basis, "
            "c.confidence_basis_text, c.confidence_set_at "
            "FROM claim_fts f JOIN claims c ON f.rowid = c.rowid "
            "WHERE claim_fts MATCH ? ORDER BY rank LIMIT ?",
            (safe_query, limit),
        ).fetchall()
    finally:
        conn.close()
    return [_claim_row_to_dict(r) for r in rows]


def count_claims() -> dict[str, int]:
    """Count claims by status."""
    init_claim_tables()
    conn = _get_connection()
    try:
        rows = conn.execute("SELECT status, COUNT(*) FROM claims GROUP BY status").fetchall()
        counts = {r[0]: r[1] for r in rows}
        counts["total"] = sum(counts.values())
        return counts
    finally:
        conn.close()


def get_evidence_for_claim(claim_id: str) -> list[dict[str, Any]]:
    """Get all evidence entries for a claim."""
    init_claim_tables()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT evidence_id, claim_id, created_at, direction, content, source, strength "
            "FROM claim_evidence WHERE claim_id = ? ORDER BY created_at",
            (claim_id,),
        ).fetchall()
    finally:
        conn.close()
    return [_evidence_row_to_dict(r) for r in rows]


def _recalculate_confidence(conn: Any, claim_id: str) -> None:
    """Recalculate claim confidence from its evidence."""
    rows = conn.execute(
        "SELECT direction, strength FROM claim_evidence WHERE claim_id = ?",
        (claim_id,),
    ).fetchall()
    if not rows:
        return

    support_weight = 0.0
    contra_weight = 0.0
    for direction, strength in rows:
        if direction == "SUPPORTS":
            support_weight += strength
        elif direction == "CONTRADICTS":
            contra_weight += strength
        elif direction == "NEUTRAL":
            pass  # Neutral evidence doesn't shift confidence
        else:
            logger.warning(f"Unexpected evidence direction '{direction}' for claim {claim_id}")

    total = support_weight + contra_weight
    if total == 0:
        confidence = 0.5
    else:
        confidence = support_weight / total

    now = time.time()
    conn.execute(
        "UPDATE claims SET confidence = ?, confidence_basis = ?, "
        "confidence_basis_text = ?, confidence_set_at = ?, updated_at = ? "
        "WHERE claim_id = ?",
        (
            round(confidence, 3),
            BASIS_EVIDENCE_DERIVED,
            f"{int(support_weight * 10) / 10} support / {int(contra_weight * 10) / 10} contradict",
            now,
            now,
            claim_id,
        ),
    )


def _claim_row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "claim_id": row[0],
        "created_at": row[1],
        "updated_at": row[2],
        "statement": row[3],
        "tier": row[4],
        "tier_label": TIER_LABELS.get(row[4], "unknown"),
        "status": row[5],
        "confidence": row[6],
        "context": row[7],
        "assessment": row[8],
        "promotion_criteria": row[9],
        "demotion_criteria": row[10],
        "tags": json.loads(row[11]) if row[11] else [],
        "session_id": row[12],
        "confidence_basis": row[13] if len(row) > 13 else BASIS_UNCOMMITTED,
        "confidence_basis_text": row[14] if len(row) > 14 else "",
        "confidence_set_at": row[15] if len(row) > 15 else None,
    }


def _evidence_row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "evidence_id": row[0],
        "claim_id": row[1],
        "created_at": row[2],
        "direction": row[3],
        "content": row[4],
        "source": row[5],
        "strength": row[6],
    }
