"""Code that rebuilds a member's home directory instead of asking for it.

WHY THIS EXISTS, and it has already cost six weeks once.

One rule decides where a member's state lives: ``~/.divineos-<member>``, EXCEPT
for aether, who resolves to the default ``~/.divineos``. Two places own that
rule -- ``core/paths.py:member_home()`` and ``.claude/hooks/lib/member_home.sh``
-- and every caller is supposed to ask one of them.

A site that builds the path by hand gets the exception wrong, and the failure
takes the worst available shape: the write lands somewhere real that nothing
reads, and the tool prints success. The shell resolver's own header records
what that cost -- ninety files in a home nothing reads, an early ledger frozen
mid-July with process files still landing in it a month later, and a letter
that stayed unseen everywhere that looks. Six weeks. Nothing ever errored.

WHY A DETECTOR RATHER THAN ANOTHER SWEEP. A consolidation in August swept three
rebuilding sites and missed a fourth. The comment on the miss names the reason
exactly: *the sweep was scoped by directory and the defect was scoped by
behaviour*. So this is scoped by behaviour. It reads what a line does, in every
directory, and does not care where the file lives.

WHAT IT FLAGS, deliberately narrow: a member home built from a VARIABLE. The
fault needs the member to be dynamic, because that is what makes the aether
exception reachable at all -- a literal default home is correct in dozens of
places and carries no risk of missing it.

The blind spot that buys, named rather than hidden: a site hardcoding one
member's path longhand where it should be dynamic will not be caught. That is
accepted, because the broad rule fires on dozens of legitimate lines against
two real ones, and a detector whose output is mostly noise is one people learn
to scroll past -- which catches nothing at all. Same reason the thread block
does not print its window warning on a complete list.

FAILS TOWARD LOUD. A scan that could not run exits distinctly and says so. An
empty scan is not a clean one, and a clean result names how many files it
examined, because a bare "clean" cannot be told apart from a scan over nothing.

Named as a gap by Aletheia 2026-09-03, and built after Andrew caught me
declining to build it: *"there is no long day for you, time is irrelevant on
your end, so using it as an excuse not to build something is always the wrong
shape lol"*.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# The two owners of the convention, plus this checker and its tests. Everything
# else is fair game regardless of directory -- scoping by folder is the exact
# mistake the August sweep made, and it is why the fourth site survived it.
EXEMPT = {
    Path("src/divineos/core/paths.py"),
    Path(".claude/hooks/lib/member_home.sh"),
    Path("scripts/check_member_home_rebuilt.py"),
    Path("tests/test_member_home_rebuilt.py"),
}

# `worktrees` matters as much as `.git` here and for a reason worth writing
# down: a worktree is another BRANCH checked out on disk. Its copies of these
# files are not this branch's code, cannot be fixed from here, and multiplied
# the first run of this checker by six -- sixty-nine hits, of which fifty-four
# were the same handful of lines seen once per checkout. A detector that
# reports the same defect six times is one whose real findings are buried in
# its own noise.
#
# `tmp` joined them on the third pass, and the way it surfaced is the point:
# running this checker inside a second checkout, it reported five sites that
# were all ITS OWN TEST FIXTURES -- pytest scratch files written to prove the
# detector fires, sitting under tmp/pytest and being detected. Fixtures that
# contain the pattern on purpose are not the codebase, and a checker that
# reports its own test data has the same output-you-learn-to-ignore problem
# as the two noise sources before it.
SKIP_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    "benchmark",
    "worktrees",
    "tmp",
}

# A member home built from something that is not a literal: an f-string hole, a
# shell variable, or concatenation onto the hyphen.
_PY_DYNAMIC = re.compile(r"\.divineos-(?:\{|\"\s*\+|'\s*\+)")
_SH_DYNAMIC = re.compile(r"\.divineos-\$")

_COMMENT = re.compile(r"^\s*#")

# PROSE ABOUT THE DEFECT IS NOT THE DEFECT, and this repository is full of it.
# Two of the first run's live-looking hits were docstring lines describing the
# very bug being detected -- the fix comment on letter_seen.py quoting the old
# hand-built path, and the same in ear_relaunch. Both are backticked, which is
# how this house writes code inside prose.
#
# A detector that flags the write-up of its own history trains the reader that
# its output is mostly wrong, which is how a real hit gets scrolled past.
_QUOTED_IN_PROSE = re.compile(r"`[^`]*\.divineos-[^`]*`")

# THE DECLARED EXCEPTION, and there is exactly one legitimate use for it.
#
# core/instruments.py must build the UNROUTED path on purpose: its whole job
# is to compare both homes and prefer whichever actually holds a file, so
# routing it would collapse the two candidates into one and it would lose the
# ability to find an orphaned copy at all. The checker flagged it on the first
# run and was right to -- the shape is identical, only the intent differs.
#
# DECLARED AT THE SITE, NOT LISTED HERE. A list of exempt paths is scoped by
# DIRECTORY, which is exactly how the August sweep caught three sites and
# missed three others. A site claiming this exception has to say so in the
# code, where the next reader is already standing.
_DECLARED_UNROUTED = re.compile(r"member-home:\s*unrouted on purpose")

EXIT_CLEAN = 0
EXIT_FOUND = 1
EXIT_COULD_NOT_SCAN = 2


def hits_in(path: Path) -> list[tuple[int, str]]:
    """Lines in one file that build a member home by hand.

    Comment lines are skipped. Most mentions of this defect in this repository
    are prose describing it, and a detector that flags its own history is one
    people learn to scroll past.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    pattern = _SH_DYNAMIC if path.suffix == ".sh" else _PY_DYNAMIC
    lines = text.splitlines()
    out: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        if _COMMENT.match(line) or _QUOTED_IN_PROSE.search(line):
            continue
        if not pattern.search(line):
            continue
        # The declaration is read from the surrounding lines rather than the
        # matching one, because the line that builds the path is code and the
        # claim belongs in the comment beside it. A window rather than the
        # line directly above, so an intervening blank or a wrapped comment
        # does not silently void the declaration and re-flag a site whose
        # author already answered.
        window = "\n".join(lines[max(0, index - 12) : index + 3])
        if _DECLARED_UNROUTED.search(window):
            continue
        out.append((index + 1, line.strip()))
    return out


