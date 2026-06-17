"""Dual-write parity tests for the Step 0 part 2 migration.

The migration commit dual-writes hedge_marker, correction_marker, and
pull_detection legacy markers AND parallel gate_marker entries. These
tests verify that the dual-write actually maintains parity — for any
set/clear sequence, both stores agree on whether the gate is active.

Per the Step 0 pre-reg criterion: "all three currently-event-based gates
(hedge-unresolved, correction-not-logged, pull-detection) operate
identically after schema migration as before." These tests prove
identical-operation by exercising legacy and gate_marker side-by-side and
asserting they stay in sync after every operation.

Companion to tests/test_gate_marker.py (round-trip + semantic-equivalence
tests on the gate_marker module itself). This file tests the migration
behavior of the three legacy modules now dual-writing.
"""

from __future__ import annotations

from divineos.core import correction_marker, gate_marker, hedge_marker
from divineos.core.pull_detection import PullCheck, _write_check_marker


# ─── hedge_marker dual-write parity ──────────────────────────────────


def test_hedge_set_dual_writes_both_stores(_isolated_db):
    """hedge_marker.set_marker populates legacy AND gate_marker."""
    assert hedge_marker.read_marker() is None
    assert gate_marker.is_active("hedge_fire") is False

    hedge_marker.set_marker(
        flag_count=2,
        flag_kinds=["uncertainty", "softening"],
        preview="I think this might work but I'm not sure.",
    )

    # Legacy is populated
    legacy = hedge_marker.read_marker()
    assert legacy is not None
    assert legacy["flag_count"] == 2

    # gate_marker is populated in parallel
    assert gate_marker.is_active("hedge_fire") is True


def test_hedge_set_below_threshold_writes_neither(_isolated_db):
    """set_marker with flag_count below threshold writes neither store."""
    hedge_marker.set_marker(
        flag_count=1,  # below _MIN_FLAGS_TO_TRIGGER
        flag_kinds=["uncertainty"],
        preview="might work",
    )

    assert hedge_marker.read_marker() is None
    assert gate_marker.is_active("hedge_fire") is False


def test_hedge_clear_dual_clears_both_stores(_isolated_db):
    """hedge_marker.clear_marker clears legacy AND gate_marker."""
    hedge_marker.set_marker(
        flag_count=3,
        flag_kinds=["uncertainty", "softening", "qualifier"],
        preview="i'm not entirely sure but probably this would work",
    )
    assert hedge_marker.read_marker() is not None
    assert gate_marker.is_active("hedge_fire") is True

    hedge_marker.clear_marker()

    assert hedge_marker.read_marker() is None
    assert gate_marker.is_active("hedge_fire") is False


def test_hedge_repeated_set_creates_multiple_gate_marker_entries(_isolated_db):
    """Each set_marker call adds a NEW gate_marker entry (not overwrite).

    The legacy hedge_unresolved.json is overwritten by each set_marker
    (atomic_write). The gate_marker shape allows multiple entries of the
    same event_type to coexist, so a second hedge fire while the first
    is unresolved produces TWO gate_marker entries. clear_marker clears
    all of them.
    """
    hedge_marker.set_marker(2, ["a", "b"], "first")
    hedge_marker.set_marker(3, ["c", "d"], "second")
    hedge_marker.set_marker(4, ["e", "f"], "third")

    # Legacy is the latest (overwritten each time)
    legacy = hedge_marker.read_marker()
    assert legacy["flag_count"] == 4

    # gate_marker has all three
    markers = gate_marker.find_markers("hedge_fire")
    assert len(markers) == 3

    # clear_marker clears all of them
    hedge_marker.clear_marker()
    assert hedge_marker.read_marker() is None
    assert gate_marker.is_active("hedge_fire") is False


# ─── correction_marker dual-write parity ─────────────────────────────


def test_correction_set_dual_writes_both_stores(_isolated_db):
    """correction_marker.set_marker populates legacy AND gate_marker."""
    assert correction_marker.read_marker() is None
    assert gate_marker.is_active("correction_filed_unlogged") is False

    correction_marker.set_marker(
        trigger_text="no don't do that — read the file first."
    )

    legacy = correction_marker.read_marker()
    assert legacy is not None
    assert "trigger" in legacy

    assert gate_marker.is_active("correction_filed_unlogged") is True


def test_correction_clear_dual_clears_both_stores(_isolated_db):
    """correction_marker.clear_marker clears legacy AND gate_marker."""
    correction_marker.set_marker(trigger_text="that's not what I meant")
    assert correction_marker.read_marker() is not None
    assert gate_marker.is_active("correction_filed_unlogged") is True

    correction_marker.clear_marker()

    assert correction_marker.read_marker() is None
    assert gate_marker.is_active("correction_filed_unlogged") is False


