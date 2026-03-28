"""Tests for stale knowledge auto-flagging in health_check."""

import os
import time

from divineos.core.knowledge import (
    _get_connection,
    _has_temporal_markers,
    health_check,
    init_knowledge_table,
    store_knowledge,
)
from divineos.core.ledger import init_db


class TestHasTemporalMarkers:
    """Test temporal marker detection."""

    def test_detects_currently(self):
        assert _has_temporal_markers("The system is currently broken") is True

    def test_detects_is_broken(self):
        assert _has_temporal_markers("The build is broken after last merge") is True

    def test_detects_in_progress(self):
        assert _has_temporal_markers("Migration is in progress right now") is True

    def test_no_markers(self):
        assert _has_temporal_markers("Python uses indentation for blocks") is False

    def test_detects_wip(self):
        assert _has_temporal_markers("The auth system is WIP") is True

    def test_detects_blocked_on(self):
        assert _has_temporal_markers("Feature is blocked on API approval") is True


class TestStaleKnowledgeDecay:
    """Test that health_check decays stale entries."""

    def test_old_unused_entry_decays(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            # Create an entry that's 45 days old with zero access
            kid = store_knowledge(
                knowledge_type="FACT",
                content="The old server runs on port 8080 with default config",
                confidence=0.9,
            )
            conn = _get_connection()
            old_time = time.time() - (45 * 86400)
            conn.execute(
                "UPDATE knowledge SET created_at = ?, access_count = 0 WHERE knowledge_id = ?",
                (old_time, kid),
            )
            conn.commit()
            conn.close()

            result = health_check()

            # Entry should have decayed
            assert result["stale_decayed"] >= 1

            conn = _get_connection()
            row = conn.execute(
                "SELECT confidence FROM knowledge WHERE knowledge_id = ?",
                (kid,),
            ).fetchone()
            conn.close()
            assert row[0] < 0.9  # confidence reduced
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_temporal_entry_decays_faster(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            # Create a temporal entry 20 days old (> 14 day threshold)
            kid = store_knowledge(
                knowledge_type="FACT",
                content="The build is currently broken after the merge",
                confidence=0.9,
            )
            conn = _get_connection()
            old_time = time.time() - (20 * 86400)
            conn.execute(
                "UPDATE knowledge SET created_at = ?, access_count = 5 WHERE knowledge_id = ?",
                (old_time, kid),
            )
            conn.commit()
            conn.close()

            result = health_check()

            assert result["temporal_decayed"] >= 1

            conn = _get_connection()
            row = conn.execute(
                "SELECT confidence FROM knowledge WHERE knowledge_id = ?",
                (kid,),
            ).fetchone()
            conn.close()
            assert row[0] < 0.9
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_directive_immune_to_decay(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            # Create a DIRECTIVE that's old with zero access
            kid = store_knowledge(
                knowledge_type="DIRECTIVE",
                content="Always run tests after making code changes to verify correctness",
                confidence=0.9,
            )
            conn = _get_connection()
            old_time = time.time() - (60 * 86400)
            conn.execute(
                "UPDATE knowledge SET created_at = ?, access_count = 0 WHERE knowledge_id = ?",
                (old_time, kid),
            )
            conn.commit()
            conn.close()

            health_check()

            # DIRECTIVE should be unchanged
            conn = _get_connection()
            row = conn.execute(
                "SELECT confidence FROM knowledge WHERE knowledge_id = ?",
                (kid,),
            ).fetchone()
            conn.close()
            assert row[0] == 0.9
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_recent_entry_no_decay(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            kid = store_knowledge(
                knowledge_type="FACT",
                content="Python three point twelve added type parameter syntax support",
                confidence=0.9,
            )

            health_check()

            conn = _get_connection()
            row = conn.execute(
                "SELECT confidence FROM knowledge WHERE knowledge_id = ?",
                (kid,),
            ).fetchone()
            conn.close()
            assert row[0] == 0.9  # no decay, it's new
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_high_contradiction_count_flags(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            kid = store_knowledge(
                knowledge_type="FACT",
                content="The database schema has fifteen tables for storing user data",
                confidence=0.9,
            )
            # Manually set contradiction_count to 3
            conn = _get_connection()
            conn.execute(
                "UPDATE knowledge SET contradiction_count = 3 WHERE knowledge_id = ?",
                (kid,),
            )
            conn.commit()
            conn.close()

            result = health_check()

            assert result["contradiction_flagged"] >= 1

            conn = _get_connection()
            row = conn.execute(
                "SELECT confidence FROM knowledge WHERE knowledge_id = ?",
                (kid,),
            ).fetchone()
            conn.close()
            assert row[0] < 0.9
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_stale_floor_at_minimum(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            kid = store_knowledge(
                knowledge_type="FACT",
                content="An ancient fact about some system that nobody remembers anymore",
                confidence=0.2,
            )
            conn = _get_connection()
            old_time = time.time() - (90 * 86400)
            conn.execute(
                "UPDATE knowledge SET created_at = ?, access_count = 0 WHERE knowledge_id = ?",
                (old_time, kid),
            )
            conn.commit()
            conn.close()

            health_check()

            conn = _get_connection()
            row = conn.execute(
                "SELECT confidence FROM knowledge WHERE knowledge_id = ?",
                (kid,),
            ).fetchone()
            conn.close()
            assert row[0] >= 0.2  # floor of 0.2 respected
        finally:
            os.environ.pop("DIVINEOS_DB", None)
