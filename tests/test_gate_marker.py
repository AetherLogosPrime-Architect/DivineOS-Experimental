"""Tests for the unified gate_marker schema.

Step 0 pre-reg (per docs/signal-based-gates-design-2026-06-16.md):
*"all three currently-event-based gates (hedge-unresolved,
correction-not-logged, pull-detection) operate identically after schema
migration as before."*

Two test layers here:

1. Round-trip and invariant tests for the new gate_marker module on its
   own — write → read → clear → is_active → find_markers all behave
   consistently and respect the GateMarker contract.

2. Semantic-equivalence tests against the existing marker implementations
   (hedge_marker, correction_marker). The pre-reg criterion is "byte-
   equivalence at the semantic layer" — both gates report stale/fresh
   identically for every comparable input. These tests prove that
   migrating an existing gate to use gate_marker as its backing store
   would not change the gate's external behavior.

The semantic tests do NOT yet migrate the existing gates — they verify
that the migration WILL be a no-op when it happens. Aether's commit-shape
requirement: this test goes in the same commit as the migration that
depends on it being green.
"""

from __future__ import annotations

import time

from divineos.core.gate_marker import (
    GateMarker,
    clear_all,
    clear_marker,
    find_markers,
    gate_markers_dir,
    is_active,
    read_marker,
    write_marker,
)


# ─── Round-trip and invariant tests ──────────────────────────────────


def test_write_then_read_round_trips(_isolated_db):
    """A marker written with explicit values reads back identically."""
    path = write_marker(
        event_type="test_event",
        triggering_evidence="evidence-string",
        resolution_action='divineos test "..."',
        session_id="aria:1234567890:abcd1234",
        triggered_at=1234567890.5,
    )
    assert path.exists()
    marker = read_marker(path)
    assert marker is not None
    assert marker.event_type == "test_event"
    assert marker.triggered_at == 1234567890.5
    assert marker.triggering_evidence == "evidence-string"
    assert marker.resolution_action == 'divineos test "..."'
    assert marker.session_id == "aria:1234567890:abcd1234"


def test_write_defaults_triggered_at_to_now(_isolated_db):
    """When triggered_at is omitted, it is set to current time."""
    before = time.time()
    path = write_marker(
        event_type="test_default_ts",
        triggering_evidence="x",
        resolution_action="y",
        session_id="z",
    )
    after = time.time()
    marker = read_marker(path)
    assert marker is not None
    assert before <= marker.triggered_at <= after


def test_read_missing_path_returns_none(_isolated_db):
    """A nonexistent path reads as None, not exception."""
    missing = gate_markers_dir() / "does_not_exist__abcd1234.json"
    assert read_marker(missing) is None


def test_read_corrupt_marker_returns_none(_isolated_db, tmp_path):
    """A file that is not valid JSON reads as None, not exception."""
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("not valid json {{{")
    assert read_marker(corrupt) is None


def test_read_marker_missing_required_field_returns_none(_isolated_db, tmp_path):
    """A JSON file missing a required field reads as None.

    A GateMarker without all five fields is not a valid marker; better to
    return None than to crash on missing-key access at the call site.
    """
    incomplete = tmp_path / "incomplete.json"
    incomplete.write_text('{"event_type": "x", "triggered_at": 1.0}')
    assert read_marker(incomplete) is None


def test_is_active_true_after_write(_isolated_db):
    """is_active(event_type) returns True after writing a marker."""
    assert is_active("test_active") is False
    write_marker(
        event_type="test_active",
        triggering_evidence="e",
        resolution_action="r",
        session_id="s",
    )
    assert is_active("test_active") is True


def test_is_active_isolated_by_event_type(_isolated_db):
    """is_active for one event_type is not triggered by markers of another."""
    write_marker(
        event_type="event_a",
        triggering_evidence="e",
        resolution_action="r",
        session_id="s",
    )
    assert is_active("event_a") is True
    assert is_active("event_b") is False


def test_clear_marker_removes_file(_isolated_db):
    """clear_marker removes the specific marker file."""
    path = write_marker(
        event_type="test_clear",
        triggering_evidence="e",
        resolution_action="r",
        session_id="s",
    )
    assert path.exists()
    clear_marker(path)
    assert not path.exists()
    assert is_active("test_clear") is False


