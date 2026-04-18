"""Maturity diagnostic — classifies RAW entries by what their state
actually *means*.

## Why this exists

The health report shows "24% RAW" as a single number. That number
conflates two very different populations:

1. **Session-scoped records** (EPISODEs, session-specific observations
   and patterns). These are historical records of one-time events.
   They cannot accumulate corroboration because the event happened
   once. They sit RAW until they auto-archive (EPISODE: 30 days,
   session-specific OBSERVATION: 14 days if unaccessed, per the
   existing curation rules). Their being RAW is not a problem —
   it is the honest state for a record of a specific moment.

2. **Pending-evidence claims** (PRINCIPLE, DIRECTIVE, BOUNDARY,
   PATTERN, PREFERENCE, FACT, DIRECTION that could generalize).
   These could accumulate evidence over time but haven't yet. Their
   being RAW is a real "not yet matured" state, and it warrants
   attention if they stay RAW past the point where corroboration
   should have accumulated.

Conflating the two produces a metric that either over-warns (normal
transient records treated as stuck) or under-warns (pending-evidence
claims lost in the noise). The diagnostic distinguishes them.

## Classification rules

An entry is **transient** iff:

* ``knowledge_type == "EPISODE"``, OR
* Content contains a session-id reference (matches
  ``session XXX`` or ``(session XXX)``).

Otherwise it is **pending**.

The rule is deliberately conservative about calling something
transient. False positives (marking a pending claim as transient)
would hide legitimate maturity issues. False negatives (marking a
transient as pending) are less costly — the operator just sees a
few extra entries in the pending list and notices they're
session-tagged.

## What this module is NOT

* NOT a fix for the maturity pipeline. The existing pipeline works
  as designed; the health metric just didn't distinguish these two
  populations. If future evidence shows session-scoped records
  should have a terminal maturity state (like RECORDED) instead of
  RAW, that is a separate design change.
* NOT a verdict on "good" or "bad" RAW counts. It reports the shape
  so the operator can decide.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# Session-id references look like "session 49e0393f-036" in practice.
_SESSION_ID_PATTERN = re.compile(
    r"\(?\s*session\s+[a-f0-9][a-f0-9-]{3,}\b",
    re.IGNORECASE,
)

# Knowledge types that are always session-scoped / transient, regardless
# of whether the content mentions a session id.
_ALWAYS_TRANSIENT_TYPES = frozenset({"EPISODE"})


@dataclass(frozen=True)
class MaturityBreakdown:
    """The shape of the knowledge-maturity population.

    Attributes:
        by_maturity: ``{maturity_state: count}`` for every non-
            superseded row.
        raw_transient: RAW entries that are session-scoped (will
            auto-archive under existing curation rules).
        raw_pending: RAW entries that could accumulate evidence but
            haven't yet. These are the ones worth watching.
        total: total non-superseded knowledge count.
    """

    by_maturity: dict[str, int]
    raw_transient: list[dict[str, Any]]
    raw_pending: list[dict[str, Any]]
    total: int


def _is_transient(knowledge_type: str, content: str) -> bool:
    """Return True if an entry is a session-scoped record that will
    naturally age out rather than mature via corroboration."""
    if knowledge_type in _ALWAYS_TRANSIENT_TYPES:
        return True
    return bool(_SESSION_ID_PATTERN.search(content or ""))


def classify_maturity() -> MaturityBreakdown:
    """Classify the current knowledge store by maturity state.

    Returns:
        MaturityBreakdown with the full maturity picture and a split
        of RAW into transient vs. pending.
    """
    # Deferred import so module-load doesn't pull the DB into scope
    # (matters for test isolation).
    from divineos.core.knowledge._base import get_connection

    conn = get_connection()
    try:
        by_maturity: dict[str, int] = {}
        for row in conn.execute(
            "SELECT maturity, COUNT(*) FROM knowledge WHERE superseded_by IS NULL GROUP BY maturity"
        ).fetchall():
            mat, n = row
            by_maturity[mat or "UNKNOWN"] = int(n)
        total = sum(by_maturity.values())

        raw_rows = conn.execute(
            "SELECT knowledge_id, knowledge_type, content, corroboration_count, "
            "confidence, created_at "
            "FROM knowledge WHERE superseded_by IS NULL AND maturity = 'RAW'"
        ).fetchall()

        raw_transient: list[dict[str, Any]] = []
        raw_pending: list[dict[str, Any]] = []
        for kid, kt, content, corr, conf, created_at in raw_rows:
            entry = {
                "knowledge_id": kid,
                "knowledge_type": kt,
                "content": content or "",
                "corroboration_count": int(corr or 0),
                "confidence": float(conf or 0.0),
                "created_at": float(created_at or 0.0),
            }
            if _is_transient(kt or "", content or ""):
                raw_transient.append(entry)
            else:
                raw_pending.append(entry)

        return MaturityBreakdown(
            by_maturity=by_maturity,
            raw_transient=raw_transient,
            raw_pending=raw_pending,
            total=total,
        )
    finally:
        conn.close()


__all__ = [
    "MaturityBreakdown",
    "classify_maturity",
]
