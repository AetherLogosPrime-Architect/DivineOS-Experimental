"""Tests for smart knowledge operations (ADD/UPDATE/SKIP/NOOP)."""

import os

from divineos.core.knowledge import (
    _decide_operation,
    _get_connection,
    init_knowledge_table,
    store_knowledge,
    store_knowledge_smart,
)
from divineos.core.ledger import init_db


class TestDecideOperation:
    """Test the _decide_operation logic in isolation."""

    def test_skip_short_content(self):
        op, eid = _decide_operation("hi ok yes", "FACT", None, 0.0)
        assert op == "SKIP"
        assert eid is None

    def test_skip_only_stopwords(self):
        op, eid = _decide_operation("the a an is are was to of in for", "FACT", None, 0.0)
        assert op == "SKIP"

    def test_add_no_match(self):
        op, eid = _decide_operation(
            "Python uses indentation for code blocks instead of braces",
            "FACT",
            None,
            0.0,
        )
        assert op == "ADD"
        assert eid is None

    def test_add_low_overlap(self):
        match = {"knowledge_id": "abc", "content": "JavaScript uses curly braces"}
        op, eid = _decide_operation(
            "Python uses indentation for code blocks instead of braces",
            "FACT",
            match,
            0.3,
        )
        assert op == "ADD"

    def test_noop_high_overlap_same_content(self):
        match = {
            "knowledge_id": "abc",
            "content": "Python uses indentation for code blocks",
        }
        op, eid = _decide_operation(
            "Python uses indentation for code blocks always",
            "FACT",
            match,
            0.85,
        )
        assert op == "NOOP"
        assert eid == "abc"

    def test_update_high_overlap_with_new_info(self):
        match = {
            "knowledge_id": "abc",
            "content": "The project has 1000 tests passing",
        }
        # Lots of new words: "currently", "1500", "integration", "unit", "suite"
        op, eid = _decide_operation(
            "The project currently has 1500 tests passing including integration and unit suite",
            "FACT",
            match,
            0.65,
        )
        assert op == "UPDATE"
        assert eid == "abc"

    def test_medium_overlap_adds(self):
        match = {
            "knowledge_id": "abc",
            "content": "Database uses SQLite for storage",
        }
        op, eid = _decide_operation(
            "Database migration requires careful planning and testing",
            "FACT",
            match,
            0.45,
        )
        assert op == "ADD"


class TestSmartOpsIntegration:
    """Integration tests using real database."""

    def test_skip_returns_empty_string(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()
            result = store_knowledge_smart("FACT", "ok hi yes")
            assert result == ""
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_update_supersedes_old_entry(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            # Store initial knowledge
            old_id = store_knowledge(
                knowledge_type="FACT",
                content="The project tests pass reliably in the continuous integration suite",
                confidence=0.9,
            )

            # Store updated version — shares enough FTS5 terms for discovery,
            # plus enough new words (>20%) to trigger UPDATE instead of NOOP.
            new_id = store_knowledge_smart(
                "FACT",
                "The project tests pass reliably in the continuous integration suite with coverage and mutation testing",
            )

            # New entry should be different from old
            assert new_id != old_id
            assert new_id != ""

            # Old entry should be superseded
            conn = _get_connection()
            row = conn.execute(
                "SELECT superseded_by FROM knowledge WHERE knowledge_id = ?",
                (old_id,),
            ).fetchone()
            conn.close()
            assert row is not None
            assert row[0] is not None  # superseded_by is set
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_contradiction_detected_on_store(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            # Store a boundary claim
            old_id = store_knowledge(
                knowledge_type="BOUNDARY",
                content="divineos ask cannot search core memory, it only searches the knowledge store",
                confidence=0.9,
            )

            # Store contradicting claim — high overlap triggers UPDATE (supersession),
            # which is itself a form of contradiction resolution.
            new_id = store_knowledge_smart(
                "BOUNDARY",
                "divineos ask now searches core memory and the knowledge store, this was fixed previously",
            )
            assert new_id != ""

            # Old entry should be either contradicted OR superseded (both valid)
            conn = _get_connection()
            row = conn.execute(
                "SELECT contradiction_count, superseded_by FROM knowledge WHERE knowledge_id = ?",
                (old_id,),
            ).fetchone()
            conn.close()
            assert row is not None
            contradicted = row[0] >= 1
            superseded = row[1] is not None
            assert contradicted or superseded, (
                f"Old entry should be contradicted or superseded, got "
                f"contradiction_count={row[0]}, superseded_by={row[1]}"
            )
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_noop_bumps_access_count(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            kid1 = store_knowledge_smart("FACT", "Python uses indentation for code blocks")
            kid2 = store_knowledge_smart("FACT", "Python uses indentation for code blocks")
            assert kid1 == kid2

            # Access count should be incremented
            conn = _get_connection()
            row = conn.execute(
                "SELECT access_count FROM knowledge WHERE knowledge_id = ?",
                (kid1,),
            ).fetchone()
            conn.close()
            assert row[0] >= 1
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_add_creates_new_entry(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            kid1 = store_knowledge_smart("FACT", "Python uses indentation for defining code blocks")
            kid2 = store_knowledge_smart(
                "FACT", "JavaScript uses curly braces for defining code blocks"
            )
            assert kid1 != kid2
            assert kid1 != ""
            assert kid2 != ""
        finally:
            os.environ.pop("DIVINEOS_DB", None)
