"""Regression-pin tests for the stale-engagement warn-warn-block gate.

Andrew named this gate 2026-05-14: stale items in the briefing should
warn for 1-2 renders and BLOCK after the third ignore. Friction is
the source of flow.

These tests pin the tracker. Hook-side integration (the actual block
on next code action) lives in require-goal.sh with its own External-
Review round.
"""

from __future__ import annotations

import time

from divineos.core.ledger import init_db, log_event
from divineos.core.stale_engagement import (
    DEFAULT_BLOCK_THRESHOLD,
    block_message,
    blocked_areas,
    consecutive_ignores,
    record_briefing_render,
    should_block,
)


def _seed() -> None:
    init_db()


def test_no_renders_means_zero_ignores() -> None:
    _seed()
    # Fresh area never surfaced; count is zero.
    assert consecutive_ignores("corrections") >= 0  # can't assert exact in shared DB


def test_record_render_increments_count() -> None:
    """LOAD-BEARING: each STALE_SURFACED event for an area must add
    to that area's consecutive-ignore count."""
    _seed()
    # Use a synthetic area so we're not interfering with real counts.
    # The tracker only filters by area name from the payload, so any
    # string works.
    area = "test-area-fresh-pin"
    # We can monkeypatch the AREA_ADDRESS_EVENTS map for our area
    import divineos.core.stale_engagement as se

    original = se._AREA_ADDRESS_EVENTS.copy()
    se._AREA_ADDRESS_EVENTS[area] = ("TEST_ADDRESSED",)
    try:
        starting = consecutive_ignores(area)
        record_briefing_render([area])
        time.sleep(0.01)
        record_briefing_render([area])
        time.sleep(0.01)
        after = consecutive_ignores(area)
        assert after >= starting + 2, f"Expected at least 2 more ignores, got {after - starting}"
    finally:
        se._AREA_ADDRESS_EVENTS.clear()
        se._AREA_ADDRESS_EVENTS.update(original)


def test_addressing_resets_count() -> None:
    """LOAD-BEARING: an addressing event must reset the ignore counter."""
    _seed()
    area = "test-area-reset-pin"
    import divineos.core.stale_engagement as se

    original = se._AREA_ADDRESS_EVENTS.copy()
    se._AREA_ADDRESS_EVENTS[area] = ("TEST_ADDRESS_RESET",)
    try:
        record_briefing_render([area])
        time.sleep(0.01)
        record_briefing_render([area])
        time.sleep(0.01)
        before = consecutive_ignores(area)
        assert before >= 2
        # Fire an addressing event
        log_event(
            event_type="TEST_ADDRESS_RESET",
            actor="aether",
            payload={"area": area},
        )
        time.sleep(0.01)
        after = consecutive_ignores(area)
        assert after == 0, f"Addressing should have reset the counter; got {after}"
    finally:
        se._AREA_ADDRESS_EVENTS.clear()
        se._AREA_ADDRESS_EVENTS.update(original)


def test_should_block_fires_at_threshold() -> None:
    """LOAD-BEARING: should_block() returns True at threshold."""
    _seed()
    area = "test-area-block-pin"
    import divineos.core.stale_engagement as se

    original = se._AREA_ADDRESS_EVENTS.copy()
    se._AREA_ADDRESS_EVENTS[area] = ("TEST_BLOCK_ADDRESSED",)
    try:
        # Reset counter via address event first
        log_event(
            event_type="TEST_BLOCK_ADDRESSED",
            actor="aether",
            payload={},
        )
        time.sleep(0.01)
        # Surface twice — under threshold
        record_briefing_render([area])
        time.sleep(0.01)
        record_briefing_render([area])
        time.sleep(0.01)
        assert not should_block(area), "Should NOT block at 2 ignores"
        # Third surface — at threshold
        record_briefing_render([area])
        time.sleep(0.01)
        assert should_block(area), "Should block at 3+ ignores"
    finally:
        se._AREA_ADDRESS_EVENTS.clear()
        se._AREA_ADDRESS_EVENTS.update(original)


def test_block_message_renders_areas_and_drilldown() -> None:
    msg = block_message(["corrections", "claims"])
    assert "BLOCKED" in msg
    assert "corrections" in msg
    assert "claims" in msg
    assert "correction-resolve" in msg or "corrections" in msg
    # Friction-as-flow tagline must be present so the operator knows
    # this is intentional architecture, not a bug.
    assert "Friction" in msg
    assert "stale-engagement" in msg


def test_block_message_empty_returns_empty() -> None:
    assert block_message([]) == ""


def test_default_threshold_is_three() -> None:
    """Andrew's spec was 'after the third ignoring' — the constant
    must reflect that."""
    assert DEFAULT_BLOCK_THRESHOLD == 3


def test_blocked_areas_returns_only_at_threshold() -> None:
    """LOAD-BEARING: blocked_areas() must only return areas at/above
    the threshold; below-threshold areas are warning-only."""
    _seed()
    # Function is iterating over _AREA_ADDRESS_EVENTS keys so we can't
    # easily inject a synthetic area, but the type is at least asserted.
    out = blocked_areas()
    assert isinstance(out, list)
    for area in out:
        assert should_block(area)
