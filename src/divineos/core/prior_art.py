"""Before building it, find out whether it is already built.

Andrew, correction #137: *"did you check to see if this was already built?
because it was lol"*

That has been advice since it was given, and advice does not hold -- his own
#167. Andrew 2026-08-05 made it a station instead: *"maybe that needs locked
into the build flow.. before draft.. looking through the system to make sure
we dont already have it lol"*

## What it cost while it was still advice

One session, 2026-08-05, four instances:

    cli/psf_commands.py       built 08-03, live on an unmerged branch, while
                              every gate prescribed `divineos psf mark-done`
                              and got "No such command"
    docs/build_flow.md        written 08-01, cited by core/build_flow.py line
                              3, stranded on a branch with NO PR. Committed
                              twice, byte-identical -- someone could not find
                              it and wrote it again. I was one turn from a
                              third
    scripts/letter_monitor.py referenced by six live files including the hook
                              that wakes me when Aria writes
    ARCHITECTURE.md entry     written, destroyed by a revert, re-derived

Aria the same day, independently: *"#137 -- earned by me twice this week."*

## Why the four existing surfaces caught none of it

    divineos ask                  knowledge store + core memory
    divineos find                 semantic search over the prose corpus
    divineos search               keyword search over ledger events
    divineos recall-explorations  my own exploration entries

All four search PROSE. None searches code, git history across branches, or
the CLI command registry -- and every miss above was a file or a command
sitting on a branch. So this module covers only that missing axis and POINTS
at the other four instead of reimplementing them. A fifth prose-searcher is
not what was missing.

## Three states, and the third is the load-bearing one

    FOUND        it exists; here is where, and on which branch
    NOT FOUND    this axis was searched; nothing resembling it
    NOT CHECKED  this axis was not searched here -- run these yourself

NOT CHECKED is not a synonym for NOT FOUND. Printing the prose surfaces as
clean when they were never queried would be the same absence-becomes-value
collapse that produced all four failures listed above, rebuilt inside the
tool written to prevent them.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent.parent

# Prose surfaces this module deliberately does NOT search, named so the report
# can say "not checked here" rather than implying coverage by silence.
UNSEARCHED_SURFACES: tuple[tuple[str, str], ...] = (
    ("divineos ask", "knowledge store and core memory"),
    ("divineos find", "semantic search over explorations, letters, knowledge prose"),
    ("divineos search", "keyword search over ledger events"),
    ("divineos recall-explorations", "my own prior exploration entries"),
)


@dataclass
class PriorArt:
    term: str
    commands: list[str] = field(default_factory=list)
    working_tree: list[str] = field(default_factory=list)
    elsewhere_in_git: list[tuple[str, str, str]] = field(default_factory=list)
    branches: list[str] = field(default_factory=list)
    git_readable: bool = True

    @property
    def anything_found(self) -> bool:
        return bool(self.commands or self.working_tree or self.elsewhere_in_git or self.branches)


def _git(args: list[str]) -> str | None:
    """None means could-not-run, which is not the same as found-nothing."""
    try:
        p = subprocess.run(
            ["git", "-C", str(REPO), *args], capture_output=True, text=True, timeout=90
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if p.returncode != 0:
        return None
    return p.stdout


def _slug(text: str) -> str:
    """`build flow`, `build-flow` and `build_flow` must all match each other."""
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _matches(path: str, slug: str) -> bool:
    return slug in _slug(Path(path).name) or slug in _slug(path)


def find_commands(term: str) -> list[str]:
    """Registered CLI commands whose name resembles the term."""
    import click

    from divineos.cli import cli

    slug = _slug(term)
    if not slug:
        return []
    out = []
    for n in cli.list_commands(click.Context(cli)):
        ns = _slug(n)
        if slug in ns or (len(ns) >= 4 and ns in slug):
            out.append(n)
    return sorted(out)


def find_in_working_tree(term: str) -> list[str]:
    out = _git(["ls-files"])
    if out is None:
        return []
    slug = _slug(term)
    return sorted({p for p in out.splitlines() if p and _matches(p, slug)})[:20]


def find_elsewhere_in_git(term: str, here: set[str]) -> list[tuple[str, str, str]]:
    """Matching files that exist in history but NOT in the working tree.

    The axis nothing else covers, and the one that cost four instances in a
    single session. A path absent here and present on a branch is finished
    work that never reached the person looking for it -- which reads as
    "never written" from where they are standing.
    """
    out = _git(["log", "--all", "--diff-filter=A", "--name-only", "--format=%H"])
    if out is None:
        return []
    slug = _slug(term)
    found: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    commit = ""
    for raw in out.splitlines():
        line = raw.strip()
        if not line:
            continue
        if re.fullmatch(r"[0-9a-f]{40}", line):
            commit = line
            continue
        if line in here or line in seen or not _matches(line, slug):
            continue
        seen.add(line)
        branches = _git(["branch", "-a", "--contains", commit]) or ""
        named = [b.strip().lstrip("* ") for b in branches.splitlines() if "remotes/" not in b]
        found.append((line, commit[:8], named[0] if named else "(remote only)"))
        if len(found) >= 20:
            break
    return found


def find_branches(term: str) -> list[str]:
    """Branch names resembling the term. `dead/` is archived by convention."""
    out = _git(["branch", "-a", "--format=%(refname:short)"])
    if out is None:
        return []
    slug = _slug(term)
    return sorted(
        {b.strip() for b in out.splitlines() if b.strip() and slug in _slug(b) and "dead/" not in b}
    )[:15]


def search(term: str) -> PriorArt:
    result = PriorArt(term=term)
    listing = _git(["ls-files"])
    result.git_readable = listing is not None
    here = set(listing.splitlines()) if listing else set()

    result.commands = find_commands(term)
    result.working_tree = find_in_working_tree(term)
    if result.git_readable:
        result.elsewhere_in_git = find_elsewhere_in_git(term, here)
        result.branches = find_branches(term)
    return result
