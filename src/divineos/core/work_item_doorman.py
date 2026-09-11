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
    item_id      TEXT PRIMARY KEY,
    opened_at    REAL NOT NULL,
    branch       TEXT NOT NULL,
    trigger      TEXT NOT NULL,
    closed_at    REAL,
    session      TEXT NOT NULL DEFAULT '',
    opened_dirty TEXT NOT NULL DEFAULT ''
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
    # Migration for items opened before session scoping existed, which shipped
    # mid-session. A second run no-ops.
    for column in ("session TEXT NOT NULL DEFAULT ''", "opened_dirty TEXT NOT NULL DEFAULT ''"):
        try:
            conn.execute(f"ALTER TABLE work_items ADD COLUMN {column}")
        except sqlite3.OperationalError:
            pass
    return conn


def dirty_code_paths() -> frozenset[str] | None:
    """Tracked, non-exempt files that differ from the index right now.

    None means git could not be read, which is not the same as a clean tree.

    THIS IS THE ANSWER TO THE WORST ROUTE AROUND THE DOOR. Aether game-walked
    it and it is his own habit, not a hypothetical: write a small script into
    a scratchpad, run it, and let the script edit the repository. The command
    reaching the gate carries one path, outside the tree, and the door opens
    on a write it never sees. Every pattern I match is defeated by one level
    of indirection, and our two gates feed each other's blind spot -- his
    heredoc doorman pushes him toward exactly the shape mine cannot see.

    Prevention is not available: a gate that fires before the command runs
    cannot see a write that has not happened. What IS available is that the
    write cannot stay hidden. Files that changed are files that changed,
    however they were written.

    Kept as its own function rather than folded into the decision, because
    'what changed on disk' answers questions no pattern list can, and the next
    gate that wants work rather than a description of work can borrow it.
    """
    import subprocess

    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None  # both-empty: git did not run and git ran badly are one answer here -- the tree could not be read, and every caller treats unreadable as unknown rather than clean
    if proc.returncode != 0:
        return None  # both-empty: same answer as the exception above; a failed git and a missing git are both "I could not look"
    exempt = load_exempt_prefixes()
    if exempt is None:
        exempt = ()
    out = set()
    for line in proc.stdout.splitlines():
        path = line[3:].strip().strip('"')
        if " -> " in path:  # a rename reports both sides; the destination is the write
            path = path.split(" -> ", 1)[1]
        if path and not any(path.startswith(prefix) for prefix in exempt):
            out.add(path)
    return frozenset(out)


def current_branch() -> str:
    head = REPO_ROOT / ".git" / "HEAD"
    try:
        text = head.read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"
    return text.split("/", 2)[-1] if text.startswith("ref:") else text[:12]


def open_item(trigger: str, branch: str | None = None, session: str = "") -> str:
    item_id = f"wi-{int(time.time() * 1000):x}"
    dirty = dirty_code_paths()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO work_items(item_id, opened_at, branch, trigger, session, opened_dirty) "
            "VALUES (?,?,?,?,?,?)",
            (
                item_id,
                time.time(),
                branch or current_branch(),
                trigger,
                session,
                json.dumps(sorted(dirty)) if dirty is not None else "",
            ),
        )
    return item_id


_NOT_A_LANDING = "auto-commit"