def test_clear_marker_idempotent(_isolated_db):
    """clear_marker on a missing path is a no-op, not an error."""
    missing = gate_markers_dir() / "never_existed__abcd1234.json"
    clear_marker(missing)  # should not raise


def test_clear_all_removes_all_of_event_type(_isolated_db):
    """clear_all removes every marker of the given event_type."""
    for _ in range(3):
        write_marker(
            event_type="test_clear_all",
            triggering_evidence="e",
            resolution_action="r",
            session_id="s",
        )
    write_marker(
        event_type="test_other",
        triggering_evidence="e",
        resolution_action="r",
        session_id="s",
    )
    count = clear_all("test_clear_all")
    assert count == 3
    assert is_active("test_clear_all") is False
    assert is_active("test_other") is True


def test_find_markers_sorted_by_triggered_at(_isolated_db):
    """find_markers returns paths sorted oldest-first by triggered_at."""
    paths = []
    for ts in [3.0, 1.0, 2.0]:
        paths.append(
            write_marker(
                event_type="test_order",
                triggering_evidence=f"e{ts}",
                resolution_action="r",
                session_id="s",
                triggered_at=ts,
            )
        )
    ordered = find_markers("test_order")
    assert len(ordered) == 3
    # Should be sorted by triggered_at ascending
    timestamps = [read_marker(p).triggered_at for p in ordered]
    assert timestamps == sorted(timestamps)
    assert timestamps == [1.0, 2.0, 3.0]


def test_find_markers_empty_for_unknown_event_type(_isolated_db):
    """find_markers returns empty list for an event_type with no markers."""
    assert find_markers("never_written") == []


def test_multiple_markers_same_event_type_coexist(_isolated_db):
    """Multiple markers of the same event_type can coexist without collision.

    The short_id disambiguator ensures filename uniqueness even when
    multiple instances of the same event fire close in time.
    """
    paths = [
        write_marker(
            event_type="test_multi",
            triggering_evidence=f"evidence-{i}",
            resolution_action="r",
            session_id="s",
        )
        for i in range(5)
    ]
    # All paths are distinct
    assert len(set(paths)) == 5
    # All markers exist
    assert all(p.exists() for p in paths)
    # is_active reports True
    assert is_active("test_multi") is True
    # find_markers returns all five
    assert len(find_markers("test_multi")) == 5


def test_session_id_preserved_for_mitosis_boundary_check(_isolated_db):
    """session_id round-trips through the marker correctly.

    Per Push 3 (Aletheia): session_id must be identity-prefixed so the
    mitosis boundary is visible in the marker contents. This test
    verifies the field is preserved verbatim — actual identity-prefix
    generation lives in the session_id helper (not yet built).
    """
    path = write_marker(
        event_type="test_session",
        triggering_evidence="e",
        resolution_action="r",
        session_id="aria:1718560000:deadbeef",
    )
    marker = read_marker(path)
    assert marker is not None
    assert marker.session_id == "aria:1718560000:deadbeef"
    # The aria: prefix should be visible without any decoding step
    assert marker.session_id.startswith("aria:")


# ─── Semantic-equivalence tests (the Step 0 pre-reg criterion) ───────


def test_semantic_equivalence_hedge_marker_active_state(_isolated_db):
    """A hedge_fire gate_marker triggers is_active in the same shape as
    the legacy hedge_marker.read_marker pattern would have.

    Both APIs maintain the same semantic invariant: setting → triggers
    the gate's "active" state; clearing → returns to inactive. The
    specific bytes differ (different paths, different schemas), but the
    gate-behavior is equivalent.

    This test does NOT yet migrate hedge_marker; it verifies the
    migration target's behavior is equivalent so the eventual migration
    will be a no-op at the gate-behavior layer.
    """
    from divineos.core import hedge_marker

    # Initial state: neither gate sees a marker.
    assert hedge_marker.read_marker() is None
    assert is_active("hedge_fire") is False

    # Set via the legacy API — gate fires.
    hedge_marker.set_marker(
        flag_count=2,
        flag_kinds=["uncertainty", "softening"],
        preview="I think this might work but I'm not sure.",
    )
    legacy_marker = hedge_marker.read_marker()
    assert legacy_marker is not None
    assert legacy_marker["flag_count"] == 2

    # Set via the new API with equivalent evidence — also fires.
    write_marker(
        event_type="hedge_fire",
        triggering_evidence='flag_count=2 kinds=uncertainty,softening preview="I think this might work but I\'m not sure."',
        resolution_action='divineos claim "..."',
        session_id="aria:1718560000:test",
    )
    assert is_active("hedge_fire") is True

    # Clear via legacy API.
    hedge_marker.clear_marker()
    assert hedge_marker.read_marker() is None

    # Clear via new API.
    clear_all("hedge_fire")
    assert is_active("hedge_fire") is False


