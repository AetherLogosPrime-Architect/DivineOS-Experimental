"""Tests for knowledge contradiction detection and resolution."""

import os

from divineos.core.knowledge_contradiction import (
    ContradictionMatch,
    increment_contradiction_count,
    resolve_contradiction,
    scan_for_contradictions,
)


class TestScanForContradictions:
    """Test contradiction scanning logic."""

    def test_no_contradictions_for_different_topics(self):
        existing = [
            {
                "knowledge_id": "abc",
                "knowledge_type": "FACT",
                "content": "The sky is blue and clear today",
                "superseded_by": None,
            },
        ]
        matches = scan_for_contradictions("Python uses indentation for blocks", "FACT", existing)
        assert matches == []

    def test_temporal_contradiction_detected(self):
        existing = [
            {
                "knowledge_id": "old-1",
                "knowledge_type": "BOUNDARY",
                "content": "divineos ask cannot search core memory, it only searches the knowledge store",
                "superseded_by": None,
            },
        ]
        matches = scan_for_contradictions(
            "divineos ask now searches core memory and the knowledge store, this was fixed previously",
            "BOUNDARY",
            existing,
        )
        assert len(matches) == 1
        assert matches[0].contradiction_type == "TEMPORAL"
        assert matches[0].existing_id == "old-1"

    def test_direct_contradiction_detected(self):
        existing = [
            {
                "knowledge_id": "old-2",
                "knowledge_type": "PRINCIPLE",
                "content": "Always use mocks for database testing",
                "superseded_by": None,
            },
        ]
        matches = scan_for_contradictions(
            "Never use mocks for database testing, use real databases",
            "PRINCIPLE",
            existing,
        )
        assert len(matches) == 1
        assert matches[0].contradiction_type == "DIRECT"
        assert matches[0].negation_detected is True

    def test_supersession_detected_high_overlap(self):
        existing = [
            {
                "knowledge_id": "old-3",
                "knowledge_type": "FACT",
                "content": "The project has 1000 tests passing in the test suite",
                "superseded_by": None,
            },
        ]
        matches = scan_for_contradictions(
            "The project has 1676 tests passing in the test suite",
            "FACT",
            existing,
        )
        assert len(matches) == 1
        assert matches[0].contradiction_type == "SUPERSESSION"

    def test_skips_superseded_entries(self):
        existing = [
            {
                "knowledge_id": "old-4",
                "knowledge_type": "FACT",
                "content": "The system is broken and not working",
                "superseded_by": "newer-entry",
            },
        ]
        matches = scan_for_contradictions(
            "The system is not broken and working fine",
            "FACT",
            existing,
        )
        assert matches == []

    def test_skips_different_types(self):
        existing = [
            {
                "knowledge_id": "old-5",
                "knowledge_type": "DIRECTIVE",
                "content": "Always run tests after code changes",
                "superseded_by": None,
            },
        ]
        matches = scan_for_contradictions(
            "Never run tests after code changes",
            "PRINCIPLE",  # Different type
            existing,
        )
        assert matches == []

    def test_low_overlap_no_contradiction(self):
        existing = [
            {
                "knowledge_id": "old-6",
                "knowledge_type": "FACT",
                "content": "The database uses SQLite for storage",
                "superseded_by": None,
            },
        ]
        matches = scan_for_contradictions(
            "Memory hierarchy has three tiers",
            "FACT",
            existing,
        )
        assert matches == []


