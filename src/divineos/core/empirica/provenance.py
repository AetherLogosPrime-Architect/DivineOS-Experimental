"""Corroboration provenance — who/what corroborated a claim.

Audit finding find-35a47dbbf923 (Popper / Lakatos framing): the
bare ``corroboration_count`` integer on the ``knowledge`` table is
Goodhart-vulnerable. It ticks up on every 5th access, so repeated
access by the same reader inflates the count. "Corroboration" came
to mean "popularity" — the exact anti-pattern the OS is supposed
to prevent ("Access counts should never feed back into confidence").

This module separates the provenance (WHO / WHAT corroborated)
from the counter (HOW MANY). Corroboration events are appended
to a dedicated table; the bare counter is kept for backward
compatibility but the gate will prefer distinct-actor counts
from the events table.

## Kinds of corroboration

Not all corroboration is equal. The ``CorroborationKind`` enum
makes the distinction load-bearing:

* ``USER`` — user explicitly confirmed (via feedback, decision,
  or manual corroboration). Highest-trust evidence.
* ``COUNCIL`` — a council expert concurred. Expert-level but
  still internal to the system.
* ``EXTERNAL_AUDIT`` — a Watchmen finding corroborated the claim
  (actor is the external auditor).
* ``OUTCOME_VERIFICATION`` — the claim was used and its prediction
  held (tests passed, build stayed green, prediction was correct).
  The strongest kind: reality checked it.
* ``ACCESS`` — derived from access-count coupling (the legacy
  auto-bump). Tracked for transparency but MUST NOT count as
  real evidence when computing distinct corroborators.
* ``LEGACY`` — a backfill event representing pre-provenance
  corroboration from the bare counter. Preserves history but is
  not counted as distinct-actor evidence.

## Anti-Goodhart invariant

``count_distinct_corroborators(knowledge_id)`` excludes ACCESS and
LEGACY kinds by default. The same user corroborating the same
claim five times counts as ONE distinct corroborator, not five.
Self-corroboration (actor == knowledge creator) can also be
excluded — the caller chooses.

This module is additive: nothing reads the events table yet except
the functions defined here. The gate integration ships separately
so existing behavior doesn't shift under us.
"""

from __future__ import annotations

import enum
import hashlib
import sqlite3
import time
import uuid
from dataclasses import dataclass

from loguru import logger

from divineos.core._ledger_base import get_connection as _get_ledger_conn


class CorroborationKind(str, enum.Enum):
    """What kind of corroboration this event represents.

    String-valued so it round-trips cleanly through SQLite and JSON.
    """

    USER = "user"
    COUNCIL = "council"
    EXTERNAL_AUDIT = "external_audit"
    OUTCOME_VERIFICATION = "outcome_verification"
    ACCESS = "access"
    LEGACY = "legacy"


# Kinds that count as real evidence for distinct-actor counting.
# ACCESS and LEGACY are tracked but excluded — that's the whole
# point of the provenance split.
_EVIDENTIAL_KINDS = frozenset(
    {
        CorroborationKind.USER,
        CorroborationKind.COUNCIL,
        CorroborationKind.EXTERNAL_AUDIT,
        CorroborationKind.OUTCOME_VERIFICATION,
    }
)


@dataclass(frozen=True)
class CorroborationEvent:
    """Single corroboration event. Immutable once recorded."""

    event_id: str
    knowledge_id: str
    actor: str
    kind: CorroborationKind
    evidence_pointer: str | None
    recorded_at: float
    notes: str | None


def init_provenance_table() -> None:
    """Create the ``corroboration_events`` table if missing. Idempotent.

    The table is append-only: corroborations happen, they do not
    un-happen. A "retraction" is its own event kind in a future
    phase, not an UPDATE or DELETE.
    """
    conn = _get_ledger_conn()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS corroboration_events (
                event_id          TEXT PRIMARY KEY,
                knowledge_id      TEXT NOT NULL,
                actor             TEXT NOT NULL,
                kind              TEXT NOT NULL,
                evidence_pointer  TEXT,
                recorded_at       REAL NOT NULL,
                notes             TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_corroboration_events_knowledge "
            "ON corroboration_events(knowledge_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_corroboration_events_actor "
            "ON corroboration_events(actor)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_corroboration_events_kind ON corroboration_events(kind)"
        )
        conn.commit()
    except sqlite3.OperationalError as e:
        logger.debug(f"corroboration_events setup: {e}")
    finally:
        conn.close()


