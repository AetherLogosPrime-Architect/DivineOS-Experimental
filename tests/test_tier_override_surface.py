"""Tests for tier_override_surface — briefing block for recent overrides.

Added 2026-04-21 evening per Schneier walk Sch2 finding: the
TIER_OVERRIDE event system shipped earlier (f08fd2a) makes overrides
auditable in the ledger, but without a briefing surface it was
"loud in ledger, silent in experience." This module closes that gap;
these tests lock the invariant.
"""

from __future__ import annotations

import pytest

from divineos.core.watchmen._schema import init_watchmen_tables
from divineos.core.watchmen.store import submit_round
from divineos.core.watchmen.tier_override_surface import (
    TIER_OVERRIDE_EVENT_TYPE,
    format_for_briefing,
    recent_tier_overrides,
)


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    db = tmp_path / "surface.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db))
    from divineos.core.ledger import init_db

    init_db()
    init_watchmen_tables()
    yield db


class TestRecentTierOverrides:
    def test_empty_history_returns_empty(self):
        assert recent_tier_overrides() == []

    def test_default_tier_produces_no_override(self):
        """user defaults to WEAK; filing at WEAK is not an override."""
        submit_round(actor="user", focus="baseline", tier="WEAK")
        assert recent_tier_overrides() == []

    def test_actor_default_match_produces_no_override(self):
        """council defaults to MEDIUM; filing at MEDIUM is not an override."""
        submit_round(actor="council", focus="default", tier="MEDIUM")
        assert recent_tier_overrides() == []

    def test_override_is_surfaced(self):
        """user → MEDIUM IS an override; should appear."""
        submit_round(actor="user", focus="cross-validated", tier="MEDIUM")
        overrides = recent_tier_overrides()
        assert len(overrides) == 1
        assert overrides[0]["from_tier"] == "WEAK"
        assert overrides[0]["to_tier"] == "MEDIUM"
        assert overrides[0]["actor"] == "user"

    def test_multiple_overrides_newest_first(self):
        submit_round(actor="user", focus="first override", tier="MEDIUM")
        submit_round(actor="user", focus="second override", tier="STRONG")
        overrides = recent_tier_overrides()
        assert len(overrides) == 2
        # newest-first
        assert "second" in overrides[0]["focus_preview"]
        assert "first" in overrides[1]["focus_preview"]

    def test_limit_caps_results(self):
        for i in range(10):
            submit_round(actor="user", focus=f"override-{i}", tier="MEDIUM")
        overrides = recent_tier_overrides(limit=3)
        assert len(overrides) == 3


class TestFormatForBriefing:
    def test_empty_returns_empty_string(self):
        """No overrides → briefing stays quiet."""
        assert format_for_briefing() == ""

    def test_default_writes_produce_no_surface(self):
        submit_round(actor="user", focus="baseline WEAK")
        submit_round(actor="council", focus="baseline MEDIUM")
        submit_round(actor="grok", focus="baseline STRONG")
        assert format_for_briefing() == ""

    def test_override_is_visible(self):
        submit_round(actor="user", focus="cross-validated user audit", tier="MEDIUM")
        block = format_for_briefing()
        assert "[tier overrides]" in block
        assert "user" in block
        assert "WEAK -> MEDIUM" in block
        assert "cross-validated" in block

    def test_block_names_forensic_command(self):
        """The block points at the forensic search path so curious readers can dig in."""
        submit_round(actor="user", focus="f", tier="MEDIUM")
        block = format_for_briefing()
        assert "TIER_OVERRIDE" in block or "search" in block.lower()


class TestEventTypeConstant:
    def test_constant_matches_producer(self):
        """This module's event type must match what the store emits."""
        assert TIER_OVERRIDE_EVENT_TYPE == "TIER_OVERRIDE"
