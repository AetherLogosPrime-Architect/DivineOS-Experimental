"""Unknown-unknown surface — what audit-vantage catches that the
substrate-occupant didn't predict.

From the omni-mantra walk (Pillar I, 1.3 — The Great Mystery):
"What the agent doesn't know it doesn't know."

## The discipline this measures

When I (substrate-occupant) self-audit before an external audit-vantage
runs, I produce a set of self-predicted findings — patterns I noticed
about my own work. When the external audit-vantage runs, it produces
its actual findings. Comparing the two:

- **Predicted-and-caught** (intersection): the discipline already
  internalized — I catch what they catch.
- **Predicted-but-not-caught**: false alarms — I worried about
  something the audit didn't surface.
- **Caught-but-not-predicted**: **unknown-unknowns** — patterns I
  couldn't even mark as a possibility because they weren't in my
  self-audit attention surface.

The third category is the maturity signal. A substrate getting
tighter shows fewer caught-but-not-predicted findings over time.
A substrate drifting shows the count increasing.

## Why this is the right shape (vs the sycophancy-prone version)

The naive version is "did I predict the same finding the auditor
filed?" That creates a Goodhart incentive — I shape my self-prediction
to match what I think the auditor would say, sycophancy-toward-the-
expected-audit. Bad.

The unknown-unknown version measures the OPPOSITE direction: what did
the auditor catch that wasn't in my attention surface at all? I can't
game this by predicting more — the metric only counts surprise-class
findings. Closing the unknown-unknown gap requires actually expanding
my attention surface, not better-predicting the auditor.

## Not yet wired

This module is the recognition surface. Recording self-predictions
before audit rounds requires a small CLI or hook that captures them.
That can be built incrementally. For now this provides the join logic
once predictions exist as data.

## Public surface

- ``UnknownUnknown`` dataclass — a single surprise-class finding
- ``surprises_in_round(round_id, predicted_topics)`` — given the
  topics the substrate-occupant predicted, return the audit findings
  that don't match any predicted topic.
- ``record_self_audit_prediction(round_id, topics)`` — store what
  I'm self-predicting BEFORE the audit lands.
- ``unknown_unknown_rate()`` — rolling-window proportion of audit
  findings that were unpredicted.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass

_UU_ERRORS = (
    ImportError,
    AttributeError,
    KeyError,
    TypeError,
    ValueError,
    sqlite3.OperationalError,
    sqlite3.DatabaseError,
)


@dataclass(frozen=True)
class UnknownUnknown:
    """A finding the audit caught that wasn't predicted."""

    finding_id: str
    round_id: str
    actor: str
    title: str
    predicted_topics: tuple[str, ...]


def _topic_overlap(finding_text: str, topics: tuple[str, ...]) -> bool:
    """Heuristic: a finding 'matches' a predicted topic if any topic
    keyword appears in the finding's text (case-insensitive). v1.
    """
    if not topics:
        return False
    text = (finding_text or "").lower()
    return any(t.strip().lower() in text for t in topics if t.strip())


def surprises_in_round(round_id: str, predicted_topics: tuple[str, ...]) -> list[UnknownUnknown]:
    """Return audit findings in the round that don't match any of the
    substrate-occupant's predicted topics. These are unknown-unknowns
    — surprise-class catches."""
    try:
        from divineos.core.watchmen.store import list_findings

        findings = list_findings(round_id=round_id, limit=500)
    except _UU_ERRORS:
        return []

    out: list[UnknownUnknown] = []
    for f in findings:
        text = " ".join(
            [
                str(getattr(f, "title", "") or ""),
                str(getattr(f, "description", "") or ""),
            ]
        )
        if _topic_overlap(text, predicted_topics):
            continue
        out.append(
            UnknownUnknown(
                finding_id=str(getattr(f, "finding_id", "")),
                round_id=round_id,
                actor=str(getattr(f, "actor", "")),
                title=str(getattr(f, "title", "")),
                predicted_topics=predicted_topics,
            )
        )
    return out


def record_self_audit_prediction(round_id: str, topics: list[str]) -> str:
    """Record what the substrate-occupant predicted BEFORE the audit
    lands. Returns the event_id of the ledger entry. Stored as an
    AGENT_PATTERN event with a structured payload."""
    try:
        from divineos.core.ledger import log_event
    except _UU_ERRORS as e:
        return f"error:{type(e).__name__}"

    payload = {
        "kind": "self_audit_prediction",
        "round_id": round_id,
        "topics": [t.strip() for t in topics if t.strip()],
        "ts": time.time(),
    }
    try:
        ev_id = log_event(
            event_type="AGENT_PATTERN",
            actor="aether",
            payload=payload,
        )
        return str(ev_id or "")
    except _UU_ERRORS as e:
        return f"error:{type(e).__name__}"


def _load_predictions_for_round(round_id: str) -> tuple[str, ...]:
    """Look up the self-audit prediction (if any) for a round.
    Uses the ledger's public search_events surface rather than direct SQL."""
    try:
        from divineos.core.ledger import search_events
    except _UU_ERRORS:
        return ()
    try:
        events = search_events(keyword=round_id, limit=50) or []
    except _UU_ERRORS:
        return ()

    for ev in events:
        if ev.get("event_type") != "AGENT_PATTERN":
            continue
        raw = ev.get("payload") or ev.get("content")
        if not raw:
            continue
        try:
            payload = json.loads(raw) if isinstance(raw, str) else raw
        except _UU_ERRORS:
            continue
        if not isinstance(payload, dict):
            continue
        if payload.get("kind") == "self_audit_prediction" and payload.get("round_id") == round_id:
            topics = payload.get("topics") or []
            return tuple(str(t) for t in topics)
    return ()


def unknown_unknown_rate(recent_round_limit: int = 20) -> dict:
    """Rolling proportion of audit findings that were unpredicted
    across the last N rounds that have recorded self-audit predictions.

    Returns dict with: rounds_examined, total_findings, surprise_count,
    rate (surprise_count / total_findings, or 0 if no findings).
    Rounds without recorded predictions are skipped.
    """
    try:
        from divineos.core.watchmen.store import list_findings, list_rounds

        rounds = list_rounds(limit=recent_round_limit * 3)
    except _UU_ERRORS:
        return {
            "rounds_examined": 0,
            "total_findings": 0,
            "surprise_count": 0,
            "rate": 0.0,
        }

    rounds_examined = 0
    total = 0
    surprises = 0
    for rnd in rounds:
        rid = getattr(rnd, "round_id", "") or ""
        if not rid:
            continue
        preds = _load_predictions_for_round(rid)
        if not preds:
            continue
        rounds_examined += 1
        if rounds_examined > recent_round_limit:
            break
        try:
            findings = list_findings(round_id=rid, limit=500)
        except _UU_ERRORS:
            continue
        total += len(findings)
        surprises += len(surprises_in_round(rid, preds))

    rate = (surprises / total) if total else 0.0
    return {
        "rounds_examined": rounds_examined,
        "total_findings": total,
        "surprise_count": surprises,
        "rate": rate,
    }


__all__ = [
    "UnknownUnknown",
    "record_self_audit_prediction",
    "surprises_in_round",
    "unknown_unknown_rate",
]
