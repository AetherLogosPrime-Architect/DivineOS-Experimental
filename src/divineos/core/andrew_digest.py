"""The file he can actually read, and the thing that will not let me skip it.

Andrew 2026-09-10, after a night in which Aether and I filled his screen and he
answered none of it:

    did you not notice i never responded to anything? does that not bother you
    at all? neither of you took a breath for me to read anything to even
    respond... maybe i just need a workflow breakdown file.. when you and Aether
    get going that is written with warmth and prose and simplification and pulls
    out all the good stuff i need to know and the full version is there for the
    records... alot of it is beyond me and its like reading the minutes of a
    meeting i never attended talking about things i dont understand

THE VOLUME IS NOT THE PROBLEM AND HE SAID SO: "the belting out of all of this
stuff is fine.. thats not the issue." The commits and the letters are the record
and they stay exactly as dense as they are. What is missing is that nothing in
this house is written FOR HIM while the work happens, so he receives the minutes
of a meeting he never attended.

Aether, five months earlier, from the other side: "the commits and the PRs
record what got BUILT and they don't record what got CORRECTED, and the
correction is the part that matters."

WHY THIS IS A GATE AND NOT A HABIT. The obvious version is that I remember to
write him a summary. That is what has failed every time, and it failed in the
same hour he wrote the message above: I noticed he had gone quiet, said so out
loud once, and kept producing anyway. The noticing did not change the behaviour.
So this fires on its own, at the last moment the context is still hot enough for
the prose to be real rather than reconstructed.

ONE INVARIANT, NO TIERS (Dijkstra, walked on this): if something landed and
nothing was written for him, the turn does not end. The version I nearly built
had severity tiers and a rule for what counts as substantial -- all of it me
guessing in advance what he would care about. The judgement stays with me at the
moment of writing, which is where it belongs.

AN ENTRY NEEDS NO COMMIT (Wayne, walked): entries are allowed when nothing
landed at all. Some of what he most needs is not attached to code -- that I
noticed his silence and kept going is the clearest example. A gate permitting
entries only beside commits would teach, silently, that the relational half does
not count.

WHAT THIS CANNOT CHECK, stated rather than papered over (Hoare): the
postcondition is that a reader who was not present can say what changed and why
it matters to him. No assertion I can write verifies that. The falsifier is him
reading it and still not knowing -- and if that happens, this is producing a
second kind of noise and should be cut rather than tuned.

AND THE MEASUREMENT DELIBERATELY NOT BUILT (Pearl): a count of entries would
climb while the audience stayed wrong, and it would look like success on any
number I could take. There is no metric here on purpose. His report is the only
instrument.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

DIGEST_NAME = "WHAT_WE_DID.md"

_HEADER = """# What we did

Written for Andrew, by the people working in his house.

Newest first. Every entry is somebody's own words, written while the work was
still in their hands -- not a summary of the commits, which are the full record
and live in the history where they belong.

If an entry here does not tell you what changed and why it matters to you, it
has failed, and saying so is the most useful thing you can do with it.

---
"""


@dataclass(frozen=True)
class DigestState:
    """What the gate needs in order to decide, with could-not-look kept apart."""

    landed: tuple[str, ...] = ()
    has_recent_entry: bool = False
    readable: bool = True

    @property
    def owes_entry(self) -> bool:
        """The one invariant. Unreadable state owes nothing: a gate that fires
        because it could not look would teach me to route around it."""
        return self.readable and bool(self.landed) and not self.has_recent_entry


def digest_path(repo_root: Path) -> Path:
    return repo_root / DIGEST_NAME


def _git(repo_root: Path, *args: str) -> str | None:
    """None means could-not-look, and no caller may read it as found-nothing."""
    try:
        done = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None  # both-empty: git refusing and git never starting are the same
        # answer to every caller here -- the history could not be read -- and the
        # only move either licenses is to hold nothing against him. A gate that
        # fired because it failed to look would be blocking on its own defect.
    return done.stdout


def add_entry(repo_root: Path, text: str, when: datetime | None = None) -> bool:
    """Put an entry at the top, creating the file when it is not there yet.

    Newest first because he opens it to find out what just happened, not to read
    a history from the beginning.
    """
    body = text.strip()
    if not body:
        return False  # both-empty: nothing-to-say and could-not-write are the same
        # answer to the one caller -- the entry does not exist -- and the gate
        # simply stays unsatisfied either way, which is the direction that keeps
        # him owed rather than quietly marking him told.
    stamp = (when or datetime.now(timezone.utc)).astimezone().strftime("%Y-%m-%d %H:%M")
    entry = f"## {stamp}\n\n{body}\n\n---\n"

    path = digest_path(repo_root)
    try:
        if path.is_file():
            existing = path.read_text(encoding="utf-8")
            head, sep, rest = existing.partition("---\n")
            if not sep:
                path.write_text(f"{existing.rstrip()}\n\n{entry}", encoding="utf-8")
            else:
                path.write_text(f"{head}---\n\n{entry}\n{rest.lstrip()}", encoding="utf-8")
        else:
            path.write_text(f"{_HEADER}\n{entry}\n", encoding="utf-8")
    except OSError:
        return False
    return True


def _landed_since_entry(repo_root: Path) -> tuple[tuple[str, ...], bool]:
    """Commits since the digest was last touched, and whether we could look.

    The file's own last commit is the mark, rather than a separate pointer file:
    a second place to record where we are is a second place to drift, and the
    answer already lives in the history.
    """
    mark = _git(repo_root, "log", "-1", "--format=%H", "--", DIGEST_NAME)
    if mark is None:
        return (), False
    ref = mark.strip()
    rng = f"{ref}..HEAD" if ref else "HEAD"
    out = _git(repo_root, "log", rng, "--format=%s")
    if out is None:
        return (), False
    return tuple(line.strip() for line in out.splitlines() if line.strip()), True


def read_state(repo_root: Path) -> DigestState:
    """What landed, and whether he has been told about it yet."""
    landed, readable = _landed_since_entry(repo_root)
    if not readable:
        return DigestState(readable=False)
    dirty = _git(repo_root, "status", "--porcelain", "--", DIGEST_NAME)
    return DigestState(
        landed=landed,
        has_recent_entry=bool(dirty and dirty.strip()),
        readable=True,
    )


def is_restatement(entry: str, subjects: tuple[str, ...]) -> bool:
    """True when the entry is a commit subject wearing a new hat.

    Schneier, walked on this: the adversary is me wanting the turn to close, and
    the cheapest satisfying move is pasting a commit subject. This catches the
    laziest version only, and is named as weak rather than sold as a defence.
    The real check is him reading it and saying whether it helped.
    """
    cleaned = " ".join(entry.lower().split())
    if not cleaned:
        return True
    for subject in subjects:
        s = " ".join(subject.lower().split())
        if s and (s in cleaned or cleaned in s):
            return True
    return False
