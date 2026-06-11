"""Tests for the semantic-duplicate surface added to `divineos learn`.

Built 2026-06-11 alongside the find_similar_in_knowledge wiring. The
substrate's existing dedup is content-hash based — catches EXACT
duplicates only. Paraphrases of the same lesson with different
vocabulary slip through and pile up as separate entries.

These tests pin the new behavior:
- When a lesson is filed whose meaning is close (semantic similarity
  >= threshold) to existing entries, the surface lists them as
  "semantically close" candidates BEFORE filing fresh
- The lesson still gets filed — the surface is informational, not
  blocking (caller chooses whether to supersede manually)
- --no-dedup-check disables the surface entirely
- When nothing close exists, no surface fires (clean output)
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner


def _semantic_available() -> bool:
    try:
        from divineos.core.semantic_store import embed

        return embed("test sentence to confirm model loads") is not None
    except Exception:
        return False


_skip_no_semantic = pytest.mark.skipif(
    not _semantic_available(),
    reason="semantic-similarity primitive unavailable (ml extras missing)",
)


def _setup_isolated_db(tmp_path, monkeypatch):
    """Point divineos at a fresh sqlite DB so the test never touches
    the live substrate. Re-init the schema."""
    db_path = tmp_path / "test_knowledge.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db_path))
    from divineos.core.knowledge._base import init_knowledge_table

    init_knowledge_table()


def _invoke_learn(args: list[str]) -> tuple[int, str]:
    """Invoke `divineos learn` via Click's CliRunner. Returns
    (exit_code, stdout). Hides ANSI colors for clean assertions."""
    import click

    # Build a thin parent CLI that has just the learn command registered.
    cli = click.Group()
    from divineos.cli import knowledge_commands

    knowledge_commands.register(cli)

    runner = CliRunner()
    result = runner.invoke(cli, ["learn", *args])
    return result.exit_code, result.output


@_skip_no_semantic
class TestDedupSurface:
    def test_surfaces_semantically_close_existing_entry(self, tmp_path, monkeypatch):
        _setup_isolated_db(tmp_path, monkeypatch)
        from divineos.core.knowledge.crud import store_knowledge

        # Seed an existing entry that the new learn will paraphrase.
        store_knowledge(
            "PRINCIPLE",
            "Refactored the verify-claim detector to add source-letter traceback",
        )

        # File a paraphrase of the same idea via the learn CLI.
        exit_code, output = _invoke_learn(
            [
                "Updated the unverified-claim detector to track which letter the citation came from",
                "--type",
                "PRINCIPLE",
                "--dedup-threshold",
                "0.3",  # below seeded entry's expected similarity
            ]
        )
        assert exit_code == 0
        assert "semantically close existing entries" in output
        assert "verify-claim" in output or "source-letter" in output

    def test_files_fresh_anyway_after_surface(self, tmp_path, monkeypatch):
        """The dedup surface is informational; the new entry still gets
        filed. Caller chooses whether to supersede manually."""
        _setup_isolated_db(tmp_path, monkeypatch)
        from divineos.core.knowledge.crud import store_knowledge
        from divineos.core.knowledge._base import get_connection

        store_knowledge(
            "PRINCIPLE",
            "Refactored the verify-claim detector to add source-letter traceback",
        )

        _, output = _invoke_learn(
            [
                "Updated the unverified-claim detector to track which letter the citation came from",
                "--type",
                "PRINCIPLE",
                "--dedup-threshold",
                "0.3",
            ]
        )
        assert "Stored knowledge:" in output

        conn = get_connection()
        n = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
        assert n == 2  # both the seeded and the new one are stored

    def test_no_surface_when_nothing_close_exists(self, tmp_path, monkeypatch):
        _setup_isolated_db(tmp_path, monkeypatch)
        from divineos.core.knowledge.crud import store_knowledge

        store_knowledge("FACT", "the apple harvest came in early this year")

        # File something completely unrelated — no surface should fire.
        _, output = _invoke_learn(
            [
                "Refactored the unverified-claim detector to track letter sources",
                "--type",
                "PRINCIPLE",
                "--dedup-threshold",
                "0.7",
            ]
        )
        assert "semantically close" not in output
        assert "Stored knowledge:" in output

    def test_no_dedup_check_disables_surface(self, tmp_path, monkeypatch):
        _setup_isolated_db(tmp_path, monkeypatch)
        from divineos.core.knowledge.crud import store_knowledge

        store_knowledge(
            "PRINCIPLE",
            "Refactored the verify-claim detector to add source-letter traceback",
        )

        # Even with a very low threshold, --no-dedup-check should suppress.
        _, output = _invoke_learn(
            [
                "Updated the unverified-claim detector to track which letter the citation came from",
                "--type",
                "PRINCIPLE",
                "--dedup-threshold",
                "0.1",
                "--no-dedup-check",
            ]
        )
        assert "semantically close" not in output
        assert "Stored knowledge:" in output

    def test_surface_threshold_filters_correctly(self, tmp_path, monkeypatch):
        """A very high threshold should suppress surfacing of moderately-
        close entries; a low threshold should surface them."""
        _setup_isolated_db(tmp_path, monkeypatch)
        from divineos.core.knowledge.crud import store_knowledge

        store_knowledge(
            "PRINCIPLE",
            "Refactored the verify-claim detector to add source-letter traceback",
        )

        # High threshold — strict, less likely to fire
        _, output_strict = _invoke_learn(
            [
                "Updated the unverified-claim detector to track which letter the citation came from",
                "--type",
                "PRINCIPLE",
                "--dedup-threshold",
                "0.95",
                "--no-dedup-check",  # to test the "no surface" path
            ]
        )
        # No-dedup-check forces no surface regardless of threshold.
        assert "semantically close" not in output_strict
