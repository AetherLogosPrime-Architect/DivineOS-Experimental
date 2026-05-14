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


def test_compass_row_previews_concerns_first() -> None:
    """LOAD-BEARING: _row_compass populates preview when drift/concerns
    exist; concerns come BEFORE drifting in the preview order because
    concerns are already in a virtue-deficient/excess zone."""
    from divineos.core.briefing_dashboard import _row_compass

    row = _row_compass()
    if row is not None and row.stale_count > 0:
        assert row.preview, (
            "Compass row exists with drift but preview is empty — "
            "discovery-gap fix regressed for compass."
        )
        # Concerns are tagged [concern]; drifting are tagged [drifting].
        # If both exist, the [concern] lines must come first.
        concern_idxs = [
            i for i, p in enumerate(row.preview) if p.startswith("[concern]")
        ]
        drifting_idxs = [
            i for i, p in enumerate(row.preview) if p.startswith("[drifting]")
        ]
        if concern_idxs and drifting_idxs:
            assert max(concern_idxs) < min(drifting_idxs), (
                "Compass preview ordering regressed: drifting entries "
                "appeared before concern entries, but concerns should "
                "always come first (already in zone vs trending into "
                "zone)."
            )


def test_audit_findings_row_previews_highest_severity_first() -> None:
    """LOAD-BEARING: _row_audit_findings populates preview when
    unresolved findings exist; HIGH-severity findings appear before
    LOW-severity ones."""
    from divineos.core.briefing_dashboard import _row_audit_findings

    row = _row_audit_findings()
    if row is not None and row.count > 0:
        assert row.preview, (
            "Audit findings row exists but preview is empty — "
            "discovery-gap fix regressed for audit findings."
        )
        # Each preview line is tagged with [SEVERITY]. The severity
        # ordering is HIGH > MEDIUM > LOW > INFO.
        sev_rank = {"[HIGH]": 0, "[MEDIUM]": 1, "[LOW]": 2, "[INFO]": 3}
        seen_ranks: list[int] = []
        for p in row.preview:
            for tag, rank in sev_rank.items():
                if p.startswith(tag):
                    seen_ranks.append(rank)
                    break
        # Must be monotone non-decreasing (each entry no worse than
        # the prior).
        assert seen_ranks == sorted(seen_ranks), (
            f"Audit-finding preview not sorted by severity ascending; "
            f"got ranks {seen_ranks}."
        )


def test_preregs_row_previews_overdue_first() -> None:
    """LOAD-BEARING: _row_preregs populates preview when open
    pre-registrations exist; overdue ones appear before upcoming
    ones in the preview."""
    from divineos.core.briefing_dashboard import _row_preregs

    row = _row_preregs()
    if row is not None and row.count > 0:
        assert row.preview, (
            "Preregs row exists but preview is empty — discovery-gap "
            "fix regressed for preregs."
        )
        overdue_idxs = [
            i for i, p in enumerate(row.preview) if p.startswith("[overdue")
        ]
        upcoming_idxs = [
            i for i, p in enumerate(row.preview)
            if p.startswith("[due in") or p.startswith("[no review")
        ]
        if overdue_idxs and upcoming_idxs:
            assert max(overdue_idxs) < min(upcoming_idxs), (
                "Prereg preview ordering regressed: upcoming entries "
                "appeared before overdue entries."
            )
