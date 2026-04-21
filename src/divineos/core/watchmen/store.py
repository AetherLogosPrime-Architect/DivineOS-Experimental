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

from divineos.core.knowledge import _get_connection
from divineos.core.watchmen._schema import init_watchmen_tables
from divineos.core.watchmen.types import (
    EXTERNAL_ACTORS,
    INTERNAL_ACTORS,
    AuditRound,
    Finding,
    FindingCategory,
    FindingStatus,
    ReviewStance,
    Severity,
    Tier,
    tier_for_actor,
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
    tier: Tier | str | None = None,
) -> str:
    """Create a new audit round. Returns the round_id.

    An audit round groups related findings from a single audit session.
    The tier defaults to the actor's default (see ``tier_for_actor``). Callers
    can override explicitly for edge cases (e.g., a user-filed round that
    explicitly references multiple independent confirmations could be filed
    at MEDIUM).
    """
    normalized_actor = _validate_actor(actor)
    init_watchmen_tables()

    resolved_tier = _resolve_tier(tier, normalized_actor)

    round_id = f"round-{uuid.uuid4().hex[:12]}"
    now = time.time()

    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO audit_rounds "
            "(round_id, created_at, actor, focus, expert_count, notes, tier) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (round_id, now, normalized_actor, focus, expert_count, notes, resolved_tier.value),
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
            {
                "round_id": round_id,
                "focus": focus,
                "expert_count": expert_count,
                "tier": resolved_tier.value,
            },
            validate=False,
        )
    except (ImportError, OSError, sqlite3.OperationalError, TypeError, ValueError):
        pass  # Ledger logging is best-effort

    logger.info(
        f"Audit round created: {round_id} by {normalized_actor} [{resolved_tier.value}] — {focus}"
    )
    return round_id


def _resolve_tier(tier: Tier | str | None, actor: str) -> Tier:
    """Resolve an explicit tier argument against the actor's default.

    - None → use the actor's default tier
    - Tier instance → use as-is
    - string → parse to Tier (raises ValueError on invalid)
    """
    if tier is None:
        return tier_for_actor(actor)
    if isinstance(tier, Tier):
        return tier
    try:
        return Tier(tier.upper())
    except ValueError:
        valid = ", ".join(t.value for t in Tier)
        raise ValueError(f"Invalid tier '{tier}'. Valid: {valid}") from None


def _resolve_review_stance(stance: ReviewStance | str | None) -> ReviewStance | None:
    """Parse a review-stance argument. None stays None."""
    if stance is None:
        return None
    if isinstance(stance, ReviewStance):
        return stance
    try:
        return ReviewStance(stance.upper())
    except ValueError:
        valid = ", ".join(s.value for s in ReviewStance)
        raise ValueError(f"Invalid review stance '{stance}'. Valid: {valid}") from None


