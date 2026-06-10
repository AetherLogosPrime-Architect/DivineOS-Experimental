"""Tests for `divineos backlog` — structural-debt tracker CLI.

Andrew 2026-06-09: TaskCreate dumps the live list every few turns;
~100 entries consumed ~37% of session bytes. The discipline keeps the
live list small (<5 current-arc items); long-term debt lives in
docs/wireup-backlog.md. The CLI keeps the markdown parseable.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from divineos.cli import backlog_commands as bl
from divineos.cli import cli


_TEMPLATE = """# Wire-Up Backlog

intro text

## Clusters

<!-- BACKLOG-ENTRIES-BEGIN -->

<!-- BACKLOG-ENTRIES-END -->
"""


@pytest.fixture
def backlog_file(tmp_path, monkeypatch) -> Path:
    """Lay down a minimal backlog template and point the CLI at it."""
    path = tmp_path / "wireup-backlog.md"
    path.write_text(_TEMPLATE, encoding="utf-8")
    monkeypatch.setenv("DIVINEOS_BACKLOG_PATH", str(path))
    return path


class TestAddEntry:
    def test_first_add_creates_cluster_section(self, backlog_file):
        bl.add_entry("Wire X to Y", cluster="gates", description="closes Z")
        body = backlog_file.read_text(encoding="utf-8")
        assert "### gates" in body
        assert "Wire X to Y" in body
        assert "closes Z" in body

    def test_second_add_same_cluster_appends(self, backlog_file):
        bl.add_entry("first", cluster="gates", description="a")
        bl.add_entry("second", cluster="gates", description="b")
        body = backlog_file.read_text(encoding="utf-8")
        # Only one cluster header; both entries present.
        assert body.count("### gates") == 1
        assert "first" in body
        assert "second" in body

    def test_add_different_clusters_creates_separate_sections(self, backlog_file):
        bl.add_entry("a", cluster="gates", description="")
        bl.add_entry("b", cluster="briefing", description="")
        body = backlog_file.read_text(encoding="utf-8")
        assert "### gates" in body
        assert "### briefing" in body

    def test_add_entry_includes_filed_date(self, backlog_file):
        bl.add_entry("X", cluster="c", description="")
        body = backlog_file.read_text(encoding="utf-8")
        # YYYY-MM-DD shape inside [filed ...]
        import re

        assert re.search(r"\[filed \d{4}-\d{2}-\d{2}\]", body)

    def test_add_preserves_text_outside_markers(self, backlog_file):
        bl.add_entry("X", cluster="c", description="")
        body = backlog_file.read_text(encoding="utf-8")
        # Header and intro must survive.
        assert "# Wire-Up Backlog" in body
        assert "intro text" in body
        assert "## Clusters" in body

    def test_add_with_missing_file_raises(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_BACKLOG_PATH", str(tmp_path / "nope.md"))
        with pytest.raises(FileNotFoundError):
            bl.add_entry("X", cluster="c", description="")


class TestListEntries:
    def test_empty_file_returns_empty(self, backlog_file):
        assert bl.list_entries() == {}

    def test_after_add_lists_entries(self, backlog_file):
        bl.add_entry("first", cluster="gates", description="a")
        bl.add_entry("second", cluster="briefing", description="b")
        result = bl.list_entries()
        assert set(result.keys()) == {"gates", "briefing"}
        assert any("first" in e for e in result["gates"])
        assert any("second" in e for e in result["briefing"])

    def test_filter_to_one_cluster(self, backlog_file):
        bl.add_entry("a", cluster="gates", description="")
        bl.add_entry("b", cluster="briefing", description="")
        result = bl.list_entries(cluster="gates")
        assert list(result.keys()) == ["gates"]


class TestCliSurface:
    def test_add_cmd_via_cli(self, backlog_file):
        result = CliRunner().invoke(
            cli, ["backlog", "add", "Fix X", "--cluster", "gates", "-d", "closes Y"]
        )
        assert result.exit_code == 0
        assert "Filed under [gates]" in result.output
        body = backlog_file.read_text(encoding="utf-8")
        assert "Fix X" in body

    def test_list_cmd_via_cli(self, backlog_file):
        bl.add_entry("test entry", cluster="x", description="d")
        result = CliRunner().invoke(cli, ["backlog", "list"])
        assert result.exit_code == 0
        assert "test entry" in result.output

    def test_list_empty_message(self, backlog_file):
        result = CliRunner().invoke(cli, ["backlog", "list"])
        assert result.exit_code == 0
        assert "empty" in result.output.lower()

    def test_add_to_missing_backlog_exits_nonzero(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_BACKLOG_PATH", str(tmp_path / "nope.md"))
        result = CliRunner().invoke(cli, ["backlog", "add", "X", "--cluster", "c"])
        assert result.exit_code != 0
