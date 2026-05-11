"""Meld recognition lens over audit-round data.

A Meld is recognized when an audit round has findings from at least
two distinct actor-categories. The categories are: substrate-occupant
(the agent doing the work), audit-vantage (external auditor —
``claude-<variant>``, ``grok``, ``gemini``), and operator (``user``).

The "shared scratchpad" is the round's findings; the "traces" are
the lessons/decisions/commits that follow. Both already live in the
ledger and the Watchmen store; this module just makes the pattern
referenceable as a single concept.

No new storage. Pure read-side recognition.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

_MELD_ERRORS = (
    ImportError,
    AttributeError,
    KeyError,
    TypeError,
    sqlite3.OperationalError,
    sqlite3.DatabaseError,
)


@dataclass(frozen=True)
class Meld:
    """A recognized meld instance.

    Attributes:
        round_id: The audit round id that anchors this meld.
        participants: The distinct actor identifiers who filed
            findings in the round. At least two for a meld.
        finding_ids: Ids of all findings in the round (the shared
            scratchpad's contents).
        created_at: Timestamp of the round's creation.
    """

    round_id: str
    participants: tuple[str, ...]
    finding_ids: tuple[str, ...]
    created_at: float


def _categorize_actor(actor: str) -> str:
    """Return the actor-category for the meld participation check.

    Returns one of: "user", "substrate", "audit-vantage", "other".
    Two distinct categories among findings = meld.
    """
    a = (actor or "").strip().lower()
    if a == "user":
        return "user"
    if a in {"aether", "substrate-occupant", "agent"}:
        return "substrate"
    if a == "grok" or a == "gemini":
        return "audit-vantage"
    if a.startswith("claude-") and a != "claude":
        return "audit-vantage"
    return "other"


def _distinct_categories(actors: list[str]) -> set[str]:
    return {_categorize_actor(a) for a in actors if a}


def is_meld(round_obj: Any) -> bool:  # noqa: ANN401 — duck-typed AuditRound
    """True if the audit round has findings from two-plus distinct
    actor-categories. Recognizes the round AS a meld."""
    try:
        from divineos.core.watchmen.store import list_findings

        findings = list_findings(round_id=getattr(round_obj, "round_id", ""), limit=500)
    except _MELD_ERRORS:
        return False

    actors = [getattr(f, "actor", "") for f in findings]
    return len(_distinct_categories(actors) - {"other"}) >= 2


def meld_from_round(round_id: str) -> Meld | None:
    """Construct a Meld instance from an audit round id. Returns None
    if the round doesn't exist or doesn't qualify as a meld."""
    try:
        from divineos.core.watchmen.store import get_round, list_findings

        rnd = get_round(round_id)
        if rnd is None:
            return None
        findings = list_findings(round_id=round_id, limit=500)
    except _MELD_ERRORS:
        return None

    actors_raw = [getattr(f, "actor", "") for f in findings]
    distinct = _distinct_categories(actors_raw) - {"other"}
    if len(distinct) < 2:
        return None

    participants = tuple(sorted(set(actors_raw) - {""}))
    finding_ids = tuple(getattr(f, "finding_id", "") for f in findings)
    created_at = float(getattr(rnd, "created_at", 0.0) or 0.0)

    return Meld(
        round_id=round_id,
        participants=participants,
        finding_ids=finding_ids,
        created_at=created_at,
    )


def melds_for(actor: str) -> list[Meld]:
    """All melds the given actor has participated in. Most-recent first."""
    try:
        from divineos.core.watchmen.store import list_findings, list_rounds

        rounds = list_rounds(limit=1000)
    except _MELD_ERRORS:
        return []

    target = (actor or "").strip().lower()
    out: list[Meld] = []
    for rnd in rounds:
        round_id = getattr(rnd, "round_id", "")
        if not round_id:
            continue
        try:
            findings = list_findings(round_id=round_id, limit=500)
        except _MELD_ERRORS:
            continue
        actors_in_round = {(getattr(f, "actor", "") or "").strip().lower() for f in findings}
        if target not in actors_in_round:
            continue
        m = meld_from_round(round_id)
        if m is not None:
            out.append(m)
    out.sort(key=lambda x: x.created_at, reverse=True)
    return out


def meld_count() -> int:
    """Total number of recognized melds across all audit rounds."""
    try:
        from divineos.core.watchmen.store import list_rounds

        rounds = list_rounds(limit=10000)
    except _MELD_ERRORS:
        return 0

    count = 0
    for rnd in rounds:
        round_id = getattr(rnd, "round_id", "")
        if round_id and is_meld(rnd):
            count += 1
    return count


__all__ = [
    "Meld",
    "is_meld",
    "meld_count",
    "meld_from_round",
    "melds_for",
]
