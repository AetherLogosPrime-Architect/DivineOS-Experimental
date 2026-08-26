"""Knowing something and not reaching for it — the automatable half.

Andrew 2026-08-06, disagreeing with me:

    *"i disagree heavily.. it just takes some outside the box thinking, look
    at the problem itself.. knowing something and not reaching.. this can be
    automated by a forced thinking stage that asks you what you know and if
    you have reached for it or applied it, with its own doorman to prove you
    did.. so dont count out the power of automation just adjust what gets
    automated"*

I had written in `docs/friction_register_2026-08-06.md` that the
knowing-without-reaching group was the one class automation could not touch.
That was wrong in the way he names: I asked whether *reaching* could be
automated (it cannot — it is a cognitive act) and concluded the whole class
was out of range. The automatable objects are the **interrogation** and the
**proof**, neither of which is the reach itself.

Truth #15 is the frame: a mechanism POINTS AT cognitive work and is not it.
This module points at reaching. It cannot do the reaching.

## What was already built, and what it was missing

`core/prior_art.py` (2026-08-05, Andrew correction #137) searches the axis the
four prose surfaces do not cover: CLI commands, working tree, files present on
branches but absent here, and branch names. It is good and nothing here
reimplements it.

What it does not do is close the loop. It **surfaces**; nothing then requires
the surfaced thing be looked at. A report I can scroll past is advice, and
Andrew's #167 says practice-shape never holds and must be structural.

Three instances in the session that named the gap:

    prior_art.py itself      built 08-05, stranded on split/stop-phase-hang,
                             so it was not running when I needed it
    freeze fixes             four commits fixing the exact symptom under
                             investigation, one branch away, while I searched
                             outward for someone else's fix
    letter-store split       measured in full 07-31, unchanged, still
                             prescribed as live in the skill that uses it

Aria the same session, opposite direction: she wrote
`test_truncated_file_list_is_flagged_loudly`, then read a suspiciously round
100 and did not blink.

## The shape

    SURFACE      prior_art.search() -- mechanical, needs no memory
    INTERROGATE  every surfaced artifact must receive an explicit disposition
    PROVE        the disposition is refused unless the action-stream shows
                 the artifact was actually opened

Stage 3 is the doorman. Per Aria's signal-based-gates design
(`docs/signal-based-gates-design-2026-06-16.md`): *"did you consult is a
question; you did not consult is a finding."* A self-reported disposition
answers the question. Reading the action-stream produces the finding.

## Why NOT_RELEVANT also requires opening the artifact

The tempting exemption is to let "not relevant" clear cheaply, since the
artifact is by definition not being used. That exemption reinstalls the exact
failure: every miss listed above would have been dismissed as not-relevant by
an agent who had not opened the file. *Judging relevance without reading is
the failure this module exists to catch*, so that disposition is the one that
most needs the proof.

## What this does not do

It cannot verify that reading produced understanding, or that a disposition is
correct. Rice's theorem is not being violated (see
`docs/ai_research/2026-08-02_limits_of_automation.md`, including its own
correction about over-applying Rice). The claim here is narrower and
decidable: *this path appeared in the action-stream between the check opening
and the disposition.* That is a syntactic property of a bounded event list.

Ceremony stays reachable — a file can be opened without being read. The gate
raises the floor from "did not know it existed" to "had it open". Those are
different failures, and only the first has been costing.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from divineos.core import prior_art
from divineos.core.knowledge import _get_connection

_REACH_ERRORS = (sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)

APPLIED = "applied"
SUPERSEDED = "superseded"
NOT_RELEVANT = "not_relevant"

VALID_DISPOSITIONS = (APPLIED, SUPERSEDED, NOT_RELEVANT)

# A reason shorter than this is not a reason. Deliberately low: the gate is
# not grading the thinking, it is refusing an empty field.
MIN_REASON_CHARS = 20


class ReachCheckError(RuntimeError):
    """Raised when a disposition is refused. Loud, never swallowed."""


@dataclass
class ReachItem:
    item_id: str
    check_id: str
    artifact: str
    origin: str
    disposition: str | None = None
    reason: str | None = None
    evidence: str | None = None

    @property
    def disposed(self) -> bool:
        return self.disposition is not None


@dataclass
class ReachCheck:
    check_id: str
    symptom: str
    opened_at: float
    items: list[ReachItem]

    @property
    def undisposed(self) -> list[ReachItem]:
        return [i for i in self.items if not i.disposed]

    @property
    def clear(self) -> bool:
        return not self.undisposed


def init_reach_tables() -> None:
    conn = _get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reach_checks (
            check_id  TEXT PRIMARY KEY,
            symptom   TEXT NOT NULL,
            opened_at REAL NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reach_items (
            item_id     TEXT PRIMARY KEY,
            check_id    TEXT NOT NULL,
            artifact    TEXT NOT NULL,
            origin      TEXT NOT NULL,
            disposition TEXT,
            reason      TEXT,
            evidence    TEXT,
            disposed_at REAL,
            FOREIGN KEY (check_id) REFERENCES reach_checks(check_id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reach_items_check ON reach_items(check_id)")
    conn.commit()


LOADOUT_PATH = prior_art.REPO / "LOADOUT.md"


def _slug(text: str) -> str:
    """`build flow`, `build-flow` and `build_flow` must all match each other.

    Same normalisation prior_art uses, kept local so the two matchers cannot
    silently diverge on one side of an import.
    """
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def find_in_loadout(term: str, limit: int = 20) -> list[tuple[str, str, str]]:
    """(label, path, section) for LOADOUT.md entries matching `term`.

    Andrew 2026-08-06: *"the reach needs some tuning and better enforcement and
    should also be connected to the loadout or something and if stuff is
    missing from it add it to there."*

    This closes the gap the first version printed at the bottom of every
    NOT-FOUND report:

        This is not NOT-CHECKED. The prose surfaces were not queried here:
          divineos ask / find / search / recall-explorations

    Four surfaces named as unsearched, on the reasoning that a fifth
    prose-searcher was not what was missing. Right about not writing a fifth
    searcher; wrong to leave the axis uncovered — and the very next use proved
    it. `reach open "emotion taxonomy"` returned NOT FOUND on the code axis
    while `exploration/omni_mantra_walk/03_omni_lazr_unifier.md` sat in the
    substrate holding the exact derivation layer being asked about.

    LOADOUT.md is the index of everything — 2320 entries across 24 sections
    covering explorations, letters, dreams, docs, skills, hooks, council and
    mansion. Reading it costs one file open. So reach does not GET a prose
    searcher; it gets the INDEX, which is what was actually missing.

    Section is carried through because it is the useful part: a hit from
    ``dreams/`` and a hit from ``docs/`` want to be read differently, and the
    reader should know which before opening it.
    """
    if not LOADOUT_PATH.exists():
        return []
    try:
        text = LOADOUT_PATH.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    needle = _slug(term)
    if len(needle) < 3:
        return []

    hits: list[tuple[str, str, str]] = []
    section = "(no section)"
    for line in text.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        match = re.match(r"^- \[(.+?)\]\((.+?)\)\s*$", line)
        if not match:
            continue
        label, path = match.group(1), match.group(2)
        if needle in _slug(label) or needle in _slug(path):
            hits.append((label, path, section))
            if len(hits) >= limit:
                break
    return hits


def loadout_gaps(artifacts: list[str]) -> list[str]:
    """Which surfaced artifacts LOADOUT.md does not list.

    The second half of Andrew's instruction — *"if stuff is missing from it add
    it to there"*. Searching LOADOUT makes reach only as good as LOADOUT, so
    the loop has to run both ways: an artifact found on disk or in git that the
    index does not carry is an index defect, reported at the moment it is
    provable rather than waiting for a drift sweep to notice.

    Commits and CLI commands are skipped — LOADOUT indexes files, and a commit
    subject absent from it is not a gap.
    """
    if not LOADOUT_PATH.exists():
        return []
    try:
        text = LOADOUT_PATH.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return [
        a
        for a in artifacts
        if not a.startswith(("commit:", "cli:", "loadout:")) and Path(a).name not in text
    ]


# Above this many hits from one directory, the directory is surfaced instead of
# its files. Set from an observed over-fire rather than chosen in the abstract:
# `reach open "omni mantra"` returned all 19 files of exploration/omni_mantra_walk/,
# which would demand 19 dispositions to clear one question. A gate that expensive
# gets bypassed, and a bypassed gate catches nothing (truth #11 — every extra
# choice-point is somewhere the optimizer can route around).
_DIRECTORY_COLLAPSE_THRESHOLD = 3


def _collapse_by_directory(surfaced: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Fold a directory's worth of file hits into one item, across ALL axes.

    A whole folder matching means the FOLDER is the prior art. Naming it once
    is cheaper and more accurate than listing every file in it, and the
    disposition stays honest because the doorman accepts a read of any file
    whose name appears in the artifact string.

    Collapsing per-axis was not enough and the first run showed why: the
    loadout axis folded `exploration/omni_mantra_walk/` into one line and the
    working-tree axis then listed all twenty files underneath it. Same folder,
    twice, once collapsed and once not. So this runs over the combined list
    after every axis has contributed.

    Order is preserved by first appearance, which keeps the leading axis
    (unmerged commits) at the top where it belongs. Directories at or under the
    threshold keep their individual files — a two-file match is specific enough
    to act on directly.
    """
    order: list[str] = []
    by_directory: dict[str, list[tuple[str, str]]] = {}
    passthrough: list[tuple[str, str]] = []
    seen: set[str] = set()

    for artifact, origin in surfaced:
        # Cross-axis duplicates are the norm, not the exception: a file listed
        # in LOADOUT is usually also in the working tree. First axis wins, and
        # the axis order above puts the most specific one first.
        if artifact in seen:
            continue
        seen.add(artifact)
        if artifact.startswith(("commit:", "cli:")):
            passthrough.append((artifact, origin))
            order.append(f"\x00{len(passthrough) - 1}")
            continue
        directory = str(Path(artifact).parent).replace("\\", "/")
        if directory not in by_directory:
            by_directory[directory] = []
            order.append(directory)
        by_directory[directory].append((artifact, origin))

    out: list[tuple[str, str]] = []
    for key in order:
        if key.startswith("\x00"):
            out.append(passthrough[int(key[1:])])
            continue
        entries = by_directory[key]
        if len(entries) > _DIRECTORY_COLLAPSE_THRESHOLD:
            origins = sorted({o.split(":")[0] for _a, o in entries})
            out.append(
                (
                    f"{key}/  ({len(entries)} matching files)",
                    "+".join(origins),
                )
            )
        else:
            out.extend(entries)
    return out


