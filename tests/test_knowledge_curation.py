"""Tests for knowledge curation — layer assignment, archival, text cleanup."""

import time

from divineos.core.knowledge._base import _get_connection, init_knowledge_table
from divineos.core.knowledge.curation import (
    assign_layer,
    clean_entry_text,
    ensure_layer_column,
    run_curation,
)
from divineos.core.knowledge.crud import store_knowledge


def _store(
    content: str,
    ktype: str = "PRINCIPLE",
    confidence: float = 1.0,
    source: str = "INHERITED",
    access: int = 0,
    age_days: float = 0.0,
    maturity: str = "RAW",
) -> str:
    """Helper to store a knowledge entry with custom age."""
    kid = store_knowledge(ktype, content, confidence=confidence, source=source)
    if age_days > 0 or access > 0 or maturity != "RAW":
        conn = _get_connection()
        try:
            created = time.time() - (age_days * 86400)
            conn.execute(
                "UPDATE knowledge SET created_at = ?, updated_at = ?, "
                "access_count = ?, maturity = ? WHERE knowledge_id = ?",
                (created, created, access, maturity, kid),
            )
            conn.commit()
        finally:
            conn.close()
    return kid


class TestCleanEntryText:
    def test_removes_user_signal_repr(self):
        raw = "UserSignal(signal_type='correction', content='fix the thing', timestamp='2026-03-28T02:23')"
        cleaned = clean_entry_text(raw)
        assert "UserSignal" not in cleaned
        assert "signal_type" not in cleaned

    def test_cleans_correction_pattern(self):
        raw = "I was it works exactly as designed:, but got corrected -- i want it to block not just warn"
        cleaned = clean_entry_text(raw)
        assert "User correction:" in cleaned
        assert "i want it to block" in cleaned
        assert "I was it works" not in cleaned

    def test_cleans_affirmation_pattern(self):
        raw = "I fixed and pushed and it worked well -- user affirmed: perfect how is this all feeling now?"
        cleaned = clean_entry_text(raw)
        assert "User affirmed:" in cleaned
        assert "perfect" in cleaned

    def test_preserves_clean_text(self):
        clean = "Use SQLite for storage -- zero dependencies, embedded, reliable."
        assert clean_entry_text(clean) == clean

    def test_normalizes_whitespace(self):
        raw = "too   many    spaces   here"
        cleaned = clean_entry_text(raw)
        assert "  " not in cleaned


class TestLayerAssignment:
    def test_recent_correction_is_urgent(self):
        entry = {
            "created_at": time.time() - 3600,  # 1 hour ago
            "source": "CORRECTED",
            "confidence": 1.0,
            "access_count": 0,
            "maturity": "RAW",
            "knowledge_type": "PRINCIPLE",
        }
        assert assign_layer(entry) == "urgent"

    def test_old_correction_is_not_urgent(self):
        entry = {
            "created_at": time.time() - 200000,  # > 1 day
            "source": "CORRECTED",
            "confidence": 1.0,
            "access_count": 5,
            "maturity": "TESTED",
            "knowledge_type": "PRINCIPLE",
        }
        assert assign_layer(entry) != "urgent"

    def test_low_confidence_is_archived(self):
        entry = {
            "created_at": time.time() - 86400 * 30,
            "source": "INHERITED",
            "confidence": 0.2,
            "access_count": 1,
            "maturity": "RAW",
            "knowledge_type": "FACT",
        }
        assert assign_layer(entry) == "archive"

    def test_old_episode_is_archived(self):
        entry = {
            "created_at": time.time() - 86400 * 35,
            "source": "INHERITED",
            "confidence": 1.0,
            "access_count": 3,
            "maturity": "RAW",
            "knowledge_type": "EPISODE",
        }
        assert assign_layer(entry) == "archive"

    def test_established_principle_is_stable(self):
        entry = {
            "created_at": time.time() - 86400 * 10,  # 10 days old
            "source": "DEMONSTRATED",
            "confidence": 0.95,
            "access_count": 20,
            "maturity": "CONFIRMED",
            "knowledge_type": "PRINCIPLE",
        }
        assert assign_layer(entry) == "stable"

    def test_directive_stays_active(self):
        entry = {
            "created_at": time.time() - 86400 * 10,
            "source": "INHERITED",
            "confidence": 1.0,
            "access_count": 50,
            "maturity": "CONFIRMED",
            "knowledge_type": "DIRECTIVE",
        }
        # Directives are always active (operating principles)
        assert assign_layer(entry) == "active"

    def test_normal_entry_is_active(self):
        entry = {
            "created_at": time.time() - 86400 * 3,
            "source": "INHERITED",
            "confidence": 0.8,
            "access_count": 5,
            "maturity": "TESTED",
            "knowledge_type": "FACT",
        }
        assert assign_layer(entry) == "active"


class TestRunCuration:
    def setup_method(self):
        init_knowledge_table()
        ensure_layer_column()

    def test_curation_assigns_layers(self):
        _store(
            "A recent correction needs attention", ktype="PRINCIPLE", source="CORRECTED", age_days=0
        )
        _store("An old episode from ages ago", ktype="EPISODE", age_days=35)
        _store(
            "A well-established principle everyone knows",
            ktype="PRINCIPLE",
            confidence=0.95,
            access=25,
            age_days=14,
            maturity="CONFIRMED",
        )

        result = run_curation()
        assert result["layers_assigned"] > 0

    def test_curation_cleans_text(self):
        kid = _store(
            "I was doing X, but got corrected -- you need to do Y instead because reasons",
            ktype="PRINCIPLE",
        )
        result = run_curation()

        conn = _get_connection()
        try:
            row = conn.execute(
                "SELECT content FROM knowledge WHERE knowledge_id = ?", (kid,)
            ).fetchone()
        finally:
            conn.close()

        assert row is not None
        assert "User correction:" in row[0]
        assert result["text_cleaned"] > 0

    def test_curation_returns_counts(self):
        result = run_curation()
        assert "layers_assigned" in result
        assert "text_cleaned" in result
        assert "archived" in result
        assert "promoted_stable" in result
        assert "promoted_urgent" in result