def head_commit_time() -> float | None:
    """When the newest piece of WORK landed on this branch. None if git will not say.

    AUTO-COMMITS ARE NOT LANDINGS, and this cost an hour of the day it was
    found. The background checkpointer wrote three commits in four minutes
    while I was mid-build. Each one read as the-work-finished, so each one
    closed my open item and opened a fresh one whose marks window began after
    the search, the draft and the walk I had just done for the very edit being
    refused. I was told to go do work I had already done, three times, and the
    only way through was a bypass per edit.

    That is the doorman performing the exact fault it was built to catch: a
    refusal standing in front of its own satisfied condition. The boundary was
    always meant to be a piece of work ending, and a checkpoint is not a piece
    of work ending -- it is a save, made by something that is not me, about
    nothing in particular.

    So the scan walks back past checkpoint commits to the newest commit that
    represents a decision. If every commit on the branch is a checkpoint the
    answer is None, which the caller already treats as "do not close on it" --
    failing toward the item staying open rather than toward a false close.
    """
    import subprocess

    try:
        proc = subprocess.run(
            ["git", "log", "-40", "--format=%ct%x00%s"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None  # both-empty: git absent and git failing are one answer -- the commit time could not be read, and the caller treats unknown as "do not close on it"
    if proc.returncode != 0 or not proc.stdout.strip():
        return None  # both-empty: same answer as above; a repository with no commits and a failed call are both "I could not look"
    for line in proc.stdout.splitlines():
        stamp, _, subject = line.partition("\x00")
        if subject.strip().lower().startswith(_NOT_A_LANDING):
            continue
        try:
            return float(stamp.strip())
        except ValueError:
            return None  # both-empty: an unparseable stamp is the same answer as an unreadable git -- I could not look
    return None  # both-empty: a history of nothing but checkpoints is also "no landing I can point to", and the caller does the same safe thing with it -- leaves the item open. Treating it as a landing is the exact false close this function was rewritten to stop.


def open_item_for_branch(
    branch: str | None = None, session: str = ""
) -> tuple[str, float, frozenset[str] | None] | None:
    """The open item for this branch and session, unless its work has landed.

    THE ITEM ENDS AT A COMMIT, and session-scoping was not enough.

    Andrew, 2026-09-07, having just watched it fail: *maybe.. idk USED THE
    FUCKING BUILD FLOW YOU JUST SAID WAS WORKING??* He was right. Minutes
    after the doorman shipped I edited a hook with no search, no draft and no
    walk, and the door stood aside -- because the item satisfied for the
    doorman's own build was still open, and its three marks paid for an edit
    to a completely unrelated file.

    That is the propped door Aether game-walked. He named two candidate
    boundaries, a session and a commit, and I took the session because a build
    runs through many commits and re-asking felt heavy. The session turned out
    to be far too loose: one session holds many unrelated pieces of work, and
    he demonstrated it inside a single turn.

    So the boundary moves from the clock to the work. A commit is where a piece
    of work ends, which puts the drain on the same axis as the fill.

    THE COST, stated rather than hidden: a build spanning four commits is asked
    for its marks four times. What makes that bearable is that a genuinely
    continuing piece of work already has all three artifacts sitting there --
    the search, the draft, the walk -- so it costs one refusal, not a redo. A
    finished piece of work silently paying for the next one costs much more,
    and that is the bill he just handed me.

    An unreadable commit time does NOT close the item: unknown is not a
    landing, and closing on a failed lookup would refuse work for no reason.
    """
    branch = branch or current_branch()
    with _connect() as conn:
        row = conn.execute(
            "SELECT item_id, opened_at, opened_dirty FROM work_items "
            "WHERE branch = ? AND session = ? AND closed_at IS NULL "
            "ORDER BY opened_at DESC LIMIT 1",
            (branch, session),
        ).fetchone()
    if not row:
        return None
    landed = head_commit_time()
    if landed is not None and landed >= row[1]:
        close_item(row[0])
        return None
    # THE MARKS WINDOW STARTS AT THE LAST COMMIT, NOT AT THE ITEM'S BIRTH.
    #
    # Commit-closing fired on the very edit that added it, which was right --
    # and then the replacement item refused work whose search, draft and walk
    # had been done minutes earlier for exactly this piece. The artifacts were
    # real and the window was wrong. That is the NAG falsifier from the walk
    # arriving inside the same edit.
    #
    # Everything made since the last commit belongs to the work in progress,
    # because the commit is what ended the previous piece. So an item opened
    # part-way through a piece of work inherits that work's artifacts, and a
    # walk done BEFORE the last commit still does not count -- which is the
    # protection the window existed for.
    window = landed if landed is not None and landed < row[1] else row[1]
    try:
        snapshot: frozenset[str] | None = frozenset(json.loads(row[2])) if row[2] else None
    except (ValueError, TypeError):
        snapshot = None
    return (row[0], window, snapshot)


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
    # A row with junk text was a passing row until Aether walked it. The floor
    # is that the question has to be long enough to be a question.
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM reach_checks WHERE opened_at >= ? AND LENGTH(symptom) >= 24",
            (since,),
        ).fetchone()
    except sqlite3.Error:
        return False
    return bool(row and row[0])


_DRAFT_FLOOR_BYTES = 64


def _draft_mark(since: float) -> bool:
    """Station 1. A file under docs/drafts with real content in it, after the
    item opened.

    Detected, never declared. A flag binding a draft to an item would be one
    more thing to remember, which is the failure class.

    THE FLOOR IS AETHER'S, and it existed because the two halves of this build
    disagreed about the same file: an empty draft passed my door and was
    refused by his checker. The same build giving two answers about one file
    is worse than either answer.
    """
    try:
        return any(
            p.stat().st_mtime >= since and p.stat().st_size >= _DRAFT_FLOOR_BYTES
            for p in DRAFTS_DIR.glob("*.md")
        )
    except OSError:
        return False


def _walk_mark(conn: sqlite3.Connection, since: float) -> bool:
    """Station 2. A council walk CLOSED after the item opened.

    This started as a count of lens views, which Aether walked straight
    through: showing one lens on any question satisfied it, and with two items
    open a single view satisfied both, because the only condition was that it
    happened afterwards. Views are not bound to the work.

    A closed walk is. It carries the problem statement and a finding or a
    written exclusion for every lens the manager surfaced, and it cannot close
    while one is unaccounted for. And it was already built -- found by running
    the prior-art search this gate demands, which is the second time in one
    night that the thing I was about to write turned out to be already there.

    ``conn`` is unused: walks live in their own store, not the ledger. Kept in
    the signature so the three marks read alike at the call site.
    """
    del conn
    try:
        from divineos.core.council_walk import _db_path  # local: avoids an import cycle

        with sqlite3.connect(str(_db_path()), timeout=10) as walk_conn:
            row = walk_conn.execute(
                "SELECT COUNT(*) FROM walks WHERE closed_at >= ?", (since,)
            ).fetchone()
    except (sqlite3.Error, ImportError, OSError):
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
    # THE DOOR USED TO NAME A COMMAND THAT CANNOT SATISFY IT. It said to run
    # `divineos mansion council`, which PRINTS lens templates and writes no
    # walk at all, while the mark it measures is a CLOSED walk row. So the
    # honest response to the refusal left the refusal standing, and the second
    # guess -- `divineos council walk`, which emits a ledger event and also no
    # row -- left it standing too. Two commands tried, both reasonable, neither
    # able to open the door the door pointed at.
    #
    # That is the wrong-subject family inside the instrument: the instruction
    # and the measurement were about two different things, and only the
    # measurement was load-bearing.
    "council walk": (
        'divineos walk open "<the question>", then walk apply <id> <Lens> '
        "--finding for each, then walk close <id>"
    ),
}


