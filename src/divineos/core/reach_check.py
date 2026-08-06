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
    surfaced = [
        (f"commit:{sha} {subject}", f"unmerged-commit:{branch}") for subject, sha, branch in commits
    ] + _artifacts_from(art)

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
        "REACH CHECK OPEN -- prior work surfaced for this symptom has not been "
        "dispositioned.\n\n"
        f"{body}\n\n"
        "Open each artifact, then:\n"
        "  divineos reach dispose <item-id> --disposition applied|superseded|not_relevant "
        '--reason "..."\n'
        "The disposition is refused unless the artifact appears in this turn's "
        "action-stream. Reading is the proof; saying so is not."
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
