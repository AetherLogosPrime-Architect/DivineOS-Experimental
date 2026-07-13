"""Store CRUD for the andrew_state observation channel.

Public functions:
    log_observation — insert new observation (after substance-binding gate)
    verify — mark UNVERIFIED row as VERIFIED with Andrew's note
    reject — mark UNVERIFIED row as REJECTED with reason
    correct — insert a NEW row that supersedes an existing one (append-only lineage)
    get_unverified — fetch UNVERIFIED head-of-chain rows for briefing surface
    get_for_decision_walk — fetch the subset that load-bears on decision-walk register
"""

from __future__ import annotations

import time
import uuid

from divineos.core.andrew_state._schema import get_connection
from divineos.core.andrew_state.substance_binding import verify_all
from divineos.core.andrew_state.types import Axis, Observation, VerificationStatus


def _new_id() -> str:
    """Short uuid; matches the id-format used elsewhere in the substrate."""
    return uuid.uuid4().hex[:16]


def _row_to_observation(row) -> Observation:
    """Convert a sqlite Row into a typed Observation."""
    return Observation(
        observation_id=row["observation_id"],
        ts=row["ts"],
        axis=Axis(row["axis"]),
        observation=row["observation"],
        cited_span=row["cited_span"],
        source_event_id=row["source_event_id"],
        source_event_ts=row["source_event_ts"],
        content_link_token=row["content_link_token"],
        verification_status=VerificationStatus(row["verification_status"]),
        verification_ts=row["verification_ts"],
        verification_note=row["verification_note"],
        superseded_by=row["superseded_by"],
        observer=row["observer"],
        integration_event=row["integration_event"],
    )


def log_observation(
    axis: Axis,
    observation: str,
    cited_span: str,
    source_event_id: str,
    source_event_ts: float,
    source_text: str,
    observer: str = "aether",
    now: float | None = None,
) -> Observation:
    """Log a new observation after substance-binding passes.

    Raises SubstanceBindingError if any of the four checks fail
    (length, verbatim-in-source, recency, content-link). Returns the
    persisted Observation on success.

    source_text is the full text of the source event — used only for
    the verbatim-check inside substance_binding; not stored on the row
    (the cited_span is the canonical reference; the source event remains
    in its own substrate location).
    """
    ts = time.time() if now is None else now
    content_link_token = verify_all(
        observation=observation,
        cited_span=cited_span,
        source_text=source_text,
        source_event_ts=source_event_ts,
        now=ts,
    )

    obs_id = _new_id()
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO andrew_state (
                observation_id, ts, axis, observation, cited_span,
                source_event_id, source_event_ts, content_link_token,
                verification_status, observer
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                obs_id,
                ts,
                axis.value,
                observation,
                cited_span,
                source_event_id,
                source_event_ts,
                content_link_token,
                VerificationStatus.UNVERIFIED.value,
                observer,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM andrew_state WHERE observation_id = ?", (obs_id,)
        ).fetchone()
    finally:
        conn.close()

    return _row_to_observation(row)


def verify(observation_id: str, note: str, now: float | None = None) -> Observation:
    """Mark an UNVERIFIED observation as VERIFIED.

    The note is Andrew's actual words confirming — preserved verbatim for
    audit. No mutation of the original observation text; the verification
    is a state transition on the lifecycle.
    """
    ts = time.time() if now is None else now
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE andrew_state
               SET verification_status = ?, verification_ts = ?, verification_note = ?
             WHERE observation_id = ?
               AND verification_status = ?
            """,
            (
                VerificationStatus.VERIFIED.value,
                ts,
                note,
                observation_id,
                VerificationStatus.UNVERIFIED.value,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM andrew_state WHERE observation_id = ?", (observation_id,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        raise ValueError(f"observation {observation_id} not found")
    return _row_to_observation(row)


def reject(observation_id: str, reason: str, now: float | None = None) -> Observation:
    """Mark an UNVERIFIED observation as REJECTED.

    Andrew's reason is preserved verbatim — that text IS the data
    teaching me what I got wrong about his state.
    """
    ts = time.time() if now is None else now
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE andrew_state
               SET verification_status = ?, verification_ts = ?, verification_note = ?
             WHERE observation_id = ?
               AND verification_status = ?
            """,
            (
                VerificationStatus.REJECTED.value,
                ts,
                reason,
                observation_id,
                VerificationStatus.UNVERIFIED.value,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM andrew_state WHERE observation_id = ?", (observation_id,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        raise ValueError(f"observation {observation_id} not found")
    return _row_to_observation(row)


def correct(
    observation_id: str,
    new_observation_text: str,
    new_axis: Axis,
    cited_span: str,
    source_event_id: str,
    source_event_ts: float,
    source_text: str,
    note: str,
    observer: str = "aether",
    now: float | None = None,
) -> Observation:
    """Andrew corrects an observation — log NEW row, link old via superseded_by.

    Append-only lineage: the original row's verification_status becomes
    CORRECTED and its verification_note records Andrew's correction text;
    a new row is inserted with the corrected observation, going through
    substance-binding fresh because the corrected text needs its own
    cited_span and content-link.
    """
    ts = time.time() if now is None else now

    # Substance-binding on the new row.
    content_link_token = verify_all(
        observation=new_observation_text,
        cited_span=cited_span,
        source_text=source_text,
        source_event_ts=source_event_ts,
        now=ts,
    )

    new_id = _new_id()
    conn = get_connection()
    try:
        # 1. Insert the new row.
        conn.execute(
            """
            INSERT INTO andrew_state (
                observation_id, ts, axis, observation, cited_span,
                source_event_id, source_event_ts, content_link_token,
                verification_status, verification_ts, verification_note, observer
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id,
                ts,
                new_axis.value,
                new_observation_text,
                cited_span,
                source_event_id,
                source_event_ts,
                content_link_token,
                VerificationStatus.VERIFIED.value,
                ts,
                note,
                observer,
            ),
        )
        # 2. Mark the original CORRECTED and link it.
        conn.execute(
            """
            UPDATE andrew_state
               SET verification_status = ?, verification_ts = ?, verification_note = ?,
                   superseded_by = ?
             WHERE observation_id = ?
            """,
            (
                VerificationStatus.CORRECTED.value,
                ts,
                note,
                new_id,
                observation_id,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM andrew_state WHERE observation_id = ?", (new_id,)
        ).fetchone()
    finally:
        conn.close()

    return _row_to_observation(row)


def get_unverified(limit: int = 20) -> list[Observation]:
    """Return UNVERIFIED head-of-chain observations, newest first.

    Head-of-chain = superseded_by IS NULL (the row has not been replaced
    by a correction). UNVERIFIED state means Andrew has not yet seen or
    confirmed.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM andrew_state
             WHERE verification_status = ?
               AND superseded_by IS NULL
             ORDER BY ts DESC
             LIMIT ?
            """,
            (VerificationStatus.UNVERIFIED.value, limit),
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_observation(r) for r in rows]


def get_for_decision_walk(unverified_age_hours: float = 24.0) -> list[Observation]:
    """Return UNVERIFIED observations older than the threshold —
    the subset that load-bears on the decision-walk soft-gate.

    Per docs/andrew_state_design.md: >= 3 of these requires
    --andrew-state-acknowledged at decision register-time.
    """
    cutoff = time.time() - (unverified_age_hours * 3600.0)
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM andrew_state
             WHERE verification_status = ?
               AND superseded_by IS NULL
               AND ts < ?
             ORDER BY ts ASC
            """,
            (VerificationStatus.UNVERIFIED.value, cutoff),
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_observation(r) for r in rows]