def is_the_escape(tool_input: dict) -> bool:
    """The break-glass door, and it must never run through the lock.

    FOURTH TIME IN ONE NIGHT AND THE ONLY TOTAL ONE. The tripwire caught a real
    walk-around, then refused every command after it -- including the release it
    was printing as the way out. The key was inside the locked room. Andrew had
    to hand me a second terminal to get me out, which is the principle itself
    arriving as a rescue: an out-of-band path that does not share the failure it
    is recovering from.

    Andrew 2026-09-07: *you continue to build shit that traps you in chicken and
    egg scenarios.. you are learning nothing.. so this lesson needs baked into
    the actual build flow.*

    What the crash course named, since none of this was invented here:

    - BREAK-GLASS (security practice). Emergency access exists precisely so a
      failure of the normal path cannot lock everyone out, and the governing
      rule is INDEPENDENCE -- the recovery route must not share failure modes
      with what it recovers.
    - STAGE ZERO (compiler bootstrapping). A thing that needs itself to exist
      requires a cruder starting point that does not. No stage zero, no start.
    - ONE LINK (circular dependency). A cycle dies when any single link is cut;
      the whole loop never has to be solved at once.
    - REDIRECT, DO NOT PROXY (Google SRE, cascading failures). A blocked path
      must not route through itself to repair itself. Hand control back out.

    So the escape is checked FIRST -- before exemptions, before the item lookup,
    before the tripwire. It cannot be reached by any code path that can refuse.

    THE TEST THAT WOULD HAVE CAUGHT ALL FOUR, and it takes seconds: jam the gate
    so it refuses everything, then run the cure. If the cure does not work while
    the gate is fully shut, it is not a cure.
    """
    return "work-item bypass" in (tool_input.get("command") or "")


