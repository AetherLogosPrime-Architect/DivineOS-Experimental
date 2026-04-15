"""Watchmen CRUD — submit, query, and resolve audit findings.

Actor validation is the first line of self-trigger prevention.
Only external actors can submit findings. Internal actors are
structurally rejected before any data touches the database.
"""

import json
import sqlite3
import time
import uuid
from typing import Any

from loguru import logger

from divineos.core.knowledge._base import _get_connection
from divineos.core.watchmen._schema import init_watchmen_tables
from divineos.core.watchmen.types import (
    EXTERNAL_ACTORS,
    INTERNAL_ACTORS,
    AuditRound,
    Finding,
    FindingCategory,
    FindingStatus,
    Severity,
)


def _validate_actor(actor: str) -> str:
    """Validate and normalize the actor name.

    Raises ValueError if the actor is an internal system component.
    Returns the normalized (lowercased) actor name.
    """
    normalized = actor.strip().lower()
    if normalized in INTERNAL_ACTORS:
        raise ValueError(
            f"Actor '{actor}' is an internal component and cannot submit audit findings. "
            f"Only external actors are allowed: {', '.join(sorted(EXTERNAL_ACTORS))}"
        )
    if not normalized:
        raise ValueError("Actor name cannot be empty")
    return normalized


def submit_round(
    actor: str,
    focus: str,
    expert_count: int = 0,
    notes: str = "",
) -> str:
    """Create a new audit round. Returns the round_id.

    An audit round groups related findings from a single audit session.
    """
    normalized_actor = _validate_actor(actor)
    init_watchmen_tables()

    round_id = f"round-{uuid.uuid4().hex[:12]}"
    now = time.time()

    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO audit_rounds (round_id, created_at, actor, focus, expert_count, notes) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (round_id, now, normalized_actor, focus, expert_count, notes),
        )
        conn.commit()
    finally:
        conn.close()

    # Log to ledger
    try:
        from divineos.core.ledger import log_event

        log_event(
            "AUDIT_ROUND_CREATED",
            normalized_actor,
            {"round_id": round_id, "focus": focus, "expert_count": expert_count},
            validate=False,
        )
    except (ImportError, OSError, sqlite3.OperationalError, TypeError, ValueError):
        pass  # Ledger logging is best-effort

    logger.info(f"Audit round created: {round_id} by {normalized_actor} — {focus}")
    return round_id


def submit_finding(
    round_id: str,
    actor: str,
    severity: str,
    category: str,
    title: str,
    description: str,
    recommendation: str = "",
    tags: list[str] | None = None,
) -> str:
    """Submit a single audit finding. Returns the finding_id.

    Actor validation prevents internal components from self-auditing.
    """
    normalized_actor = _validate_actor(actor)
    init_watchmen_tables()

    # Validate enums
    try:
        sev = Severity(severity.upper())
    except ValueError:
        valid = ", ".join(s.value for s in Severity)
        raise ValueError(f"Invalid severity '{severity}'. Valid: {valid}") from None

    try:
        cat = FindingCategory(category.upper())
    except ValueError:
        valid = ", ".join(c.value for c in FindingCategory)
        raise ValueError(f"Invalid category '{category}'. Valid: {valid}") from None

    # Verify round exists
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT round_id FROM audit_rounds WHERE round_id = ?", (round_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Audit round '{round_id}' does not exist")

        finding_id = f"find-{uuid.uuid4().hex[:12]}"
        now = time.time()
        tags_json = json.dumps(tags or [])

        conn.execute(
            "INSERT INTO audit_findings "
            "(finding_id, round_id, created_at, actor, severity, category, "
            "title, description, recommendation, tags) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                finding_id,
                round_id,
                now,
                normalized_actor,
                sev.value,
                cat.value,
                title,
                description,
                recommendation,
                tags_json,
            ),
        )

        # Update finding count on the round
        conn.execute(
            "UPDATE audit_rounds SET finding_count = finding_count + 1 WHERE round_id = ?",
            (round_id,),
        )
        conn.commit()
    finally:
        conn.close()

    logger.info(f"Finding submitted: {finding_id} [{sev.value}] {title[:60]}")
    return finding_id


