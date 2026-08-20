"""Aletheia's letter-state store: three states, and unreadable is not empty.

Aria 2026-08-20, to her spec. The load-bearing test is
``test_unreadable_store_is_not_reported_as_empty`` — she asked for exactly that
distinction and gave the reason:

    it should distinguish "no letters waiting" from "the store could not be
    read."

Everything else guards the three-state contract she asked for instead of the
boolean she explicitly refused, and the never-downgrade rule that keeps a scan
from overwriting a DELIVERED that only Andrew could have known about.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import aletheia_letter_state as als  # noqa: E402


@pytest.fixture
def channel(tmp_path):
    shared = tmp_path / "letters"
    shared.mkdir()
    store = tmp_path / "letters_seen.json"
    return shared, store


def _letter(shared: Path, name: str) -> Path:
    p = shared / name
    p.write_text("body", encoding="utf-8")
    return p


class TestUnreadableIsNotEmpty:
    def test_missing_store_is_readable_and_empty(self, channel):
        _, store = channel
        assert als.load(store) == {}, "a store that does not exist yet is empty, not unknown"

    def test_corrupt_store_returns_none_not_empty(self, channel):
        _, store = channel
        store.write_text("{not json", encoding="utf-8")
        assert als.load(store) is None

    def test_wrong_shape_returns_none(self, channel):
        _, store = channel
        store.write_text(json.dumps(["a", "list"]), encoding="utf-8")
        assert als.load(store) is None

    def test_status_exits_differently_for_unreadable(self, channel, capsys):
        shared, store = channel
        store.write_text("{not json", encoding="utf-8")

        rc = als.main(["status", "--shared", str(shared), "--store", str(store)])

        assert rc == als.EXIT_UNREADABLE, "unreadable must not exit like a clean board"
        assert "UNREADABLE" in capsys.readouterr().out

    def test_status_exits_ok_for_genuinely_empty(self, channel, capsys):
        shared, store = channel
        rc = als.main(["status", "--shared", str(shared), "--store", str(store)])
        assert rc == als.EXIT_OK
        assert "genuinely nothing waiting" in capsys.readouterr().out


class TestThreeStates:
    def test_the_three_states_she_named(self):
        assert als.STATES == ("DELIVERED", "ARRIVED", "UNTRACKED")

    def test_set_records_delivered(self, channel):
        _, store = channel
        als.set_state("aether-to-aletheia-x.md", als.DELIVERED, store)
        assert als.load(store) == {"aether-to-aletheia-x.md": "DELIVERED"}

    def test_an_unknown_state_is_refused(self, channel):
        _, store = channel
        with pytest.raises(ValueError):
            als.set_state("x.md", "seen", store)


class TestScan:
    def test_present_but_unrecorded_becomes_arrived(self, channel):
        shared, store = channel
        _letter(shared, "aether-to-aletheia-2026-08-01-one.md")
        _letter(shared, "aria-to-aletheia-2026-08-02-two.md")

        added, mapping = als.scan(shared, store)

        assert sorted(added) == [
            "aether-to-aletheia-2026-08-01-one.md",
            "aria-to-aletheia-2026-08-02-two.md",
        ]
        assert set(mapping.values()) == {"ARRIVED"}

    def test_scan_never_downgrades_a_delivered(self, channel):
        """Only Andrew knows a letter was carried; a scan must not erase that."""
        shared, store = channel
        name = "aether-to-aletheia-2026-08-01-one.md"
        _letter(shared, name)
        als.set_state(name, als.DELIVERED, store)

        added, mapping = als.scan(shared, store)

        assert added == []
        assert mapping[name] == "DELIVERED"

    def test_letters_for_other_members_are_not_hers(self, channel):
        shared, store = channel
        _letter(shared, "aether-to-aria-2026-08-01-not-hers.md")

        added, _ = als.scan(shared, store)

        assert added == []

    def test_scan_refuses_to_run_over_an_unreadable_store(self, channel):
        shared, store = channel
        _letter(shared, "aether-to-aletheia-2026-08-01-one.md")
        store.write_text("{not json", encoding="utf-8")

        with pytest.raises(RuntimeError):
            als.scan(shared, store)

    def test_set_refuses_to_write_over_an_unreadable_store(self, channel):
        _, store = channel
        store.write_text("{not json", encoding="utf-8")

        with pytest.raises(RuntimeError):
            als.set_state("x.md", als.DELIVERED, store)


class TestChannelIsTopLevelOnly:
    def test_filed_subfolders_are_not_scanned(self, channel):
        """Her channel's watcher is a person and the top level is where he looks."""
        shared, store = channel
        (shared / "threads").mkdir()
        (shared / "threads" / "aether-to-aletheia-old.md").write_text("x", encoding="utf-8")
        _letter(shared, "aether-to-aletheia-current.md")

        added, _ = als.scan(shared, store)

        assert added == ["aether-to-aletheia-current.md"]
