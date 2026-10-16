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
    """Normalize an actor name, defending against unicode bypass.

    Audit finding 2026-05-03 round 12: a plain ``.strip().lower()``
    does NOT remove U+00A0 (no-break space), U+2009 (thin space),
    U+202F (narrow no-break space), or other unicode-whitespace
    variants. An LLM copy-pasting from a formatted document could
    file as ``"\\u00a0claude"`` — bypassing the INTERNAL_ACTORS
    frozenset check because the literal string isn't ``"claude"``.

    Verified bypass before fix:
      record_outcome(prereg_id, actor="\\u200bclaude", outcome=SUCCESS)
      ...succeeds — agent flips its own pre-reg.

    NFKC normalization folds these compatibility forms to canonical
    ASCII so ``.strip()`` actually removes them. The transform is shared
    with ``watchmen.store._validate_actor`` via
    ``actor_normalize.normalize_actor`` — this used to be a verbatim
    copy of that function's inline logic; the shared module removes the
    duplication so the two cannot drift apart.
    """
    from divineos.core.actor_normalize import normalize_actor

    normalized = normalize_actor(actor)
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
    prereg = PreRegistration(
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
        # Rows written before this column existed are shorter, and a short row
        # means the question was never asked — not that the answer was none.
        embarrassing_reading=row[15] if len(row) > 15 else None,
        review_after_uses=row[16] if len(row) > 16 else None,
        uses_of=row[17] if len(row) > 17 else None,
        uses_baseline=row[18] if len(row) > 18 else None,
    )
    if prereg.review_after_uses is not None:
        # Every reader sorts and prints by review_ts, and for a usage row the stored
        # value is only a placeholder. Resolve it HERE, once, so no reader has to
        # know there are two kinds (Aria, 2026-10-16: the briefing, the summary,
        # the show/export and the todo ranking all read review_ts directly): the
        # moment the Nth use happened if the review is due, otherwise a date far
        # past any horizon. The stored value is ignored either way.
        prereg.review_ts = _usage_review_ts(prereg)
    return prereg


def _usage_review_ts(prereg: PreRegistration) -> float:
    from divineos.core.ledger import count_events_of_type, nth_event_timestamp

    never = prereg.created_at + _INERT_DATE_DAYS * SECONDS_PER_DAY
    if not prereg.uses_of or prereg.review_after_uses is None:
        return never
    if usage_progress(prereg, count_events_of_type) < prereg.review_after_uses:
        return never
    due_at = nth_event_timestamp(
        prereg.uses_of, (prereg.uses_baseline or 0) + prereg.review_after_uses - 1
    )
    return due_at if due_at is not None else never


_SELECT_ALL_COLS = (
    "prereg_id, created_at, actor, mechanism, claim, success_criterion, "
    "falsifier, review_ts, review_window_days, outcome, outcome_ts, "
    "outcome_notes, linked_claim_id, linked_commit, tags, embarrassing_reading, "
    "review_after_uses, uses_of, uses_baseline"
)

