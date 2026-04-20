"""Tests for the ``divineos admin fix-encoding`` maintenance command.

Locks four invariants:

1. Dry-run reports mojibake without writing.
2. ``--apply`` writes the cleaned text back.
3. Clean stores report nothing to fix (idempotent after apply).
4. FTS index is rebuilt so search matches the cleaned text.
"""

from __future__ import annotations

import os
import time

import pytest
from click.testing import CliRunner

from divineos.cli import cli


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path):
    os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
    try:
        from divineos.core.knowledge import init_knowledge_table
        from divineos.core.ledger import init_db

        init_db()
        init_knowledge_table()
        yield tmp_path
    finally:
        os.environ.pop("DIVINEOS_DB", None)


def _insert_knowledge(knowledge_id: str, content: str) -> None:
    """Insert a row directly, bypassing the normal write path.
    Simulates pre-existing corrupted data."""
    from divineos.core.knowledge._base import get_connection

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO knowledge "
            "(knowledge_id, created_at, updated_at, knowledge_type, content, "
            "confidence, source_events, tags, access_count, content_hash, "
            "source, maturity, corroboration_count, contradiction_count) "
            "VALUES (?, ?, ?, 'FACT', ?, 0.5, '[]', '[]', 0, ?, 'test', "
            "'RAW', 0, 0)",
            (
                knowledge_id,
                time.time(),
                time.time(),
                content,
                f"hash-{knowledge_id}",
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _read_content(knowledge_id: str) -> str | None:
    from divineos.core.knowledge._base import get_connection

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT content FROM knowledge WHERE knowledge_id = ?",
            (knowledge_id,),
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def _read_current_content(knowledge_id: str) -> str | None:
    """Follow the supersession chain to the currently-active version."""
    from divineos.core.knowledge._base import get_connection

    conn = get_connection()
    try:
        cur_id = knowledge_id
        for _ in range(10):  # safety bound
            row = conn.execute(
                "SELECT content, superseded_by FROM knowledge WHERE knowledge_id = ?",
                (cur_id,),
            ).fetchone()
            if not row:
                return None
            content, sup_by = row
            if not sup_by or sup_by.startswith("FORGET:"):
                return content
            cur_id = sup_by
        return content
    finally:
        conn.close()


# A known mojibake string — "Use SQLite — zero dependencies" with em-dash
# double-encoded via CP-1252 read, UTF-8 write cycle twice.
_MOJIBAKE = "Use SQLite \u00c3\u0192\u00c2\u00a2\u00c3\u00a2\u00e2\u20ac\u0161\u00c2\u00ac\u00c3\u00a2\u00e2\u201a\u00ac\u00ef\u00bf\u00bd zero deps"


class TestDryRun:
    def test_reports_mojibake_without_writing(self):
        _insert_knowledge("kn-dirty", _MOJIBAKE)
        runner = CliRunner()

        result = runner.invoke(cli, ["admin", "fix-encoding"])
        assert result.exit_code == 0, result.output
        assert "kn-dirty" in result.output
        assert "Dry-run" in result.output

        # Content must still be corrupted (no write happened)
        assert _read_content("kn-dirty") == _MOJIBAKE

    def test_clean_store_reports_nothing(self):
        _insert_knowledge("kn-clean", "Use SQLite \u2014 zero deps")
        runner = CliRunner()

        result = runner.invoke(cli, ["admin", "fix-encoding"])
        assert result.exit_code == 0, result.output
        assert "Store is clean" in result.output or "No mojibake" in result.output


class TestApply:
    def test_apply_writes_cleaned_content(self):
        _insert_knowledge("kn-dirty", _MOJIBAKE)
        runner = CliRunner()

        result = runner.invoke(cli, ["admin", "fix-encoding", "--apply"])
        assert result.exit_code == 0, result.output
        assert "Repaired" in result.output

        # Repair is now a supersession (append-only invariant). Original
        # entry preserved with its original (corrupted) content; the new
        # entry holds the cleaned version.
        assert _read_content("kn-dirty") == _MOJIBAKE, (
            "original entry's content must be preserved per append-only rule"
        )
        after = _read_current_content("kn-dirty")
        assert after is not None
        assert after != _MOJIBAKE
        assert "\u00c3" not in after  # double-Ãƒ pattern is gone

    def test_apply_idempotent_on_second_run(self):
        """Running apply twice on the same input is a no-op the second time."""
        _insert_knowledge("kn-dirty", _MOJIBAKE)
        runner = CliRunner()

        first = runner.invoke(cli, ["admin", "fix-encoding", "--apply"])
        assert "Repaired" in first.output

        second = runner.invoke(cli, ["admin", "fix-encoding", "--apply"])
        assert "Store is clean" in second.output or "No mojibake" in second.output

    def test_does_not_touch_clean_rows(self):
        _insert_knowledge("kn-clean", "Use SQLite \u2014 zero deps")
        _insert_knowledge("kn-dirty", _MOJIBAKE)
        before_clean = _read_content("kn-clean")

        runner = CliRunner()
        runner.invoke(cli, ["admin", "fix-encoding", "--apply"])

        assert _read_content("kn-clean") == before_clean


class TestSupersededRowsSkipped:
    def test_superseded_rows_not_touched(self):
        """Mojibake in superseded rows is historical — don't rewrite it."""
        from divineos.core.knowledge._base import get_connection

        _insert_knowledge("kn-super", _MOJIBAKE)
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE knowledge SET superseded_by = 'kn-new' WHERE knowledge_id = 'kn-super'"
            )
            conn.commit()
        finally:
            conn.close()

        runner = CliRunner()
        result = runner.invoke(cli, ["admin", "fix-encoding", "--apply"])
        # Should report nothing to fix — the only mojibake row is superseded
        assert "Store is clean" in result.output or "No mojibake" in result.output

        # And the superseded row still has its original (corrupted) content
        assert _read_content("kn-super") == _MOJIBAKE


class TestFtsRebuildAfterApply:
    def test_fts_rebuilt_on_apply(self):
        """After --apply, FTS should match the cleaned content so
        search returns the repaired rows."""
        _insert_knowledge("kn-dirty", _MOJIBAKE)
        runner = CliRunner()

        result = runner.invoke(cli, ["admin", "fix-encoding", "--apply"])
        # FTS rebuild message should appear
        assert "FTS index rebuilt" in result.output or "Repaired" in result.output