def submit_finding(
    round_id: str,
    actor: str,
    severity: str,
    category: str,
    title: str,
    description: str,
    recommendation: str = "",
    tags: list[str] | None = None,
    tier: Tier | str | None = None,
    reviewed_finding_id: str = "",
    review_stance: ReviewStance | str | None = None,
) -> str:
    """Submit a single audit finding. Returns the finding_id.

    Actor validation prevents internal components from self-auditing.

    Review-chain arguments:
      - ``reviewed_finding_id``: when set, this finding is a *review of* the
        referenced finding. The referenced finding must exist. Pairs with
        ``review_stance``.
      - ``review_stance``: CONFIRMS / DISPUTES / REFINES. Required when
        ``reviewed_finding_id`` is set; ignored otherwise.

    Tier defaults to the actor's default (see ``tier_for_actor``). Reviews
    do NOT automatically escalate the reviewed finding's tier — the chain is
    data; tier computation is a query-time operation (see
    ``chain_tier_for_finding``) so historical tiers stay immutable.
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

    resolved_tier = _resolve_tier(tier, normalized_actor)
    resolved_stance = _resolve_review_stance(review_stance)

    # Review-chain consistency: stance and reviewed_finding_id must agree.
    if reviewed_finding_id and resolved_stance is None:
        raise ValueError(
            "review_stance is required when reviewed_finding_id is set "
            "(CONFIRMS / DISPUTES / REFINES)"
        )
    if resolved_stance is not None and not reviewed_finding_id:
        raise ValueError("reviewed_finding_id is required when review_stance is set")

    # Verify round exists, and reviewed finding if claimed
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT round_id FROM audit_rounds WHERE round_id = ?", (round_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Audit round '{round_id}' does not exist")

        if reviewed_finding_id:
            rev = conn.execute(
                "SELECT finding_id FROM audit_findings WHERE finding_id = ?",
                (reviewed_finding_id,),
            ).fetchone()
            if not rev:
                raise ValueError(f"Reviewed finding '{reviewed_finding_id}' does not exist")

        finding_id = f"find-{uuid.uuid4().hex[:12]}"
        now = time.time()
        tags_json = json.dumps(tags or [])
        stance_str = resolved_stance.value if resolved_stance else ""

        conn.execute(
            "INSERT INTO audit_findings "
            "(finding_id, round_id, created_at, actor, severity, category, "
            "title, description, recommendation, tags, tier, "
            "reviewed_finding_id, review_stance) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                resolved_tier.value,
                reviewed_finding_id,
                stance_str,
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

    chain_note = (
        f" [reviews {reviewed_finding_id[:8]} {resolved_stance.value}]" if resolved_stance else ""
    )
    logger.info(
        f"Finding submitted: {finding_id} [{sev.value}/{resolved_tier.value}] "
        f"{title[:60]}{chain_note}"
    )
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


_ROUND_COLUMNS = "round_id, created_at, actor, focus, expert_count, finding_count, notes, tier"


def _row_to_round(row: Any) -> AuditRound:
    """Convert an audit_rounds row to an AuditRound dataclass."""
    return AuditRound(
        round_id=row[0],
        created_at=row[1],
        actor=row[2],
        focus=row[3],
        expert_count=row[4],
        finding_count=row[5],
        notes=row[6],
        tier=Tier(row[7]) if row[7] else Tier.WEAK,
    )


def get_round(round_id: str) -> AuditRound | None:
    """Retrieve a single audit round by ID."""
    conn = _get_connection()
    try:
        row = conn.execute(
            f"SELECT {_ROUND_COLUMNS} FROM audit_rounds WHERE round_id = ?",  # nosec B608
            (round_id,),
        ).fetchone()
        if not row:
            return None
        return _row_to_round(row)
    finally:
        conn.close()


_FINDING_COLUMNS = (
    "finding_id, round_id, created_at, actor, severity, category, "
    "title, description, recommendation, status, resolution_notes, routed_to, tags, "
    "tier, reviewed_finding_id, review_stance"
)


def get_finding(finding_id: str) -> Finding | None:
    """Retrieve a single finding by ID."""
    conn = _get_connection()
    try:
        row = conn.execute(
            f"SELECT {_FINDING_COLUMNS} FROM audit_findings WHERE finding_id = ?",  # nosec B608
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
            f"SELECT {_ROUND_COLUMNS} "  # nosec B608
            f"FROM audit_rounds ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_row_to_round(r) for r in rows]
    finally:
        conn.close()


def list_reviews_of(finding_id: str) -> list[Finding]:
    """List all findings that review the given finding (the inverse chain).

    Returns every finding whose ``reviewed_finding_id`` equals ``finding_id``,
    ordered oldest-first. Useful for walking the review tree: start from a
    root finding, fetch its reviews, recursively fetch each review's reviews.
    """
    conn = _get_connection()
    try:
        rows = conn.execute(
            f"SELECT {_FINDING_COLUMNS} FROM audit_findings "  # nosec B608
            f"WHERE reviewed_finding_id = ? ORDER BY created_at ASC",
            (finding_id,),
        ).fetchall()
        return [_row_to_finding(r) for r in rows]
    finally:
        conn.close()


def chain_tier_for_finding(finding_id: str) -> Tier:
    """Compute the effective tier of a finding given its review chain.

    Rules:
      - A finding's base tier is its own ``tier`` column.
      - A CONFIRMS review escalates the chain to max(chain_tier, review_tier).
      - A DISPUTES review does NOT escalate — disputed findings stay at
        base tier but surface as "contested" in briefing (future work).
      - A REFINES review escalates partially: chain reaches min(review_tier, MEDIUM)
        even if the review itself is STRONG, because "refines" signals nuance
        not full confirmation.

    Returns the effective tier. A finding with no reviews returns its own tier.
    """
    base = get_finding(finding_id)
    if base is None:
        return Tier.WEAK

    effective = base.tier
    tier_rank = {Tier.WEAK: 0, Tier.MEDIUM: 1, Tier.STRONG: 2}

    for review in list_reviews_of(finding_id):
        if review.review_stance == ReviewStance.CONFIRMS:
            if tier_rank[review.tier] > tier_rank[effective]:
                effective = review.tier
        elif review.review_stance == ReviewStance.REFINES:
            # Cap the uplift at MEDIUM even for strong reviewers
            capped = Tier.MEDIUM if review.tier == Tier.STRONG else review.tier
            if tier_rank[capped] > tier_rank[effective]:
                effective = capped
        # DISPUTES: no escalation

    return effective


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
            f"SELECT {_FINDING_COLUMNS} "  # nosec B608
            f"FROM audit_findings {where} ORDER BY created_at DESC LIMIT ?",
            params,
        ).fetchall()
        return [_row_to_finding(r) for r in rows]
    finally:
        conn.close()


def _row_to_finding(row: Any) -> Finding:
    """Convert a database row to a Finding dataclass."""
    tags = json.loads(row[12]) if row[12] else []
    tier = Tier(row[13]) if len(row) > 13 and row[13] else Tier.WEAK
    reviewed_id = row[14] if len(row) > 14 else ""
    stance_raw = row[15] if len(row) > 15 else ""
    stance = ReviewStance(stance_raw) if stance_raw else None
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
        tier=tier,
        reviewed_finding_id=reviewed_id or "",
        review_stance=stance,
    )