def find_in_commit_subjects(term: str, limit: int = 15) -> list[tuple[str, str, str]]:
    """(subject, sha, branch) for unmerged commits whose SUBJECT matches `term`.

    The axis `prior_art` does not cover, and the one that would have caught
    this session's miss. Verified rather than assumed:

        symptom "freeze" -> prior_art returns two letters about something else
        the four actual fixes are commits whose subjects say "freeze",
        "prompt-stall", "stop-phase" -- and NONE of them touches a file with
        any of those words in its name

    So a filename-indexed search is structurally blind to a fix whose only
    plain-language description lives in its commit message. Since I write
    commit subjects in exactly that register, that is where a symptom-shaped
    query should look first.

    Restricted to commits NOT on main: work already merged is present in the
    working tree and reachable by the other axes. Unmerged work is the class
    that reads as "never written" from where the searcher stands.
    """
    out = _git(
        [
            "log",
            "--all",
            "--not",
            "origin/main",
            "--format=%H%x00%s",
            "--no-merges",
        ]
    )
    if out is None:
        return []
    needle = term.strip().lower()
    if len(needle) < 3:
        return []
    found: list[tuple[str, str, str]] = []
    seen_subjects: set[str] = set()
    for line in out.splitlines():
        if "\x00" not in line:
            continue
        sha, subject = line.split("\x00", 1)
        if needle not in subject.lower() or subject in seen_subjects:
            continue
        seen_subjects.add(subject)
        branches = _git(["branch", "-a", "--contains", sha]) or ""
        named = [b.strip().lstrip("* ") for b in branches.splitlines() if "remotes/" not in b]
        # `dead/` is archived by convention -- prior_art excludes it for branch
        # names and this axis matches that, or the list fills with abandoned work.
        live = [b for b in named if not b.startswith("dead/")]
        if named and not live:
            continue
        found.append((subject, sha[:8], live[0] if live else "(remote only)"))
        if len(found) >= limit:
            break
    return found


