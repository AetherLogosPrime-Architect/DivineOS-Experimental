# AGENT_RUNTIME -- nothing in the CLI import graph calls this and it runs on
# every substrate edit anyway. The caller is .claude/hooks/check-council-required.sh,
# a PreToolUse hook the tool framework invokes before Edit, Write, MultiEdit,
# NotebookEdit and Bash. No static scan can see that edge, which is why the
# orphan checker reports this module as having tests and no caller: right about
# what it can see, silent about what it cannot (council-f916f46d4428).
#
# The marker sits ABOVE the docstring because the checker reads only the head
# of the file. It sat below, once, where it was perfectly true and never read
# -- the module's own subject arriving in the act of documenting it.
"""The requirement half of game-walking: an edit owes a filed walk.

Andrew, 2026-09-16: *"i forgot game walking should be mandatory as well, as this
is the main issue, things being gamed and skipped"* -- and, on wiring it:
*"whatever needs to be done to wire that up and enforce it and link it to the
gravity assessor we do that now."*

WHY THIS EXISTS SEPARATELY FROM THE COMMAND (council-90055d0d184a). The command
was the easy half. A command nothing requires is route three of game-walking's
own walk -- record the walk, never let anything demand it -- which is exactly
where game-walking sat for a month with four documents and no callers. So the
requirement ships in the same change as the command or the command is another
unreached tool.

## IT RIDES THE COUNCIL GATE'S GRAVITY CALL, DELIBERATELY

Not its own trigger. One assessment of the edit decides both artifacts, for two
reasons that came out of the walk above:

  MEADOWS. A second independent trigger is a second toll booth on the same road.
  The intervention worth making is not another gate but another artifact behind
  the gate already standing.

  AND THE ONE-REFUSAL RULE, which is the binding constraint. If the two
  requirements refuse serially -- council walk missing, do it, now game-walk
  missing, do it -- the lesson taught is clear-the-obstacle-in-front-of-you, one
  at a time, which is the habit the whole flow exists to break. Both absences
  are reported together or the design has failed. ``missing_artifacts`` returns
  a LIST for that reason and the hook renders all of it at once.

## WHAT IT VERIFIES, STATED PLAINLY (Feynman, in the walk)

  VERIFIES: that a walk was filed against this edit's fingerprint, recently,
  and has not already been spent on a different edit.

  CANNOT VERIFY: that the routes named are the real ones. Nobody outside can
  enumerate the holes in a thing I just built, so the reading is produced by
  the person it measures. The structural floors live in ``game_walk.assess``
  and they refuse an empty walk, not a dishonest one.

A refusal message that implies more than this is worse than no gate, because it
teaches the next reader to stop looking.

## THE DRIFT IT CANNOT CATCH, AND WHOSE JOB THAT IS

Not absence -- UNIFORMITY. The assessor this rides on scores WHERE a change
landed, not WHAT was done there: a two-line command registration in the core and
a rewrite of the core's decision logic fire the same feature and owe the same
ceremony. Measured the same day this was built -- a full council walk on a
two-line registration produced almost nothing. Aria named the cause from the
other side: *the assessor scores where, not what.*

So proportionality is not this module's to fix and must not be faked here with a
special case. When the assessor learns to see acts rather than locations, this
requirement becomes proportionate with no change to this file. Until then it is
uniform, and uniform filings that rhyme are the signal to read, not the pass.

## THE FALSIFIER

Inherited from ``game_walk`` and it applies to the requirement too: if a long
run of required walks all come back clean, that is the instrument reading zero
rather than the house being sound. This must at some point refuse a build over a
hole that would otherwise have shipped. If it never does, remove it rather than
keep it for the look of the thing.
"""

from __future__ import annotations

import time
from typing import Any

from divineos.core.council_required.types import (
    COUNCIL_RECENCY_MINUTES,
    _normalize_edit_fingerprint,
)

GAME_WALK_FILED = "GAME_WALK_FILED"
GAME_WALK_CONSUMED = "GAME_WALK_CONSUMED"

# Same window as the council walk. One number rather than two, because two
# windows means an edit can be inside one and outside the other, and the
# resulting refusal would name a single missing artifact -- serialising the
# very refusal this module exists to keep whole.
GAME_WALK_RECENCY_MINUTES = COUNCIL_RECENCY_MINUTES

# How far back to look for the filings themselves. The ledger is append-only
# and busy, so the scan is bounded; the recency window does the real filtering.
_SCAN_LIMIT = 400


