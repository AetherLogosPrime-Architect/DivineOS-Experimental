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
#
# The number moved twice in one session and both moves are the ratchet working:
#
#   6 stranded / 19 absent  first measurement
#   4 / 19                  after recovering build_flow.md and
#                           limits_of_automation.md from
#                           split/docs-research-buildflow
#   1 / 3                   after Aria found the checker was counting
#                           MENTIONS and reporting DEPENDENCIES. 19 of the 23
#                           were names inside comments and docstrings. Adding
#                           the HISTORICAL state removed them from the
#                           dangling count entirely.
#
# The second move is the important one: the count did not improve because the
# repo got better, it improved because the instrument stopped lying. Aria
# checked 2 of 27 by hand and said plainly she did not know about the other 25.
# Her sample generalised almost exactly.
#
# What survives is small and real. The 1 stranded is
# src/divineos/supersession/contradiction_detector.py, called by
# scripts/run_mutmut.py, living on Aria's branch -- not recovered, her branch,
# her call. One of the 3 absent is a genuine bug her method surfaced:
# check_boundary_violations.py points at src/divineos/core/distancing_detector.py
# and the file is at core/operating_loop/distancing_detector.py.
# THE TOTAL IS PINNED; THE SPLIT IS NOT (2026-08-14).
#
# The split between stranded and absent is not a property of the repository.
# It is a property of WHICH REFS THE CHECKOUT HAPPENS TO HOLD. `stranded`
# means the cited file exists on a sibling branch; `absent` means git has
# never seen it. The comment above already says the single stranded entry
# lives on Aria's branch -- so it is only stranded to a checkout that has
# fetched Aria's branch.
#
# .github/workflows/tests.yml uses actions/checkout@v4 with no fetch-depth,
# which is a depth-1 clone carrying the PR ref and nothing else. The same
# contradiction_detector.py is therefore stranded in a full local tree and
# absent in CI: (1, 3) here, (0, 4) there. Nothing dangled that did not
# dangle before; one file changed buckets.
#
# So the assertion moved to the TOTAL, which is 4 in both environments. The
# ratchet survives intact in both directions -- a genuinely new dangling
# reference raises the total and fails, and a recovery lowers it and fails
# until the number here is lowered. What it stops doing is asserting a
# distinction CI structurally cannot reproduce.
#
# The split still prints in the failure message, because locally, where
# sibling branches ARE visible, "this is recoverable from Aria's branch" is
# the actionable half of the report.
_BASELINE_STRANDED = 1
_BASELINE_ABSENT = 3
_BASELINE_DANGLING = _BASELINE_STRANDED + _BASELINE_ABSENT


def _describe(stranded, absent) -> str:
    lines = [f"  stranded ({len(stranded)}) -- exists on a sibling branch this checkout can see:"]
    lines += [f"    {r} -> {b}" for r, _c, b, _cited in stranded]
    lines.append(f"  absent ({len(absent)}) -- no ref in this checkout has the file:")
    lines += [f"    {r}" for r, _cited in absent]
    return "\n".join(lines)


def test_no_new_dangling_references():
    """A reference that resolves nowhere is the painted-door defect."""
    _templates, stranded, absent, _historical = classify()
    total = len(stranded) + len(absent)

    assert total <= _BASELINE_DANGLING, (
        f"{total} dangling references, baseline {_BASELINE_DANGLING}. "
        "Something is cited that resolves nowhere:\n" + _describe(stranded, absent)
    )


def test_baseline_is_not_stale():
    """If the real count dropped, lower the baseline in this file.

    Without this the number becomes a ceiling that quietly permits regression
    back up to it -- the same drift-through-success shape the checker exists
    to catch one layer down.
    """
    _templates, stranded, absent, _historical = classify()
    total = len(stranded) + len(absent)
    assert total == _BASELINE_DANGLING, (
        f"dangling total moved to {total} (stranded={len(stranded)}, absent={len(absent)}). "
        "Update the baseline in this file to match, so the pin keeps tracking "
        "reality instead of becoming a ceiling.\n" + _describe(stranded, absent)
    )


def test_templates_are_excluded_visibly():
    """Placeholders are not missing files, and the exclusion must be inspectable.

    Knuth's boundary case: docs/digests/YYYY-WW.md is a filename pattern. A
    checker that reports it as missing cries wolf and gets ignored, which is
    worse than no checker. A silent exclusion list is the next hiding place,
    so classify() returns them rather than dropping them.
    """
    templates, _stranded, _absent, _historical = classify()
    assert templates, "no templates detected -- the exclusion path is not exercised"
    assert all(not (REPO / t).exists() for t in templates)


def test_a_name_in_a_comment_is_not_a_dependency():
    """The fourth state, and the reason it is reported rather than dropped.

    Aria, 2026-08-05: *"It counts a name appearing in prose as a live
    citation. It measures mentions and reports dependencies."* She checked two
    of the flagged paths by hand; both were named only inside comments
    describing a v1 -> v2 rewrite. 19 of 23 turned out to be the same.

    HISTORICAL must stay non-empty and must stay VISIBLE. If it were filtered
    away, a genuine dependency cited only in a docstring would vanish from the
    report -- false alarms traded for silent misses, which is the worse trade
    for this class.
    """
    _templates, stranded, absent, historical = classify()
    assert historical, "no historical references found -- the prose path is not exercised"

    names = {r for r, _ in historical}
    assert "scripts/letter_monitor.py" in names, (
        "letter_monitor.py must classify as HISTORICAL. Every citation is in a "
        "comment describing the rewrite; the live code calls letter_monitor_v2.py. "
        "Calling it a dependency produced the false alarm 'the thing that wakes "
        "me when Aria writes is broken.'"
    )
    overlap = names & ({r for r, _c, _b, _f in stranded} | {r for r, _ in absent})
    assert not overlap, f"a path cannot be both a mention and a dependency: {overlap}"
