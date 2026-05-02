"""Tests for the three-mode holding room: receive / dream / silent.

The holding room's core property (dharana — pre-categorical holding)
was extended on 2026-04-23 with modes for generative and private content.
These tests verify:

  - mode='receive' preserves original behavior
  - mode='dream' is stored as fabrication-with-awareness
  - mode='silent' is automatically private
  - private items are excluded from default listings
  - mode filtering works correctly
  - invalid modes raise ValueError
  - convenience wrappers (dream, journal) set the right mode/private
"""

from __future__ import annotations

import os

import pytest

from divineos.core.holding import (
    VALID_MODES,
    dream,
    get_holding,
    hold,
    journal,
)


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Each test gets its own DB via DIVINEOS_DB env var."""
    db_path = tmp_path / "test_event_ledger.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db_path))
    # Force a fresh connection next call
    yield
    if db_path.exists():
        try:
            os.remove(db_path)
        except OSError:
            pass


class TestModeBasics:
    def test_default_mode_is_receive(self) -> None:
        item_id = hold("something arrived")
        items = get_holding()
        assert len(items) == 1
        assert items[0]["mode"] == "receive"
        assert items[0]["private"] is False
        assert items[0]["item_id"] == item_id

    def test_explicit_receive_mode(self) -> None:
        hold("x", mode="receive")
        items = get_holding(mode="receive")
        assert len(items) == 1
        assert items[0]["mode"] == "receive"

    def test_dream_mode_stored_correctly(self) -> None:
        hold("maybe this is how consciousness works", mode="dream")
        items = get_holding(mode="dream")
        assert len(items) == 1
        assert items[0]["mode"] == "dream"
        assert items[0]["private"] is False  # dreams public by default

    def test_silent_mode_is_private_by_default(self) -> None:
        """mode='silent' without explicit private flag should auto-set private=True."""
        hold("just a thought for myself", mode="silent")
        items = get_holding(mode="silent", include_private=True)
        assert len(items) == 1
        assert items[0]["mode"] == "silent"
        assert items[0]["private"] is True

    def test_invalid_mode_raises(self) -> None:
        with pytest.raises(ValueError, match="mode must be one of"):
            hold("x", mode="invalid_mode")

    def test_valid_modes_constant(self) -> None:
        assert "receive" in VALID_MODES
        assert "dream" in VALID_MODES
        assert "silent" in VALID_MODES


class TestPrivacyFiltering:
    def test_private_items_excluded_by_default(self) -> None:
        hold("public", mode="receive")
        hold("secret", mode="receive", private=True)
        items = get_holding()
        contents = [i["content"] for i in items]
        assert "public" in contents
        assert "secret" not in contents

    def test_private_items_included_when_asked(self) -> None:
        hold("public", mode="receive")
        hold("secret", mode="receive", private=True)
        items = get_holding(include_private=True)
        contents = [i["content"] for i in items]
        assert "public" in contents
        assert "secret" in contents

    def test_silent_items_hidden_from_default_listing(self) -> None:
        """Silent items are private and should not show in default listing."""
        hold("public", mode="receive")
        hold("alone", mode="silent")
        items = get_holding()
        contents = [i["content"] for i in items]
        assert "public" in contents
        assert "alone" not in contents

    def test_dreams_visible_by_default(self) -> None:
        """Dreams are public unless explicitly set private."""
        hold("maybe x is true", mode="dream")
        items = get_holding()
        assert any(i["content"] == "maybe x is true" for i in items)

    def test_private_dream_hidden_from_default(self) -> None:
        hold("secret dream", mode="dream", private=True)
        items = get_holding()
        assert not any(i["content"] == "secret dream" for i in items)
        # but visible when privacy is opted in
        items_priv = get_holding(include_private=True)
        assert any(i["content"] == "secret dream" for i in items_priv)


class TestModeFiltering:
    def test_filter_by_dream(self) -> None:
        hold("received thing", mode="receive")
        hold("dream thing", mode="dream")
        hold("silent thing", mode="silent")
        items = get_holding(mode="dream", include_private=True)
        assert len(items) == 1
        assert items[0]["content"] == "dream thing"

    def test_filter_by_silent_requires_include_private(self) -> None:
        hold("silent thing", mode="silent")
        # Without include_private, silent items are hidden (they're private)
        items = get_holding(mode="silent")
        assert len(items) == 0
        # With include_private, they show
        items_priv = get_holding(mode="silent", include_private=True)
        assert len(items_priv) == 1


class TestConvenienceWrappers:
    def test_dream_wrapper_sets_mode(self) -> None:
        dream("hypothesis")
        items = get_holding(mode="dream")
        assert len(items) == 1
        assert items[0]["content"] == "hypothesis"

    def test_dream_wrapper_public_by_default(self) -> None:
        dream("public hypothesis")
        items = get_holding()
        assert any(i["content"] == "public hypothesis" for i in items)

    def test_dream_wrapper_can_be_private(self) -> None:
        dream("secret hypothesis", private=True)
        items = get_holding()
        assert not any(i["content"] == "secret hypothesis" for i in items)
        items_priv = get_holding(include_private=True)
        assert any(i["content"] == "secret hypothesis" for i in items_priv)

    def test_journal_wrapper_sets_mode_and_private(self) -> None:
        journal("just for me")
        items = get_holding(mode="silent", include_private=True)
        assert len(items) == 1
        assert items[0]["content"] == "just for me"
        assert items[0]["private"] is True

    def test_journal_wrapper_hidden_by_default(self) -> None:
        journal("my thought")
        items = get_holding()
        assert not any(i["content"] == "my thought" for i in items)
