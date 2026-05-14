"""Regression-pin tests for the briefing-dashboard U-shape reorder.

Empirical backing: Liu et al. 2024 TACL ("Lost in the Middle") —
LLMs show a U-shaped attention curve; ~30% accuracy drop on items
positioned in the middle of long contexts. Mitigation: critical
items at top and bottom, padding in the middle.

If these tests fail, the briefing has reverted to insertion-order
rendering and middle items are once again the loudest signal sink.
"""

from __future__ import annotations

from divineos.core.briefing_dashboard import DashboardRow, _reorder_u_shape


def _row(name: str, stale: int) -> DashboardRow:
    return DashboardRow(
        area=name,
        count=stale,
        stale_count=stale,
        drill_down=f"-> divineos {name}",
        detail="",
    )


def test_reorder_skips_small_lists() -> None:
    """Lists of 4 or fewer rows are within chunk range; reordering
    them is theater. Return as-is."""
    rows = [_row("a", 5), _row("b", 1), _row("c", 0)]
    assert _reorder_u_shape(rows) == rows


def test_reorder_places_highest_stale_at_top_and_bottom() -> None:
    """LOAD-BEARING: the highest-staleness items must end up at
    positions 0 and -1 (top and bottom)."""
    rows = [
        _row("low1", 0),
        _row("low2", 0),
        _row("highest", 100),
        _row("medium", 5),
        _row("second-highest", 50),
        _row("low3", 0),
    ]
    out = _reorder_u_shape(rows)
    # Highest staleness should be at position 0 (top)
    assert out[0].area == "highest"
    # Second-highest should be at position -1 (bottom edge)
    assert out[-1].area == "second-highest"


def test_reorder_lowest_stale_in_middle() -> None:
    """Middle positions should be the LOW-staleness rows."""
    rows = [
        _row("a", 0),
        _row("b", 0),
        _row("c", 99),
        _row("d", 0),
        _row("e", 88),
        _row("f", 0),
        _row("g", 77),
    ]
    out = _reorder_u_shape(rows)
    middle = out[len(out) // 2]
    # The middle row should be one of the zero-staleness ones
    assert middle.stale_count == 0


def test_reorder_preserves_all_rows() -> None:
    """No row should be dropped or duplicated by the reorder."""
    rows = [_row(f"row-{i}", i) for i in range(10)]
    out = _reorder_u_shape(rows)
    assert len(out) == len(rows)
    assert {r.area for r in out} == {r.area for r in rows}


def test_reorder_preserves_canonical_order_when_all_stale_counts_zero() -> None:
    """Aletheia round-5cdc2f48c642 Finding 39: when stale-count is
    uniform across all rows (especially the all-fresh case), the
    reorder has no signal to amplify and would scramble canonical
    _ROW_FNS order based on sort stability — burying orientation
    rows (directives, project-purpose) in the middle of the U.
    Skip the reorder."""
    rows = [
        _row("directives", 0),
        _row("compass", 0),
        _row("project-purpose", 0),
        _row("family-letters", 0),
        _row("explorations", 0),
        _row("holding", 0),
    ]
    out = _reorder_u_shape(rows)
    assert out == rows, (
        "All-stale-zero case must preserve canonical order; "
        "Finding-39 regression — fresh orientation rows would be "
        "scrambled into the middle of the U with no semantic basis."
    )


def test_reorder_preserves_canonical_order_when_all_stale_counts_uniform() -> None:
    """Same guard for the all-equal-nonzero case: signal is uniform
    so the U-shape has nothing to amplify."""
    rows = [
        _row("a", 5),
        _row("b", 5),
        _row("c", 5),
        _row("d", 5),
        _row("e", 5),
    ]
    out = _reorder_u_shape(rows)
    assert out == rows, (
        "Uniform-nonzero-stale case must preserve canonical order; "
        "reordering with no signal differential is pure scramble."
    )
