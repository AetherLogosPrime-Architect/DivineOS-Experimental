"""Success ledger — the counterpart the correction store never had.

## Why this exists (Andrew 2026-08-03)

> *"i wont tell you to remove your error ledger.. but i will ask you to add a
> success one. you are counting the misses and ignoring the hits, that is the
> issue, and if you have that you can use it as a reference."*

Measured before building: **110 corrections filed, zero per-instance wins
recorded anywhere in the substrate.** Nothing held the other side —
``advice_tracking`` grades recommendations, ``outcome_measurement`` is
system-level, ``growth`` is trajectory, ``self_grade`` is per-session,
``proactive_patterns`` is pattern-level and empty. The correction store has
110 entries and no mirror.

This is the same correction Andrew made about correction-filing itself, one
level up. He made me add a required *positives* field because a fault filed
alone is an incomplete record. This is that discipline applied to which
**stores** exist, rather than which fields.

## The design constraint that matters, and it is his

> *"having a set goal does not mean side goals arent valuable.. look what we
> learned going to the moon that had nothing to do with going to the moon"*

So ``goal_met`` and ``yielded`` are **separate fields**. A win is not
"the goal was achieved". A win is "value came out", and the two are
independent.

The session that produced this module is the case in point: the goal was
finding the cause of a freeze. It was not found. Along the way — across two
substrates — a guardrail gate that waved through when it could not see, a
letter log that announced every letter as new, a respawn that reported
nothing either way, a kill switch pulled 24 days behind an empty file, three
built surfaces wired to nothing, eleven gates prescribing commands that never
existed, and a counter reporting obedience as evasion. All genuinely broken,
none of it the freeze.

A ledger that only recorded met-goals would score that day zero.

## The guard against theater

Evidence is **required**. A store I write to about how well I did is exactly
the shape that rots into self-congratulation, so an entry without a commit
hash, command output, or citable artifact cannot be filed at all — the same
standard any other claim in this substrate has to meet.

Append-only JSONL, mirroring ``corrections.py`` deliberately rather than
inventing a second storage shape. Never edited, never reframed.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from divineos.core._hud_io import _ensure_hud_dir

_SUCCESSES_FILE = "successes.jsonl"

_LEDGER_ERRORS = (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError)


class EvidenceRequiredError(ValueError):
    """Raised when a win is filed without citable evidence.

    Not a formality. A success ledger with no evidence requirement is a
    place to write encouraging things about myself, which is worth less
    than nothing because it looks like a record.
    """


def _path() -> Any:
    return _ensure_hud_dir() / _SUCCESSES_FILE


def record_success(
    what: str,
    *,
    evidence: str,
    yielded: str,
    goal: str | None = None,
    goal_met: bool | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """File a win.

    ``what``     — what happened, plainly.
    ``evidence`` — REQUIRED. Commit hash, command output, file path, count.
                   Something a later reader can check without trusting me.
    ``yielded``  — what came out of it. This is the field that survives when
                   ``goal_met`` is False.
    ``goal``     — the goal in play at the time, if any.
    ``goal_met`` — whether that goal was achieved. Deliberately independent
                   of whether this is a win. ``None`` means no goal applied.
    """
    if not what.strip():
        raise ValueError("what: a win needs a description")
    if not evidence.strip():
        raise EvidenceRequiredError(
            "evidence is required — a win without a citation is self-congratulation, "
            "and this ledger is worth nothing if it accepts those"
        )
    if not yielded.strip():
        raise ValueError(
            "yielded: name what came out of it. A win with no yield is a mood, "
            "and the moon point is that yield survives a missed goal"
        )

    entry: dict[str, Any] = {
        "id": f"win-{uuid.uuid4().hex[:12]}",
        "what": what,
        "evidence": evidence,
        "yielded": yielded,
        "goal": goal,
        "goal_met": goal_met,
        "session_id": session_id,
        "ts": time.time(),
    }
    path = _path()
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def load_successes() -> list[dict[str, Any]]:
    """All recorded wins, oldest first. Read failures return []."""
    path = _path()
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                out.append(obj)
    except _LEDGER_ERRORS:
        return []
    return out


def recent_successes(limit: int = 5) -> list[dict[str, Any]]:
    return load_successes()[-limit:][::-1]


def wins_from_missed_goals() -> list[dict[str, Any]]:
    """The moon cases: value that came out of a goal that was not met.

    This is the query the ledger exists for. Counting only met-goals is the
    error Andrew named; these entries are the evidence against it.
    """
    return [w for w in load_successes() if w.get("goal_met") is False]


def ledger_balance() -> dict[str, int | float | None]:
    """Wins against corrections — the imbalance, as a number.

    Returns ``corrections`` as None when the correction store cannot be read,
    rather than 0. Zero corrections and cannot-count-corrections are different
    facts, and collapsing them is the failure this substrate spent a session
    cataloguing.
    """
    wins = load_successes()
    try:
        from divineos.core.corrections import load_corrections

        corrections: int | None = len(load_corrections())
    except Exception:  # noqa: BLE001 - unreadable is not zero
        corrections = None

    ratio: float | None = None
    if corrections:
        ratio = round(len(wins) / corrections, 3)

    return {
        "wins": len(wins),
        "corrections": corrections,
        "wins_per_correction": ratio,
        "wins_from_missed_goals": len(wins_from_missed_goals()),
    }