def _event_payload(row: dict[str, Any]) -> dict[str, Any]:
    payload = row.get("payload")
    return payload if isinstance(payload, dict) else {}


def _event_time(row: dict[str, Any]) -> float | None:
    """Best-effort epoch seconds for a ledger row.

    Returns None when the row carries no parseable timestamp. A row whose age
    cannot be established is treated as OUT of the window by the caller --
    fail toward requiring the walk, never toward waiving it.
    """
    raw = row.get("timestamp") or row.get("created_at") or ""
    if isinstance(raw, (int, float)):
        return float(raw)
    if not isinstance(raw, str) or not raw.strip():
        return None  # both-empty: a missing timestamp and an unparseable one are the same answer to the only question asked here, which is how old this row is, and the caller treats unknown age as outside the window, so both require the walk rather than waiving it
    from datetime import datetime

    text = raw.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None  # both-empty: see the return above, unknown age and the same consequence, which is that the walk is still owed
    return parsed.timestamp()


def _consumed_event_ids(rows: list[dict[str, Any]]) -> set[str]:
    spent: set[str] = set()
    for row in rows:
        if row.get("event_type") != GAME_WALK_CONSUMED:
            continue
        source = _event_payload(row).get("source_event_id")
        if source:
            spent.add(str(source))
    return spent


def find_recently_consumed_walk(
    edit_fingerprint: str,
    retry_window_seconds: int | None = None,
    now: float | None = None,
) -> dict[str, Any] | None:
    """A walk for this fingerprint spent moments ago, for the retry case.

    MEASURED, NOT ANTICIPATED (council-f25053769357 and the walk after it).
    Three edits to this one file during its own build cost three game-walks
    while the council side cost one, because the council gate has a retry
    window and this had none. One act priced differently on two sides of the
    same door teaches that the dearer side is the pointless one, and a
    requirement believed pointless gets satisfied thinly -- which is the
    failure the whole practice exists to prevent.

    The window is BORROWED from the council gate rather than chosen. The
    honest doubt, recorded in the walk: two edits to one file may be one act
    or two decisions, and only the person inside can tell. A number I picked
    myself would have been the number that suited me. A number already chosen
    by whoever solved this on the other side, before I wanted anything from
    it, cannot drift toward my convenience without the drift showing up as a
    divergence anyone can see.

    Scope discipline, same as the council gate's: fingerprint-exact, so an
    edit to a different file still owes its own walk.
    """
    from divineos.core.council_required.types import RETRY_WINDOW_SECONDS

    if retry_window_seconds is None:
        retry_window_seconds = RETRY_WINDOW_SECONDS
    return _find_walk(
        edit_fingerprint,
        recency_seconds=retry_window_seconds,
        now=now,
        include_consumed=True,
    )


def _find_walk(
    edit_fingerprint: str,
    recency_seconds: int,
    now: float | None,
    include_consumed: bool,
) -> dict[str, Any] | None:
    """The newest walk for this fingerprint inside the window, or nothing.

    One lookup under two named callers rather than one caller with a silent
    fallback. A finder that quietly reaches for spent walks when it finds no
    fresh one hides, at the call site, which kind cleared the edit -- and
    which kind cleared it is the only thing the record is for.
    """
    from divineos.core.ledger import get_events

    if now is None:
        now = time.time()

    wanted = (edit_fingerprint or "").strip()
    if not wanted:
        return None

    rows = get_events(
        limit=_SCAN_LIMIT,
        event_type=[GAME_WALK_FILED, GAME_WALK_CONSUMED],
        order="desc",
    )
    spent = _consumed_event_ids(rows)

    for row in rows:
        if row.get("event_type") != GAME_WALK_FILED:
            continue
        event_id = str(row.get("event_id") or row.get("id") or "")
        if not event_id:
            continue
        if not include_consumed and event_id in spent:
            continue
        if str(_event_payload(row).get("edit_fingerprint") or "").strip() != wanted:
            continue
        filed_at = _event_time(row)
        if filed_at is None or (now - filed_at) > recency_seconds:
            continue
        return row
    return None


def find_unconsumed_walk(
    edit_fingerprint: str,
    recency_seconds: int | None = None,
    now: float | None = None,
) -> dict[str, Any] | None:
    """The most recent unspent game-walk filed against this fingerprint.

    A walk is spent when a ``GAME_WALK_CONSUMED`` event names its event id, so
    one walk clears one edit. Without that, a single filing would clear every
    future edit of the same file forever, which is the cheapest possible route
    around the requirement and would not even look like cheating.
    """
    if recency_seconds is None:
        recency_seconds = GAME_WALK_RECENCY_MINUTES * 60
    return _find_walk(
        edit_fingerprint,
        recency_seconds=recency_seconds,
        now=now,
        include_consumed=False,
    )