# A usage-based pre-registration still needs a value in the NOT NULL date
# columns. This is a placeholder far past any horizon, and the overdue query
# ignores the date for usage rows, so it can never make one overdue.
_INERT_DATE_DAYS = 3650


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
    embarrassing_reading: str | None = None,
    review_after_uses: int | None = None,
    uses_of: str | None = None,
) -> str:
    """File a new pre-registration.

    ``embarrassing_reading`` is Aria's test, 2026-09-09, after two measures
    of mine shipped in one evening that could not contradict me: the first
    could not vary at all, the second varied with my own prose. Both had
    falsifiers written for them. Her sharper form is not *what would falsify
    the claim* but *what number would this thing have to produce for me to be
    sorry I built it* — and a measure with no such number is not a measure.
    Left optional at this layer so older rows read as NULL, meaning the
    question was never asked rather than answered with none; the command-line
    path requires it, which is where a new measure actually gets filed.

    ``review_after_uses`` and ``uses_of`` schedule the review by USE (Dad,
    2026-10-16: reviews go by usage, never by date; a vacation must not make a
    review due with no data, and heavy use must not wait out a calendar). Both
    must be given together. The review is due once the ledger holds
    ``review_after_uses`` more events of type ``uses_of`` than it did at filing,
    and ``review_window_days`` is then ignored. Filing is refused when the
    ledger holds no event of that type at all: a count that cannot move reads
    as "not due" forever, and that is a broken instrument, not a quiet one.

    Returns the prereg_id. Raises ValueError if any required field is
    empty or review_window_days is not positive.
    """
    use_based = review_after_uses is not None or uses_of is not None
    baseline: int | None = None
    if use_based:
        if review_after_uses is None or not uses_of or not uses_of.strip():
            raise ValueError("A usage review needs both review_after_uses and uses_of.")
        if review_after_uses <= 0:
            raise ValueError(f"review_after_uses must be positive (got {review_after_uses}).")
        uses_of = uses_of.strip()
        from divineos.core.ledger import count_events_of_type

        from divineos.core.ledger_compressor import _COMPRESSIBLE_TYPES

        if uses_of in _COMPRESSIBLE_TYPES:
            raise ValueError(
                f"'{uses_of}' is pruned from the ledger on a conveyor belt, so its count can "
                f"fall below the baseline and the review would silently never come due. "
                f"Name an event type that is kept."
            )
        baseline = count_events_of_type(uses_of)
        if baseline == 0:
            raise ValueError(
                f"The ledger holds no '{uses_of}' events, so a count of them could never "
                f"move. Name an event type that has happened at least once."
            )
        review_window_days = _INERT_DATE_DAYS
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
            f"INSERT INTO pre_registrations ({_SELECT_ALL_COLS}) "  # noqa: S608  # nosec B608 — static column list
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                embarrassing_reading.strip() if embarrassing_reading else None,
                review_after_uses,
                uses_of,
                baseline,
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
            f"SELECT {_SELECT_ALL_COLS} FROM pre_registrations WHERE prereg_id = ?",  # noqa: S608  # nosec B608
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
            f"SELECT {_SELECT_ALL_COLS} FROM pre_registrations{where} "  # noqa: S608  # nosec B608
            "ORDER BY created_at DESC LIMIT ?",
            params,
        ).fetchall()
        return [_row_to_prereg(r) for r in rows]
    finally:
        conn.close()


def get_overdue_pre_registrations(now: float | None = None) -> list[PreRegistration]:
    """Pre-registrations that are due and whose outcome is still OPEN.

    These are the ones the briefing must surface — they are the mechanism's
    "wake up and check whether your prediction held" events.

    Two kinds, and the date means different things to each. A legacy row is due
    when its ``review_ts`` has passed. A usage row (``review_after_uses`` set)
    is due when the ledger holds that many more events of its type than it did
    at filing, and its date is ignored: a calendar must never make a review due
    when nothing was used (Dad, 2026-10-16: "i could go on vacation for 30 days
    come back and you have no data").
    """
    init_pre_registrations_tables()
    ts = now if now is not None else time.time()
    conn = _get_connection()
    try:
        rows = conn.execute(
            f"SELECT {_SELECT_ALL_COLS} FROM pre_registrations "  # noqa: S608  # nosec B608
            "WHERE outcome = ? ORDER BY created_at ASC",
            (Outcome.OPEN.value,),
        ).fetchall()
    finally:
        conn.close()

    from divineos.core.ledger import count_events_of_type

    due: list[PreRegistration] = []
    for row in rows:
        prereg = _row_to_prereg(row)
        if prereg.review_after_uses is None:
            if prereg.review_ts <= ts:
                due.append(prereg)
        elif usage_progress(prereg, count_events_of_type) >= prereg.review_after_uses:
            due.append(prereg)
    due.sort(key=lambda p: p.review_ts if p.review_after_uses is None else p.created_at)
    return due


def usage_progress(prereg: PreRegistration, counter: Any) -> int:
    """How many uses have happened since filing; 0 for a date-scheduled row."""
    if prereg.review_after_uses is None or not prereg.uses_of:
        return 0
    return max(0, int(counter(prereg.uses_of)) - (prereg.uses_baseline or 0))


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

    # An assessment is what a review window was opened FOR, so recording one
    # closes it here rather than at the call site. Leaving that to the caller
    # would make every earned window indistinguishable from a lapsed one on
    # the single occasion it was forgotten, which is the whole measurement.
    try:
        from divineos.core.pre_registrations.review_window import close_windows_for

        close_windows_for(prereg_id)
    except _STORE_ERRORS:
        pass

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
