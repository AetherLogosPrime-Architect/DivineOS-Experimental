"""Characterization test for dangling path references.

Feathers, from the walk that designed the checker: pin the behavior before
changing it. Without a recorded baseline the count is unfalsifiable -- I could
recover two files, say "improved", and nobody could check.

Deming, from the same walk, pulls the other way: 27 misses out of 301
references is a ~9% system rate, common-cause, and blocking a commit on it
would be tampering. The two are resolved by splitting them. The precommit
report is advisory and never blocks. This test blocks, because a failing test
is information addressed to me, not an interruption addressed to the work.

The assertion is one-directional on purpose. Going UP fails: a new dangling
reference is a new instance of the defect. Going DOWN fails too, but only to
force the number here to be lowered -- otherwise the baseline rots into a
ceiling nobody notices they are under.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from check_referenced_paths import classify  # noqa: E402

# Measured 2026-08-05, the session that found docs/build_flow.md stranded on a
# branch with no PR after I had concluded it was never written.
_BASELINE_STRANDED = 6
_BASELINE_ABSENT = 19


def test_no_new_dangling_references():
    """A reference that resolves nowhere is the painted-door defect."""
    _templates, stranded, absent = classify()

    assert len(stranded) <= _BASELINE_STRANDED, (
        f"{len(stranded)} stranded references, baseline {_BASELINE_STRANDED}. "
        "A file exists on another branch and is cited as if it were here:\n"
        + "\n".join(f"  {r} -> {b}" for r, _c, b, _cited in stranded)
    )
    assert len(absent) <= _BASELINE_ABSENT, (
        f"{len(absent)} absent references, baseline {_BASELINE_ABSENT}. "
        "Something is cited that git has never seen:\n"
        + "\n".join(f"  {r}" for r, _cited in absent)
    )


def test_baseline_is_not_stale():
    """If the real count dropped, lower the baseline in this file.

    Without this the number becomes a ceiling that quietly permits regression
    back up to it -- the same drift-through-success shape the checker exists
    to catch one layer down.
    """
    _templates, stranded, absent = classify()
    assert (len(stranded), len(absent)) == (_BASELINE_STRANDED, _BASELINE_ABSENT), (
        f"counts moved to stranded={len(stranded)} absent={len(absent)}. "
        "Update _BASELINE_STRANDED / _BASELINE_ABSENT in this file to match, "
        "so the pin keeps tracking reality instead of becoming a ceiling."
    )


def test_templates_are_excluded_visibly():
    """Placeholders are not missing files, and the exclusion must be inspectable.

    Knuth's boundary case: docs/digests/YYYY-WW.md is a filename pattern. A
    checker that reports it as missing cries wolf and gets ignored, which is
    worse than no checker. A silent exclusion list is the next hiding place,
    so classify() returns them rather than dropping them.
    """
    templates, _stranded, _absent = classify()
    assert templates, "no templates detected -- the exclusion path is not exercised"
    assert all(not (REPO / t).exists() for t in templates)
