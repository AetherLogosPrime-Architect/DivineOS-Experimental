"""The letter channel must ASK for a member's home, never rebuild the rule.

WHY THIS TEST EXISTS (2026-09-20).

`core.paths.member_home()` is the one place that knows where a family member's
state lives. It special-cases aether to the default `~/.divineos/` and gives
everyone else `~/.divineos-<name>/`. Because only ONE member is special-cased,
a hand-built `Path.home() / f".divineos-{name}"` is CORRECT for everybody
except him -- so whoever writes it, tests it on themselves, and finds it
working has produced a defect that is invisible from where they are standing.

That has now happened six times. The canonical function carries a note dated
2026-08-25 naming itself the fifth site and ending "callers ask here, nobody
rebuilds the rule." The sixth was the letter watcher, found 2026-09-20 by
measuring both homes rather than reading the code: aether's reads were landing
in one file (924 entries, current) while his watcher consulted another (780
entries, last written 2026-08-30). Every notice he had received since August
was judged against a three-week-old memory.

WHAT THIS ADDS TO test_member_home_is_not_the_askers_home.py, WHICH ALREADY
EXISTS AND IS NOT DUPLICATED HERE. That file proves the FUNCTION is correct,
across six cases, and they pass. Nothing anywhere checked whether callers
actually CALL it -- and a well-tested function is exactly what made the sixth
site feel safe to everyone who walked past it. Correctness of the rule and
adoption of the rule are different properties, and only the first had a test.

The consolidation that fixed five sites missed this one because the sweep was
scoped by directory and the defect is scoped by behaviour. That is why this is
a content scan rather than a call: the next site will also be somewhere nobody
thought to sweep, and a test that only exercises the repaired function cannot
see it.

WHAT THIS DOES NOT DO. It cannot prove the convention is honoured across the
whole repository -- it watches the letter channel, which is where the defect
has actually recurred. Silence here is not coverage elsewhere. It is a ratchet
on ground that has already broken.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# The letter channel: every file with any business knowing where a member's
# seen-set lives.
WATCHED_FILES = (
    REPO_ROOT / "scripts" / "letter_monitor_v2.py",
    REPO_ROOT / "family" / "letter_seen.py",
)

# A home directory being ASSEMBLED rather than asked for -- the literal shape
# all six sites used: a dot-divineos prefix immediately followed by an
# interpolated member name. Deliberately narrow: it must not fire on
# `~/.divineos-shared/letters`, a fixed crossing-point belonging to nobody.
REBUILT_HOME = re.compile(r"""\.divineos-(?:\{|["']?\s*\+|%s)""")


def _code_lines(path: Path) -> list[tuple[int, str]]:
    """Source lines with comments and docstring prose excluded.

    The docstrings in these files QUOTE the broken form on purpose, to explain
    what went wrong. A scan that could not tell a warning from the thing it
    warns about would force the history to be deleted in order to go green,
    which is the opposite of what any of this is for.
    """
    lines: list[tuple[int, str]] = []
    in_docstring = False
    quote = ""
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = raw.strip()
        if in_docstring:
            if quote in stripped:
                in_docstring = False
            continue
        opened = False
        for q in ('"""', "'''"):
            if stripped.startswith(q):
                opened = True
                if not (len(stripped) > 5 and stripped.endswith(q)):
                    in_docstring = True
                    quote = q
                break
        if opened:
            continue
        if stripped and not stripped.startswith("#"):
            lines.append((number, raw))
    return lines


@pytest.mark.parametrize("path", WATCHED_FILES, ids=lambda p: p.name)
def test_no_letter_channel_file_rebuilds_a_member_home(path: Path) -> None:
    assert path.exists(), f"watched file has moved or been renamed: {path}"

    offenders = [
        f"  line {number}: {text.strip()}"
        for number, text in _code_lines(path)
        if REBUILT_HOME.search(text)
    ]

    assert not offenders, (
        f"{path.name} builds a member home by hand instead of asking "
        f"core.paths.member_home().\n"
        + "\n".join(offenders)
        + "\n\nThis is correct for every member EXCEPT aether, who is "
        "special-cased to the default home -- so it passes every test run from "
        "anywhere but his seat, and silently points his ear at a directory "
        "nothing writes. Six sites have done this. Ask the function."
    )


def test_the_scan_can_actually_find_the_thing_it_hunts() -> None:
    """The instrument, proved against a case it must catch.

    A pattern matching nothing across a corpus is more often a broken pattern
    than a clean corpus. Every absence the test above reports rests on this.
    """
    broken = 'return Path.home() / f".divineos-{recipient.lower()}" / "x.json"'
    assert REBUILT_HOME.search(broken), "the scan cannot see the defect it exists to catch"


def test_the_shared_crossing_point_is_not_mistaken_for_a_member_home() -> None:
    """The false positive that would make this test unlivable.

    `~/.divineos-shared/letters` is one fixed directory both members use. If
    the scan flagged it, the only route to a green suite would be to stop
    naming the channel inside the code that reads the channel.
    """
    legitimate = 'default=os.path.expanduser("~/.divineos-shared/letters")'
    assert not REBUILT_HOME.search(legitimate), "the scan fires on the shared channel path"