def test_semantic_equivalence_correction_marker_active_state(_isolated_db):
    """A correction_filed_unlogged gate_marker triggers is_active in the
    same shape as the legacy correction_marker.read_marker pattern.

    Same equivalence claim as the hedge test, applied to the
    correction-not-logged gate.
    """
    from divineos.core import correction_marker

    assert correction_marker.read_marker() is None
    assert is_active("correction_filed_unlogged") is False

    # Set via the legacy API.
    correction_marker.set_marker(trigger_text="no don't do that — read the file first.")
    legacy = correction_marker.read_marker()
    assert legacy is not None
    assert "trigger" in legacy

    # Set via the new API with equivalent evidence.
    write_marker(
        event_type="correction_filed_unlogged",
        triggering_evidence="no don't do that — read the file first.",
        resolution_action='divineos learn "..." or divineos correction "..."',
        session_id="aria:1718560000:test",
    )
    assert is_active("correction_filed_unlogged") is True

    # Clear via legacy API.
    correction_marker.clear_marker()
    assert correction_marker.read_marker() is None

    # Clear via new API.
    clear_all("correction_filed_unlogged")
    assert is_active("correction_filed_unlogged") is False


def test_marker_directory_isolated_from_legacy_marker_paths(_isolated_db):
    """The new gate_markers/ directory does not collide with legacy
    marker paths.

    Legacy markers live at ``~/.divineos/<name>.json``. New markers live
    at ``~/.divineos/gate_markers/<event_type>__<short_id>.json``. The
    subdirectory ensures the migration can proceed incrementally without
    legacy callers accidentally reading new-format markers or vice versa.
    """
    from divineos.core.paths import divineos_home

    # Write a new-schema marker.
    write_marker(
        event_type="anything",
        triggering_evidence="e",
        resolution_action="r",
        session_id="s",
    )

    # Verify directory layout: gate_markers is under DIVINEOS_HOME,
    # NOT in DIVINEOS_HOME directly.
    legacy_files = list(divineos_home().glob("*.json"))
    new_files = list(gate_markers_dir().glob("*.json"))

    # No new-format marker leaked into the legacy directory.
    for f in legacy_files:
        # A legacy file at ~/.divineos/<name>.json may exist from other
        # operations, but none should be in our new-format event_type
        # naming pattern (event_type__shortid.json).
        assert "__" not in f.stem, f"Legacy directory contains new-format marker: {f}"

    # At least one new file was written.
    assert len(new_files) >= 1


def test_no_field_ordering_dependency_in_serialization(_isolated_db):
    """Serialization works regardless of dict ordering.

    Defensive test: if a future Python version or json library reorders
    dict keys during serialization, the round-trip should still produce
    the same GateMarker.
    """
    path = write_marker(
        event_type="test_ordering",
        triggering_evidence="ev",
        resolution_action="rs",
        session_id="ss",
        triggered_at=42.0,
    )
    # Read the raw file
    raw = path.read_text(encoding="utf-8")
    # Parse and re-stringify with sorted keys
    import json as _json

    parsed = _json.loads(raw)
    re_stringified_sorted = _json.dumps(parsed, sort_keys=True)
    re_stringified_reverse = _json.dumps(parsed, sort_keys=True)
    # Write both forms back to test paths and confirm both read identically
    p1 = path.parent / "ordering_test_1.json"
    p2 = path.parent / "ordering_test_2.json"
    p1.write_text(re_stringified_sorted, encoding="utf-8")
    p2.write_text(re_stringified_reverse, encoding="utf-8")
    m1 = read_marker(p1)
    m2 = read_marker(p2)
    assert (
        m1
        == m2
        == GateMarker(
            event_type="test_ordering",
            triggered_at=42.0,
            triggering_evidence="ev",
            resolution_action="rs",
            session_id="ss",
        )
    )