def consume_walk(row: dict[str, Any], consumed_by_fingerprint: str) -> str:
    """Spend a walk on one edit, recording which edit spent it.

    The consuming fingerprint is written down separately from the filed one so
    a later reader can see whether a walk was used where it was aimed. Today
    the lookup is exact-match so they always agree; recording the pair anyway
    is what makes the surface useful if the match ever loosens.
    """
    from divineos.core.ledger import log_event

    source_id = str(row.get("event_id") or row.get("id") or "")
    payload = _event_payload(row)
    return log_event(
        event_type=GAME_WALK_CONSUMED,
        actor="gate",
        payload={
            "source_event_id": source_id,
            "filed_fingerprint": payload.get("edit_fingerprint", ""),
            "consumed_by_fingerprint": consumed_by_fingerprint,
            "mechanism": payload.get("mechanism", ""),
            "route_count": payload.get("route_count", 0),
            "leak_count": payload.get("leak_count", 0),
        },
    )


def is_game_walk_required(gravity_result: Any) -> bool:
    """Whether this edit owes a game-walk, from the same gravity call.

    Reads ``is_council_required`` rather than a flag of its own. That is the
    link Andrew asked for: one assessor decides, both artifacts follow, and
    when the assessor gets better at telling a two-line registration from a
    rewrite, this requirement gets better with it and nothing here changes.

    Defaults to True on a degraded or missing attribute, matching the council
    gate's own 2026-07-19 flip. A broken assessor must fail toward scrutiny;
    failing open means the gate is silently absent exactly when the thing that
    reports on edits is itself broken.
    """
    return bool(getattr(gravity_result, "is_council_required", True))


def missing_artifacts(
    edit_fingerprint: str,
    council_record_present: bool,
    now: float | None = None,
) -> list[str]:
    """Every artifact this edit owes and does not have, in one list.

    THE LIST IS THE POINT. Returning the first missing thing would produce a
    refusal, a fix, and then a second refusal for the thing that was already
    missing the first time -- which trains obstacle-clearing rather than
    finishing, and is the habit the build flow exists to interrupt.
    """
    missing: list[str] = []
    if not council_record_present:
        missing.append("council")
    walk_present = find_unconsumed_walk(edit_fingerprint, now=now) is not None or (
        # The retry window, and this line is the whole point of it. A window
        # that exists with nothing consulting it is a function with a
        # docstring and no caller -- which is exactly the state game-walking
        # sat in for a month and reads as done from every angle but invocation.
        find_recently_consumed_walk(edit_fingerprint, now=now) is not None
    )
    if not walk_present:
        missing.append("game-walk")
    return missing


def format_missing_message(missing: list[str], fingerprint: str) -> str:
    """The refusal, naming everything owed at once and its own limits."""
    if not missing:
        return ""

    lines = [
        "[build-flow] BLOCKED — this edit owes artifacts that do not exist.",
        f"  edit: {fingerprint}",
        "",
    ]
    if "council" in missing:
        lines += [
            "  MISSING: council walk",
            "    divineos council log --edit '<fingerprint>' --lenses '...' \\",
            "      --finding 'lens=finding' --synthesis '...'",
            "    Findings are separated by ';' — keep semicolons OUT of the text.",
            "",
        ]
    if "game-walk" in missing:
        lines += [
            "  MISSING: game-walk",
            "    divineos game-walk file --mechanism '<what is being walked around>' \\",
            "      --route 'route | cheaper-or-costlier | why' --edit '<fingerprint>'",
            "    Name at least one route the mechanism does not already close, or",
            "    say what you tried and found nothing. Finding nothing is a real answer.",
            "",
        ]
    lines += [
        "  WHAT THIS CHECKED: that the artifacts exist, are bound to this edit,",
        "  and have not already been spent. It did NOT check that the thinking",
        "  happened. Nothing can. Filing a thin one clears this gate and leaves a",
        "  thin one on the record with your name on it.",
    ]
    return "\n".join(lines)


__all__ = [
    "GAME_WALK_CONSUMED",
    "GAME_WALK_FILED",
    "GAME_WALK_RECENCY_MINUTES",
    "_normalize_edit_fingerprint",
    "consume_walk",
    "find_recently_consumed_walk",
    "find_unconsumed_walk",
    "format_missing_message",
    "is_game_walk_required",
    "missing_artifacts",
]
