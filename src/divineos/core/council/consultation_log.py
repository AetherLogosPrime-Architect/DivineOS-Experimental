"""Council consultation logging — record every consult, audit opt-in.

Mode 1.5 design (Andrew, 2026-04-21):
  - Every council consultation gets logged as an event to the ledger
    (event_type=COUNCIL_CONSULTATION). This is lightweight, non-gating,
    and always-on. The agent's reasoning trail stays retrievable even
    for exploratory consultations.
  - Only consultations explicitly promoted to audit (via the --audit flag
    or the separate `audit from-council` command) create an audit_round
    plus audit_findings. That path bumps the cadence.

This keeps two signals cleanly separated:
  - Consultation log: what the agent asked the council and what came back
  - Audit log: findings the operator chose to count toward the review cadence

Tier defaults for audit-promoted council rounds are MEDIUM (see
watchmen.types.tier_for_actor — "council" maps to Tier.MEDIUM). Operators
can override at promotion time.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass

from loguru import logger

from divineos.core.council.framework import LensAnalysis

CONSULTATION_EVENT_TYPE = "COUNCIL_CONSULTATION"


@dataclass(frozen=True)
class LoggedConsultation:
    """Reference to a logged consultation — the event_id is the handle."""

    event_id: str
    consultation_id: str  # Shorter human-facing ID for CLI references
    timestamp: float


def log_consultation(
    question: str,
    selected_expert_names: list[str],
    analyses: list[LensAnalysis],
    synthesis: str,
) -> LoggedConsultation:
    """Record a council consultation as a ledger event (always-on).

    Does NOT create an audit_round. Use ``promote_to_audit`` to do that
    explicitly. Returns a ``LoggedConsultation`` with the event_id and a
    shorter consultation_id for CLI lookup.
    """
    consultation_id = f"consult-{uuid.uuid4().hex[:12]}"
    timestamp = time.time()

    payload = {
        "consultation_id": consultation_id,
        "question": question,
        "selected_experts": list(selected_expert_names),
        "concerns_by_expert": {a.expert_name: list(a.concerns) for a in analyses if a.concerns},
        "synthesis_preview": synthesis[:400] if synthesis else "",
        "timestamp": timestamp,
    }

    event_id = ""
    try:
        from divineos.core.ledger import log_event

        event_id = log_event(
            CONSULTATION_EVENT_TYPE,
            "council",
            payload,
            validate=False,
        )
    except (ImportError, OSError, sqlite3.OperationalError, TypeError, ValueError) as e:
        logger.debug(f"Consultation log best-effort skip: {e}")

    return LoggedConsultation(
        event_id=event_id,
        consultation_id=consultation_id,
        timestamp=timestamp,
    )


def promote_to_audit(
    consultation_id: str,
    tier: str | None = None,
    focus_override: str | None = None,
) -> str:
    """Promote a logged consultation to a formal audit_round + findings.

    Walks back to the ledger event, extracts the fired concerns, and
    creates an audit_round with actor=council plus one audit_finding per
    fired concern. Returns the new round_id.

    Raises ValueError if the consultation_id does not resolve to a
    COUNCIL_CONSULTATION event.
    """
    from divineos.core.watchmen.store import submit_finding, submit_round

    payload = _fetch_consultation_payload(consultation_id)

    question = payload.get("question", "")
    concerns_by_expert: dict[str, list[str]] = payload.get("concerns_by_expert", {})
    focus = focus_override or f"Council consultation: {question[:140]}"

    round_id = submit_round(
        actor="council",
        focus=focus,
        expert_count=len(payload.get("selected_experts", [])),
        notes=f"Promoted from consultation {consultation_id}",
        tier=tier,
    )

    # Each fired concern becomes a finding tagged with the expert that surfaced it.
    for expert_name, concerns in concerns_by_expert.items():
        for concern in concerns:
            title = concern[:80] + ("…" if len(concern) > 80 else "")
            submit_finding(
                round_id=round_id,
                actor="council",
                severity="MEDIUM",  # Default — operator can resolve/adjust later
                category="BEHAVIOR",  # Default category for council concerns
                title=title,
                description=concern,
                tags=[f"expert:{expert_name}", f"consultation:{consultation_id}"],
                tier=tier,
            )

    logger.info(
        f"Promoted consultation {consultation_id} to audit round {round_id} "
        f"with {sum(len(v) for v in concerns_by_expert.values())} findings"
    )
    return round_id


def _fetch_consultation_payload(consultation_id: str) -> dict:
    """Look up the consultation event's payload by consultation_id.

    Raises ValueError if not found.
    """
    from divineos.core._ledger_base import get_connection

    conn = get_connection()
    try:
        # payload is stored as JSON; we need to look up by consultation_id inside it
        rows = conn.execute(
            "SELECT event_id, payload FROM system_events WHERE event_type = ? ORDER BY timestamp DESC",
            (CONSULTATION_EVENT_TYPE,),
        ).fetchall()
    finally:
        conn.close()

    for _event_id, payload_json in rows:
        try:
            payload = json.loads(payload_json)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(payload, dict) and payload.get("consultation_id") == consultation_id:
            return dict(payload)

    raise ValueError(f"No COUNCIL_CONSULTATION event found for consultation_id {consultation_id!r}")


def list_recent_consultations(limit: int = 20) -> list[dict]:
    """Return recent COUNCIL_CONSULTATION payloads, newest first.

    Used by the CLI to show a picker for promote-to-audit.
    """
    from divineos.core._ledger_base import get_connection

    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT timestamp, payload FROM system_events WHERE event_type = ? "
            "ORDER BY timestamp DESC LIMIT ?",
            (CONSULTATION_EVENT_TYPE, limit),
        ).fetchall()
    finally:
        conn.close()

    results: list[dict] = []
    for ts, payload_json in rows:
        try:
            payload = json.loads(payload_json)
        except (json.JSONDecodeError, TypeError):
            continue
        payload.setdefault("timestamp", ts)
        results.append(payload)
    return results


__all__ = [
    "CONSULTATION_EVENT_TYPE",
    "LoggedConsultation",
    "list_recent_consultations",
    "log_consultation",
    "promote_to_audit",
]
