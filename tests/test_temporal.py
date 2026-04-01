"""Tests for Temporal Dimension — knowledge knows when it was true."""

import os
import time

from divineos.core.knowledge._base import (
    _get_connection,
    init_knowledge_table,
)
from divineos.core.knowledge.crud import (
    store_knowledge,
    supersede_knowledge,
    update_knowledge,
)
from divineos.core.knowledge.temporal import (
    expire_knowledge,
    format_changes_summary,
    get_changes_since,
    get_valid_at,
    init_temporal_columns,
    set_validity,
    stamp_valid_from,
)
from divineos.core.ledger import init_db


class TestTemporalColumns:
    """Temporal columns should be added safely."""

    def test_init_temporal_columns(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()
            # Should not raise on first call
            init_temporal_columns()
            # Should not raise on second call (idempotent)
            init_temporal_columns()

            conn = _get_connection()
            cols = [c[1] for c in conn.execute("PRAGMA table_info(knowledge)").fetchall()]
            conn.close()
            assert "valid_from" in cols
            assert "valid_until" in cols
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_columns_added_by_init_knowledge_table(self, tmp_path):
        """init_knowledge_table now adds temporal columns automatically."""
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            conn = _get_connection()
            cols = [c[1] for c in conn.execute("PRAGMA table_info(knowledge)").fetchall()]
            conn.close()
            assert "valid_from" in cols
            assert "valid_until" in cols
        finally:
            os.environ.pop("DIVINEOS_DB", None)


class TestValidFromStamping:
    """New knowledge should get valid_from set automatically."""

    def test_store_sets_valid_from(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            before = time.time()
            kid = store_knowledge(
                knowledge_type="FACT",
                content="The API uses version 2",
                confidence=0.8,
            )
            after = time.time()

            conn = _get_connection()
            row = conn.execute(
                "SELECT valid_from, valid_until FROM knowledge WHERE knowledge_id = ?",
                (kid,),
            ).fetchone()
            conn.close()

            assert row[0] is not None  # valid_from set
            assert before <= row[0] <= after
            assert row[1] is None  # valid_until not set (still valid)
        finally:
            os.environ.pop("DIVINEOS_DB", None)


class TestSupersessionSetsValidUntil:
    """Superseding knowledge should mark old entry with valid_until."""

    def test_update_knowledge_sets_valid_until(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            old_id = store_knowledge(
                knowledge_type="FACT",
                content="The API uses version 1",
                confidence=0.8,
            )
            before_update = time.time()
            new_id = update_knowledge(old_id, "The API uses version 2")

            conn = _get_connection()
            old_row = conn.execute(
                "SELECT valid_until FROM knowledge WHERE knowledge_id = ?",
                (old_id,),
            ).fetchone()
            new_row = conn.execute(
                "SELECT valid_from FROM knowledge WHERE knowledge_id = ?",
                (new_id,),
            ).fetchone()
            conn.close()

            assert old_row[0] is not None  # old entry expired
            assert old_row[0] >= before_update
            assert new_row[0] is not None  # new entry has valid_from
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_supersede_knowledge_sets_valid_until(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            kid = store_knowledge(
                knowledge_type="FACT",
                content="This bug is still open",
                confidence=0.7,
            )
            supersede_knowledge(kid, "Bug was fixed")

            conn = _get_connection()
            row = conn.execute(
                "SELECT valid_until FROM knowledge WHERE knowledge_id = ?",
                (kid,),
            ).fetchone()
            conn.close()

            assert row[0] is not None
        finally:
            os.environ.pop("DIVINEOS_DB", None)


class TestSetValidity:
    """Direct validity manipulation."""

    def test_set_validity_on_existing(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            kid = store_knowledge(
                knowledge_type="FACT",
                content="Something temporal",
                confidence=0.8,
            )
            now = time.time()
            result = set_validity(kid, valid_from=now - 100, valid_until=now)
            assert result is True

            conn = _get_connection()
            row = conn.execute(
                "SELECT valid_from, valid_until FROM knowledge WHERE knowledge_id = ?",
                (kid,),
            ).fetchone()
            conn.close()
            assert abs(row[0] - (now - 100)) < 1
            assert abs(row[1] - now) < 1
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_set_validity_on_missing_returns_false(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()
            assert set_validity("nonexistent", valid_from=1.0) is False
        finally:
            os.environ.pop("DIVINEOS_DB", None)


class TestExpireKnowledge:
    """Expiring knowledge sets valid_until to now."""

    def test_expire_sets_valid_until(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            kid = store_knowledge(
                knowledge_type="FACT",
                content="Currently true fact",
                confidence=0.9,
            )
            before = time.time()
            expire_knowledge(kid)

            conn = _get_connection()
            row = conn.execute(
                "SELECT valid_until FROM knowledge WHERE knowledge_id = ?",
                (kid,),
            ).fetchone()
            conn.close()
            assert row[0] is not None
            assert row[0] >= before
        finally:
            os.environ.pop("DIVINEOS_DB", None)


class TestStampValidFrom:
    """stamp_valid_from only sets if not already set."""

    def test_stamps_when_null(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            kid = store_knowledge(
                knowledge_type="FACT",
                content="Test fact",
                confidence=0.8,
            )
            # Clear valid_from to simulate old entry
            conn = _get_connection()
            conn.execute(
                "UPDATE knowledge SET valid_from = NULL WHERE knowledge_id = ?",
                (kid,),
            )
            conn.commit()
            conn.close()

            result = stamp_valid_from(kid)
            assert result is True

            conn = _get_connection()
            row = conn.execute(
                "SELECT valid_from FROM knowledge WHERE knowledge_id = ?",
                (kid,),
            ).fetchone()
            conn.close()
            assert row[0] is not None
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_does_not_overwrite_existing(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            kid = store_knowledge(
                knowledge_type="FACT",
                content="Test fact with valid_from",
                confidence=0.8,
            )
            conn = _get_connection()
            original = conn.execute(
                "SELECT valid_from FROM knowledge WHERE knowledge_id = ?",
                (kid,),
            ).fetchone()[0]
            conn.close()

            # Try to stamp again
            stamp_valid_from(kid)

            conn = _get_connection()
            after = conn.execute(
                "SELECT valid_from FROM knowledge WHERE knowledge_id = ?",
                (kid,),
            ).fetchone()[0]
            conn.close()
            assert original == after
        finally:
            os.environ.pop("DIVINEOS_DB", None)


class TestGetValidAt:
    """Temporal queries return knowledge valid at a specific time."""

    def test_returns_currently_valid(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            store_knowledge(
                knowledge_type="FACT",
                content="Currently valid fact",
                confidence=0.8,
            )
            results = get_valid_at(time.time())
            assert len(results) >= 1
            assert any("Currently valid" in r["content"] for r in results)
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_excludes_expired(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            kid = store_knowledge(
                knowledge_type="FACT",
                content="Expired fact",
                confidence=0.8,
            )
            expire_knowledge(kid)

            # Query for "now" — expired entry should not appear
            results = get_valid_at(time.time() + 1)
            assert not any("Expired fact" in r["content"] for r in results)
        finally:
            os.environ.pop("DIVINEOS_DB", None)


class TestGetChangesSince:
    """Changes since a timestamp."""

    def test_new_entries_appear(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            before = time.time() - 1
            store_knowledge(
                knowledge_type="FACT",
                content="A new fact",
                confidence=0.8,
            )
            changes = get_changes_since(before)
            assert len(changes["new"]) >= 1
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_superseded_entries_appear(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            kid = store_knowledge(
                knowledge_type="FACT",
                content="Old version",
                confidence=0.8,
            )
            before = time.time() - 1
            update_knowledge(kid, "New version")

            changes = get_changes_since(before)
            assert len(changes["superseded"]) >= 1
            assert len(changes["new"]) >= 1
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_no_changes_returns_empty(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            # Query future time — nothing happened yet
            changes = get_changes_since(time.time() + 1000)
            assert len(changes["new"]) == 0
            assert len(changes["superseded"]) == 0
        finally:
            os.environ.pop("DIVINEOS_DB", None)


class TestFormatChangesSummary:
    """Summary formatting for display."""

    def test_empty_changes(self):
        result = format_changes_summary({"new": [], "expired": [], "superseded": [], "updated": []})
        assert "No changes" in result

    def test_new_entries_formatted(self):
        changes = {
            "new": [{"knowledge_type": "FACT", "content": "A new discovery about the system"}],
            "expired": [],
            "superseded": [],
            "updated": [],
        }
        result = format_changes_summary(changes)
        assert "1 new" in result
        assert "FACT" in result

    def test_superseded_entries_formatted(self):
        changes = {
            "new": [],
            "expired": [],
            "superseded": [{"content": "Old knowledge replaced"}],
            "updated": [],
        }
        result = format_changes_summary(changes)
        assert "1 superseded" in result

    def test_truncates_long_lists(self):
        changes = {
            "new": [{"knowledge_type": "FACT", "content": f"Fact {i}"} for i in range(10)],
            "expired": [],
            "superseded": [],
            "updated": [],
        }
        result = format_changes_summary(changes)
        assert "and 5 more" in result
