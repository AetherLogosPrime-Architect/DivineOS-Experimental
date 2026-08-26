"""Tests for scripts/wiring_gap_phase1.py — scope-to-new-functions wiring-gap check.

Pinned 2026-05-12 after the Phase 0 → Phase 1 design transition. The narrowing
from "every public function in core/" (Phase 0, 80% FP) to "functions added in
the commit range" (Phase 1) is the precision move; these tests pin the
classifier behavior and the hook-file scan path.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

# ruff: noqa: E402
import wiring_gap_phase1 as wgp


# ─── _is_public ──────────────────────────────────────────────────────


def test_is_public_simple_name():
    assert wgp._is_public("foo")


def test_is_public_rejects_private():
    assert not wgp._is_public("_foo")
    assert not wgp._is_public("__foo")


def test_is_public_rejects_dunder():
    assert not wgp._is_public("__init__")
    assert not wgp._is_public("__call__")


def test_is_public_rejects_empty():
    assert not wgp._is_public("")


# ─── _DEF_LINE regex ─────────────────────────────────────────────────


def test_def_line_matches_top_level():
    m = wgp._DEF_LINE.match("+def my_function(x):")
    assert m is not None
    assert m.group(1) == "my_function"


def test_def_line_matches_indented_method():
    m = wgp._DEF_LINE.match("+    def my_method(self):")
    assert m is not None
    assert m.group(1) == "my_method"


def test_def_line_no_match_on_context_line():
    # Context lines don't start with + (only addition diff lines do)
    m = wgp._DEF_LINE.match(" def foo(x):")
    assert m is None


def test_def_line_no_match_on_deletion():
    m = wgp._DEF_LINE.match("-def removed(x):")
    assert m is None


def test_method_indent_pattern():
    assert wgp._METHOD_INDENT.match("+    def bar(self):")
    assert not wgp._METHOD_INDENT.match("+def bar(x):")


# ─── _classify ───────────────────────────────────────────────────────


def _fn(name: str, prod: list[str], test: list[str]) -> wgp.NewFunction:
    f = wgp.NewFunction(
        name=name, file="src/divineos/core/foo.py", commit="abc", commit_subject="x"
    )
    f.production_callers = prod
    f.test_callers = test
    return f


def test_classify_zero_callers_is_wiring_gap():
    f = _fn("dead_on_arrival", [], [])
    assert "ZERO-CALLERS" in wgp._classify(f)


def test_classify_test_only_when_no_prod_callers():
    f = _fn("test_helper", [], ["tests/test_foo.py"])
    assert "TEST-ONLY" in wgp._classify(f)


def test_classify_single_prod_caller():
    f = _fn("called_once", ["src/divineos/core/bar.py"], [])
    assert "SINGLE-PRODUCTION-CALLER" in wgp._classify(f)


def test_classify_wired_with_multiple_callers():
    f = _fn(
        "many_callers",
        ["src/divineos/core/a.py", "src/divineos/core/b.py"],
        ["tests/test_a.py"],
    )
    assert wgp._classify(f) == "WIRED"


# ─── Integration: real repo run ──────────────────────────────────────

# How many distinct new functions the real-repo smoke test will hand to the
# caller scan. This is the quantity that actually drives cost — it multiplies
# by repo size and by xdist worker count — and bounding it directly is what
# makes the test footprint-stable regardless of how large the last three
# commits were. Chosen to sit well inside the per-worker memory and timeout
# budget on Windows, which is the platform that has failed three times.
_CALLER_SCAN_BUDGET = 40


def test_phase1_run_against_recent_history_returns_clean_results():
    """Smoke test: run Phase 1 over the last ~5 commits and verify the
    invariants hold. This is a real-repo test — exercising the actual git
    parsing + caller scanning path.

    Invariants we expect after Phase 1 narrowing + hook-file scan:
    - Every NewFunction has at least the expected dataclass fields populated
    - Total functions classified equals total found

    History window narrowed 2026-07-03 from HEAD~30 to HEAD~5 to fix the
    xdist worker-crash flake: 30 commits × N functions × full-repo caller
    scan across 16 parallel workers exceeded per-worker memory on Windows.
    Andrew authorized as the root-cause fix for the 'phase1 flake' trap
    that had been bypassed 4+ times.

    Further narrowed 2026-07-10 from HEAD~5 to HEAD~3 after the same
    xdist crash reproduced on a branch whose recent commits happened to
    be unusually large (auto-cycle work). The 5-commit heuristic isn't
    footprint-stable because commit size varies; 3 commits stays well
    inside per-worker memory on Windows. Same invariant coverage —
    caller scan does not crash, dataclass fields populated, dedup works.
    Andrew authorized as the same-shape root-cause narrowing.

    Third recurrence 2026-08-26, and this time the bound changes rather
    than the number. The window is still HEAD~3, but a 244-file squash
    landed on main, so every branch cut fresh from main now carries it
    inside three commits and the caller scan runs past its timeout.

    The 2026-07-10 note already contains the diagnosis — *the commit
    heuristic isn't footprint-stable because commit size varies* — and
    the remedy applied twice was to lower the count anyway. A smaller
    count is the same unstable measure set nearer the floor; it survives
    until the next large commit and no longer. So the cost is bounded by
    what actually drives it: the number of distinct functions handed to
    the caller scan, which is the quantity multiplied by repo size and
    by worker count.

    Truncating the sample does not weaken the test. Every invariant here
    is per-function — the scan does not crash, fields are populated,
    each classification lands in a known bucket — so a bounded sample
    exercises them identically to an unbounded one. What an unbounded
    sample adds is not coverage but exposure to whatever size the last
    three commits happened to be.
    """
    commits = wgp._commits_in_range("HEAD~3..HEAD")
    if not commits:
        # Repo without enough history — skip
        return
    functions: list[wgp.NewFunction] = []
    for sha, subject in commits:
        functions.extend(wgp._new_functions_in_commit(sha, subject))

    # Dedup
    seen: dict[tuple[str, str], wgp.NewFunction] = {}
    for fn in functions:
        seen.setdefault((fn.name, fn.file), fn)
    deduped = list(seen.values())

    # Footprint bound, sorted so the sample is the same set on every run
    # rather than whatever order git happened to yield.
    deduped.sort(key=lambda fn: (fn.file, fn.name))
    deduped = deduped[:_CALLER_SCAN_BUDGET]

    # Caller scan should not crash
    wgp._scan_callers(deduped)

    # Every classification falls into one of the four buckets
    valid_buckets = {
        "ZERO-CALLERS (wiring-gap candidate)",
        "TEST-ONLY (no production callers)",
        "SINGLE-PRODUCTION-CALLER",
        "WIRED",
    }
    for fn in deduped:
        assert wgp._classify(fn) in valid_buckets


def test_phase1_render_includes_summary_section():
    """The rendered output should always include the summary section even when
    there are zero new functions."""
    output = wgp._render("HEAD~1..HEAD", [], [], only_zero=False)
    assert "## Summary" in output
    assert "Commits in range: 0" in output


def test_phase1_render_only_zero_filters_other_buckets():
    """When --only-zero-callers, output should not list WIRED bucket details."""
    fn_wired = _fn("wired_one", ["src/divineos/core/a.py", "src/divineos/core/b.py"], [])
    fn_zero = _fn("zero_one", [], [])
    output = wgp._render("range", [("abc", "msg")], [fn_wired, fn_zero], only_zero=True)
    # Zero-callers section should appear
    assert "## ZERO-CALLERS" in output
    # WIRED detail section should NOT appear (summary still shows count)
    detail_marker = "## WIRED"
    # Allow the summary to mention the bucket label, but the detail section
    # should not be present:
    assert detail_marker not in output


def test_phase1_render_full_includes_all_nonempty_buckets():
    fn_wired = _fn("wired_one", ["src/divineos/core/a.py", "src/divineos/core/b.py"], [])
    fn_zero = _fn("zero_one", [], [])
    output = wgp._render("range", [("abc", "msg")], [fn_wired, fn_zero], only_zero=False)
    assert "## ZERO-CALLERS" in output
    assert "## WIRED" in output
