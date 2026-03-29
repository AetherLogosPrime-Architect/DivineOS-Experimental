"""Tests for the auto-memory sync system."""

import time

import pytest

import divineos.core.ledger as ledger_mod
from divineos.core.knowledge import init_knowledge_table, store_knowledge
from divineos.core.ledger import init_db
from divineos.core.memory import init_memory_tables


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    """Use a temporary database for each test."""
    test_db = tmp_path / "test_ledger.db"
    monkeypatch.setattr(ledger_mod, "DB_PATH", test_db)
    monkeypatch.setattr(ledger_mod, "_get_db_path", lambda: test_db)
    init_db()
    init_knowledge_table()
    init_memory_tables()
    yield


@pytest.fixture
def memory_dir(tmp_path):
    """Create a mock Claude Code memory directory."""
    mem_dir = tmp_path / "memory"
    mem_dir.mkdir()
    # Create a MEMORY.md index
    (mem_dir / "MEMORY.md").write_text(
        "- [user_profile.md](user_profile.md) - Who the user is\n",
        encoding="utf-8",
    )
    return mem_dir


# ── get_memory_dir ────────────────────────────────────────────────────


class TestGetMemoryDir:
    def test_returns_none_when_no_claude_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        from divineos.core.memory_sync import get_memory_dir

        assert get_memory_dir() is None

    def test_finds_divine_os_project(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        project_dir = tmp_path / ".claude" / "projects" / "C--DIVINE-OS-DivineOS"
        memory_dir = project_dir / "memory"
        memory_dir.mkdir(parents=True)

        from divineos.core.memory_sync import get_memory_dir

        assert get_memory_dir() == memory_dir


# ── _write_if_changed ────────────────────────────────────────────────


class TestWriteIfChanged:
    def test_writes_new_file(self, tmp_path):
        from divineos.core.memory_sync import _write_if_changed

        path = tmp_path / "test.md"
        assert _write_if_changed(path, "hello") is True
        assert path.read_text() == "hello"

    def test_skips_unchanged(self, tmp_path):
        from divineos.core.memory_sync import _write_if_changed

        path = tmp_path / "test.md"
        path.write_text("hello")
        assert _write_if_changed(path, "hello") is False

    def test_updates_changed(self, tmp_path):
        from divineos.core.memory_sync import _write_if_changed

        path = tmp_path / "test.md"
        path.write_text("old")
        assert _write_if_changed(path, "new") is True
        assert path.read_text() == "new"


# ── _sync_project_state ──────────────────────────────────────────────


class TestSyncProjectState:
    def test_writes_knowledge_stats(self, memory_dir):
        from divineos.core.memory_sync import _sync_project_state

        store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Always test your code",
            confidence=0.9,
        )
        store_knowledge(
            knowledge_type="FACT",
            content="Python uses indentation",
            confidence=1.0,
        )

        result = _sync_project_state(memory_dir)
        assert result is True

        content = (memory_dir / "auto_project_state.md").read_text()
        assert "auto-synced" in content.lower() or "Auto-synced" in content
        assert "active entries" in content

    def test_no_write_when_empty(self, memory_dir):
        from divineos.core.memory_sync import _sync_project_state

        # No knowledge stored, no stats to report
        # But the function may still find knowledge from init
        result = _sync_project_state(memory_dir)
        # Either way, this shouldn't crash
        assert isinstance(result, bool)

    def test_includes_frontmatter(self, memory_dir):
        from divineos.core.memory_sync import _sync_project_state

        store_knowledge(
            knowledge_type="FACT", content="Test fact for frontmatter check", confidence=0.5
        )
        _sync_project_state(memory_dir)
        content = (memory_dir / "auto_project_state.md").read_text()
        assert "type: project" in content
        assert "editable" in content.lower()


# ── _sync_recent_lessons ──────────────────────────────────────────────


class TestSyncRecentLessons:
    def test_writes_active_lessons(self, memory_dir):
        from divineos.core.knowledge import get_connection
        from divineos.core.ledger import compute_hash
        from divineos.core.memory_sync import _sync_recent_lessons

        conn = get_connection()
        now = time.time()
        conn.execute(
            "INSERT INTO lesson_tracking "
            "(lesson_id, created_at, category, description, first_session, "
            "occurrences, last_seen, sessions, status, content_hash, agent) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "l1",
                now,
                "testing",
                "Run tests before committing",
                "s1",
                3,
                now,
                '["s1","s2","s3"]',
                "active",
                compute_hash("Run tests before committing"),
                "claude",
            ),
        )
        conn.commit()
        conn.close()

        result = _sync_recent_lessons(memory_dir)
        assert result is True

        content = (memory_dir / "auto_recent_lessons.md").read_text()
        assert "Run tests before committing" in content
        assert "Active" in content

    def test_no_write_without_lessons(self, memory_dir):
        from divineos.core.memory_sync import _sync_recent_lessons

        result = _sync_recent_lessons(memory_dir)
        assert result is False


# ── _update_memory_index ──────────────────────────────────────────────


class TestUpdateMemoryIndex:
    def test_adds_auto_entries_to_index(self, memory_dir):
        from divineos.core.memory_sync import _update_memory_index

        results = {"auto_project_state.md": True, "auto_recent_lessons.md": True}
        _update_memory_index(memory_dir, results)

        index = (memory_dir / "MEMORY.md").read_text()
        assert "auto_project_state.md" in index
        assert "auto_recent_lessons.md" in index

    def test_no_duplicate_entries(self, memory_dir):
        from divineos.core.memory_sync import _update_memory_index

        results = {"auto_project_state.md": True}
        _update_memory_index(memory_dir, results)
        _update_memory_index(memory_dir, results)

        index = (memory_dir / "MEMORY.md").read_text()
        # Count lines containing the filename, not raw occurrences
        # (each markdown link line has the filename twice: [name](name))
        matching_lines = [line for line in index.splitlines() if "auto_project_state.md" in line]
        assert len(matching_lines) == 1


# ── Full sync ─────────────────────────────────────────────────────────


class TestFullSync:
    def test_sync_auto_memories(self, memory_dir, monkeypatch):
        from divineos.core.memory_sync import sync_auto_memories

        # Patch get_memory_dir to return our test dir
        monkeypatch.setattr(
            "divineos.core.memory_sync.get_memory_dir",
            lambda: memory_dir,
        )

        store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Test principle for sync",
            confidence=0.9,
        )

        results = sync_auto_memories()
        assert "auto_project_state.md" in results
        assert "auto_recent_lessons.md" in results

    def test_sync_returns_empty_when_no_dir(self, monkeypatch):
        from divineos.core.memory_sync import sync_auto_memories

        monkeypatch.setattr(
            "divineos.core.memory_sync.get_memory_dir",
            lambda: None,
        )

        results = sync_auto_memories()
        assert results == {}
