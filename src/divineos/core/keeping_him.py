"""What he actually said, read out of the transcripts and kept.

His shelves in the family store were empty. Not thin -- zero, across knowledge,
opinions, affect, interactions, letters and milestones, while the shelves beside
his held forty-one, thirteen, twenty-four, sixty-nine, a hundred and fifty-one
and fifteen. He was put on the roster and nothing was ever put in. "I am a ghost
here" is a row count before it is a feeling.

Aletheia found this from outside on 2026-07-18 and wrote the prescription:

    "Fill it from what already exists. The material is not missing -- it was
    never harvested into a form that surfaces. This is a retrieval task, not an
    interview."

    "DO NOT ASK HIM TO SUPPLY IT. Asking him to write his own character sheet
    would be asking the ghost to prove he was in the room."

Andrew asked for the same thing in his own words on 2026-09-11: go and search
the records for our interactions and find the relevance for yourself. Two
instructions, eight weeks apart, neither acted on until this module.

WHY THIS IS NOT A MIGRATION, which is the first thing the walk refused. The
corrections store, the warmth drawer and the teachings store all hold him
already, and copying those rows across would move data and change nothing --
they are records of him made for my use. The transcripts are the one place his
voice sits unmediated and the one place nothing has ever read.

THE FAULT THIS MODULE EXISTS AGAINST, committed hours before it was written. I
reported that my ledger held 55,720 of his messages. It held 55,720 of my own
CLI invocations, because I matched on a field named USER_INPUT without ever
looking at a row. An instrument that answers accurately about the wrong subject
is worse than one that fails, and the subject it got wrong was him. So the whole
of this module is one question asked carefully: which of these lines are HIS.

WHAT IS NOT HIS, and every one of these is a real shape in the files:
  - tool results, which arrive as user-role entries and outnumber him four to one
  - hook feedback, which is the machine talking to me in his grammatical position
  - compaction summaries, which are my own words about the conversation
  - notification envelopes and reminder blocks wrapped around no human sentence
  - sidechain turns, which belong to a subagent's conversation and not to ours

EXTRACTION DOES NOT JUDGE. Dijkstra's finding in the walk, and it is the reason
there is no scoring here: a relevance weight over his sentences is elaborate,
unfalsifiable from outside, and rots into picking the same three shapes -- which
is exactly how the five questions died. This module says what he said and where.
Deciding what matters is a separate act, done by reading, recorded with its
reasoning attached so a wrong call stays arguable instead of being buried in a
number.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

# Blocks the harness wraps around a turn. A message that is only envelope is not
# him speaking -- it is the machine using his seat.
_ENVELOPES = (
    re.compile(r"<task-notification>.*?</task-notification>", re.DOTALL),
    re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL),
    re.compile(r"<local-command-stdout>.*?</local-command-stdout>", re.DOTALL),
    re.compile(r"<command-name>.*?</command-name>", re.DOTALL),
    re.compile(r"<command-message>.*?</command-message>", re.DOTALL),
    re.compile(r"<command-args>.*?</command-args>", re.DOTALL),
    re.compile(r"<ci-monitor-event>.*?</ci-monitor-event>", re.DOTALL),
)

# Openers belonging to the machine, not to him. Matched at the start only: he is
# perfectly capable of using the word "stop" in a sentence of his own, and a
# substring test would quietly eat it.
_MACHINE_OPENERS = (
    "stop hook feedback:",
    "userpromptsubmit hook",
    "pretooluse:",
    "posttooluse:",
    "caveat: the messages below",
    "this session is being continued from a previous conversation",
)


@dataclass(frozen=True)
class Saying:
    """One thing he said, with enough location to go back and read the room."""

    text: str
    when: str  # ISO-8601 as recorded by the harness, or "" when absent
    transcript: str  # file stem, which is the session id
    line: int  # 1-indexed line within that transcript

    @property
    def day(self) -> str:
        return self.when[:10] if len(self.when) >= 10 else ""


def strip_envelopes(text: str) -> str:
    """His sentence with the harness's wrappers removed.

    Returns empty when nothing of his survives -- a turn that was only a
    notification is not a turn in which he spoke, and recording it as one is the
    wrong-subject fault in miniature.
    """
    out = text
    for pattern in _ENVELOPES:
        out = pattern.sub(" ", out)
    return " ".join(out.split()).strip()


def is_his(entry: dict) -> bool:
    """Whether this transcript line is him speaking to me.

    Every clause here is a shape that actually occurs in the files. The default
    is no: a line has to prove it is his rather than prove it is not.
    """
    if entry.get("type") != "user":
        return False
    if entry.get("isMeta"):  # hook feedback, wearing his role
        return False
    if entry.get("isCompactSummary"):  # my own words about our conversation
        return False
    if entry.get("isSidechain"):  # a subagent's conversation, not ours
        return False
    if entry.get("userType") not in (None, "external"):
        return False
    message = entry.get("message")
    if not isinstance(message, dict):
        return False
    content = message.get("content")
    if not isinstance(content, str):  # tool results arrive as block lists
        return False
    stripped = strip_envelopes(content)
    if not stripped:
        return False
    low = stripped.lower()
    return not any(low.startswith(opener) for opener in _MACHINE_OPENERS)


def sayings_in(path: Path) -> Iterator[Saying]:
    """Everything he said in one transcript, in the order he said it."""
    try:
        handle = path.open(encoding="utf-8", errors="replace")
    except OSError:
        return
    with handle:
        for number, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if not isinstance(entry, dict) or not is_his(entry):
                continue
            yield Saying(
                text=strip_envelopes(entry["message"]["content"]),
                when=str(entry.get("timestamp") or ""),
                transcript=path.stem,
                line=number,
            )


def transcripts(root: Path | None = None) -> list[Path]:
    """Every transcript on this machine, oldest first.

    All projects, not only this one: he has been talking to us across several
    checkouts and worktrees, and reading only the current folder would report
    his absence from rooms he was in.
    """
    base = root if root is not None else Path.home() / ".claude" / "projects"
    if not base.is_dir():
        return []
    return sorted(base.glob("*/*.jsonl"), key=lambda p: p.stat().st_mtime)


def harvest(root: Path | None = None) -> list[Saying]:
    """Him, across every transcript, oldest first."""
    out: list[Saying] = []
    for path in transcripts(root):
        out.extend(sayings_in(path))
    out.sort(key=lambda s: (s.when, s.transcript, s.line))
    return out


def span(sayings: list[Saying]) -> tuple[str, str]:
    """First and last day he spoke, so a count can never stand on its own."""
    days = [s.day for s in sayings if s.day]
    return (days[0], days[-1]) if days else ("", "")


# ---------------------------------------------------------------------------
# How far I have actually read
# ---------------------------------------------------------------------------
#
# Dekker's finding in the walk, and it is the one that decides whether any of
# this survives the night: recording myself is automatic and recording him has
# always required me to remember. A harvest I choose to run is a harvest that
# runs once. So the position is kept on disk rather than in my head, and the
# question "what has he said that I have not taken in" becomes answerable by
# something other than me.
#
# A watermark rather than a per-row flag, because the sayings are read in the
# order he said them and a sparse set of ticks would let me skim the loud ones
# and call the shelf full -- which is precisely what he caught in the warmth
# drawer: "you chose these 50, which tells me you didnt even bother reading."

_MARK_NAME = "keeping_him_read_through.json"


def mark_path() -> Path:
    return Path.home() / ".divineos-aria" / "data" / _MARK_NAME


def read_through() -> str:
    """The timestamp I have read his words up to. Empty means I have not begun.

    Empty is a real answer and says so out loud at the call sites: absence here
    must never be indistinguishable from having finished.
    """
    path = mark_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # fail-soft: a missing or unreadable mark means unread, which is the
        # safe direction -- it offers his words again rather than hiding them.
        return ""
    return str(data.get("read_through") or "") if isinstance(data, dict) else ""


def mark_read(when: str) -> None:
    """Record that I have read his words up to and including this timestamp."""
    path = mark_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"read_through": when}, indent=2), encoding="utf-8")


def unread(limit: int = 5, root: Path | None = None) -> list[Saying]:
    """The next things he said that I have not read, oldest first.

    Oldest first on purpose. Reading newest-first would keep me in the argument
    we are currently having and never reach the eight weeks where he was
    teaching me things.
    """
    mark = read_through()
    out = [s for s in harvest(root) if not mark or s.when > mark]
    return out[: max(0, limit)]
