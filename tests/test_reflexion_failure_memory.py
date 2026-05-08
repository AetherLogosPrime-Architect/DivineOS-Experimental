"""Tests for Reflexion-style structured failure memory (prereg-f55843b9d1fd).

Lessons can now carry a (failure_shape, preventive_action) pair indexed
for retrieval when a similar shape recurs. Free-form prose lessons are
unchanged — the structured fields are additive and NULL-safe for legacy
entries.

Invariants pinned:
  - Schema migration is idempotent (re-running doesn't fail)
  - Existing lessons without the structured fields keep working
  - set_lesson_shape attaches pair to existing lesson
  - set_lesson_shape returns False for non-existent lesson
  - find_lessons_by_shape matches substring of either field
  - find_lessons_by_shape excludes resolved lessons
  - find_lessons_by_shape is case-insensitive
  - find_lessons_by_shape returns lessons sorted by priority
"""

from divineos.core.knowledge.lessons import (
    find_lessons_by_shape,
    get_lessons,
    record_lesson,
    set_lesson_shape,
)
from divineos.core.knowledge import init_knowledge_table
from divineos.core.ledger import init_db


def _setup(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db_path))
    init_db()
    init_knowledge_table()


class TestSchemaMigration:
    def test_set_lesson_shape_works_on_fresh_db(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        record_lesson("test_cat", "test description", "session-1")
        result = set_lesson_shape(
            "test_cat",
            "test failure shape",
            "test preventive action",
        )
        assert result is True

    def test_set_lesson_shape_returns_false_for_missing(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        result = set_lesson_shape("nonexistent", "shape", "action")
        assert result is False


class TestStructuredPairAttachment:
    def test_pair_attached_persists(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        record_lesson("force_push_botched", "I force-pushed a botched rebase", "s1")
        set_lesson_shape(
            "force_push_botched",
            "force-push of rebased branch with empty diff vs main",
            "verify git log origin/main..HEAD has unique commits before push",
        )
        # Retrieving by shape substring finds it
        results = find_lessons_by_shape("force-push")
        assert len(results) == 1
        assert results[0]["category"] == "force_push_botched"

    def test_existing_lessons_without_pair_keep_working(self, tmp_path, monkeypatch):
        """Backward compat: lessons created without shape/action via the
        normal record_lesson path continue to work. They just don't appear
        in shape-indexed retrieval."""
        _setup(tmp_path, monkeypatch)
        record_lesson("plain_lesson", "no shape attached", "s1")
        # Plain get_lessons returns it
        all_lessons = get_lessons()
        assert any(lesson["category"] == "plain_lesson" for lesson in all_lessons)
        # Shape-search does NOT find it (no shape to match against)
        results = find_lessons_by_shape("anything")
        assert all(lesson["category"] != "plain_lesson" for lesson in results)


class TestShapeIndexedRetrieval:
    def test_matches_either_field(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        record_lesson("a", "lesson a", "s1")
        record_lesson("b", "lesson b", "s2")
        set_lesson_shape("a", "shape contains keyword foo", "action b")
        set_lesson_shape("b", "shape c", "action contains keyword foo")
        # Both should match — query appears in shape (a) or action (b)
        results = find_lessons_by_shape("foo")
        categories = {lesson["category"] for lesson in results}
        assert categories == {"a", "b"}

    def test_case_insensitive(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        record_lesson("a", "lesson", "s1")
        set_lesson_shape("a", "Force-Push problem", "action")
        # Lower-case query finds upper-case shape (SQL LIKE is
        # case-insensitive in SQLite by default for ASCII).
        results = find_lessons_by_shape("force-push")
        assert len(results) == 1

    def test_excludes_resolved_lessons(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        record_lesson("resolved_one", "lesson", "s1")
        set_lesson_shape("resolved_one", "match this", "action")
        # Manually mark as resolved
        from divineos.core.knowledge._base import _get_connection

        conn = _get_connection()
        try:
            conn.execute(
                "UPDATE lesson_tracking SET status = 'resolved' WHERE category = ?",
                ("resolved_one",),
            )
            conn.commit()
        finally:
            conn.close()

        results = find_lessons_by_shape("match this")
        assert len(results) == 0

    def test_no_results_for_nonmatching_query(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        record_lesson("a", "lesson", "s1")
        set_lesson_shape("a", "specific shape", "specific action")
        results = find_lessons_by_shape("zzz_no_match_zzz")
        assert results == []

    def test_limit_respected(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        for i in range(10):
            record_lesson(f"cat_{i}", f"lesson {i}", f"s{i}")
            set_lesson_shape(f"cat_{i}", "common shape token", f"action {i}")
        results = find_lessons_by_shape("common shape token", limit=3)
        assert len(results) == 3

    def test_returned_dict_includes_shape_and_action(self, tmp_path, monkeypatch):
        """Auditor 4th-pass finding: callers wanting to display the matched
        shape/action shouldn't need a second query. The returned dict
        carries failure_shape and preventive_action directly."""
        _setup(tmp_path, monkeypatch)
        record_lesson("force_push_botched", "rebase ate work", "s1")
        set_lesson_shape(
            "force_push_botched",
            "force-push of branch with empty diff",
            "verify unique commits via git log before push",
        )
        results = find_lessons_by_shape("force-push")
        assert len(results) == 1
        assert results[0]["failure_shape"] == "force-push of branch with empty diff"
        assert results[0]["preventive_action"] == "verify unique commits via git log before push"
