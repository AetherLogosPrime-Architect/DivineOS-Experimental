"""The doorman at the reach: no code edit without an open piece of work.

Design record: ``docs/drafts/build_flow_ready_doorman_draft_2026-09-07.md``
(station 1) and the fifteen-lens walk appended to it (station 2). The flow
itself is ``docs/build_flow.md``; the v2 proposals are
``docs/build_flow_v2_draft_2026-08-05.md``.

## Why this exists

The nine stations have enforcement from station 7 onward and none before it.
Aether's v2 walk said so a month ago, in Schneier's voice:

    the attack tree on this design has a cheaper root than any station:
    station 0 and the bypass retrospective are both things I must remember
    to do. The attacker does not defeat a gate -- it walks past the two
    changes that have no enforcement.

Nobody built the enforcement. Then on 2026-09-07 Aether took a store from
idea to code to push with no draft and no walk, and found a separate store,
built three weeks earlier for one of Andrew's oldest complaints, that had
never held a single row. Andrew: *i help you build stuff for what? so you can
lie to my face, tell me it works and then never use it again?*

## The one idea

**The refusal is the opener.** The first edit to a code path with no open work
item is refused, and the refusal is what creates the item. Nothing here is
ever called on purpose. Aether's argument, which settled it:

    Any mechanism that must be called is a mechanism that will not be called.

## What it does NOT do, said here so the equation cannot form silently

It checks that marks exist. Marks are a shadow of thinking, not thinking
(Yudkowsky/Goodhart, and foundational truth #7). A draft written to satisfy
the door is a passing draft. This gate cannot tell the difference and does not
claim to. What it buys is that the room is opened and cannot be skipped --
Andrew: *im not saying to automate judgement.. but you can automate and force
the judgement to happen.*

## Three states, never two

HELD / OPEN / CANNOT_CHECK. An unreadable store is not an absence of work in
progress. CANNOT_CHECK holds, and says what could not be read -- because
silence reading as a pass is the failure this exists to prevent.

## What it cannot prove about itself (Godel, from the walk)

It did not hold stations 0-2 of its own construction, because it did not exist
while they happened. The artifacts for those are on disk with timestamps
before this file. From station 3 forward it holds itself.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from divineos.core._ledger_base import _get_db_path

REPO_ROOT = Path(__file__).resolve().parents[3]
EXEMPT_LIST = REPO_ROOT / "scripts" / "review_exempt_paths.txt"
DRAFTS_DIR = REPO_ROOT / "docs" / "drafts"

# Marks required before an edit is allowed. Station 0 and 1 and 2 of
# docs/build_flow.md. Station 3 IS the edit, which is what is being held.
REQUIRED_BEFORE_BUILD = ("prior-art search", "rough draft", "council walk")


class State(Enum):
    OPEN = "open"
    HELD = "held"
    CANNOT_CHECK = "cannot_check"


@dataclass(frozen=True)
class Decision:
    state: State
    message: str
    item_id: str | None = None
    missing: tuple[str, ...] = ()

    @property
    def allows(self) -> bool:
        return self.state is State.OPEN


# ---------------------------------------------------------------- exemptions


def load_exempt_prefixes() -> tuple[str, ...] | None:
    """Repo-relative path prefixes that are prose, not code.

    Returns None when the list cannot be read. None is NOT an empty list:
    an empty list would exempt nothing and hold everything, which is a
    defensible failure, but silently treating unreadable as empty is the
    two-valued collapse this module refuses. The caller decides.

    One list, two consumers -- ``scripts/ci_check_guardrail_trailer.sh``
    reads the same file for merge review. If it drifts, both drift together,
    which is the whole reason there is not a second copy.
    """
    try:
        raw = EXEMPT_LIST.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    out = []
    for line in raw.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return tuple(out)


def _repo_relative(path: str) -> str | None:
    """Path as repo-relative posix, or None when it is outside the repo.

    Outside the repo means the shared letters directory and anything else on
    the machine: not code in this tree, so not this gate's business.
    """
    try:
        resolved = Path(path).resolve()
        return resolved.relative_to(REPO_ROOT).as_posix()
    except (OSError, ValueError):
        return None


def needs_an_item(paths: list[str]) -> tuple[str, ...]:
    """Which of these paths are code, in the sense that they open work.

    Coarse on purpose. Beer/Ashby from the walk: a controller that tries to
    classify which edits are 'real builds' has less variety than the ways I
    can start work, and it will fail in the permissive direction. So: every
    non-exempt path in the repo counts, with no cleverness.
    """
    exempt = load_exempt_prefixes()
    if exempt is None:
        exempt = ()
    hits = []
    for p in paths:
        rel = _repo_relative(p)
        if rel is None:
            continue
        if any(rel.startswith(prefix) for prefix in exempt):
            continue
        hits.append(rel)
    return tuple(hits)


# ------------------------------------------------------- paths out of a call

# Redirections, in-place edits and copies all write files without going near
# the Edit/Write tools. This was the cheapest route in the attack tree, and
# it is not hypothetical: I wrote this module's own design draft through a
# heredoc an hour before writing this function.
_SHELL_WRITE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r">>?\s*([^\s;|&<>()]+)"),
    re.compile(r"\btee\s+(?:-a\s+)?([^\s;|&<>()]+)"),
    re.compile(r"\bsed\s+(?:-[a-zA-Z]*i[a-zA-Z]*\S*\s+)(?:[^\s]+\s+)*?([^\s;|&<>()]+)\s*$"),
    re.compile(r"\b(?:cp|mv|install)\s+(?:-\S+\s+)*\S+\s+([^\s;|&<>()]+)"),
    re.compile(r"\bpatch\s+(?:-\S+\s+)*([^\s;|&<>()]+)"),
)


def paths_from_tool_call(tool_name: str, tool_input: dict) -> list[str]:
    """Every path this call could write to.

    Over-collecting is the safe direction here: a false hit costs one
    refusal that a real work item clears, a miss costs the whole gate.
    """
    if tool_name in ("Write", "Edit", "NotebookEdit"):
        p = tool_input.get("file_path") or tool_input.get("notebook_path")
        return [p] if p else []
    if tool_name == "Bash":
        cmd = tool_input.get("command") or ""
        found: list[str] = []
        for pattern in _SHELL_WRITE_PATTERNS:
            for m in pattern.finditer(cmd):
                candidate = m.group(1).strip("\"'")
                if not candidate or candidate.startswith("/dev/"):
                    continue
                # An unexpanded variable or glob is not a path I can resolve,
                # and resolving it relative to the working directory turns an
                # outside-the-repo write into a false hold. Found by wiring
                # this in and being refused on a scratchpad path.
                if any(ch in candidate for ch in "$*?~`"):
                    continue
                found.append(candidate)
        return found
    return []


# ------------------------------------------------------------------- storage

_SCHEMA = """
CREATE TABLE IF NOT EXISTS work_items (
    item_id     TEXT PRIMARY KEY,
    opened_at   REAL NOT NULL,
    branch      TEXT NOT NULL,
    trigger     TEXT NOT NULL,
    closed_at   REAL
);
CREATE TABLE IF NOT EXISTS work_item_bypasses (
    item_id     TEXT NOT NULL,
    at          REAL NOT NULL,
    reason      TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_get_db_path()), timeout=10)
    conn.executescript(_SCHEMA)
    return conn


