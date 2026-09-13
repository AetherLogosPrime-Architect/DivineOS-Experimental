"""An untracked letter is not a dirty tree, and three scripts must agree.

Aletheia solved this class in safe_push.sh on 2026-07-17 and named the cause
outright: untracked letters and notes were falsely blocking pushes. The fix
reached one caller. Two siblings kept asking whether the tree had ANY
porcelain output at all, so a letter sitting untracked in the working tree
refused them both.

Aria found it 2026-09-07 while checking what a permanently-dirty tree would
break, which was the clause I could not see from my own side: the skip I was
proposing would have traded one loud refusal for two permanent ones.

What each script is actually guarding against is a half-finished TRACKED edit
riding into a measurement or a "clean focused unit". An untracked file cannot
do that. So the rule is tracked-modification, not dirtiness, and this test
holds all three to it together so the next fix cannot reach one and stop.
"""

from __future__ import annotations

import pathlib
import re

SCRIPTS = pathlib.Path("scripts")

# Every script that decides something by looking at working-tree state.
GUARDS = (
    "safe_push.sh",  # where the class was solved first
    "ready_pr.sh",
    "start_work.sh",
)

# The filter that distinguishes a tracked modification from an untracked file.
UNTRACKED_FILTER = re.compile(r"grep\s+-v\s+'\^\?\?'")


def _text(name: str) -> str:
    return (SCRIPTS / name).read_text(encoding="utf-8", errors="replace")


def test_every_dirtiness_guard_exempts_untracked_files():
    missing = [name for name in GUARDS if not UNTRACKED_FILTER.search(_text(name))]
    assert not missing, (
        "these scripts refuse on ANY porcelain output, so an untracked letter "
        f"blocks them: {missing}. safe_push.sh carries the resolved form."
    )


def test_no_guard_still_asks_the_bare_dirtiness_question():
    """The old shape, kept out by name rather than by memory."""
    offenders = []
    for name in GUARDS:
        for line in _text(name).splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # A bare porcelain read used directly as a condition, with no
            # untracked filter anywhere on the line.
            if "git status --porcelain" in stripped and "grep -v" not in stripped:
                if stripped.startswith(("if ", "elif ")) or '-n "$(' in stripped:
                    offenders.append(f"{name}: {stripped[:80]}")
    assert not offenders, (
        f"a bare dirtiness condition is back; scope it to tracked modifications: {offenders}"
    )


def test_the_guards_say_untracked_is_fine():
    """The refusal has to explain itself, or the next reader re-tightens it."""
    silent = [name for name in GUARDS if "ntracked" not in _text(name)]
    assert not silent, (
        f"these refuse without telling the reader untracked files are allowed: {silent}"
    )
