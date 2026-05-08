"""Tests for `divineos prereg export` — repo-portable markdown dump.

The export subcommand exists to bridge the runtime-only/repo-only gap:
pre-registrations live in a SQLite store that does not survive a fresh
clone, so a reviewer reading just the repo cannot see what mechanisms
the agent committed itself to. Exporting them to ``docs/pre_regs/<id>.md``
makes the commitment travel with the source.
"""

from __future__ import annotations

import os

import pytest
from click.testing import CliRunner

from divineos.cli import cli
from divineos.core.knowledge import init_knowledge_table
from divineos.core.ledger import init_db
from divineos.core.pre_registrations import (
    file_pre_registration,
    init_pre_registrations_tables,
)


@pytest.fixture(autouse=True)
def _prereg_db(tmp_path):
    os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
    try:
        init_db()
        init_knowledge_table()
        init_pre_registrations_tables()
        yield
    finally:
        os.environ.pop("DIVINEOS_DB", None)


def _file_one(mechanism: str = "test_mech") -> str:
    return file_pre_registration(
        actor="aether",
        mechanism=mechanism,
        claim="detects pattern X in session",
        success_criterion="metric Y drops within 30 days",
        falsifier="metric Y unchanged or rising at review",
        review_window_days=30,
        tags=["test", "portability"],
    )


class TestExport:
    def test_empty_store_reports_nothing(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["prereg", "export", "--out-dir", str(tmp_path / "out")])
        assert result.exit_code == 0
        assert "No pre-registrations" in result.output

    def test_writes_one_file_per_prereg(self, tmp_path):
        pid_a = _file_one("mech_a")
        pid_b = _file_one("mech_b")

        out = tmp_path / "out"
        runner = CliRunner()
        result = runner.invoke(cli, ["prereg", "export", "--out-dir", str(out)])
        assert result.exit_code == 0, result.output
        assert (out / f"{pid_a}.md").exists()
        assert (out / f"{pid_b}.md").exists()

    def test_markdown_contains_load_bearing_fields(self, tmp_path):
        pid = _file_one("portable_mech")
        out = tmp_path / "out"
        runner = CliRunner()
        runner.invoke(cli, ["prereg", "export", "--out-dir", str(out)])
        body = (out / f"{pid}.md").read_text(encoding="utf-8")

        # Every load-bearing field must round-trip into the markdown.
        assert "portable_mech" in body
        assert "aether" in body
        assert "detects pattern X" in body
        assert "metric Y drops within 30 days" in body
        assert "metric Y unchanged or rising at review" in body
        assert "OPEN" in body  # outcome
        assert "test, portability" in body  # tags
        assert pid in body

    def test_outcome_filter(self, tmp_path):
        # All filed prereg start OPEN; FAILED filter should yield nothing.
        _file_one()
        out = tmp_path / "out"
        runner = CliRunner()
        result = runner.invoke(
            cli, ["prereg", "export", "--out-dir", str(out), "--outcome", "FAILED"]
        )
        assert result.exit_code == 0
        assert "No pre-registrations" in result.output
        # And nothing was written.
        assert not out.exists() or not any(out.iterdir())

    def test_creates_out_dir(self, tmp_path):
        _file_one()
        nested = tmp_path / "deeply" / "nested" / "out"
        runner = CliRunner()
        result = runner.invoke(cli, ["prereg", "export", "--out-dir", str(nested)])
        assert result.exit_code == 0
        assert nested.is_dir()
        assert any(nested.glob("*.md"))