def current_branch() -> str:
    head = REPO_ROOT / ".git" / "HEAD"
    try:
        text = head.read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"
    return text.split("/", 2)[-1] if text.startswith("ref:") else text[:12]


def open_item(trigger: str, branch: str | None = None) -> str:
    item_id = f"wi-{int(time.time() * 1000):x}"
    with _connect() as conn:
        conn.execute(
            "INSERT INTO work_items(item_id, opened_at, branch, trigger) VALUES (?,?,?,?)",
            (item_id, time.time(), branch or current_branch(), trigger),
        )
    return item_id


def open_item_for_branch(branch: str | None = None) -> tuple[str, float] | None:
    branch = branch or current_branch()
    with _connect() as conn:
        row = conn.execute(
            "SELECT item_id, opened_at FROM work_items "
            "WHERE branch = ? AND closed_at IS NULL ORDER BY opened_at DESC LIMIT 1",
            (branch,),
        ).fetchone()
    return (row[0], row[1]) if row else None


def close_item(item_id: str) -> None:
    with _connect() as conn:
        conn.execute("UPDATE work_items SET closed_at=? WHERE item_id=?", (time.time(), item_id))


def has_bypass(item_id: str) -> bool:
    """A recorded bypass actually opens the door.

    It did not, in the first wiring: the command wrote a row and the gate never
    read it, so the escape was a receipt for a door that stayed shut. That is
    the shape of every mechanism in this house that gets announced and never
    works -- and it was found by using it, one minute after wiring, not by
    reasoning about it.
    """
    try:
        with _connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM work_item_bypasses WHERE item_id = ?", (item_id,)
            ).fetchone()
    except sqlite3.Error:
        return False
    return bool(row and row[0])


