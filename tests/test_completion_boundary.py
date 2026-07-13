"""Tests for the completion-boundary module (Phase 1b)."""

from __future__ import annotations

import pytest

from divineos.core.completion_boundary import (
    WIRE_STATUS_VALUES,
    list_recent_completions,
    record_completion,
)


def test_record_yes_without_next_succeeds():
    b = record_completion("PR #195", wired="yes")
    assert b.wired == "yes"
    assert b.next_plan is None
    assert b.event_id


def test_record_partial_requires_next():
    with pytest.raises(ValueError, match="next_plan"):
        record_completion("PR #195", wired="partial")


def test_record_no_requires_next():
    with pytest.raises(ValueError, match="next_plan"):
        record_completion("PR #195", wired="no")


def test_record_retracted_requires_next():
    with pytest.raises(ValueError, match="next_plan"):
        record_completion("PR #195", wired="retracted")


def test_record_partial_with_next_succeeds():
    b = record_completion(
        "PR #195",
        wired="partial",
        next_plan="finish wiring next session",
    )
    assert b.wired == "partial"
    assert b.next_plan == "finish wiring next session"


def test_empty_artifact_rejected():
    with pytest.raises(ValueError, match="artifact_reference"):
        record_completion("   ", wired="yes")


def test_invalid_wired_rejected():
    with pytest.raises(ValueError, match="wired"):
        record_completion("PR #195", wired="kinda")


def test_wired_normalized_to_lowercase():
    b = record_completion("PR #195", wired="YES")
    assert b.wired == "yes"


def test_all_four_wire_status_values_accepted():
    for v in WIRE_STATUS_VALUES:
        kwargs = {"wired": v}
        if v != "yes":
            kwargs["next_plan"] = "next step"
        b = record_completion("PR #195", **kwargs)
        assert b.wired == v


def test_list_recent_completions_returns_filed_entries():
    record_completion("PR #999", wired="yes", source="test")
    entries = list_recent_completions(limit=10)
    assert any((e.get("payload") or {}).get("artifact_reference") == "PR #999" for e in entries)


def test_boundary_type_defaults_to_explicit_complete():
    b = record_completion("PR #195", wired="yes")
    assert b.boundary_type == "explicit_complete"


def test_boundary_type_payload_includes_field():
    record_completion("PR #boundary-type-check", wired="yes", boundary_type="pr_merge")
    entries = list_recent_completions(limit=20)
    matching = [
        e
        for e in entries
        if (e.get("payload") or {}).get("artifact_reference") == "PR #boundary-type-check"
    ]
    assert matching, "expected to find the just-filed boundary"
    assert matching[0]["payload"]["boundary_type"] == "pr_merge"


def test_boundary_type_invalid_rejected():
    with pytest.raises(ValueError, match="boundary_type"):
        record_completion("PR #195", wired="yes", boundary_type="bogus_type")


def test_boundary_type_accepts_all_three_values():
    for bt in ("explicit_complete", "pr_merge", "tests_green"):
        b = record_completion(f"artifact-{bt}", wired="yes", boundary_type=bt)
        assert b.boundary_type == bt


def test_list_recent_completions_orders_newest_first():
    """Explicit ordering contract — guards against upstream get_events default changes."""
    import time as _time

    record_completion("PR #order-1", wired="yes")
    _time.sleep(0.01)
    record_completion("PR #order-2", wired="yes")
    _time.sleep(0.01)
    record_completion("PR #order-3", wired="yes")
    entries = list_recent_completions(limit=10)
    arts = [
        (e.get("payload") or {}).get("artifact_reference")
        for e in entries
        if (e.get("payload") or {}).get("artifact_reference", "").startswith("PR #order-")
    ]
    assert arts[:3] == ["PR #order-3", "PR #order-2", "PR #order-1"]


def test_depends_on_round_trip():
    b = record_completion(
        "PR #195",
        wired="partial",
        next_plan="finish 1c",
        depends_on="PR #194",
    )
    assert b.depends_on == "PR #194"