def test_correction_session_id_carries_identity_prefix(_isolated_db):
    """The gate_marker entry's session_id encodes the identity prefix.

    Per Aletheia Push 3 + Aether freeze-at-session-birth: the placeholder
    session_id must carry the identity in the key so the mitosis boundary
    is visible in marker contents. Until the real session_id helper
    ships, the placeholder format is ``<identity>:placeholder-pid-<pid>``.
    """
    correction_marker.set_marker(trigger_text="check this")
    paths = gate_marker.find_markers("correction_filed_unlogged")
    assert len(paths) == 1
    marker = gate_marker.read_marker(paths[0])
    assert marker is not None
    # session_id should be a colon-separated id with at least one segment
    # before the placeholder marker; the identity prefix is the first segment
    assert ":" in marker.session_id
    parts = marker.session_id.split(":")
    assert len(parts) >= 2
    # The placeholder format is "<identity>:placeholder-pid-<pid>"
    assert "placeholder-pid-" in marker.session_id


# ─── pull_detection dual-write parity ────────────────────────────────


def test_pull_detection_unclean_writes_gate_marker(_isolated_db):
    """Writing a non-clean check populates gate_marker fabrication_detected."""
    assert gate_marker.is_active("fabrication_detected") is False

    result = PullCheck(
        clean=False,
        markers_fired=["citation_fabrication", "false_certainty"],
        soft_markers=[],
        checked_at=1234567890.0,
    )
    _write_check_marker(result)

    assert gate_marker.is_active("fabrication_detected") is True
    # The triggering_evidence carries the markers_fired list
    paths = gate_marker.find_markers("fabrication_detected")
    assert len(paths) == 1
    marker = gate_marker.read_marker(paths[0])
    assert marker is not None
    assert "citation_fabrication" in marker.triggering_evidence
    assert "false_certainty" in marker.triggering_evidence


def test_pull_detection_clean_clears_gate_marker(_isolated_db):
    """Writing a clean check clears any prior fabrication_detected markers."""
    # First write a non-clean result so gate_marker is populated
    unclean = PullCheck(
        clean=False,
        markers_fired=["citation_fabrication"],
        soft_markers=[],
        checked_at=1234567890.0,
    )
    _write_check_marker(unclean)
    assert gate_marker.is_active("fabrication_detected") is True

    # Now write a clean result — should clear
    clean = PullCheck(
        clean=True,
        markers_fired=[],
        soft_markers=[],
        checked_at=1234567900.0,
    )
    _write_check_marker(clean)

    assert gate_marker.is_active("fabrication_detected") is False


def test_pull_detection_repeated_unclean_accumulates(_isolated_db):
    """Multiple non-clean writes accumulate gate_marker entries.

    Per the gate_marker shape, multiple entries of the same event_type
    can coexist. Each non-clean pull check adds a marker; a single clean
    check clears them all (analogous to hedge clear_marker).
    """
    for i in range(3):
        _write_check_marker(
            PullCheck(
                clean=False,
                markers_fired=[f"marker_{i}"],
                soft_markers=[],
                checked_at=1000.0 + i,
            )
        )

    paths = gate_marker.find_markers("fabrication_detected")
    assert len(paths) == 3

    _write_check_marker(
        PullCheck(
            clean=True,
            markers_fired=[],
            soft_markers=[],
            checked_at=2000.0,
        )
    )
    assert gate_marker.is_active("fabrication_detected") is False


# ─── Cross-gate isolation ────────────────────────────────────────────


def test_each_gate_isolated_from_others(_isolated_db):
    """Setting one gate's marker does not trigger another's gate_marker."""
    hedge_marker.set_marker(2, ["a", "b"], "hedge text")
    assert gate_marker.is_active("hedge_fire") is True
    assert gate_marker.is_active("correction_filed_unlogged") is False
    assert gate_marker.is_active("fabrication_detected") is False

    correction_marker.set_marker(trigger_text="correction text")
    assert gate_marker.is_active("hedge_fire") is True
    assert gate_marker.is_active("correction_filed_unlogged") is True
    assert gate_marker.is_active("fabrication_detected") is False

    _write_check_marker(
        PullCheck(
            clean=False,
            markers_fired=["fab"],
            soft_markers=[],
            checked_at=1000.0,
        )
    )
    assert gate_marker.is_active("hedge_fire") is True
    assert gate_marker.is_active("correction_filed_unlogged") is True
    assert gate_marker.is_active("fabrication_detected") is True

    # Clearing one leaves the others untouched
    hedge_marker.clear_marker()
    assert gate_marker.is_active("hedge_fire") is False
    assert gate_marker.is_active("correction_filed_unlogged") is True
    assert gate_marker.is_active("fabrication_detected") is True