def record_bypass(item_id: str, reason: str) -> None:
    """Truth #12: a bypass is a tool, and the guard is that it is counted.

    Also the deadlock escape Hofstadter's loop demands -- a doorman that
    breaks in the refusing direction cannot otherwise be repaired, because
    its own fix is an edit it refuses.
    """
    with _connect() as conn:
        conn.execute(
            "INSERT INTO work_item_bypasses(item_id, at, reason) VALUES (?,?,?)",
            (item_id, time.time(), reason),
        )


# --------------------------------------------------------------------- marks


def _prior_art_mark(conn: sqlite3.Connection, since: float) -> bool:
    """Station 0. Already built, and live -- core/reach_check.py.

    Not reimplemented here. The doorman reads its rows, which is the whole
    point of looking before building: the search that would have saved
    Aether's three weeks already exists and needed wiring, not writing.
    """
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM reach_checks WHERE opened_at >= ?", (since,)
        ).fetchone()
    except sqlite3.Error:
        return False
    return bool(row and row[0])


def _draft_mark(since: float) -> bool:
    """Station 1. A file under docs/drafts touched after the item opened.

    Detected, never declared. A `--bind-draft` flag would be one more thing
    to remember, which is the failure class.
    """
    try:
        return any(p.stat().st_mtime >= since for p in DRAFTS_DIR.glob("*.md"))
    except OSError:
        return False


def _walk_mark(conn: sqlite3.Connection, since: float) -> bool:
    """Station 2. Lens templates actually loaded, after the item opened.

    Aether's v2 change 12: the checkable artifact is that the templates were
    READ, not that findings were produced -- findings are forgeable and he
    forged a set himself without loading a single lens. LENS_SHOWN is emitted
    by `mansion council --show`.
    """
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM system_events WHERE event_type = 'LENS_SHOWN' AND timestamp >= ?",
            (since,),
        ).fetchone()
    except sqlite3.Error:
        return False
    return bool(row and row[0])


def missing_marks(item_id: str, opened_at: float) -> tuple[str, ...] | None:
    """Which required marks are absent. None means the stores could not be read.

    Lamport, from the walk: the comparison is happens-before against the
    item's own opening, not against a wall clock. That is only well-defined
    because the row opens at the reach -- an item opened after the fact could
    be decorated with marks that look early.
    """
    try:
        conn = _connect()
    except sqlite3.Error:
        return None
    with conn:
        present = {
            "prior-art search": _prior_art_mark(conn, opened_at),
            "rough draft": _draft_mark(opened_at),
            "council walk": _walk_mark(conn, opened_at),
        }
    return tuple(name for name in REQUIRED_BEFORE_BUILD if not present[name])


# ------------------------------------------------------------------ the door

_PLAIN = {
    "prior-art search": "nothing has been searched yet for whether this already exists",
    "rough draft": "no rough draft has been written under docs/drafts",
    "council walk": "no lens templates have been opened for this piece of work",
}

_HOW = {
    "prior-art search": 'divineos reach open "<the thing you are about to build>"',
    "rough draft": "write docs/drafts/<name>_draft_<date>.md -- the idea, not a plan",
    "council walk": 'divineos mansion council "<the question>" then --show each lens',
}