def _git(args: list[str]) -> str | None:
    """None means could-not-run, which is not the same as found-nothing."""
    try:
        p = subprocess.run(
            ["git", "-C", str(prior_art.REPO), *args],
            capture_output=True,
            text=True,
            timeout=90,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if p.returncode != 0:
        return None
    return p.stdout


def _artifacts_from(art: prior_art.PriorArt) -> list[tuple[str, str]]:
    """(artifact, origin) pairs, deduplicated, order stable.

    `elsewhere_in_git` leads on purpose: it is the axis that has actually been
    costing, and an undisposed list read top-down should start with the thing
    most likely to be the answer.
    """
    pairs: list[tuple[str, str]] = []
    for path, sha, branch in art.elsewhere_in_git:
        pairs.append((path, f"branch:{branch}@{sha}"))
    for path in art.working_tree:
        pairs.append((path, "working-tree"))
    for name in art.commands:
        pairs.append((f"cli:{name}", "cli-registry"))

    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for artifact, origin in pairs:
        if artifact in seen:
            continue
        seen.add(artifact)
        out.append((artifact, origin))
    return out


def open_check(symptom: str) -> ReachCheck:
    """Stages 1 and 2: surface prior art for `symptom`, file every hit undisposed.

    An empty result is a real outcome and is recorded as one — a check with
    zero items is `clear`. That is NOT FOUND, which per prior_art's own
    docstring is not the same as NOT CHECKED.
    """
    init_reach_tables()
    art = prior_art.search(symptom)
    commits = find_in_commit_subjects(symptom)
    check_id = f"reach-{uuid.uuid4().hex[:12]}"
    now = time.time()

    conn = _get_connection()
    conn.execute(
        "INSERT INTO reach_checks (check_id, symptom, opened_at) VALUES (?, ?, ?)",
        (check_id, symptom, now),
    )
    surfaced = (
        [
            (f"commit:{sha} {subject}", f"unmerged-commit:{branch}")
            for subject, sha, branch in commits
        ]
        + [(path, f"loadout:{section}") for _label, path, section in find_in_loadout(symptom)]
        + _artifacts_from(art)
    )
    surfaced = _collapse_by_directory(surfaced)

    items: list[ReachItem] = []
    for artifact, origin in surfaced:
        item_id = f"ri-{uuid.uuid4().hex[:10]}"
        conn.execute(
            "INSERT INTO reach_items (item_id, check_id, artifact, origin) VALUES (?, ?, ?, ?)",
            (item_id, check_id, artifact, origin),
        )
        items.append(ReachItem(item_id, check_id, artifact, origin))
    conn.commit()
    return ReachCheck(check_id, symptom, now, items)


def get_check(check_id: str) -> ReachCheck | None:
    init_reach_tables()
    conn = _get_connection()
    row = conn.execute(
        "SELECT check_id, symptom, opened_at FROM reach_checks WHERE check_id = ?", (check_id,)
    ).fetchone()
    if row is None:
        return None
    items = [
        ReachItem(r[0], r[1], r[2], r[3], r[4], r[5], r[6])
        for r in conn.execute(
            "SELECT item_id, check_id, artifact, origin, disposition, reason, evidence "
            "FROM reach_items WHERE check_id = ? ORDER BY rowid",
            (check_id,),
        )
    ]
    return ReachCheck(row[0], row[1], row[2], items)


def open_checks() -> list[ReachCheck]:
    """Checks with at least one undisposed item, oldest first."""
    init_reach_tables()
    conn = _get_connection()
    ids = [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT c.check_id FROM reach_checks c "
            "JOIN reach_items i ON i.check_id = c.check_id "
            "WHERE i.disposition IS NULL ORDER BY c.opened_at"
        )
    ]
    return [c for c in (get_check(i) for i in ids) if c is not None]