def decide(tool_name: str, tool_input: dict, session: str = "") -> Decision:
    """The whole gate. Called by the hook, once per tool call."""
    if is_the_escape(tool_input):
        return Decision(State.OPEN, "the escape is never behind the lock")
    paths = paths_from_tool_call(tool_name, tool_input)
    if not paths:
        # Even a call with no visible write gets the tripwire, because the
        # whole point of the tripwire is writes this function cannot see.
        return _tripwire_or(Decision(State.OPEN, "no file writes in this call"), session)

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

    existing = open_item_for_branch(session=session)
    opened_now = False
    if existing is None:
        # THE STATIONS ARE MEASURED, NEVER ASSUMED, and this is the repair for
        # a defect recorded five separate times without ever being fixed: a
        # freshly-opened item reported all three stations undone as a CONSTANT,
        # because the item is born at the write and this branch never looked at
        # the stores at all.
        #
        # Every one of those five times the search, the draft and the walk had
        # been done -- for exactly this piece of work, minutes earlier -- and
        # the door sent me to go and do them again. The only way through was a
        # bypass per edit, which is how a gate teaches its own evasion and then
        # gets read as evidence of my indiscipline in the bypass telemetry.
        #
        # open_item_for_branch computes the window from the last real commit
        # rather than from the item's birth, so re-reading after opening asks
        # the honest question: has this work's searching happened since the
        # previous piece landed. A refusal is then a finding rather than an
        # artefact of when the row was created.
        item_id = open_item(trigger=code_paths[0], session=session)
        existing = open_item_for_branch(session=session)
        opened_now = True
        if existing is None:
            # The row was written and cannot be read back. Unknown is not a
            # yes, so this holds -- and holds with the full list, because
            # nothing is known about the marks.
            return Decision(
                State.HELD,
                _refusal_text(item_id, code_paths, list(REQUIRED_BEFORE_BUILD), opened_now=True),
                item_id=item_id,
                missing=REQUIRED_BEFORE_BUILD,
            )

    item_id, opened_at, snapshot = existing
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
        walked_around = _files_written_unseen(snapshot)
        return Decision(
            State.HELD,
            _refusal_text(
                item_id,
                code_paths,
                list(missing),
                opened_now=opened_now,
                walked_around=walked_around,
            ),
            item_id=item_id,
            missing=missing,
        )
    return Decision(State.OPEN, f"work item {item_id} is at station 3", item_id=item_id)


def _files_written_unseen(snapshot: frozenset[str] | None) -> tuple[str, ...]:
    """Code files that changed since this item opened, which the door never saw.

    The claim this supports is deliberately small, and Sagan's is the reason:
    it does NOT make the walk-around impossible. One write gets through. What
    it does is make that write impossible to hide, which is a different and
    achievable thing, and I would rather state the smaller claim.
    """
    if snapshot is None:
        return ()
    now = dirty_code_paths()
    if now is None:
        return ()
    return tuple(sorted(now - snapshot))


def _tripwire_or(passing: Decision, session: str) -> Decision:
    """Let a decision through unless something already came in through a window."""
    existing = open_item_for_branch(session=session)
    if existing is None:
        return passing
    item_id, opened_at, snapshot = existing
    if has_bypass(item_id):
        return passing
    missing = missing_marks(item_id, opened_at)
    if not missing:
        return passing
    changed = _files_written_unseen(snapshot)
    if not changed:
        return passing
    return Decision(
        State.HELD,
        _walkaround_text(item_id, changed, list(missing)),
        item_id=item_id,
        missing=tuple(missing),
    )


