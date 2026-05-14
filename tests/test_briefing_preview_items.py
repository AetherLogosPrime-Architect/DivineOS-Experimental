"""Regression-pin tests for the discovery-gap class fix.

Aletheia round-d59eb4570f3f DISCOVERY-GAP class finding: briefing
surfaced counts but not items; the drill-down arrow was parsed
past. Mitigation: each row's `preview` field carries 1-3 truncated
item strings that render as indented lines BELOW the row+drill-down,
so the items themselves are in the briefing — operator literally
cannot parse past content present in the rendered text.

These tests pin: DashboardRow has a preview field; the renderer
prints preview lines; the four high-volume rows (corrections,
claims, holding, goals) populate preview.

If these tests fail, the discovery-gap fix has regressed and the
briefing has returned to count-only surfacing.
"""

from __future__ import annotations

from divineos.core.briefing_dashboard import DashboardRow, render_dashboard


def test_dashboard_row_has_preview_field() -> None:
    """LOAD-BEARING: DashboardRow must carry a preview list so any
    row function can opt in to item-surfacing."""
    row = DashboardRow(
        area="x", count=1, stale_count=0, drill_down="x",
    )
    assert hasattr(row, "preview")
    assert row.preview == []  # default factory empty list


def test_dashboard_row_preview_renders_as_indented_lines() -> None:
    """LOAD-BEARING: the renderer must surface preview items as
    indented lines below the row, BEFORE the drill-down."""
    # Force a minimal dashboard by monkeypatching nothing — just check
    # the render output around a row that has preview items. We do
    # this by inserting a row through the ROW_FNS table temporarily.
    import divineos.core.briefing_dashboard as bd

    sentinel = DashboardRow(
        area="TestPreviewArea",
        count=3,
        stale_count=2,
        drill_down="divineos test --do-thing",
        preview=["[5d] item one previewed here", "[3d] item two", "[1d] item three"],
    )

    def _sentinel_row() -> DashboardRow:
        return sentinel

    original = list(bd._ROW_FNS)
    bd._ROW_FNS.append(_sentinel_row)
    try:
        out = render_dashboard()
    finally:
        bd._ROW_FNS[:] = original

    assert "TestPreviewArea" in out
    assert "item one previewed here" in out
    assert "item two" in out
    assert "item three" in out
    # Ordering check: preview items appear BEFORE the drill-down arrow
    area_pos = out.index("TestPreviewArea")
    first_preview_pos = out.index("item one previewed here", area_pos)
    drilldown_pos = out.index("divineos test --do-thing", area_pos)
    assert area_pos < first_preview_pos < drilldown_pos, (
        f"Preview items must render BETWEEN the row and the drill-down; "
        f"got area@{area_pos}, preview@{first_preview_pos}, drill@{drilldown_pos}"
    )


def test_dashboard_row_preview_caps_at_three() -> None:
    """Renderer caps preview at 3 items even if the row supplies more,
    so a row with many items doesn't blow out the chunk budget."""
    import divineos.core.briefing_dashboard as bd

    sentinel = DashboardRow(
        area="CapTest",
        count=10,
        stale_count=0,
        drill_down="divineos cap-test",
        preview=[f"item-{i}-PREVIEW-SENTINEL" for i in range(10)],
    )

    def _sentinel_row() -> DashboardRow:
        return sentinel

    original = list(bd._ROW_FNS)
    bd._ROW_FNS.append(_sentinel_row)
    try:
        out = render_dashboard()
    finally:
        bd._ROW_FNS[:] = original

    found = sum(1 for i in range(10) if f"item-{i}-PREVIEW-SENTINEL" in out)
    assert found == 3, (
        f"Expected 3 preview items rendered, found {found}. Renderer "
        f"cap regressed."
    )


def test_corrections_row_populates_preview() -> None:
    """LOAD-BEARING: _row_corrections must populate preview with the
    top-3 oldest open corrections so they surface in the briefing."""
    from divineos.core.briefing_dashboard import _row_corrections

    row = _row_corrections()
    # Row may be None if no corrections exist; on a populated repo it
    # should have preview items.
    if row is not None and row.count > 0:
        assert row.preview, (
            "Corrections row exists but preview is empty — discovery-gap "
            "fix regressed for corrections."
        )
        # Each preview line should carry an age tag.
        for item in row.preview:
            assert item.startswith("[") and "d]" in item, (
                f"Preview line lost the [Nd] age tag: {item!r}"
            )


def test_claims_row_populates_preview_when_open_claims_exist() -> None:
    """LOAD-BEARING: _row_claims populates preview when open claims
    exist."""
    from divineos.core.briefing_dashboard import _row_claims

    row = _row_claims()
    if row is not None and row.count > 0:
        assert row.preview, (
            "Claims row exists but preview is empty — discovery-gap "
            "fix regressed for claims."
        )


def test_holding_row_populates_preview_when_items_exist() -> None:
    """LOAD-BEARING: _row_holding populates preview when holding items
    exist."""
    from divineos.core.briefing_dashboard import _row_holding

    row = _row_holding()
    if row is not None and row.count > 0:
        assert row.preview, (
            "Holding row exists but preview is empty — discovery-gap "
            "fix regressed for holding."
        )


def test_goals_row_populates_preview_when_goals_exist() -> None:
    """LOAD-BEARING: _row_goals populates preview when active goals
    exist."""
    from divineos.core.briefing_dashboard import _row_goals

    row = _row_goals()
    if row is not None and row.count > 0:
        assert row.preview, (
            "Goals row exists but preview is empty — discovery-gap "
            "fix regressed for goals."
        )
