"""Tests for prereg_candidate_surface — forcing-function surface for pre-reg
discipline. Pinned 2026-05-12; pre-registered as prereg-1974c4f7374b."""

from __future__ import annotations

from unittest.mock import patch

from divineos.core.prereg_candidate_surface import (
    CandidateModule,
    PreregCandidateReport,
    compute_prereg_candidates,
    find_detector_modules,
    matched_module_names,
)


# ─── find_detector_modules ───────────────────────────────────────────


def test_find_detector_modules_returns_known_detectors():
    """The walker should find the operating-loop and self-monitor detectors
    that ship with the repo. This is a real-disk test, not a tmpdir test —
    we want to verify it finds what's actually shipped."""
    modules = find_detector_modules()
    short_names = {m.module_short for m in modules}
    # A few known detectors that ship in core/
    expected_subset = {
        "mirror_monitor",
        "temporal_monitor",
        "warmth_monitor",
        "mechanism_monitor",
        "performative_restraint_monitor",
        "distancing_detector",
        "jargon_dump_detector",
        "sycophancy_detector",
    }
    missing = expected_subset - short_names
    assert not missing, f"Expected detectors missing from walk: {missing}"


def test_find_detector_modules_returns_sorted_order():
    modules = find_detector_modules()
    paths = [m.module_path for m in modules]
    assert paths == sorted(paths), "find_detector_modules should return sorted results"


def test_find_detector_modules_skips_pycache():
    modules = find_detector_modules()
    for m in modules:
        assert "__pycache__" not in m.module_path
        assert not m.module_path.endswith(".pyc")


# ─── matched_module_names ────────────────────────────────────────────


def test_matched_module_names_substring_match():
    """A mechanism string mentioning a module short-name matches it."""
    mechanisms = ["the mirror_monitor will reduce reflection-rate by X"]
    matched = matched_module_names(mechanisms)
    assert "mirror_monitor" in matched


def test_matched_module_names_path_match():
    """A mechanism string mentioning a module path also matches."""
    mechanisms = ["the self_monitor/mirror_monitor module will..."]
    matched = matched_module_names(mechanisms)
    assert "mirror_monitor" in matched


def test_matched_module_names_no_match_returns_empty():
    mechanisms = ["this mechanism doesn't mention any detector at all"]
    matched = matched_module_names(mechanisms)
    assert matched == set()


def test_matched_module_names_empty_mechanisms_returns_empty():
    matched = matched_module_names([])
    assert matched == set()


# ─── compute_prereg_candidates ───────────────────────────────────────


def test_compute_returns_real_unmatched_count():
    """The current state of the repo: many detectors, few pre-regs.
    The report should show a substantial unmatched count (>0)."""
    report = compute_prereg_candidates()
    assert report.total_candidates > 0
    # As of 2026-05-12 we KNOW most detectors lack pre-regs (only 2 in DB).
    # So unmatched should be substantial.
    assert report.unmatched_count > 0
    assert report.unmatched_count <= report.total_candidates


def test_compute_when_all_matched_returns_empty_unmatched():
    """If every detector is mentioned in a pre-reg, unmatched should be 0."""
    # Mock the pre-reg store to return mechanisms mentioning every detector
    real_modules = find_detector_modules()
    mock_preregs = [
        {"mechanism": " ".join(m.module_short for m in real_modules)},
    ]

    with patch(
        "divineos.core.pre_registrations.store.list_pre_registrations",
        return_value=mock_preregs,
    ):
        report = compute_prereg_candidates()
        assert report.unmatched_count == 0
        assert report.matched_count == report.total_candidates


def test_compute_when_no_preregs_everything_unmatched():
    """If the pre-reg store returns nothing, every detector is unmatched."""
    with patch(
        "divineos.core.pre_registrations.store.list_pre_registrations",
        return_value=[],
    ):
        report = compute_prereg_candidates()
        assert report.matched_count == 0
        assert report.unmatched_count == report.total_candidates


def test_compute_handles_prereg_store_failure_gracefully():
    """If the pre-reg store raises, the report should still be returned (with
    everything unmatched — structurally honest about not being able to verify)."""
    with patch(
        "divineos.core.pre_registrations.store.list_pre_registrations",
        side_effect=RuntimeError("DB unavailable"),
    ):
        report = compute_prereg_candidates()
        # Should not crash; should treat as no matches.
        assert report.matched_count == 0
        assert report.unmatched_count == report.total_candidates


def test_report_unmatched_count_property():
    """The unmatched_count property should match len(unmatched)."""
    report = PreregCandidateReport(
        total_candidates=5,
        matched_count=2,
        unmatched=[
            CandidateModule(module_short="a_monitor", module_path="x/a_monitor"),
            CandidateModule(module_short="b_monitor", module_path="x/b_monitor"),
            CandidateModule(module_short="c_monitor", module_path="x/c_monitor"),
        ],
    )
    assert report.unmatched_count == 3


# ─── briefing-dashboard row integration ──────────────────────────────


def test_briefing_dashboard_row_fires_when_unmatched():
    """The _row_prereg_candidates row should produce a DashboardRow when
    unmatched modules exist."""
    from divineos.core.briefing_dashboard import _row_prereg_candidates

    row = _row_prereg_candidates()
    # As of 2026-05-12 we know unmatched > 0 in this repo.
    assert row is not None
    assert row.area == "Pre-reg candidates"
    assert row.count > 0
    assert "prereg" in row.drill_down


def test_briefing_dashboard_row_returns_none_when_fully_matched():
    """When every detector has a matching pre-reg, the row should NOT surface."""
    real_modules = find_detector_modules()
    mock_preregs = [
        {"mechanism": " ".join(m.module_short for m in real_modules)},
    ]

    with patch(
        "divineos.core.pre_registrations.store.list_pre_registrations",
        return_value=mock_preregs,
    ):
        from divineos.core.briefing_dashboard import _row_prereg_candidates

        row = _row_prereg_candidates()
        assert row is None


def test_briefing_dashboard_row_detail_truncates_at_3():
    """When >3 unmatched modules, the detail should show first 3 + count."""
    from divineos.core.briefing_dashboard import _row_prereg_candidates

    row = _row_prereg_candidates()
    if row is None or row.count <= 3:
        # Test only meaningful when there are >3 unmatched
        return
    assert "+" in row.detail and "more" in row.detail
