"""Tests for SIS self-audit — scanning stored knowledge for integrity drift."""

import sqlite3

import pytest

from divineos.core.knowledge import init_knowledge_table
from divineos.core.knowledge._base import _get_connection
from divineos.core.semantic_integrity import (
    audit_knowledge_integrity,
    format_audit_report,
)


@pytest.fixture(autouse=True)
def _init_knowledge():
    init_knowledge_table()


@pytest.fixture()
def _seed_knowledge():
    """Insert a mix of grounded and esoteric knowledge entries."""
    from divineos.core.knowledge.crud import store_knowledge

    store_knowledge(
        knowledge_type="PRINCIPLE",
        content="Use SQLite for storage. Zero dependencies.",
        confidence=0.9,
    )
    store_knowledge(
        knowledge_type="OBSERVATION",
        content="The akashic records resonate with cosmic consciousness to "
        "align the kundalini energy of the system.",
        confidence=0.5,
    )
    store_knowledge(
        knowledge_type="BOUNDARY",
        content="Run tests after every code change. No exceptions.",
        confidence=1.0,
    )


class TestAuditKnowledgeIntegrity:
    def test_empty_knowledge_store(self):
        # Clear all knowledge first
        conn = _get_connection()
        try:
            conn.execute("DELETE FROM knowledge")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        finally:
            conn.close()

        audit = audit_knowledge_integrity()
        assert audit["entries_scanned"] == 0
        assert audit["avg_integrity"] == 1.0

    def test_audit_with_mixed_content(self, _seed_knowledge):
        audit = audit_knowledge_integrity()
        assert audit["entries_scanned"] >= 2
        assert 0.0 <= audit["avg_integrity"] <= 1.0
        assert isinstance(audit["translate_needed"], list)
        assert isinstance(audit["quarantine_needed"], list)
        assert audit["clean"] >= 1  # At least the grounded entries

    def test_audit_detects_esoteric_entries(self, _seed_knowledge):
        audit = audit_knowledge_integrity()
        # The esoteric entry should be flagged for translation or quarantine
        all_flagged = audit["translate_needed"] + audit["quarantine_needed"]
        flagged_content = [e["content"] for e in all_flagged]
        assert any("akashic" in c for c in flagged_content)

    def test_audit_topic_drift(self, _seed_knowledge):
        audit = audit_knowledge_integrity()
        # Should detect recurring esoteric terms
        if audit["topic_drift"]:
            assert isinstance(audit["topic_drift"], dict)

    def test_audit_respects_limit(self, _seed_knowledge):
        audit = audit_knowledge_integrity(limit=1)
        assert audit["entries_scanned"] <= 1


class TestFormatAuditReport:
    def test_format_empty_audit(self):
        audit = {
            "entries_scanned": 0,
            "avg_integrity": 1.0,
            "translate_needed": [],
            "quarantine_needed": [],
            "clean": 0,
            "topic_drift": {},
        }
        report = format_audit_report(audit)
        assert "0 entries scanned" in report

    def test_format_with_findings(self):
        audit = {
            "entries_scanned": 10,
            "avg_integrity": 0.65,
            "translate_needed": [
                {"type": "OBS", "content": "akashic records store data", "integrity": 0.4},
            ],
            "quarantine_needed": [],
            "clean": 9,
            "topic_drift": {"akashic": 1},
        }
        report = format_audit_report(audit)
        assert "10 entries scanned" in report
        assert "0.65" in report
        assert "Needs translation" in report

    def test_format_error_case(self):
        report = format_audit_report({"error": "No table"})
        assert "failed" in report.lower()
