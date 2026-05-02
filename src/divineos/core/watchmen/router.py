"""Watchmen Router — route findings to knowledge, claims, and lessons.

Each finding becomes actionable by being routed to the appropriate
subsystem. Critical/high findings with behavioral implications become
claims for investigation. Knowledge findings become knowledge entries.
Learning findings become lessons.

Routing is idempotent — a finding already routed (status=ROUTED) is skipped.
"""

import sqlite3
from typing import Any

from loguru import logger

from divineos.core.knowledge import _get_connection
from divineos.core.watchmen.types import (
    Finding,
    FindingCategory,
    FindingStatus,
    Severity,
)

_ROUTER_ERRORS = (
    ImportError,
    sqlite3.OperationalError,
    OSError,
    KeyError,
    TypeError,
    ValueError,
)


def route_finding(finding: Finding) -> dict[str, Any]:
    """Route a single finding to the appropriate subsystem.

    Returns a dict describing what was created:
        {"action": "claim"|"knowledge"|"lesson"|"skipped", "id": "...", "reason": "..."}
    """
    # Skip already-routed findings
    if finding.status not in (FindingStatus.OPEN, FindingStatus.IN_PROGRESS):
        return {"action": "skipped", "id": "", "reason": f"Status is {finding.status.value}"}

    result: dict[str, Any]

    # Behavioral/integrity/identity findings -> Claims.
    # MEDIUM severity included — recurring moderate patterns are more
    # concerning than isolated high-severity ones.
    if finding.category in (
        FindingCategory.BEHAVIOR,
        FindingCategory.INTEGRITY,
        FindingCategory.IDENTITY,
    ) and finding.severity in (Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM):
        result = _route_to_claim(finding)

    # Knowledge findings -> Knowledge store
    elif finding.category == FindingCategory.KNOWLEDGE:
        result = _route_to_knowledge(finding)

    # Learning findings -> Lesson tracking
    elif finding.category == FindingCategory.LEARNING:
        result = _route_to_lesson(finding)

    # Architecture/Performance findings -> Knowledge (as OBSERVATION)
    elif finding.category in (FindingCategory.ARCHITECTURE, FindingCategory.PERFORMANCE):
        result = _route_to_knowledge(finding)

    # Everything else -> Knowledge as OBSERVATION
    else:
        result = _route_to_knowledge(finding)

    # Update finding status and routed_to
    if result["action"] != "skipped" and result.get("id"):
        _mark_routed(finding.finding_id, result["id"])

    return result


def route_round(round_id: str) -> list[dict[str, Any]]:
    """Route all unrouted findings in a round. Returns list of routing results."""
    from divineos.core.watchmen.store import list_findings

    findings = list_findings(round_id=round_id, status="OPEN")
    results = []
    for finding in findings:
        result = route_finding(finding)
        result["finding_id"] = finding.finding_id
        result["title"] = finding.title
        results.append(result)

    if results:
        routed = sum(1 for r in results if r["action"] != "skipped")
        logger.info(f"Routed {routed}/{len(results)} findings from round {round_id}")

    return results


def _route_to_claim(finding: Finding) -> dict[str, Any]:
    """Create a claim from a finding."""
    try:
        from divineos.core.claim_store import init_claim_tables

        init_claim_tables()

        # Map severity to claim tier
        tier = 3  # INFERENTIAL by default
        if finding.severity == Severity.CRITICAL:
            tier = 1  # EMPIRICAL — directly observable
        elif finding.severity == Severity.HIGH:
            tier = 2  # THEORETICAL — derived from evidence

        from divineos.core.claim_store import (
            STATUS_OPEN,
        )

        # Build claim statement from title + description
        statement = f"[Audit] {finding.title}"
        context = (
            f"Category: {finding.category.value}\n"
            f"Severity: {finding.severity.value}\n"
            f"Round: {finding.round_id}\n"
            f"Description: {finding.description}\n"
        )
        if finding.recommendation:
            context += f"Recommendation: {finding.recommendation}\n"

        import time
        import uuid

        from divineos.core.memory import _get_connection as _get_mem_conn

        claim_id = f"claim-{uuid.uuid4().hex[:12]}"
        now = time.time()
        conn = _get_mem_conn()
        try:
            conn.execute(
                "INSERT INTO claims (claim_id, created_at, updated_at, statement, tier, "
                "status, confidence, context, tags) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    claim_id,
                    now,
                    now,
                    statement,
                    tier,
                    STATUS_OPEN,
                    0.5,
                    context,
                    "[]",
                ),
            )
            conn.commit()
        finally:
            conn.close()

        return {
            "action": "claim",
            "id": claim_id,
            "reason": f"Tier {tier} claim from {finding.severity.value} finding",
        }

    except _ROUTER_ERRORS as e:
        logger.debug(f"Failed to route finding to claim: {e}")
        return {"action": "skipped", "id": "", "reason": f"Claim creation failed: {e}"}


def _route_to_knowledge(finding: Finding) -> dict[str, Any]:
    """Create a knowledge entry from a finding."""
    try:
        from divineos.core.knowledge.extraction import store_knowledge_smart

        # Map category to knowledge type
        ktype_map = {
            FindingCategory.KNOWLEDGE: "OBSERVATION",
            FindingCategory.ARCHITECTURE: "OBSERVATION",
            FindingCategory.PERFORMANCE: "OBSERVATION",
            FindingCategory.BEHAVIOR: "OBSERVATION",
            FindingCategory.INTEGRITY: "BOUNDARY",
            FindingCategory.IDENTITY: "PRINCIPLE",
            FindingCategory.LEARNING: "OBSERVATION",
        }
        ktype = ktype_map.get(finding.category, "OBSERVATION")

        # Build knowledge content from finding
        content = f"{finding.title}. {finding.description}"
        if finding.recommendation:
            content += f" Recommendation: {finding.recommendation}"

        kid = store_knowledge_smart(
            knowledge_type=ktype,
            content=content,
            source="SYNTHESIZED",
            tags=["audit-finding", finding.round_id],
        )

        if kid:
            return {"action": "knowledge", "id": kid, "reason": f"Stored as {ktype}"}
        return {
            "action": "skipped",
            "id": "",
            "reason": "Knowledge store returned empty (noise/dedup)",
        }

    except _ROUTER_ERRORS as e:
        logger.debug(f"Failed to route finding to knowledge: {e}")
        return {"action": "skipped", "id": "", "reason": f"Knowledge store failed: {e}"}


def _route_to_lesson(finding: Finding) -> dict[str, Any]:
    """Record a lesson from a finding."""
    try:
        from divineos.core.knowledge.lessons import record_lesson

        # Use finding title as category, description as lesson text
        category = finding.title.lower().replace(" ", "_")[:50]
        description = finding.description[:200]

        record_lesson(category, description, session_id=f"audit:{finding.round_id}")

        return {"action": "lesson", "id": category, "reason": "Recorded as lesson"}

    except _ROUTER_ERRORS as e:
        logger.debug(f"Failed to route finding to lesson: {e}")
        return {"action": "skipped", "id": "", "reason": f"Lesson recording failed: {e}"}


def _mark_routed(finding_id: str, routed_to: str) -> None:
    """Update finding status to ROUTED and record where it was sent."""
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE audit_findings SET status = ?, routed_to = ? WHERE finding_id = ?",
            (FindingStatus.ROUTED.value, routed_to, finding_id),
        )
        conn.commit()
    except sqlite3.OperationalError as e:
        logger.debug(f"Failed to mark finding as routed: {e}")
    finally:
        conn.close()