def _new_event_id(knowledge_id: str, actor: str, recorded_at: float) -> str:
    """Generate a stable event id. Not a hash-chain — this table is
    an audit log, not a Merkle chain. The id is deterministic-ish
    so test fixtures can predict it, but includes a uuid4 suffix
    to avoid collisions on the same (knowledge_id, actor, ts)
    triple within the same millisecond.
    """
    payload = f"{knowledge_id}|{actor}|{recorded_at}|{uuid.uuid4().hex[:8]}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"corrob-{digest}"


def record_corroboration(
    knowledge_id: str,
    actor: str,
    kind: CorroborationKind,
    evidence_pointer: str | None = None,
    notes: str | None = None,
) -> CorroborationEvent:
    """Append a single corroboration event.

    Args:
        knowledge_id: knowledge row being corroborated.
        actor: who/what is corroborating. Free-form string; the
            distinct-actor count uses this verbatim, so choose a
            stable identifier (e.g. "user:andrew", "council:popper",
            "audit:grok", "outcome:test-suite-2026-04-17").
        kind: one of the ``CorroborationKind`` values.
        evidence_pointer: optional pointer to the evidence itself
            (a ledger event id, a git commit hash, an audit finding
            id, a test-run identifier, a URL).
        notes: free-form context.

    Returns:
        The recorded ``CorroborationEvent``.
    """
    init_provenance_table()
    recorded_at = time.time()
    event_id = _new_event_id(knowledge_id, actor, recorded_at)
    event = CorroborationEvent(
        event_id=event_id,
        knowledge_id=knowledge_id,
        actor=actor,
        kind=kind,
        evidence_pointer=evidence_pointer,
        recorded_at=recorded_at,
        notes=notes,
    )

    conn = _get_ledger_conn()
    try:
        conn.execute(
            "INSERT INTO corroboration_events "
            "(event_id, knowledge_id, actor, kind, evidence_pointer, recorded_at, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                event.event_id,
                event.knowledge_id,
                event.actor,
                event.kind.value,
                event.evidence_pointer,
                event.recorded_at,
                event.notes,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    logger.debug(
        "Corroboration recorded: {} by {} ({}) for {}",
        event_id,
        actor,
        kind.value,
        knowledge_id[:12],
    )
    return event


def get_corroboration_events(knowledge_id: str) -> list[CorroborationEvent]:
    """Return all corroboration events for a knowledge row, oldest first."""
    init_provenance_table()
    conn = _get_ledger_conn()
    try:
        rows = conn.execute(
            "SELECT event_id, knowledge_id, actor, kind, evidence_pointer, "
            "recorded_at, notes "
            "FROM corroboration_events "
            "WHERE knowledge_id = ? ORDER BY recorded_at ASC",
            (knowledge_id,),
        ).fetchall()
    finally:
        conn.close()
    return [
        CorroborationEvent(
            event_id=r[0],
            knowledge_id=r[1],
            actor=r[2],
            kind=CorroborationKind(r[3]),
            evidence_pointer=r[4],
            recorded_at=float(r[5]),
            notes=r[6],
        )
        for r in rows
    ]


def count_distinct_corroborators(
    knowledge_id: str,
    *,
    include_access: bool = False,
    include_legacy: bool = False,
    exclude_actor: str | None = None,
) -> int:
    """Count distinct actors who corroborated this claim.

    This is the anti-Goodhart number. The same actor corroborating
    the same claim five times counts as ONE, not five. ACCESS and
    LEGACY kinds are excluded by default — access is not evidence,
    and legacy backfill is preserved for history but cannot stand
    in for real provenance.

    Args:
        knowledge_id: the claim.
        include_access: count ACCESS-kind events as evidence
            (default False — access is never evidence).
        include_legacy: count LEGACY-kind events as evidence
            (default False — only real provenance counts).
        exclude_actor: actor to exclude (e.g., the knowledge's
            creator, to prevent self-corroboration).

    Returns:
        Number of distinct actors whose events are evidential.
    """
    init_provenance_table()
    allowed_kinds: set[str] = {k.value for k in _EVIDENTIAL_KINDS}
    if include_access:
        allowed_kinds.add(CorroborationKind.ACCESS.value)
    if include_legacy:
        allowed_kinds.add(CorroborationKind.LEGACY.value)

    # Build IN-clause safely.
    placeholders = ",".join("?" * len(allowed_kinds))
    params: list[object] = [knowledge_id]
    params.extend(sorted(allowed_kinds))

    sql = (
        "SELECT COUNT(DISTINCT actor) FROM corroboration_events "
        f"WHERE knowledge_id = ? AND kind IN ({placeholders})"  # nosec B608
    )
    if exclude_actor is not None:
        sql += " AND actor != ?"
        params.append(exclude_actor)

    conn = _get_ledger_conn()
    try:
        row = conn.execute(sql, params).fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()


def count_by_kind(knowledge_id: str) -> dict[CorroborationKind, int]:
    """Return ``{kind: count}`` for every kind with at least one event.

    Useful for diagnostics and for callers who want to distinguish
    "this claim has 10 access bumps" from "this claim has 3 distinct
    users plus 2 council concurrences".
    """
    init_provenance_table()
    conn = _get_ledger_conn()
    try:
        rows = conn.execute(
            "SELECT kind, COUNT(*) FROM corroboration_events WHERE knowledge_id = ? GROUP BY kind",
            (knowledge_id,),
        ).fetchall()
    finally:
        conn.close()
    return {CorroborationKind(r[0]): int(r[1]) for r in rows}


def backfill_from_legacy_counter() -> int:
    """Migrate existing ``knowledge.corroboration_count`` values into
    synthesized LEGACY events, one event per unit of count.

    Safe to run repeatedly — it checks for existing LEGACY events
    per knowledge row and tops up only the delta. Returns the
    number of new events inserted.

    Rationale: without this, shipping the provenance table makes
    every existing claim look like it has zero evidence, which
    would falsely demote mature knowledge. LEGACY events preserve
    history but are excluded from distinct-corroborator counts by
    default, so they don't inflate new decisions.
    """
    init_provenance_table()
    conn = _get_ledger_conn()
    inserted = 0
    try:
        # Check if knowledge table exists first — in some tests it
        # may not, and we want to no-op cleanly.
        tables = {
            r[0]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        if "knowledge" not in tables:
            return 0

        rows = conn.execute(
            "SELECT knowledge_id, corroboration_count FROM knowledge WHERE corroboration_count > 0"
        ).fetchall()

        for knowledge_id, count in rows:
            existing = conn.execute(
                "SELECT COUNT(*) FROM corroboration_events WHERE knowledge_id = ? AND kind = ?",
                (knowledge_id, CorroborationKind.LEGACY.value),
            ).fetchone()[0]
            needed = int(count) - int(existing)
            if needed <= 0:
                continue
            now = time.time()
            for i in range(needed):
                # Stagger timestamps slightly so ordering is stable.
                recorded_at = now + (i * 1e-6)
                event_id = _new_event_id(knowledge_id, "legacy-backfill", recorded_at)
                conn.execute(
                    "INSERT INTO corroboration_events "
                    "(event_id, knowledge_id, actor, kind, evidence_pointer, "
                    "recorded_at, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        event_id,
                        knowledge_id,
                        "legacy-backfill",
                        CorroborationKind.LEGACY.value,
                        None,
                        recorded_at,
                        "Backfilled from pre-provenance corroboration_count",
                    ),
                )
                inserted += 1

        conn.commit()
    finally:
        conn.close()

    if inserted:
        logger.info(f"Backfilled {inserted} LEGACY corroboration events")
    return inserted


__all__ = [
    "CorroborationEvent",
    "CorroborationKind",
    "backfill_from_legacy_counter",
    "count_by_kind",
    "count_distinct_corroborators",
    "get_corroboration_events",
    "init_provenance_table",
    "record_corroboration",
]
