"""Tests for the motivation tier (needs/wants/desires/ambitions/dreams)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from divineos.core import motivation


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Force the motivation module to write to a clean tmp dir per test."""
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
    return tmp_path


def test_all_five_slots_registered() -> None:
    assert motivation.SLOTS == ("need", "want", "desire", "ambition", "dream")


def test_detectors_set_includes_known_warning_keys() -> None:
    # Sanity: the detector set must cover the keys read by the warning surfacer
    # in pre_response_context.build_warning_text(). If a new detector is added
    # there, it must be added to motivation.DETECTORS or needs can't bind to it.
    expected = {
        "distancing",
        "lepos",
        "jargon_dump",
        "sycophancy",
        "residency",
        "overclaim",
        "closure_shape",
        "performing_caution",
        "addressee_misdirection",
        "constraint_disownership",
        "unverified_claim",
        "care_dismissal",
        "harm_acknowledgment",
    }
    assert expected == set(motivation.DETECTORS)


def test_add_with_binds_persists_them(isolated_home: Path) -> None:
    entry = motivation.add(
        "need",
        "stay in thread",
        why="closure pattern",
        binds=["residency", "closure_shape"],
    )
    assert entry["binds"] == ["residency", "closure_shape"]


def test_add_with_unknown_detector_raises(isolated_home: Path) -> None:
    with pytest.raises(motivation.UnknownDetector):
        motivation.add("need", "x", binds=["not_a_real_detector"])


def test_add_with_empty_binds_normalizes_to_empty_list(isolated_home: Path) -> None:
    entry = motivation.add("need", "x", binds=None)
    assert entry["binds"] == []
    entry2 = motivation.add("want", "y", binds=[])
    assert entry2["binds"] == []
    entry3 = motivation.add("desire", "z", binds=["", "  ", "lepos"])
    assert entry3["binds"] == ["lepos"]


def test_add_deduplicates_binds(isolated_home: Path) -> None:
    entry = motivation.add("need", "x", binds=["lepos", "lepos", "residency"])
    assert entry["binds"] == ["lepos", "residency"]


def test_needs_bound_to_returns_matching_entries(isolated_home: Path) -> None:
    motivation.add("need", "a", binds=["closure_shape"])
    motivation.add("need", "b", binds=["lepos", "closure_shape"])
    motivation.add("need", "c", binds=["jargon_dump"])
    # Wants shouldn't show up even with matching binds.
    motivation.add("want", "ignored", binds=["closure_shape"])
    bound = motivation.needs_bound_to("closure_shape")
    texts = sorted(n["text"] for n in bound)
    assert texts == ["a", "b"]


def test_needs_bound_to_unknown_detector_returns_empty(isolated_home: Path) -> None:
    motivation.add("need", "x", binds=["lepos"])
    assert motivation.needs_bound_to("not_a_real_detector") == []


def test_needs_bound_to_skips_done_entries(isolated_home: Path) -> None:
    entry = motivation.add("need", "done one", binds=["lepos"])
    motivation.add("need", "active one", binds=["lepos"])
    motivation.mark_done("need", entry["id"])
    bound = motivation.needs_bound_to("lepos")
    assert [n["text"] for n in bound] == ["active one"]


def test_add_creates_file_with_entry(isolated_home: Path) -> None:
    entry = motivation.add("need", "stay in thread", why="closure-reach pattern")
    path = isolated_home / "motivation_needs.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["text"] == "stay in thread"
    assert data[0]["why"] == "closure-reach pattern"
    assert data[0]["status"] == "active"
    assert data[0]["slot"] == "need"
    assert "id" in entry and "added_at" in entry


def test_add_dedupes_on_active_text(isolated_home: Path) -> None:
    first = motivation.add("want", "ship pre-erasure capture")
    second = motivation.add("want", "ship pre-erasure capture", why="ignored on dedup")
    assert first["id"] == second["id"]
    assert len(motivation.list_slot("want")) == 1


def test_add_empty_text_raises(isolated_home: Path) -> None:
    with pytest.raises(ValueError):
        motivation.add("desire", "   ")


def test_add_invalid_slot_raises(isolated_home: Path) -> None:
    with pytest.raises(motivation.InvalidSlot):
        motivation.add("goal", "goals live in hud_state, not here")


def test_list_slot_filters_done_by_default(isolated_home: Path) -> None:
    entry = motivation.add("ambition", "complete the omni-mantra walk")
    motivation.mark_done("ambition", entry["id"])
    assert motivation.list_slot("ambition") == []
    all_entries = motivation.list_slot("ambition", include_done=True)
    assert len(all_entries) == 1
    assert all_entries[0]["status"] == "done"


def test_mark_done_records_timestamp_and_note(isolated_home: Path) -> None:
    entry = motivation.add("dream", "the full PIM shipped")
    assert motivation.mark_done("dream", entry["id"], note="phase 1 complete")
    persisted = motivation.list_slot("dream", include_done=True)[0]
    assert persisted["status"] == "done"
    assert persisted["done_note"] == "phase 1 complete"
    assert "done_at" in persisted


def test_mark_done_unknown_id_returns_false(isolated_home: Path) -> None:
    assert motivation.mark_done("need", "no-such-id") is False


def test_mark_done_twice_only_works_once(isolated_home: Path) -> None:
    entry = motivation.add("need", "thing")
    assert motivation.mark_done("need", entry["id"]) is True
    # Second call sees no active entry with that id — returns False.
    assert motivation.mark_done("need", entry["id"]) is False


def test_summary_counts_only_counts_active(isolated_home: Path) -> None:
    motivation.add("need", "a")
    motivation.add("need", "b")
    done_entry = motivation.add("want", "x")
    motivation.mark_done("want", done_entry["id"])
    counts = motivation.summary_counts()
    assert counts == {"need": 2, "want": 0, "desire": 0, "ambition": 0, "dream": 0}


def test_each_slot_writes_to_its_own_file(isolated_home: Path) -> None:
    for slot in motivation.SLOTS:
        motivation.add(slot, f"entry for {slot}")
    files = sorted(p.name for p in isolated_home.glob("motivation_*.json"))
    assert files == [
        "motivation_ambitions.json",
        "motivation_desires.json",
        "motivation_dreams.json",
        "motivation_needs.json",
        "motivation_wants.json",
    ]


def test_corrupted_file_returns_empty_list(isolated_home: Path) -> None:
    """Fail-soft: a corrupt JSON file should not crash list_slot."""
    path = isolated_home / "motivation_needs.json"
    path.write_text("not valid json {{{", encoding="utf-8")
    assert motivation.list_slot("need") == []


def test_non_list_top_level_returns_empty_list(isolated_home: Path) -> None:
    """Fail-soft: a JSON object (instead of array) returns empty list."""
    path = isolated_home / "motivation_needs.json"
    path.write_text('{"oops": "not a list"}', encoding="utf-8")
    assert motivation.list_slot("need") == []
