"""Tests for the knowledge maturity diagnostic.

Locks three invariants:

1. ``_is_transient`` correctly classifies EPISODE (always transient)
   and session-id-bearing content.
2. ``_is_transient`` does NOT flag generalizable claims (PRINCIPLE,
   DIRECTIVE, etc.) even when the content could superficially look
   related to a session.
3. ``classify_maturity`` returns a clean breakdown on a mixed store.
"""

from __future__ import annotations

import os
import time

import pytest

from divineos.core.knowledge.maturity_diagnostic import (
    MaturityBreakdown,
    _is_transient,
    classify_maturity,
)


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path):
    os.environ["DIVINEOS_DB"] = str(tmp_path / "maturity.db")
    try:
        from divineos.core.knowledge import init_knowledge_table
        from divineos.core.ledger import init_db

        init_db()
        init_knowledge_table()
        yield
    finally:
        os.environ.pop("DIVINEOS_DB", None)


def _insert(
    knowledge_id: str,
    knowledge_type: str,
    content: str,
    maturity: str = "RAW",
    corroboration: int = 0,
    confidence: float = 0.5,
) -> None:
    from divineos.core.knowledge._base import get_connection

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO knowledge "
            "(knowledge_id, created_at, updated_at, knowledge_type, content, "
            "confidence, source_events, tags, access_count, content_hash, "
            "source, maturity, corroboration_count, contradiction_count) "
            "VALUES (?, ?, ?, ?, ?, ?, '[]', '[]', 0, ?, 'test', ?, ?, 0)",
            (
                knowledge_id,
                time.time(),
                time.time(),
                knowledge_type,
                content,
                confidence,
                f"hash-{knowledge_id}",
                maturity,
                corroboration,
            ),
        )
        conn.commit()
    finally:
        conn.close()


class TestIsTransient:
    def test_episode_always_transient(self):
        assert _is_transient("EPISODE", "generic content with no session id")

    def test_episode_transient_with_session_id(self):
        assert _is_transient("EPISODE", "Session character: debugging.")

    def test_session_id_reference_makes_transient(self):
        """OBSERVATION with a session id is session-scoped."""
        assert _is_transient(
            "OBSERVATION",
            "I deviated by 77% (session 49e0393f-0363-4c4f-a411).",
        )

    def test_pattern_with_session_id_is_transient(self):
        assert _is_transient(
            "PATTERN",
            "Good recovery pattern (session 49e0393f-036).",
        )

    def test_principle_without_session_id_not_transient(self):
        assert not _is_transient(
            "PRINCIPLE",
            "Speak plainly. Avoid jargon.",
        )

    def test_directive_without_session_id_not_transient(self):
        assert not _is_transient(
            "DIRECTIVE",
            "Run divineos briefing at session start.",
        )

    def test_fact_without_session_id_not_transient(self):
        assert not _is_transient(
            "FACT",
            "DivineOS uses SQLite for storage.",
        )

    def test_observation_without_session_id_not_transient(self):
        """General observation, no session-scope — could generalize."""
        assert not _is_transient(
            "OBSERVATION",
            "Agents under sustained load exhibit specific failure modes.",
        )

    def test_none_content_safe(self):
        """Defensive: empty or None content shouldn't crash."""
        assert not _is_transient("PRINCIPLE", "")


class TestClassifyMaturityOnEmptyStore:
    def test_empty_store_returns_empty_breakdown(self):
        b = classify_maturity()
        assert isinstance(b, MaturityBreakdown)
        assert b.total == 0
        assert b.raw_transient == []
        assert b.raw_pending == []


class TestClassifyMaturityOnMixedStore:
    def test_splits_transient_from_pending(self):
        """Canonical mixed case — some EPISODEs, some session-scoped
        OBSERVATIONs, some general claims, some mature."""
        _insert("kn-ep1", "EPISODE", "Session character: debugging.")
        _insert("kn-obs1", "OBSERVATION", "Deviated by 77% in session abc123ef-0363.")
        _insert("kn-dir1", "DIRECTION", "Prefer plain English over jargon.")
        _insert("kn-princ", "PRINCIPLE", "Run tests before committing.", maturity="CONFIRMED")
        _insert("kn-pat", "PATTERN", "Recovery pattern across sessions.")

        b = classify_maturity()

        # Total counts everything non-superseded
        assert b.total == 5

        # Transient: EPISODE + session-scoped OBSERVATION
        transient_ids = {e["knowledge_id"] for e in b.raw_transient}
        assert "kn-ep1" in transient_ids
        assert "kn-obs1" in transient_ids

        # Pending: DIRECTION + PATTERN (no session id, could generalize)
        pending_ids = {e["knowledge_id"] for e in b.raw_pending}
        assert "kn-dir1" in pending_ids
        assert "kn-pat" in pending_ids

        # The CONFIRMED one is neither — it's not RAW
        assert "kn-princ" not in transient_ids
        assert "kn-princ" not in pending_ids

    def test_by_maturity_reflects_all_states(self):
        _insert("kn-r", "PRINCIPLE", "raw one", maturity="RAW")
        _insert("kn-t", "PRINCIPLE", "tested one", maturity="TESTED")
        _insert("kn-c", "PRINCIPLE", "confirmed one", maturity="CONFIRMED")

        b = classify_maturity()
        assert b.by_maturity["RAW"] == 1
        assert b.by_maturity["TESTED"] == 1
        assert b.by_maturity["CONFIRMED"] == 1
        assert b.total == 3

    def test_superseded_rows_excluded(self):
        """Superseded rows shouldn't count — the diagnostic is about
        the active knowledge shape."""
        from divineos.core.knowledge._base import get_connection

        _insert("kn-live", "PRINCIPLE", "active")
        _insert("kn-super", "PRINCIPLE", "old version")
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE knowledge SET superseded_by = 'kn-live' WHERE knowledge_id = 'kn-super'"
            )
            conn.commit()
        finally:
            conn.close()

        b = classify_maturity()
        assert b.total == 1


class TestBreakdownDataclass:
    def test_is_frozen(self):
        b = classify_maturity()
        with pytest.raises((AttributeError, Exception)):
            b.total = 999  # type: ignore[misc]

    def test_raw_entries_carry_full_detail(self):
        """Each entry in raw_transient / raw_pending has enough info
        for the operator to decide what to do with it."""
        _insert("kn-dir", "DIRECTION", "Be specific.")
        b = classify_maturity()

        entry = b.raw_pending[0]
        assert "knowledge_id" in entry
        assert "knowledge_type" in entry
        assert "content" in entry
        assert "corroboration_count" in entry
        assert "confidence" in entry
        assert "created_at" in entry