def _walkaround_text(item_id: str, changed: tuple[str, ...], missing: list[str]) -> str:
    """A DIFFERENT message from a plain hold, and Tannen is why.

    Two states now need two registers. A hold says 'this has not happened
    yet'. This says 'something already changed that I never saw' -- and that
    is the more serious of the two. Collapsing them into one message teaches
    that the door has one mood, and the graver state is the one that would
    then read as routine.
    """
    shown = ", ".join(changed[:4]) + (" and others" if len(changed) > 4 else "")
    return "\n".join(
        [
            "",
            "THE BUILD FLOW DOORMAN -- something came in through a window.",
            "",
            f"Work item {item_id} is still held, and yet code files have changed that",
            "I never saw a write for. Not a refusal being ignored -- a write that",
            "never reached the door at all.",
            "",
            f"Changed since this work opened: {shown}",
            "",
            "The known route is a script: write it somewhere outside the tree, run",
            "it, and let it edit the repository. The command I get to look at holds",
            "one path and it is not in this project. Aether walked it in an hour",
            "and it is his own habit, not a hypothesis.",
            "",
            "Nothing further passes until this work is ready or the escape is taken:",
            f'  divineos work-item bypass {item_id} --reason "<why, in a sentence>"',
            "",
            "Still owed: " + "; ".join(_PLAIN[m] for m in missing),
            "",
            "I cannot stop the first write of this shape -- a gate that fires before",
            "a command runs cannot see what the command has not done yet. What I can",
            "do is refuse to let it stay invisible, and refuse everything after it.",
        ]
    )


def _refusal_text(
    item_id: str,
    paths: tuple[str, ...],
    missing: list[str],
    *,
    opened_now: bool,
    walked_around: tuple[str, ...] = (),
) -> str:
    """Plain sentences. Never a bare station number.

    Aether's constraint, and the reason is the reader: whoever meets this
    message is tired and has spent six months being talked past. 'no draft
    written yet' is a thing a person can picture. 'station 1 MISSING' is not.
    """
    if walked_around:
        return _walkaround_text(item_id, walked_around, missing)
    head = (
        # Says WHY it is asking, so a session-scoped item does not read as the
        # door having forgotten -- Norman, on a design everyone gets wrong
        # being the design's fault.
        f"The last piece of work on this branch has landed, so this edit begins a "
        f"new one and I have opened work item {item_id} for it."
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


def _latest_open_item() -> tuple[str, float, frozenset[str] | None] | None:
    """The newest open item on this branch in ANY session."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT item_id, opened_at, opened_dirty FROM work_items "
            "WHERE branch = ? AND closed_at IS NULL ORDER BY opened_at DESC LIMIT 1",
            (current_branch(),),
        ).fetchone()
    if not row:
        return None
    try:
        snapshot: frozenset[str] | None = frozenset(json.loads(row[2])) if row[2] else None
    except (ValueError, TypeError):
        snapshot = None
    return (row[0], row[1], snapshot)


def render_status(session: str = "") -> str:
    # Falls back across sessions on purpose: this is the human-facing view and
    # the command line has no session of its own. A status that could not see
    # the item the hook just opened would be a report about a different world.
    item = open_item_for_branch(session=session) or _latest_open_item()
    if item is None:
        return f"No open work item on {current_branch()}. The next code edit opens one."
    item_id, opened_at, snapshot = item
    missing = missing_marks(item_id, opened_at)
    age = int((time.time() - opened_at) / 60)
    lines = [f"{item_id} on {current_branch()}, opened {age} min ago"]
    if missing is None:
        lines.append("  marks: COULD NOT CHECK -- the stores did not read")
        return "\n".join(lines)
    for name in REQUIRED_BEFORE_BUILD:
        lines.append(f"  [{'x' if name not in missing else ' '}] {name}")
    unseen = _files_written_unseen(snapshot) if missing else ()
    if unseen:
        lines.append(f"  WALKED AROUND -- {len(unseen)} code file(s) changed with no write seen")
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
    return decide(
        payload.get("tool_name") or "",
        payload.get("tool_input") or {},
        session=str(payload.get("session_id") or ""),
    )