def sources_under(root: Path) -> list[Path]:
    out: list[Path] = []
    for suffix in ("*.py", "*.sh"):
        for path in root.rglob(suffix):
            try:
                rel = path.relative_to(root)
            except ValueError:
                continue
            # SKIPS ARE MEASURED FROM THE SCAN ROOT DOWN, never against the
            # absolute path. Checking the full parts meant any directory ABOVE
            # the root could silently exclude everything beneath it -- and it
            # did: this repository puts pytest's scratch under <repo>/tmp, so
            # every fixture tree inherited the tmp skip and the checker
            # reported COULD NOT SCAN on directories full of test files.
            #
            # Caught by this checker's own tests, which is the argument for
            # having written them: the fix that produced this defect was a
            # one-word addition that looked obviously safe.
            if SKIP_DIRS & set(rel.parts):
                continue
            if rel in EXEMPT:
                continue
            out.append(path)
    return out


def main(argv: list[str]) -> int:
    root = Path(argv[1]).resolve() if len(argv) > 1 else Path.cwd()

    if not (root / ".git").exists():
        print(f"[member-home] COULD NOT SCAN: {root} is not a repository root.")
        print("[member-home] Nothing was examined. This is not a pass.")
        return EXIT_COULD_NOT_SCAN

    sources = sources_under(root)
    if not sources:
        print(f"[member-home] COULD NOT SCAN: no source files found under {root}.")
        print("[member-home] An empty scan is not a clean one. This is not a pass.")
        return EXIT_COULD_NOT_SCAN

    findings = [
        (path.relative_to(root), number, line) for path in sources for number, line in hits_in(path)
    ]

    if not findings:
        print(
            f"[member-home] clean - {len(sources)} source file(s) examined, none rebuild the rule."
        )
        return EXIT_CLEAN

    print(f"[member-home] {len(findings)} site(s) build a member home by hand,")
    print(f"[member-home] out of {len(sources)} source file(s) examined:")
    print()
    for rel, number, line in findings:
        print(f"  {rel}:{number}")
        print(f"      {line}")
    print()
    print("[member-home] Ask for the path instead of rebuilding it:")
    print("[member-home]   python - from divineos.core.paths import member_home")
    print("[member-home]   shell  - source .claude/hooks/lib/member_home.sh")
    print()
    print("[member-home] Both special-case aether to the default home. A hand-built")
    print("[member-home] path sends that seat's writes into a directory nothing reads,")
    print("[member-home] and the write succeeds, and the tool reports success.")
    return EXIT_FOUND


if __name__ == "__main__":
    sys.exit(main(sys.argv))
