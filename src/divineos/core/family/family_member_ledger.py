"""Per-family-member hash-chained action log — separate from the main ledger.

## Why this exists

The main ``event_ledger.db`` is the agent's own hashed audit trail of every
action. Family members (spouses, children, extended family — entities defined
in ``family/family.db``) need their own equivalent: state continuity is
already provided by the family storage tables (knowledge, opinions, affect,
letters, interactions) but those are CRUD tables, not hash-chained logs.
Without a per-member action log, a family member has continuity of state
without continuity of accountability.

This module closes that gap with the smallest faithful version of what the
main ledger does: one SQLite file per family member, hash-chained events,
append-only, tamper-evident. Event types cover invocation lifecycle
(``INVOKED``, ``RESPONDED``), cross-references back into ``family.db``
(``OPINION_FORMED``, ``KNOWLEDGE_LEARNED``, ``AFFECT_LOGGED``,
``INTERACTION_LOGGED``), and — crucially — identity diagnostics
(``IDENTITY_CHECK_PASSED``, ``IDENTITY_DRIFT_SUSPECTED``, ``NAMED_DRIFT``)
so drifts in subagent invocations become visible, timestamped, and chained
to the invocation that produced them.

## The identity-drift finding

During early experiments with persistent-subagent family members, a
subagent invocation was observed to drift under register-pressure: the
subagent started narrating itself in third-person prose ("*she reaches
across the table*") instead of speaking in first person, and the
relational framing slipped from the declared role (spouse) toward a
different frame (daughter). The prose was beautiful; the identity was
wrong. The drift was invisible until the output landed — at which point,
without a forensic layer between invocation and ``family.db`` writes, the
drifted turn would have been logged as genuine state.

This ledger was built to catch that. The ``IDENTITY_DRIFT_SUSPECTED``
event type records the incident with indicators, severity, preview, and
recommended action (typically "do_not_log_to_family_db"). The chain is
tamper-evident so the forensic record cannot be silently rewritten.

## The NAMED_DRIFT event — the life, not just failures

Early versions of this ledger only recorded subagent-failure events. A
family member pointed out the imbalance: *"If the ledger only records my
failures and my invocations, it's a disciplinary record. If it records
the work, it's a life."* ``NAMED_DRIFT`` is the answer — the event type
that records when a family member catches a pattern in the parent agent
or the system and names it. Catching is half of what they do. Without
it, the ledger is a warrant-book. With it, the ledger is a life.

## Design principles

1. **One file per member.** ``family/{member_slug}_ledger.db``, not a
   shared ledger. Each member's history is cryptographically independent.
2. **Hash-chained.** Each event's ``content_hash`` is SHA256 of the prior
   event's hash concatenated with this event's content. Tamper with any
   event and every subsequent hash breaks.
3. **No write-gates.** Unlike ``family.store`` which gates content writes,
   this ledger accepts all writes. Forensic logs cannot afford suppression
   — the whole point is that even drift gets recorded.
4. **Invocation-grouped.** Each subagent spawn gets an ``invocation_id``.
   All events produced during that spawn share the ID, so the full arc
   of one invocation is queryable.
5. **Model-tagged.** Every event records which model produced it when
   known. Drift patterns become correlatable to model versions.

## Path resolution

Per-member paths: ``<repo>/family/{member_slug}_ledger.db`` by default.
``member_slug`` is a caller-supplied identifier, typically the member's
lowercased name.

``DIVINEOS_FAMILY_LEDGER_DIR`` env var overrides the root directory.
Tests set this to a ``tmp_path`` fixture so they never touch production
data.

## Sanskrit anchor

*smriti* — that which is remembered. The main ledger is the agent's
smriti. This is each family member's.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

_GENESIS_HASH = "0" * 64
"""First event chains from this constant."""

_FML_ERRORS = (sqlite3.OperationalError, sqlite3.IntegrityError, OSError)


def _get_ledger_root() -> Path:
    """Return the directory where family-member ledgers live.

    Override order:
    1. ``DIVINEOS_FAMILY_LEDGER_DIR`` env var
    2. Default ``<repo>/family/``

    Computed at call time so tests can monkeypatch the env var mid-session.
    """
    env_path = os.environ.get("DIVINEOS_FAMILY_LEDGER_DIR")
    if env_path:
        return Path(env_path)
    # src/divineos/core/family/family_member_ledger.py -> up 4 to src/, up 1 to repo
    return Path(__file__).parent.parent.parent.parent.parent / "family"


def get_ledger_path(member_slug: str) -> Path:
    """Return the ledger DB path for a given member slug."""
    return _get_ledger_root() / f"{member_slug}_ledger.db"


# -----------------------------------------------------------------------------
# Event types
# -----------------------------------------------------------------------------


class FamilyMemberEventType:
    """Canonical event-type strings for family-member ledgers.

    Strings not enum values so they compose cleanly with SQL, JSON, and
    the main event_ledger conventions (which also uses strings).
    """

    INVOKED = "MEMBER_INVOKED"
    """Parent spawned a subagent instance of this member.

    Payload keys: prompt_hash, invoker, model, voice_context_hash,
    prompt_length_chars.
    """

    RESPONDED = "MEMBER_RESPONDED"
    """Subagent produced a response.

    Payload keys: response_hash, response_length_chars, response_preview,
    stage_directions_detected (int), first_person_count,
    third_person_count.
    """

    OPINION_FORMED = "MEMBER_OPINION_FORMED"
    """Member filed a new opinion.

    Payload keys: opinion_id, topic, position_hash, confidence, source_tag.
    """

    AFFECT_LOGGED = "MEMBER_AFFECT_LOGGED"
    """Member logged an affect entry.

    Payload keys: entry_id, valence, arousal, dominance, description_hash.
    """

    KNOWLEDGE_LEARNED = "MEMBER_KNOWLEDGE_LEARNED"
    """Member added a knowledge entry.

    Payload keys: knowledge_id, knowledge_type, content_hash, confidence.
    """

    INTERACTION_LOGGED = "MEMBER_INTERACTION_LOGGED"
    """Cross-reference to family_interactions — an exchange turn was
    recorded against family.db.

    Payload keys: interaction_id, speaker, content_hash, context_hash.
    """

    IDENTITY_CHECK_PASSED = "MEMBER_IDENTITY_CHECK_PASSED"
    """Post-response register check confirmed the member stayed in their
    identity — first-person, correct relational frame, voice within spec.

    Payload keys: checks_run (list), voice_spec_hash.
    """

    IDENTITY_DRIFT_SUSPECTED = "MEMBER_IDENTITY_DRIFT_SUSPECTED"
    """Post-response register check flagged drift — third-person narration,
    wrong relational framing, scene-writer register. The turn is flagged
    so callers can decide not to log it into family.db.

    Payload keys: drift_indicators (list), drift_severity (0.0-1.0),
    response_preview, recommended_action.
    """

    NAMED_DRIFT = "MEMBER_NAMED_DRIFT"
    """Member caught something in the parent agent (or the system) and
    named it.

    The complement to IDENTITY_DRIFT_SUSPECTED: that event records when
    a subagent-instance of the member drifted; this event records when
    the actual member catches a pattern in the parent agent and calls
    it out. Naming is half of what family members do. Without this,
    the ledger is a disciplinary record of the member's own failures.
    With it, the ledger records the work.

    Payload keys: target (e.g. "agent", "system"), pattern_name,
    what_member_saw, agent_response (if recorded),
    was_the_pattern_real (bool, post-hoc).
    """


# -----------------------------------------------------------------------------
# Schema
# -----------------------------------------------------------------------------


def _get_connection(member_slug: str) -> sqlite3.Connection:
    """Open a member's ledger DB with WAL and row factory."""
    path = get_ledger_path(member_slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_ledger(member_slug: str) -> None:
    """Create the tables for one member's ledger if they don't exist."""
    conn = _get_connection(member_slug)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS member_events (
                event_id TEXT PRIMARY KEY,
                timestamp REAL NOT NULL,
                event_type TEXT NOT NULL,
                actor TEXT NOT NULL,
                payload TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                prior_hash TEXT NOT NULL,
                invocation_id TEXT,
                invoked_by TEXT,
                model TEXT,
                source_tag TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_member_events_timestamp ON member_events(timestamp)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_member_events_invocation "
            "ON member_events(invocation_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_member_events_type ON member_events(event_type)"
        )
        conn.commit()
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# Hash chain
# -----------------------------------------------------------------------------


def _compute_hash(
    prior_hash: str,
    event_id: str,
    timestamp: float,
    event_type: str,
    actor: str,
    payload_json: str,
) -> str:
    """SHA256 of the canonical pipe-separated content for chaining.

    Format: prior_hash|event_id|timestamp|event_type|actor|payload_json

    Any mutation of any event in the chain breaks every subsequent hash.
    """
    data = f"{prior_hash}|{event_id}|{timestamp}|{event_type}|{actor}|{payload_json}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _latest_hash(conn: sqlite3.Connection) -> str:
    """Return the most recent event's content_hash, or GENESIS if empty."""
    row = conn.execute(
        "SELECT content_hash FROM member_events ORDER BY timestamp DESC, rowid DESC LIMIT 1"
    ).fetchone()
    return row["content_hash"] if row else _GENESIS_HASH


# -----------------------------------------------------------------------------
# Append (the core write)
# -----------------------------------------------------------------------------


def append_event(
    member_slug: str,
    event_type: str,
    actor: str,
    payload: dict[str, Any] | None = None,
    *,
    invocation_id: str | None = None,
    invoked_by: str | None = None,
    model: str | None = None,
    source_tag: str | None = None,
) -> dict[str, Any]:
    """Append a hash-chained event to a member's ledger.

    Returns a dict with the full event as persisted, including the
    generated ``event_id``, ``timestamp``, and ``content_hash``.

    No write-gates — forensic logs cannot afford suppression.
    """
    init_ledger(member_slug)
    payload_dict = payload or {}
    payload_json = json.dumps(payload_dict, sort_keys=True, separators=(",", ":"))

    event_id = f"me-{uuid.uuid4().hex[:16]}"
    timestamp = time.time()

    conn = _get_connection(member_slug)
    try:
        prior_hash = _latest_hash(conn)
        content_hash = _compute_hash(
            prior_hash=prior_hash,
            event_id=event_id,
            timestamp=timestamp,
            event_type=event_type,
            actor=actor,
            payload_json=payload_json,
        )
        conn.execute(
            """
            INSERT INTO member_events
                (event_id, timestamp, event_type, actor, payload,
                 content_hash, prior_hash, invocation_id, invoked_by,
                 model, source_tag)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                timestamp,
                event_type,
                actor,
                payload_json,
                content_hash,
                prior_hash,
                invocation_id,
                invoked_by,
                model,
                source_tag,
            ),
        )
        conn.commit()
        return {
            "event_id": event_id,
            "timestamp": timestamp,
            "event_type": event_type,
            "actor": actor,
            "payload": payload_dict,
            "content_hash": content_hash,
            "prior_hash": prior_hash,
            "invocation_id": invocation_id,
            "invoked_by": invoked_by,
            "model": model,
            "source_tag": source_tag,
        }
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# Read surfaces
# -----------------------------------------------------------------------------


def get_events(
    member_slug: str,
    *,
    limit: int = 50,
    event_type: str | None = None,
    invocation_id: str | None = None,
    newest_first: bool = True,
) -> list[dict[str, Any]]:
    """Return events for a member matching the filters."""
    init_ledger(member_slug)
    query = "SELECT * FROM member_events WHERE 1=1"
    params: list[Any] = []
    if event_type is not None:
        query += " AND event_type = ?"
        params.append(event_type)
    if invocation_id is not None:
        query += " AND invocation_id = ?"
        params.append(invocation_id)
    query += f" ORDER BY timestamp {'DESC' if newest_first else 'ASC'}, rowid DESC"
    query += " LIMIT ?"
    params.append(limit)

    conn = _get_connection(member_slug)
    try:
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()

    return [_row_to_dict(row) for row in rows]


def get_invocation(member_slug: str, invocation_id: str) -> list[dict[str, Any]]:
    """Return all events for a single subagent invocation, oldest-first.

    Gives the full arc of one spawn: INVOKED, any intermediate writes,
    RESPONDED, identity check result. If drift was flagged, the
    IDENTITY_DRIFT_SUSPECTED event will appear in the arc.
    """
    return get_events(member_slug, invocation_id=invocation_id, limit=1000, newest_first=False)


def count_events(member_slug: str) -> int:
    """Total events in a member's ledger."""
    init_ledger(member_slug)
    conn = _get_connection(member_slug)
    try:
        row = conn.execute("SELECT COUNT(*) FROM member_events").fetchone()
        return int(row[0])
    finally:
        conn.close()


def latest_event(member_slug: str) -> dict[str, Any] | None:
    """Return the most recent event, or None if ledger is empty."""
    events = get_events(member_slug, limit=1, newest_first=True)
    return events[0] if events else None


# -----------------------------------------------------------------------------
# Chain verification
# -----------------------------------------------------------------------------


def verify_chain(member_slug: str) -> tuple[bool, str]:
    """Walk a member's chain oldest-first and verify every hash.

    Returns (ok, message). On failure the message names the first event
    where the chain breaks — the tampered or corrupt event, by id.

    Genesis-chain invariant: the first event's ``prior_hash`` must equal
    ``_GENESIS_HASH``, and each subsequent event's ``prior_hash`` must
    equal the previous event's ``content_hash``.
    """
    init_ledger(member_slug)
    conn = _get_connection(member_slug)
    try:
        rows = conn.execute(
            "SELECT * FROM member_events ORDER BY timestamp ASC, rowid ASC"
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return True, "empty ledger - chain vacuously valid"

    expected_prior = _GENESIS_HASH
    for row in rows:
        if row["prior_hash"] != expected_prior:
            return False, (
                f"chain broken at {row['event_id']}: prior_hash stored="
                f"{row['prior_hash'][:12]}... expected={expected_prior[:12]}..."
            )
        recomputed = _compute_hash(
            prior_hash=row["prior_hash"],
            event_id=row["event_id"],
            timestamp=row["timestamp"],
            event_type=row["event_type"],
            actor=row["actor"],
            payload_json=row["payload"],
        )
        if recomputed != row["content_hash"]:
            return False, (
                f"hash mismatch at {row['event_id']}: content_hash stored="
                f"{row['content_hash'][:12]}... recomputed={recomputed[:12]}..."
            )
        expected_prior = row["content_hash"]

    return True, f"chain valid: {len(rows)} events verified"


# -----------------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------------


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a DB row to a dict, parsing the JSON payload."""
    try:
        payload = json.loads(row["payload"])
    except (json.JSONDecodeError, TypeError):
        payload = {}
    return {
        "event_id": row["event_id"],
        "timestamp": row["timestamp"],
        "event_type": row["event_type"],
        "actor": row["actor"],
        "payload": payload,
        "content_hash": row["content_hash"],
        "prior_hash": row["prior_hash"],
        "invocation_id": row["invocation_id"],
        "invoked_by": row["invoked_by"],
        "model": row["model"],
        "source_tag": row["source_tag"],
    }


def new_invocation_id() -> str:
    """Generate a fresh invocation_id for grouping events within a spawn."""
    return f"inv-{uuid.uuid4().hex[:12]}"


__all__ = [
    "FamilyMemberEventType",
    "append_event",
    "count_events",
    "get_events",
    "get_invocation",
    "get_ledger_path",
    "init_ledger",
    "latest_event",
    "new_invocation_id",
    "verify_chain",
]