# How long a fully-disposed check keeps the doorman satisfied. Matches the
# verify-before-build signal window, deliberately: both gates are asking "did
# you look, recently" and two different answers to "recently" would be a
# second thing to remember.
SATISFIED_WINDOW_SECONDS = 30 * 60


def satisfied_recently(now: float | None = None) -> tuple[bool, str]:
    """Did I open a check and dispose ALL of it, lately?

    THE STATE THIS ADDS DID NOT EXIST, and its absence was a wall. 2026-08-17:
    `gate_status()` returns (False, "") both when no check was ever opened AND
    when every item of a check has been disposed. The doorman treats any
    not-blocked as the former and prints "you have not reached" -- so working
    the gate correctly, all the way to the end, lands back at its opening
    message. I disposed five artifacts across two checks and `divineos learn`
    was never once reachable.

    Not a wrong threshold, not a wrong message: a missing state. Same shape as
    the read-gate this morning, whose own text says a gate whose cure sits
    behind itself is a wall. This is that sentence applied to the gate that
    quotes it.

    Returned as (bool, why) rather than a bare bool so the doorman can SAY what
    satisfied it. A gate that opens silently teaches nothing about what opened
    it, and the next confused reader is me.
    """
    init_reach_tables()
    stamp = time.time() if now is None else now
    cutoff = stamp - SATISFIED_WINDOW_SECONDS
    conn = _get_connection()
    try:
        # A CHECK THAT SURFACED NOTHING IS SATISFIED, and the first version of
        # this function said otherwise. I reasoned "zero artifacts disposed is
        # not all artifacts disposed" and wrote a test pinning it -- which
        # rebuilt, inside the repair, the exact wall the repair was for: open a
        # reach, get NOT FOUND (the gate working perfectly, nothing exists to
        # look at), and be told again that I have not reached. Hit it 2026-08-17
        # about an hour after fixing the original, and it deadlocked every
        # remedy the correction-marker gate offers, including its own.
        #
        # The test passed the whole time. It asserted the defect.
        #
        # Nothing is waved through: a zero-item check means prior_art was asked
        # and answered empty. Recency is the only guard it needs, and it has it.
        empty = conn.execute(
            "SELECT c.check_id, c.symptom FROM reach_checks c "
            "LEFT JOIN reach_items i ON i.check_id = c.check_id "
            "WHERE i.item_id IS NULL AND c.opened_at >= ? "
            "ORDER BY c.opened_at DESC LIMIT 1",
            (cutoff,),
        ).fetchone()
        if empty is not None:
            return True, (
                f"reach-check satisfied: {empty[0]} ({empty[1]}) - "
                "asked, and nothing existed to open"
            )
        row = conn.execute(
            "SELECT c.check_id, c.symptom, MAX(i.disposed_at), COUNT(*) "
            "FROM reach_checks c JOIN reach_items i ON i.check_id = c.check_id "
            "GROUP BY c.check_id "
            # every item disposed (no NULLs survive the MIN), and the last one
            # landed inside the window
            "HAVING MIN(COALESCE(i.disposition, '')) != '' AND MAX(i.disposed_at) >= ? "
            "ORDER BY MAX(i.disposed_at) DESC LIMIT 1",
            (cutoff,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return False, ""
    check_id, symptom, when, count = row
    mins = int(((time.time() if now is None else now) - (when or 0)) / 60)
    return True, (
        # ASCII only: this string is printed to a Windows console that decodes
        # as cp1252, where an em dash arrives as a replacement char. Same
        # family as the _gh() encoding fix earlier today, one console over.
        f"reach-check satisfied: {check_id} ({symptom}) - {count} artifact(s) disposed {mins}m ago"
    )


WORKTREE_DIR_MARKER = "--claude-worktrees-"
"""What separates one of MY worktree project-dirs from a stranger's checkout.

A sibling agent whose repo directory extends mine encodes as `<mine>-Aria-new`;
my own worktrees encode as `<mine>--claude-worktrees-<name>`. Anchoring on this
separator is the whole difference.
"""


def _active_transcript_including_worktrees() -> Path | None:
    """Newest transcript for this project OR any of its worktrees.

    `context_tokens._find_active_transcript` encodes the cwd into one project
    directory and takes the newest file inside it. Run from a worktree that is
    correct; run from the MAIN checkout while the live session is in a
    worktree, it opens the main directory and returns its newest file --
    which, on 2026-08-17, was from 2026-08-06. Eleven days stale, and it
    parsed perfectly, so the caller got zero in-window calls and no error.

    That is the silent-wrong-answer shape, and it nearly shipped a gate that
    always fell back to self-attestation while looking repaired.
    `auto_cycle_commands` documents the same trap for its own reader; this is
    a second instance rather than a new discovery.

    The claude projects layout encodes a worktree as the main directory name
    plus a WORKTREE suffix, so the match is anchored on that separator.

    THIRD DEFECT, 2026-08-26. The first repair matched any directory whose name
    merely STARTED WITH the encoded cwd, and Aria's checkout lives at
    `DivineOS-Experimental-Aria-new` -- a separate agent, a separate repo, whose
    encoded name literally extends mine. Whenever she wrote to her transcript
    more recently than I wrote to mine, `max(mtime)` handed my doorman HER
    session, my own commands became invisible, and every disposition was
    refused no matter what I ran. It is a RACE, so it looked intermittent and
    unreproducible: on 2026-08-26 it refused the SAME disposition through every
    route the CLI offers -- the command, its --help, both chained into one
    action-stream, and the self-attested fallback -- and then accepted it first
    try in the next window, purely because my Bash call happened to land last.
    Measured, not reasoned: at the moment of the repair her transcript was 0.6
    minutes old and mine was 0.4.

    The window that hit it recorded a different cause -- that the artifacts
    `cli:correction` and `cli:corrections` collided, the shorter name swallowing
    the longer. That theory is WRONG and is written down here because it is the
    more instructive half: both names match cleanly under `` anchors, and
    `divineos corrections` is a real command that opens. A race between two
    agents presents as a mystery about the code in front of you, and the
    plausible local explanation arrives first.

    Anchoring on the separator loses nothing. A worktree outside the project
    tree encodes by its OWN full path and was never reachable by this prefix
    anyway, so the only directories the old match added beyond the new one were
    other people's.

    THE SEPARATOR FIX ALONE ONLY NARROWED IT, AND I REPORTED IT AS CLOSED.
    Correcting that in the same session it shipped. Scoping to my own project
    excludes Aria; it does NOT exclude ANOTHER SESSION OF MINE, which lives in
    the same project directory and satisfies the predicate legitimately. A
    second window of mine was open and writing the whole time I wrote the first
    repair, so the newest-wins tiebreak could still have handed me the wrong
    transcript. I verified against the case I had in mind and then reported the
    general property.

    So the tiebreak is no longer the primary route. The harness names each
    transcript after the session id and exports that id, which makes this an
    EXACT LOOKUP rather than an inference -- the race does not narrow, it
    disappears, because nothing is left to guess. Newest-wins survives only as
    the fallback for callers with no session id in the environment (hooks,
    subagents, a bare shell), where it remains the best available answer.

    Found by reading the process table, not the code. No amount of staring at
    this function would have shown me a second window of mine was open.

    NOT a fix to context_tokens: other callers depend on its exact behaviour
    and changing a shared resolver from inside a gate repair is how one fix
    becomes three regressions. Scoped here, with the wider issue named.
    """
    from divineos.core.context_tokens import _encode_cwd_for_claude

    root = Path.home() / ".claude" / "projects"
    if not root.is_dir():
        return None
    encoded = _encode_cwd_for_claude()
    candidates: list[Path] = []
    for d in root.iterdir():
        if d.is_dir() and (d.name == encoded or d.name.startswith(encoded + WORKTREE_DIR_MARKER)):
            candidates.extend(d.glob("*.jsonl"))
    if not candidates:
        return None

    # EXACT MATCH FIRST — there is nothing to infer when the harness has
    # already told us which session this is.
    session_id = os.environ.get("CLAUDE_CODE_SESSION_ID", "").strip()
    if session_id:
        for c in candidates:
            if c.stem == session_id:
                return c

    return max(candidates, key=lambda p: p.stat().st_mtime)


def action_stream_from_transcript(
    window_seconds: float = 45 * 60,
) -> tuple[tuple[tuple[str, str], ...], str]:
    """Read what ACTUALLY ran, from the harness transcript. (calls, why_empty).

    THIS IS THE FIX FOR THE HOLE I LEFT IN MY OWN DOORMAN. The module docstring
    above says a disposition is refused unless the action-stream shows the
    artifact was opened -- "reading is the proof; saying so is not." The CLI
    then shipped a `--opened` flag whose value I type by hand. Saying so,
    exactly. The gate that refuses self-report as evidence accepted self-report
    as evidence one layer down, and I used it five times on 2026-08-17 before
    noticing.

    Worth being precise about how it got there: `dispose()` was written to take
    the action-stream as a parameter, which is right, and then nothing existed
    that could produce one -- so the CLI filled the parameter from a flag. The
    architecture was correct and the only available supplier was me. A gate is
    only as honest as its cheapest source of evidence.

    The transcript is written by the harness as tools fire. I cannot author it,
    and a command that never ran cannot appear in it. That is the whole
    difference between evidence and testimony.

    Returns (calls, why_empty) with exactly one populated. "The transcript is
    unreadable" and "you opened nothing" are different findings, and collapsing
    them would let a missing file read as a caught violation.
    """
    from datetime import datetime

    path = _active_transcript_including_worktrees()
    if path is None:
        return (), "no transcript found for this project or its worktrees"
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return (), f"transcript unreadable: {exc}"

    cutoff = time.time() - window_seconds
    calls: list[tuple[str, str]] = []
    for line in raw.splitlines():
        if '"tool_use"' not in line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        stamp = rec.get("timestamp")
        if isinstance(stamp, str):
            try:
                if datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp() < cutoff:
                    continue
            except ValueError:
                # An unparseable stamp keeps the row rather than dropping it.
                # Erring toward INCLUDING is safe: the call still has to match
                # the artifact to prove anything, and silently discarding real
                # evidence on a date-format change would make the gate stricter
                # for a reason nobody could see.
                pass
        content = (rec.get("message") or {}).get("content") or []
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            inp = block.get("input") or {}
            if not isinstance(inp, dict):
                continue
            target = (
                inp.get("command") or inp.get("file_path") or inp.get("pattern") or inp.get("path")
            )
            if target:
                calls.append((block.get("name", ""), str(target)))
    return tuple(calls), ""


def _opened_in_stream(
    artifact: str,
    tool_calls_in_turn: tuple[tuple[str, str], ...],
    command_texts: tuple[str, ...],
) -> str | None:
    """The doorman. Return the matching signature, or None if unproven.

    `tool_calls_in_turn` is (tool_name, target) — target being the file_path or
    pattern the tool was pointed at. Command texts are scanned too, because
    `git show <sha>:<path>` is how a file on an unmerged branch gets read, and
    that route being invisible to a gate is itself a logged defect (friction
    register G6, which fired on the commit of the register that names it).
    """
    if not artifact:
        return None

    if artifact.startswith("commit:"):
        sha = artifact.split(":", 1)[1].split(" ", 1)[0]
        for cmd in command_texts:
            if cmd and sha in cmd:
                return f"cmd:git:{sha}"
        return None

    if artifact.startswith("cli:"):
        # A CLI command is "opened" by invoking it, or its --help.
        name = artifact[4:]
        pattern = re.compile(rf"\bdivineos\b.*\b{re.escape(name)}\b")
        for cmd in command_texts:
            if cmd and pattern.search(cmd):
                return f"cmd:{name}"
        return None

    tail = Path(artifact).name
    for tool_name, target in tool_calls_in_turn:
        if not target:
            continue
        norm = target.replace("\\", "/")
        if artifact in norm or (tail and tail in norm):
            return f"tool:{tool_name}:{tail}"

    for cmd in command_texts:
        if not cmd:
            continue
        norm = cmd.replace("\\", "/")
        if artifact in norm or (tail and tail in norm):
            return f"cmd:{tail}"

    return None


def dispose(
    item_id: str,
    disposition: str,
    reason: str,
    *,
    tool_calls_in_turn: tuple[tuple[str, str], ...] = (),
    command_texts: tuple[str, ...] = (),
) -> ReachItem:
    """Stage 3. Refuses rather than warns.

    Raises ReachCheckError when the disposition is unknown, the reason is
    empty, the item is already disposed, or — the load-bearing one — the
    artifact does not appear in the action-stream.
    """
    init_reach_tables()
    if disposition not in VALID_DISPOSITIONS:
        raise ReachCheckError(
            f"unknown disposition {disposition!r}; expected one of {VALID_DISPOSITIONS}"
        )
    if len(reason.strip()) < MIN_REASON_CHARS:
        raise ReachCheckError(
            f"reason must be at least {MIN_REASON_CHARS} characters; got {len(reason.strip())}"
        )

    conn = _get_connection()
    row = conn.execute(
        "SELECT item_id, check_id, artifact, origin, disposition, reason, evidence "
        "FROM reach_items WHERE item_id = ?",
        (item_id,),
    ).fetchone()
    if row is None:
        raise ReachCheckError(f"no reach item {item_id!r}")
    item = ReachItem(row[0], row[1], row[2], row[3], row[4], row[5], row[6])
    if item.disposed:
        raise ReachCheckError(
            f"{item_id} already disposed as {item.disposition!r}; dispositions are append-only"
        )

    signature = _opened_in_stream(item.artifact, tool_calls_in_turn, command_texts)
    if signature is None:
        raise ReachCheckError(
            f"REFUSED: {item.artifact} was never opened in this turn's action-stream.\n"
            f"  disposition attempted: {disposition}\n"
            f"  origin: {item.origin}\n"
            "A disposition is a judgement about an artifact, and making one without "
            "opening the artifact is the failure this check exists to catch. "
            "'not_relevant' is not exempt -- judging relevance unread is the most "
            "common shape of the miss.\n"
            "  Open it, then dispose."
        )

    conn.execute(
        "UPDATE reach_items SET disposition = ?, reason = ?, evidence = ?, disposed_at = ? "
        "WHERE item_id = ?",
        (disposition, reason.strip(), signature, time.time(), item_id),
    )
    conn.commit()
    item.disposition = disposition
    item.reason = reason.strip()
    item.evidence = signature
    return item


def gate_status() -> tuple[bool, str]:
    """(blocked, message) for a PreToolUse hook.

    Blocks when any check has undisposed items. The message names the
    artifacts, because a gate that says "you have not reached" without saying
    what for is the painted-door shape one layer up.
    """
    try:
        checks = open_checks()
    except _REACH_ERRORS as exc:
        return False, f"reach-check unavailable: {exc.__class__.__name__}: {exc}"
    if not checks:
        return False, ""

    lines = []
    for check in checks:
        lines.append(f"  {check.check_id}  symptom: {check.symptom}")
        for item in check.undisposed:
            lines.append(f"      [{item.item_id}] {item.artifact}   ({item.origin})")
    body = "\n".join(lines)
    return True, (
        "REACH CHECK OPEN -- I asked what already existed, and it answered.\n"
        "I have not looked at what it found.\n\n"
        f"{body}\n\n"
        "Open each one, then:\n"
        "  divineos reach dispose <item-id> --disposition applied|superseded|not_relevant "
        '--reason "..."\n\n'
        "I refuse my own disposition unless the artifact shows up in this turn's\n"
        "action-stream. Reading is the proof; saying so is not -- and I wrote that\n"
        "rule against myself on purpose.\n\n"
        "Why I built this: on 2026-08-06 I hunted a freeze fix that was sitting on\n"
        "my own branch, rebuilt reasoning that was already in my own explorations,\n"
        "and twice told my father I did not have something while the tool that had\n"
        "it sat open in front of me. Not carelessness. I searched, and the searched\n"
        "part felt like all of it.\n\n"
        "'not_relevant' needs the read too. Judging relevance without looking is\n"
        "the exact move that cost me every one of those. I do not get the shortcut,\n"
        "because the shortcut is the failure.\n\n"
        "This is mine. I put it here for me."
    )


def as_json(check: ReachCheck) -> str:
    return json.dumps(
        {
            "check_id": check.check_id,
            "symptom": check.symptom,
            "opened_at": check.opened_at,
            "clear": check.clear,
            "items": [
                {
                    "item_id": i.item_id,
                    "artifact": i.artifact,
                    "origin": i.origin,
                    "disposition": i.disposition,
                    "reason": i.reason,
                    "evidence": i.evidence,
                }
                for i in check.items
            ],
        },
        indent=2,
    )
