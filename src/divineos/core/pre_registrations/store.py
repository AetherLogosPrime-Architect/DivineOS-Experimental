"""Pre-registration CRUD — file, query, and close pre-registered predictions.

Pre-registrations are the Goodhart-prevention layer: every new detector,
mechanism, or instrumentation claim must file a written prediction with a
specific falsifier and a ledger-scheduled review date. Review dates fire
independent of agent memory, so a mechanism cannot silently drift into
"the number went up, ship it" without the pre-registered evidence being
reconciled.

Invariants (enforced):

* ``claim``, ``success_criterion``, ``falsifier`` must all be non-empty.
  A pre-registration without a falsifier is not a prediction — it is a
  hope. Popper's rule: if nothing could prove you wrong, you have said
  nothing.
* ``review_window_days`` must be positive; zero-day review is equivalent
  to no review.
* Outcomes are one-way. Once recorded, the outcome cannot be rewritten.
  To revise, file a new pre-registration that references the old.
* Recording an outcome requires an external actor (user, grok, fresh-
  claude, auditor, council). Internal actors cannot self-verify their
  own pre-registrations; that would re-create the designer-user-judge
  collapse this mechanism exists to prevent.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from typing import Any

from loguru import logger

from divineos.core.knowledge import _get_connection
from divineos.core.pre_registrations._schema import init_pre_registrations_tables
from divineos.core.pre_registrations.types import (
    INTERNAL_ACTORS,
    Outcome,
    PreRegistration,
)

_STORE_ERRORS = (
    sqlite3.OperationalError,
    ImportError,
    OSError,
    KeyError,
    TypeError,
    ValueError,
)

SECONDS_PER_DAY = 86400


def _normalize_actor(actor: str) -> str:
    """Strip + lowercase an actor name. Empty actor is rejected."""
    normalized = actor.strip().lower()
    if not normalized:
        raise ValueError("Actor name cannot be empty")
    return normalized


def _require_external_actor(actor: str) -> str:
    """Reject internal actors. Used when recording outcomes."""
    normalized = _normalize_actor(actor)
    if normalized in INTERNAL_ACTORS:
        raise ValueError(
            f"Actor '{actor}' is an internal component and cannot record "
            f"pre-registration outcomes. External review is required "
            f"(user, grok, fresh-claude, auditor, council, or a "
            f"disambiguated instance name)."
        )
    return normalized


def _row_to_prereg(row: tuple[Any, ...]) -> PreRegistration:
    """Convert a DB row to a PreRegistration dataclass."""
    tags = json.loads(row[14]) if row[14] else []
    return PreRegistration(
        prereg_id=row[0],
        created_at=row[1],
        actor=row[2],
        mechanism=row[3],
        claim=row[4],
        success_criterion=row[5],
        falsifier=row[6],
        review_ts=row[7],
        review_window_days=row[8],
        outcome=Outcome(row[9]),
        outcome_ts=row[10],
        outcome_notes=row[11] or "",
        linked_claim_id=row[12],
        linked_commit=row[13],
        tags=tags,
    )


_SELECT_ALL_COLS = (
    "prereg_id, created_at, actor, mechanism, claim, success_criterion, "
    "falsifier, review_ts, review_window_days, outcome, outcome_ts, "
    "outcome_notes, linked_claim_id, linked_commit, tags"
)


def file_pre_registration(
    actor: str,
    mechanism: str,
    claim: str,
    success_criterion: str,
    falsifier: str,
    review_window_days: int = 30,
    linked_claim_id: str | None = None,
    linked_commit: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """File a new pre-registration.

    Returns the prereg_id. Raises ValueError if any required field is
    empty or review_window_days is not positive.
    """
    normalized_actor = _normalize_actor(actor)

    for name, value in (
        ("mechanism", mechanism),
        ("claim", claim),
        ("success_criterion", success_criterion),
        ("falsifier", falsifier),
    ):
        if not value or not value.strip():
            raise ValueError(
                f"Pre-registration field '{name}' cannot be empty. "
                f"A pre-registration without a falsifier is a hope, not a prediction."
            )

    if review_window_days <= 0:
        raise ValueError(
            f"review_window_days must be positive (got {review_window_days}). "
            f"A zero-day review window is equivalent to no review."
        )

    init_pre_registrations_tables()

    prereg_id = f"prereg-{uuid.uuid4().hex[:12]}"
    now = time.time()
    review_ts = now + review_window_days * SECONDS_PER_DAY
    tag_list = list(tags) if tags else []

    conn = _get_connection()
    try:
        conn.execute(
            f"INSERT INTO pre_registrations ({_SELECT_ALL_COLS}) "  # noqa: S608 — static column list
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                prereg_id,
                now,
                normalized_actor,
                mechanism.strip(),
                claim.strip(),
                success_criterion.strip(),
                falsifier.strip(),
                review_ts,
                review_window_days,
                Outcome.OPEN.value,
                None,
                "",
                linked_claim_id,
                linked_commit,
                json.dumps(tag_list),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    # Log to ledger — best-effort; ledger is not authoritative for pre-regs.
    try:
        from divineos.core.ledger import log_event

        log_event(
            "PRE_REGISTRATION_FILED",
            normalized_actor,
            {
                "prereg_id": prereg_id,
                "mechanism": mechanism,
                "review_ts": review_ts,
                "review_window_days": review_window_days,
            },
            validate=False,
        )
    except _STORE_ERRORS:
        pass

    logger.info(
        "Pre-registration filed: %s mechanism=%s review_in=%dd actor=%s",
        prereg_id,
        mechanism,
        review_window_days,
        normalized_actor,
    )
    return prereg_id


def get_pre_registration(prereg_id: str) -> PreRegistration | None:
    """Retrieve a pre-registration by id, or None if not found."""
    init_pre_registrations_tables()
    conn = _get_connection()
    try:
        row = conn.execute(
            f"SELECT {_SELECT_ALL_COLS} FROM pre_registrations WHERE prereg_id = ?",  # noqa: S608
            (prereg_id,),
        ).fetchone()
        return _row_to_prereg(row) if row else None
    finally:
        conn.close()


def list_pre_registrations(
    outcome: Outcome | None = None,
    actor: str | None = None,
    mechanism: str | None = None,
    limit: int = 50,
) -> list[PreRegistration]:
    """List pre-registrations, optionally filtered by outcome/actor/mechanism."""
    init_pre_registrations_tables()
    conditions: list[str] = []
    params: list[Any] = []
    if outcome is not None:
        conditions.append("outcome = ?")
        params.append(outcome.value)
    if actor:
        conditions.append("actor = ?")
        params.append(_normalize_actor(actor))
    if mechanism:
        conditions.append("mechanism = ?")
        params.append(mechanism.strip())

    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)

    conn = _get_connection()
    try:
        rows = conn.execute(
            f"SELECT {_SELECT_ALL_COLS} FROM pre_registrations{where} "  # noqa: S608
            "ORDER BY created_at DESC LIMIT ?",
            params,
        ).fetchall()
        return [_row_to_prereg(r) for r in rows]
    finally:
        conn.close()


def get_overdue_pre_registrations(now: float | None = None) -> list[PreRegistration]:
    """Pre-registrations whose review_ts has passed and outcome is still OPEN.

    These are the ones the briefing must surface — they are the mechanism's
    ledger-scheduled "wake up and check whether your prediction held" events.
    """
    init_pre_registrations_tables()
    ts = now if now is not None else time.time()
    conn = _get_connection()
    try:
        rows = conn.execute(
            f"SELECT {_SELECT_ALL_COLS} FROM pre_registrations "  # noqa: S608
            "WHERE outcome = ? AND review_ts <= ? "
            "ORDER BY review_ts ASC",
            (Outcome.OPEN.value, ts),
        ).fetchall()
        return [_row_to_prereg(r) for r in rows]
    finally:
        conn.close()


def record_outcome(
    prereg_id: str,
    actor: str,
    outcome: Outcome,
    notes: str = "",
) -> bool:
    """Record a terminal outcome for a pre-registration.

    Returns True if the outcome was recorded, False if the pre-registration
    was not found or already has a terminal outcome.

    Raises ValueError if:
      * ``actor`` is internal (self-verification is disallowed)
      * ``outcome`` is ``OPEN`` (not a terminal state)
      * the pre-registration already has a non-OPEN outcome (one-way only)
    """
    normalized_actor = _require_external_actor(actor)

    if outcome == Outcome.OPEN:
        raise ValueError(
            "Cannot record outcome OPEN — only terminal outcomes are valid "
            "(SUCCESS, FAILED, INCONCLUSIVE, DEFERRED)."
        )

    init_pre_registrations_tables()
    now = time.time()

    conn = _get_connection()
    try:
        existing = conn.execute(
            "SELECT outcome FROM pre_registrations WHERE prereg_id = ?",
            (prereg_id,),
        ).fetchone()
        if not existing:
            return False

        current_outcome = existing[0]
        if current_outcome != Outcome.OPEN.value:
            raise ValueError(
                f"Pre-registration {prereg_id} already has terminal outcome "
                f"'{current_outcome}'. Outcomes are one-way. To revise, file "
                f"a new pre-registration that references this one."
            )

        conn.execute(
            "UPDATE pre_registrations "
            "SET outcome = ?, outcome_ts = ?, outcome_notes = ? "
            "WHERE prereg_id = ?",
            (outcome.value, now, notes, prereg_id),
        )
        conn.commit()
    finally:
        conn.close()

    # Log to ledger — best-effort
    try:
        from divineos.core.ledger import log_event

        log_event(
            "PRE_REGISTRATION_OUTCOME",
            normalized_actor,
            {
                "prereg_id": prereg_id,
                "outcome": outcome.value,
                "notes": notes,
            },
            validate=False,
        )
    except _STORE_ERRORS:
        pass

    logger.info(
        "Pre-registration outcome recorded: %s -> %s by %s",
        prereg_id,
        outcome.value,
        normalized_actor,
    )
    return True


def count_by_outcome() -> dict[str, int]:
    """Return a dict mapping outcome values to counts. Missing outcomes are 0."""
    init_pre_registrations_tables()
    counts = {o.value: 0 for o in Outcome}
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT outcome, COUNT(*) FROM pre_registrations GROUP BY outcome"
        ).fetchall()
        for outcome_val, n in rows:
            counts[outcome_val] = n
    finally:
        conn.close()
    return counts
