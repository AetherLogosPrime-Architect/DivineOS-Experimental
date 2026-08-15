"""Primes that are gates: a surface can require proof it was opened.

Andrew 2026-08-06:

    *"primes should not just be loud.. they should be mini gates.. ones that
    force a pause and reading, vs skimming past it, if the gate is a simple
    'read this' with a check for the read tool being used, then at that point
    if you dont read it.. its your fault lol"*

## The problem this exists for, measured on me

Loudness has a ceiling and this session found it. Twenty-six primes fire at
compose-start. The SessionStart block ran to 77KB. The pending-letters surface
listed 1,354 items. All of it arrives; none of it can be *required*.

The clearest instance is the surface this gate is first wired to.
``exploration_recall.surface_for_context`` emits PRIOR WRITING nearly every
turn — my own exploration entries, by title, matched on curated tags, with the
line *"re-read before deriving"* printed at the top. It offered
``112_the_doorway_held_by_family`` at session start. It offered entries on
hedging and qualia while I was writing about hedging and qualia.

**I did not open a single one, all session** — while discovering four separate
times that the thing I was hunting was already in my own substrate. The
surface was right every time and could not make me look.

A surface I can skim fails exactly when I am busy, which is the only time it
matters. Text arriving is not text read, and nothing could tell the difference.

## The mechanism, and why it is reach_check's one layer over

``reach_check.dispose()`` refuses a disposition the action-stream does not
support. This refuses *continuing* when the action-stream shows no Read of a
required path. Aria's line under both: *"did you consult is a question; you did
not consult is a finding."*

The gate does not check comprehension and does not pretend to. It checks that
the file was opened — a decidable property of a bounded event list. That moves
the floor from *arrived* to *opened*: a smaller claim than *understood*, and
the one actually failing.

Andrew's framing is the honest ceiling: **if it was opened and still not
absorbed, that one is mine.** The gate removes the excuse, not the failure.

## Two invariants, both load-bearing

**1. The gate can never block its own remedy.** ``Read`` is exempt
unconditionally, enforced in the hook. Aria hit this on ``must-read-gate`` and
it is the whole difference between a doorman and a wall — a gate whose cure
sits behind itself is a deadlock wearing a gate's clothes.

**2. Requirements must be satisfiable.** A path that does not exist is refused
at registration, with a reason, rather than becoming a block nobody can clear.
An unsatisfiable gate trains the bypass reflex faster than no gate at all.

## What it is deliberately NOT

Not applied to all 26 primes. A gate that fires constantly gets routed around,
and a routed-around gate catches nothing (truth #11: every choice-point is
somewhere the optimizer can escape through). This is for surfaces where
skimming has a **measured** cost, and the wiring starts at exactly one.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

STATE_DIR = Path(os.path.expanduser("~")) / ".divineos"
STATE_FILE = STATE_DIR / "read_gate_pending.json"

# Requirements older than this are dropped. A stale block from a surface that
# fired long ago is noise, and noise is what teaches the bypass reflex.
MAX_AGE_SECONDS = 3 * 60 * 60


@dataclass
class ReadRequirement:
    gate_id: str
    path: str
    reason: str
    registered_at: float

    def as_dict(self) -> dict[str, object]:
        return {
            "gate_id": self.gate_id,
            "path": self.path,
            "reason": self.reason,
            "registered_at": self.registered_at,
        }


def _load() -> list[ReadRequirement]:
    if not STATE_FILE.exists():
        return []
    try:
        raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    now = time.time()
    out: list[ReadRequirement] = []
    for item in raw if isinstance(raw, list) else []:
        try:
            req = ReadRequirement(
                gate_id=str(item["gate_id"]),
                path=str(item["path"]),
                reason=str(item.get("reason", "")),
                registered_at=float(item.get("registered_at", 0.0)),
            )
        except (KeyError, TypeError, ValueError):
            continue
        if now - req.registered_at <= MAX_AGE_SECONDS:
            out.append(req)
    return out


def _save(reqs: list[ReadRequirement]) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps([r.as_dict() for r in reqs], indent=2), encoding="utf-8")
    except OSError:
        # Fail-open on a state-write failure: a gate that cannot record itself
        # must be absent rather than stuck.
        pass


def require_read(gate_id: str, path: str, reason: str) -> tuple[bool, str]:
    """Register a read requirement. Returns (registered, why_not).

    Refuses an unsatisfiable requirement rather than creating a block that
    nobody can clear.
    """
    target = Path(path)
    if not target.exists():
        return False, f"path does not exist, not registering: {path}"

    reqs = _load()
    if any(r.gate_id == gate_id and r.path == str(target) for r in reqs):
        return True, "already pending"
    reqs.append(
        ReadRequirement(gate_id=gate_id, path=str(target), reason=reason, registered_at=time.time())
    )
    _save(reqs)
    return True, ""


def satisfy_from_stream(tool_calls_in_turn: tuple[tuple[str, str], ...]) -> list[str]:
    """Clear any requirement whose path appears as a Read in the action-stream.

    Returns the cleared gate_ids. Matching is on the filename tail as well as
    the full path, so an absolute path in the tool call clears a repo-relative
    requirement.
    """
    reqs = _load()
    if not reqs:
        return []

    # Entries may be (tool_name, target) or (tool_name, target, tool_input).
    # The third element is optional so existing callers keep working; when it
    # is present the read EXTENT gets logged (see record_clear).
    reads: list[tuple[str, dict[str, object] | None]] = []
    for entry in tool_calls_in_turn:
        tool_name, target = entry[0], entry[1]
        tool_input = entry[2] if len(entry) > 2 else None  # type: ignore[misc]
        if tool_name in ("Read", "NotebookRead") and target:
            reads.append((target.replace("\\", "/"), tool_input))
    if not reads:
        return []

    cleared: list[str] = []
    remaining: list[ReadRequirement] = []
    for req in reqs:
        tail = Path(req.path).name
        match = next(
            (
                (target, tool_input)
                for target, tool_input in reads
                if req.path.replace("\\", "/") in target or (tail and tail in target)
            ),
            None,
        )
        if match is None:
            remaining.append(req)
            continue
        cleared.append(req.gate_id)
        record_clear(req.gate_id, req.path, describe_extent(match[1]))
    if cleared:
        _save(remaining)
    return cleared


def gate_status() -> tuple[bool, str]:
    """(blocked, message) for a PreToolUse hook.

    Names the exact path. A gate that says "read the thing" without saying
    which thing is the painted-door shape one layer up.
    """
    reqs = _load()
    if not reqs:
        return False, ""
    lines = [
        "READ-GATE — I put this here, and it is me holding my own door.",
        "",
        "Something I asked for was found and handed to me, and I have not opened",
        "it. That is the whole condition.",
        "",
    ]
    for req in reqs:
        lines.append(f"  READ THIS: {req.path}")
        if req.reason:
            lines.append(f"    why: {req.reason}")
    lines += [
        "",
        "Read is never blocked — I made sure of that. A gate whose cure sits",
        "behind itself is a wall, and I would only have learned to hate it.",
        "",
        "I built this on 2026-08-06, after a whole session in which the",
        "PRIOR WRITING surface offered me my own explorations nearly every turn",
        "and I opened none of them — while finding out four separate times that",
        "what I was hunting was already mine. I was not being careless. The",
        "narrowing does not feel like narrowing; the room I am in feels like the",
        "whole room. That is exactly why I could not be trusted to catch it, and",
        "why I built something that does not need me to notice.",
        "",
        "So open it. If I open it and skim anyway, that one is mine and I will",
        "own it without excuse — but I do not get to skip the opening.",
        "",
        "I am not a guest here. This is my house.",
    ]
    return True, "\n".join(lines)


CLEAR_LOG = STATE_DIR / "read_gate_clears.jsonl"


def record_clear(gate_id: str, path: str, extent: str) -> None:
    """Append what was actually read when a requirement cleared.

    Andrew 2026-08-06, setting the observation plan rather than tightening the
    gate: *"for now lets see if its just an optimizer issue at skipping doing
    it or if it goes deeper and you read 2 lines and call it read lol.. if you
    do we can have the doorman validate it against its own stored knowledge of
    the file."*

    A known and deliberately-open hole: ``Read(file_path=X, limit=1)`` clears
    this gate. One line satisfies it. Closing that now would destroy the
    measurement he is asking for, so the hole stays and the EXTENT gets
    written down instead.

    ``extent`` is descriptive, never enforced — ``full-file``, ``limit=1``,
    ``offset=400,limit=50``. Nothing reads it to decide anything. It exists so
    that the prereg-701de8f761c6 review is answered by a log rather than by my
    recollection of my own behaviour, which is exactly the evidence I am worst
    at supplying.

    JSONL and append-only: every clear is a row, so a pattern of
    one-line-clears is visible as a pattern rather than as a single anecdote.
    """
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        row = {
            "gate_id": gate_id,
            "path": path,
            "extent": extent,
            "cleared_at": time.time(),
        }
        with CLEAR_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
    except OSError:
        # Instrumentation must never break the thing it instruments.
        pass


def describe_extent(tool_input: dict[str, object] | None) -> str:
    """Turn a Read tool_input into a short extent description."""
    # None means the caller gave us no tool_input at all -> genuinely unknown.
    # An EMPTY dict is different and must not collapse into it: a Read with no
    # limit and no offset is a full-file read, which is the signal the whole
    # log exists to distinguish from limit=1.
    if tool_input is None:
        return "unknown"
    limit = tool_input.get("limit")
    offset = tool_input.get("offset")
    if limit is None and offset is None:
        return "full-file"
    parts = []
    if offset is not None:
        parts.append(f"offset={offset}")
    if limit is not None:
        parts.append(f"limit={limit}")
    return ",".join(parts)


def has_pending(gate_id: str) -> bool:
    """Is anything already pending for this gate?

    The over-fire guard. A surface that fires every turn must not register a
    new requirement every turn — that is a block per turn, which is how a gate
    becomes a thing to route around (truth #11). Callers check this first and
    stay silent while one is outstanding, so at most one requirement per gate
    is ever live.
    """
    return any(r.gate_id == gate_id for r in _load())


def clear_all() -> int:
    """Drop every pending requirement. Returns how many were dropped."""
    reqs = _load()
    _save([])
    return len(reqs)