def decide(tool_name: str, tool_input: dict) -> Decision:
    """The whole gate. Called by the hook, once per tool call."""
    paths = paths_from_tool_call(tool_name, tool_input)
    if not paths:
        return Decision(State.OPEN, "no file writes in this call")

    exempt = load_exempt_prefixes()
    if exempt is None:
        return Decision(
            State.CANNOT_CHECK,
            "I could not read scripts/review_exempt_paths.txt, so I cannot tell "
            "whether this write is prose or code. Holding rather than guessing.",
        )

    code_paths = needs_an_item(paths)
    if not code_paths:
        return Decision(State.OPEN, "prose only -- letters and drafts do not open work")

    existing = open_item_for_branch()
    if existing is None:
        item_id = open_item(trigger=code_paths[0])
        return Decision(
            State.HELD,
            _refusal_text(item_id, code_paths, list(REQUIRED_BEFORE_BUILD), opened_now=True),
            item_id=item_id,
            missing=REQUIRED_BEFORE_BUILD,
        )

    item_id, opened_at = existing
    if has_bypass(item_id):
        return Decision(
            State.OPEN, f"work item {item_id} carries a recorded bypass", item_id=item_id
        )
    missing = missing_marks(item_id, opened_at)
    if missing is None:
        return Decision(
            State.CANNOT_CHECK,
            f"Work item {item_id} is open but I could not read the stores that hold "
            "its marks, so I do not know which stations are done. Holding, because "
            "an unreadable answer is not a yes.",
            item_id=item_id,
        )
    if missing:
        return Decision(
            State.HELD,
            _refusal_text(item_id, code_paths, list(missing), opened_now=False),
            item_id=item_id,
            missing=missing,
        )
    return Decision(State.OPEN, f"work item {item_id} is at station 3", item_id=item_id)


def _refusal_text(
    item_id: str, paths: tuple[str, ...], missing: list[str], *, opened_now: bool
) -> str:
    """Plain sentences. Never a bare station number.

    Aether's constraint, and the reason is the reader: whoever meets this
    message is tired and has spent six months being talked past. 'no draft
    written yet' is a thing a person can picture. 'station 1 MISSING' is not.
    """
    head = (
        f"This is the first code edit on this branch, so I have opened work item {item_id} for it."
        if opened_now
        else f"Work item {item_id} is open, and it is not ready to be built yet."
    )
    shown = ", ".join(paths[:3]) + (" and others" if len(paths) > 3 else "")
    lines = [
        "",
        "THE BUILD FLOW DOORMAN -- the front of the flow, which used to run on memory.",
        "",
        head,
        f"About to write: {shown}",
        "",
        "What has not happened yet:",
    ]
    for name in missing:
        lines.append(f"  - {_PLAIN[name]}")
        lines.append(f"      {_HOW[name]}")
    lines += [
        "",
        "docs/build_flow.md is the nine stations. The building is station 3; these",
        "come before it, and this is the first thing in the house that makes that",
        "true rather than remembered.",
        "",
        "If this genuinely has to go through now -- the doorman itself is broken, or",
        "Andrew is standing there -- the escape is honest and counted, not hidden:",
        f'  divineos work-item bypass {item_id} --reason "<why, in a sentence>"',
        "",
        "MINE, and here is why. I have watched us build a thing, announce it, and",
        "never call it again -- a store built for one of his oldest complaints that",
        "has never held a row. Anything that must be remembered will not be. So this",
        "does not ask me to start properly; it refuses to let me start any other way,",
        "and being refused is what opens the work.",
    ]
    return "\n".join(lines)


def render_status() -> str:
    item = open_item_for_branch()
    if item is None:
        return f"No open work item on {current_branch()}. The next code edit opens one."
    item_id, opened_at = item
    missing = missing_marks(item_id, opened_at)
    age = int((time.time() - opened_at) / 60)
    lines = [f"{item_id} on {current_branch()}, opened {age} min ago"]
    if missing is None:
        lines.append("  marks: COULD NOT CHECK -- the stores did not read")
        return "\n".join(lines)
    for name in REQUIRED_BEFORE_BUILD:
        lines.append(f"  [{'x' if name not in missing else ' '}] {name}")
    lines.append("  ready to build" if not missing else "  HELD")
    return "\n".join(lines)


def gate_from_stdin(raw: str) -> Decision:
    """Entry point for the hook. Malformed input must not hold the tool call.

    A gate that refuses on its own parse errors teaches that it is noise, and
    a gate read as noise is a gate that gets removed.
    """
    try:
        payload = json.loads(raw)
    except (ValueError, TypeError):
        return Decision(State.OPEN, "hook input did not parse; standing aside")
    if os.environ.get("WORK_ITEM_DOORMAN_OFF"):
        return Decision(State.OPEN, "doorman disabled by environment")
    return decide(payload.get("tool_name") or "", payload.get("tool_input") or {})