class TestIncrementContradictionCount:
    """Test contradiction count increment in database."""

    def test_increment_updates_database(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            from divineos.core.knowledge import (
                _get_connection,
                init_knowledge_table,
                store_knowledge,
            )
            from divineos.core.ledger import init_db

            init_db()
            init_knowledge_table()

            kid = store_knowledge(
                knowledge_type="FACT",
                content="Test entry for contradiction count",
                confidence=0.9,
            )

            # Verify starts at 0
            conn = _get_connection()
            row = conn.execute(
                "SELECT contradiction_count FROM knowledge WHERE knowledge_id = ?",
                (kid,),
            ).fetchone()
            conn.close()
            assert row[0] == 0

            # Increment
            increment_contradiction_count(kid)

            # Verify incremented
            conn = _get_connection()
            row = conn.execute(
                "SELECT contradiction_count FROM knowledge WHERE knowledge_id = ?",
                (kid,),
            ).fetchone()
            conn.close()
            assert row[0] == 1

            # Increment again
            increment_contradiction_count(kid)
            conn = _get_connection()
            row = conn.execute(
                "SELECT contradiction_count FROM knowledge WHERE knowledge_id = ?",
                (kid,),
            ).fetchone()
            conn.close()
            assert row[0] == 2
        finally:
            os.environ.pop("DIVINEOS_DB", None)


class TestResolveContradiction:
    """Test contradiction resolution."""

    def test_temporal_supersedes_old(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            from divineos.core.knowledge import (
                _get_connection,
                init_knowledge_table,
                store_knowledge,
            )
            from divineos.core.ledger import init_db

            init_db()
            init_knowledge_table()

            old_id = store_knowledge(
                knowledge_type="BOUNDARY",
                content="The ask command cannot search core memory",
                confidence=0.9,
            )
            new_id = store_knowledge(
                knowledge_type="BOUNDARY",
                content="The ask command now searches core memory after the fix",
                confidence=0.9,
            )

            match = ContradictionMatch(
                existing_id=old_id,
                existing_content="The ask command cannot search core memory",
                overlap_score=0.7,
                negation_detected=True,
                contradiction_type="TEMPORAL",
            )

            resolve_contradiction(new_id, match)

            # Old entry should be superseded
            conn = _get_connection()
            row = conn.execute(
                "SELECT superseded_by, contradiction_count FROM knowledge WHERE knowledge_id = ?",
                (old_id,),
            ).fetchone()
            conn.close()
            assert row[0] is not None  # superseded_by set
            assert row[1] == 1  # contradiction_count incremented
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_direct_lowers_confidence(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            from divineos.core.knowledge import (
                _get_connection,
                init_knowledge_table,
                store_knowledge,
            )
            from divineos.core.ledger import init_db

            init_db()
            init_knowledge_table()

            old_id = store_knowledge(
                knowledge_type="PRINCIPLE",
                content="Always mock database calls in tests",
                confidence=0.9,
            )
            new_id = store_knowledge(
                knowledge_type="PRINCIPLE",
                content="Never mock database calls in tests",
                confidence=0.9,
            )

            match = ContradictionMatch(
                existing_id=old_id,
                existing_content="Always mock database calls in tests",
                overlap_score=0.6,
                negation_detected=True,
                contradiction_type="DIRECT",
            )

            resolve_contradiction(new_id, match)

            # Old entry should have lowered confidence
            conn = _get_connection()
            row = conn.execute(
                "SELECT confidence, contradiction_count FROM knowledge WHERE knowledge_id = ?",
                (old_id,),
            ).fetchone()
            conn.close()
            assert row[0] == 0.75  # 0.9 - 0.15
            assert row[1] == 1
        finally:
            os.environ.pop("DIVINEOS_DB", None)


class TestPipelineContradictionWiring:
    """Test that contradiction scanning works end-to-end with real DB entries."""

    def test_new_knowledge_triggers_contradiction_resolution(self, tmp_path):
        """Simulate what the pipeline does: store entries, scan, resolve."""
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            from divineos.core.knowledge import (
                _get_connection,
                init_knowledge_table,
                store_knowledge,
            )
            from divineos.core.ledger import init_db

            init_db()
            init_knowledge_table()

            # Store an existing fact
            old_id = store_knowledge(
                knowledge_type="FACT",
                content="The project has 1500 tests passing in the test suite",
                confidence=0.9,
            )

            # Store a new fact that supersedes it (high overlap, updated number)
            new_id = store_knowledge(
                knowledge_type="FACT",
                content="The project has 2073 tests passing in the test suite",
                confidence=0.9,
            )

            # Run the same logic the pipeline uses
            conn = _get_connection()
            row = conn.execute(
                "SELECT content, knowledge_type FROM knowledge WHERE knowledge_id = ?",
                (new_id,),
            ).fetchone()
            new_content, new_type = row[0], row[1]

            existing_rows = conn.execute(
                "SELECT knowledge_id, content, knowledge_type, superseded_by "
                "FROM knowledge WHERE knowledge_type = ? AND knowledge_id != ? "
                "AND superseded_by IS NULL",
                (new_type, new_id),
            ).fetchall()
            conn.close()

            existing_entries = [
                {
                    "knowledge_id": r[0],
                    "content": r[1],
                    "knowledge_type": r[2],
                    "superseded_by": r[3],
                }
                for r in existing_rows
            ]

            matches = scan_for_contradictions(new_content, new_type, existing_entries)
            assert len(matches) >= 1
            assert matches[0].existing_id == old_id

            # Resolve it
            resolve_contradiction(new_id, matches[0])

            # Old entry should now be superseded
            conn = _get_connection()
            row = conn.execute(
                "SELECT superseded_by FROM knowledge WHERE knowledge_id = ?",
                (old_id,),
            ).fetchone()
            conn.close()
            assert row[0] is not None

        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_no_self_contradiction(self, tmp_path):
        """New knowledge should not contradict itself."""
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            from divineos.core.knowledge import (
                _get_connection,
                init_knowledge_table,
                store_knowledge,
            )
            from divineos.core.ledger import init_db

            init_db()
            init_knowledge_table()

            kid = store_knowledge(
                knowledge_type="FACT",
                content="DivineOS uses append-only ledger for event storage",
                confidence=0.9,
            )

            # Query excludes self (knowledge_id != kid)
            conn = _get_connection()
            existing_rows = conn.execute(
                "SELECT knowledge_id, content, knowledge_type, superseded_by "
                "FROM knowledge WHERE knowledge_type = 'FACT' AND knowledge_id != ? "
                "AND superseded_by IS NULL",
                (kid,),
            ).fetchall()
            conn.close()

            existing_entries = [
                {
                    "knowledge_id": r[0],
                    "content": r[1],
                    "knowledge_type": r[2],
                    "superseded_by": r[3],
                }
                for r in existing_rows
            ]

            matches = scan_for_contradictions(
                "DivineOS uses append-only ledger for event storage",
                "FACT",
                existing_entries,
            )
            assert matches == []

        finally:
            os.environ.pop("DIVINEOS_DB", None)