def resolve_finding(
    finding_id: str,
    status: str,
    resolution_notes: str = "",
) -> bool:
    """Update the status and resolution notes of a finding.

    Returns True if the finding existed and was updated.
    """
    try:
        new_status = FindingStatus(status.upper())
    except ValueError:
        valid = ", ".join(s.value for s in FindingStatus)
        raise ValueError(f"Invalid status '{status}'. Valid: {valid}") from None

    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT finding_id FROM audit_findings WHERE finding_id = ?",
            (finding_id,),
        ).fetchone()
        if not row:
            return False

        conn.execute(
            "UPDATE audit_findings SET status = ?, resolution_notes = ? WHERE finding_id = ?",
            (new_status.value, resolution_notes, finding_id),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def get_round(round_id: str) -> AuditRound | None:
    """Retrieve a single audit round by ID."""
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT round_id, created_at, actor, focus, expert_count, finding_count, notes "
            "FROM audit_rounds WHERE round_id = ?",
            (round_id,),
        ).fetchone()
        if not row:
            return None
        return AuditRound(
            round_id=row[0],
            created_at=row[1],
            actor=row[2],
            focus=row[3],
            expert_count=row[4],
            finding_count=row[5],
            notes=row[6],
        )
    finally:
        conn.close()


def get_finding(finding_id: str) -> Finding | None:
    """Retrieve a single finding by ID."""
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT finding_id, round_id, created_at, actor, severity, category, "
            "title, description, recommendation, status, resolution_notes, routed_to, tags "
            "FROM audit_findings WHERE finding_id = ?",
            (finding_id,),
        ).fetchone()
        if not row:
            return None
        return _row_to_finding(row)
    finally:
        conn.close()


def list_rounds(limit: int = 20) -> list[AuditRound]:
    """List audit rounds, most recent first."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT round_id, created_at, actor, focus, expert_count, finding_count, notes "
            "FROM audit_rounds ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            AuditRound(
                round_id=r[0],
                created_at=r[1],
                actor=r[2],
                focus=r[3],
                expert_count=r[4],
                finding_count=r[5],
                notes=r[6],
            )
            for r in rows
        ]
    finally:
        conn.close()


def list_findings(
    round_id: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    category: str | None = None,
    limit: int = 50,
) -> list[Finding]:
    """List findings with optional filters."""
    conditions: list[str] = []
    params: list[Any] = []

    if round_id:
        conditions.append("round_id = ?")
        params.append(round_id)
    if status:
        conditions.append("status = ?")
        params.append(status.upper())
    if severity:
        conditions.append("severity = ?")
        params.append(severity.upper())
    if category:
        conditions.append("category = ?")
        params.append(category.upper())

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)

    conn = _get_connection()
    try:
        rows = conn.execute(
            f"SELECT finding_id, round_id, created_at, actor, severity, category, "  # nosec B608
            f"title, description, recommendation, status, resolution_notes, routed_to, tags "
            f"FROM audit_findings {where} ORDER BY created_at DESC LIMIT ?",
            params,
        ).fetchall()
        return [_row_to_finding(r) for r in rows]
    finally:
        conn.close()


def _row_to_finding(row: Any) -> Finding:
    """Convert a database row to a Finding dataclass."""
    tags = json.loads(row[12]) if row[12] else []
    return Finding(
        finding_id=row[0],
        round_id=row[1],
        created_at=row[2],
        actor=row[3],
        severity=Severity(row[4]),
        category=FindingCategory(row[5]),
        title=row[6],
        description=row[7],
        recommendation=row[8],
        status=FindingStatus(row[9]),
        resolution_notes=row[10],
        routed_to=row[11],
        tags=tags,
    )
