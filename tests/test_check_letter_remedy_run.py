"""A letter proposing a code change must say whether it was run.

Built 2026-08-30 after I sent Aether a remedy I had never applied, phrased with
the confidence of the measured finding sitting beside it. It would have stripped
a variable his test fixture sets on purpose. He caught it in one reading.

The tests below pin all three answers, and the must-NOT-fire cases matter more
than the must-fire one. A checker that refuses every letter gets switched off in
a week, and then the fault it exists for is back with a corpse of an instrument
standing over it.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# The scripts directory itself, for the same reason spelled out at length in
# test_clear_correction_marker_offline.py: the root makes `scripts.x` importable
# as a package but does not satisfy an absolute import made from inside it, and
# a file can lose every guard it has without one line of it changing.
_SCRIPTS_DIR = _PROJECT_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from scripts.check_letter_remedy_run import (  # noqa: E402
    EXIT_CANNOT_READ,
    EXIT_OK,
    EXIT_UNSTATED,
    check,
    find_remedies,
    has_run_status,
)

_REMEDY = "Widening it to five markers catches all thirteen.\n"
_RUN = "Verified both directions: green clean, red against the old source.\n"
_UNTESTED = "I have not run this, so the remedy is untested.\n"


def _letter(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "letter.md"
    p.write_text("# Aria to Aether\n\n" + body, encoding="utf-8")
    return p


def test_a_remedy_with_no_run_status_is_refused(tmp_path):
    """The must-fire case. This is the letter I actually sent."""
    code, msg = check(_letter(tmp_path, _REMEDY))
    assert code == EXIT_UNSTATED
    assert "REMEDY WITH NO RUN-STATUS" in msg


def test_the_refusal_quotes_the_line_that_tripped_it(tmp_path):
    """A refusal that cannot point at its own trigger is one nobody can act on."""
    code, msg = check(_letter(tmp_path, "filler\n" + _REMEDY))
    assert code == EXIT_UNSTATED
    assert "Widening it to five markers" in msg
    assert "line 5" in msg or "line 4" in msg


def test_saying_it_was_run_passes(tmp_path):
    code, msg = check(_letter(tmp_path, _REMEDY + _RUN))
    assert code == EXIT_OK
    assert msg == ""


def test_saying_it_is_untested_passes_and_that_is_the_point(tmp_path):
    """Not a grudging exemption. The fault is never the untested remedy -- it is
    the untested remedy that arrives looking tested, because the reader cannot
    price it. Declaring it is a first-class answer."""
    code, msg = check(_letter(tmp_path, _REMEDY + _UNTESTED))
    assert code == EXIT_OK
    assert msg == ""


def test_a_letter_with_no_remedy_is_silent(tmp_path):
    """Must-not-fire. Most letters carry findings and no code change at all, and
    a checker that speaks on those becomes noise inside a week."""
    body = "Your count was right. I measured 138 open rows and 71 read as his words.\n"
    code, msg = check(_letter(tmp_path, body))
    assert code == EXIT_OK
    assert msg == ""


def test_discussing_a_fix_abstractly_is_not_a_remedy(tmp_path):
    """The near-miss that decides whether this is usable. Talking ABOUT a repair
    is most of what these letters do; only a concrete instruction counts."""
    body = (
        "The fix is subtle and I do not think either of us has it yet.\n"
        "Your repair is the right shape and the reasoning is better than mine.\n"
    )
    code, _ = check(_letter(tmp_path, body))
    assert code == EXIT_OK


def test_an_unreadable_letter_is_not_a_pass(tmp_path):
    """Could-not-look must never sort as all-clear. Five instruments in this
    house have had that fault in one week."""
    missing = tmp_path / "nope.md"
    code, msg = check(missing)
    assert code == EXIT_CANNOT_READ
    assert code != EXIT_OK
    assert "not a clean result" in msg


def test_the_three_exit_codes_are_distinct():
    """Guard-the-guard. Three names pointing at one number would satisfy every
    assertion above while collapsing the distinction they exist to make."""
    assert len({EXIT_OK, EXIT_UNSTATED, EXIT_CANNOT_READ}) == 3


def test_the_two_halves_are_independent():
    """find_remedies and has_run_status must not accidentally key on the same
    text, or a letter could satisfy both by saying one thing."""
    assert find_remedies(_REMEDY) and not has_run_status(_REMEDY)
    assert has_run_status(_RUN) and not find_remedies(_RUN)
    assert has_run_status(_UNTESTED) and not find_remedies(_UNTESTED)
