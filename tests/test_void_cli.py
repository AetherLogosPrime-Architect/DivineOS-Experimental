"""Tests for VOID CLI commands."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from divineos.cli import cli
from divineos.core.void import mode_marker


@pytest.fixture
def void_db(tmp_path, monkeypatch):
    db = tmp_path / "void_ledger.db"
    monkeypatch.setenv("DIVINEOS_VOID_DB", str(db))
    return db


@pytest.fixture(autouse=True)
def isolated_marker(tmp_path):
    mpath = tmp_path / "void_mode.json"
    with patch.object(mode_marker, "marker_path", return_value=mpath):
        yield


@pytest.fixture
def runner():
    return CliRunner()


class TestList:
    def test_list_shows_personas(self, runner, void_db) -> None:
        r = runner.invoke(cli, ["void", "list"])
        assert r.exit_code == 0, r.output
        assert "sycophant" in r.output
        assert "nyarlathotep" in r.output
        assert "HIGH-BAR" in r.output


class TestShow:
    def test_show_existing(self, runner, void_db) -> None:
        r = runner.invoke(cli, ["void", "show", "mirror"])
        assert r.exit_code == 0, r.output
        assert "DOES NOT" in r.output

    def test_show_missing(self, runner, void_db) -> None:
        r = runner.invoke(cli, ["void", "show", "nope"])
        assert r.exit_code != 0


class TestTest:
    def test_single_persona_runs(self, runner, void_db) -> None:
        r = runner.invoke(cli, ["void", "test", "proposal-x", "--persona", "sycophant"])
        assert r.exit_code == 0, r.output
        assert "sycophant" in r.output
        assert "void_event_id" in r.output

    def test_high_bar_refused_without_flag(self, runner, void_db) -> None:
        r = runner.invoke(cli, ["void", "test", "x", "--persona", "nyarlathotep"])
        assert r.exit_code != 0

    def test_high_bar_runs_with_flag(self, runner, void_db) -> None:
        r = runner.invoke(
            cli,
            ["void", "test", "x", "--persona", "nyarlathotep", "--allow-high-bar"],
        )
        assert r.exit_code == 0, r.output


class TestTestDeep:
    def test_skips_high_bar_by_default(self, runner, void_db) -> None:
        r = runner.invoke(cli, ["void", "test-deep", "tgt"])
        assert r.exit_code == 0, r.output
        assert "SKIP nyarlathotep" in r.output
        assert "sycophant" in r.output

    def test_runs_all_with_flag(self, runner, void_db) -> None:
        r = runner.invoke(cli, ["void", "test-deep", "tgt", "--allow-high-bar"])
        assert r.exit_code == 0, r.output
        assert "SKIP" not in r.output
        assert "nyarlathotep" in r.output


class TestEvents:
    def test_events_after_run(self, runner, void_db) -> None:
        runner.invoke(cli, ["void", "test", "x", "--persona", "sycophant"])
        r = runner.invoke(cli, ["void", "events"])
        assert r.exit_code == 0, r.output
        assert "VOID_INVOCATION_STARTED" in r.output
        assert "VOID_FINDING" in r.output
        assert "VOID_SHRED" in r.output


class TestVerify:
    def test_clean_chain_ok(self, runner, void_db) -> None:
        runner.invoke(cli, ["void", "test", "x", "--persona", "sycophant"])
        r = runner.invoke(cli, ["void", "verify"])
        assert r.exit_code == 0, r.output
        assert "OK" in r.output


class TestShred:
    def test_force_required(self, runner, void_db) -> None:
        r = runner.invoke(cli, ["void", "shred"])
        assert r.exit_code != 0

    def test_force_clears_orphan(self, runner, void_db) -> None:
        mode_marker.write_marker("nyarlathotep", session_id="orphan")
        assert mode_marker.is_active() is True
        r = runner.invoke(cli, ["void", "shred", "--force"])
        assert r.exit_code == 0, r.output
        assert mode_marker.is_active() is False

    def test_force_idempotent_when_clean(self, runner, void_db) -> None:
        r = runner.invoke(cli, ["void", "shred", "--force"])
        assert r.exit_code == 0, r.output
        assert "not active" in r.output
