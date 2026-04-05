"""Tests for enhanced session continuation — structured handoff fields."""

import pytest

import divineos.core.ledger as ledger_mod
from divineos.core.hud_handoff import load_handoff_note, save_handoff_note
from divineos.core.ledger import init_db


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    """Use a temporary database so HUD dir resolves to tmp_path."""
    test_db = tmp_path / "test_ledger.db"
    monkeypatch.setattr(ledger_mod, "DB_PATH", test_db)
    monkeypatch.setattr(ledger_mod, "_get_db_path", lambda: test_db)
    init_db()
    yield


class TestStructuredHandoff:
    def test_save_load_with_new_fields(self):
        save_handoff_note(
            summary="Last session: 10 exchanges",
            open_threads=["Fix import cycle"],
            mood="solid session",
            goals_state="1 completed, 2 active",
            session_id="abc123",
            intent="Break circular imports in memory module",
            blockers=["Permission denied on worktree files"],
            next_steps=["Fix test_memory.py imports", "Run full suite"],
            context_snapshot={"session_grade": "B", "knowledge_stored": 5},
        )
        note = load_handoff_note()
        assert note is not None
        assert note["summary"] == "Last session: 10 exchanges"
        assert note["intent"] == "Break circular imports in memory module"
        assert note["blockers"] == ["Permission denied on worktree files"]
        assert note["next_steps"] == ["Fix test_memory.py imports", "Run full suite"]
        assert note["context_snapshot"]["session_grade"] == "B"
        assert note["context_snapshot"]["knowledge_stored"] == 5

    def test_backward_compat_old_note(self, tmp_path, monkeypatch):
        """Old-format notes without new fields should load without error."""
        save_handoff_note(
            summary="Old format session",
            mood="strong session",
            session_id="old-id",
        )
        note = load_handoff_note()
        assert note is not None
        assert note["summary"] == "Old format session"
        # New fields should be absent (not empty strings)
        assert "intent" not in note
        assert "blockers" not in note
        assert "next_steps" not in note
        assert "context_snapshot" not in note

    def test_empty_new_fields_omitted(self):
        """Empty new fields should not be included in the JSON."""
        save_handoff_note(
            summary="Minimal note",
            session_id="min-id",
            intent="",
            blockers=None,
            next_steps=None,
            context_snapshot=None,
        )
        note = load_handoff_note()
        assert note is not None
        assert "intent" not in note
        assert "blockers" not in note

    def test_partial_new_fields(self):
        """Only intent set, others empty."""
        save_handoff_note(
            summary="Partial note",
            session_id="partial-id",
            intent="Build graph visualization",
        )
        note = load_handoff_note()
        assert note is not None
        assert note["intent"] == "Build graph visualization"
        assert "blockers" not in note
        assert "next_steps" not in note
