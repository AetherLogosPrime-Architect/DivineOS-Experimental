"""Tests for the wire-up of expectation_tracking module via CLI.

The module (core/expectation_tracking) existed as callable code with
dedicated tests since 2026-04-30 (omni-mantra batch 3, commit ad8b9f3)
but had NO user-facing surface (no CLI, no hook integration). Same
wiring-gap shape Grok caught for care_dismissal + harm_acknowledgment
in round-22. Filed as substrate-knowledge e9bc98b6 and closed by
the expect_commands module + this test file.

## What this pins

- The CLI module imports cleanly and exposes register()
- The `expect` command group is registered with all four subcommands
- The underlying record_expectation/record_actual/open_expectations/
  calibration_summary API surface is reachable via the CLI
- End-to-end: predict produces an ID, list shows opens, close moves
  the prediction from open to closed-with-actual
"""

from __future__ import annotations

from click.testing import CliRunner


# ─── Module-level wire-up ───────────────────────────────────────────


class TestExpectCommandsModule:
    def test_module_imports(self):
        from divineos.cli import expect_commands  # noqa: F401

    def test_register_callable(self):
        from divineos.cli.expect_commands import register

        assert callable(register)


class TestCommandRegistration:
    """The expect group must be registered in the main CLI."""

    def test_expect_group_in_main_cli(self):
        from divineos.cli import cli

        # Click commands dict — the expect group should be a member
        assert "expect" in cli.commands

    def test_expect_predict_subcommand_registered(self):
        from divineos.cli import cli

        expect = cli.commands["expect"]
        assert "predict" in expect.commands  # type: ignore[attr-defined]

    def test_expect_close_subcommand_registered(self):
        from divineos.cli import cli

        expect = cli.commands["expect"]
        assert "close" in expect.commands  # type: ignore[attr-defined]

    def test_expect_list_subcommand_registered(self):
        from divineos.cli import cli

        expect = cli.commands["expect"]
        assert "list" in expect.commands  # type: ignore[attr-defined]

    def test_expect_summary_subcommand_registered(self):
        from divineos.cli import cli

        expect = cli.commands["expect"]
        assert "summary" in expect.commands  # type: ignore[attr-defined]


# ─── Underlying API reachable ───────────────────────────────────────


class TestUnderlyingAPI:
    """The CLI is a thin wrapper over core.expectation_tracking. Verify
    the underlying API stays callable and produces the shapes the CLI
    expects."""

    def test_record_expectation_returns_id(self, tmp_path, monkeypatch):
        test_db = tmp_path / "test_ledger.db"
        monkeypatch.setenv("DIVINEOS_DB", str(test_db))

        # Init the DB
        from click.testing import CliRunner

        from divineos.cli import cli

        runner = CliRunner()
        runner.invoke(cli, ["init"])

        from divineos.core.expectation_tracking import record_expectation

        eid = record_expectation(
            claim="this is a test prediction",
            basis="being run by automated tests",
        )
        assert eid.startswith("exp-"), f"expected eid to start with 'exp-', got: {eid!r}"

    def test_record_expectation_empty_claim_returns_empty(self, tmp_path, monkeypatch):
        test_db = tmp_path / "test_ledger.db"
        monkeypatch.setenv("DIVINEOS_DB", str(test_db))

        from divineos.core.expectation_tracking import record_expectation

        # Empty claim should return empty string (caller-facing rejection signal)
        assert record_expectation("", "basis") == ""
        assert record_expectation("   ", "basis") == ""


# ─── End-to-end CLI invocation ──────────────────────────────────────


class TestEndToEnd:
    """Invoke each subcommand via the Click test runner and verify
    expected output. Pins the full wire-up against regression."""

    def test_expect_group_shows_subcommands(self, tmp_path, monkeypatch):
        test_db = tmp_path / "test_ledger.db"
        monkeypatch.setenv("DIVINEOS_DB", str(test_db))

        from divineos.cli import cli

        runner = CliRunner()
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["expect"])
        assert result.exit_code == 0
        # Bare `divineos expect` shows the available subcommands
        assert "predict" in result.output
        assert "close" in result.output

    def test_expect_predict_records_and_returns_id(self, tmp_path, monkeypatch):
        test_db = tmp_path / "test_ledger.db"
        monkeypatch.setenv("DIVINEOS_DB", str(test_db))

        from divineos.cli import cli

        runner = CliRunner()
        runner.invoke(cli, ["init"])
        result = runner.invoke(
            cli,
            [
                "expect",
                "predict",
                "the test will pass",
                "--basis",
                "tests are deterministic",
            ],
        )
        assert result.exit_code == 0, f"output:\n{result.output}"
        assert "Expectation recorded" in result.output
        assert "exp-" in result.output

    def test_expect_predict_empty_claim_rejected(self, tmp_path, monkeypatch):
        test_db = tmp_path / "test_ledger.db"
        monkeypatch.setenv("DIVINEOS_DB", str(test_db))

        from divineos.cli import cli

        runner = CliRunner()
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["expect", "predict", ""])
        # Should not crash; should communicate rejection.
        assert result.exit_code == 0
        assert "empty" in result.output.lower()

    def test_expect_list_shows_open_after_predict(self, tmp_path, monkeypatch):
        test_db = tmp_path / "test_ledger.db"
        monkeypatch.setenv("DIVINEOS_DB", str(test_db))

        from divineos.cli import cli

        runner = CliRunner()
        runner.invoke(cli, ["init"])
        runner.invoke(
            cli,
            [
                "expect",
                "predict",
                "claim alpha",
                "--basis",
                "basis alpha",
            ],
        )
        result = runner.invoke(cli, ["expect", "list"])
        assert result.exit_code == 0
        assert "claim alpha" in result.output

    def test_expect_close_requires_accuracy_flag(self, tmp_path, monkeypatch):
        test_db = tmp_path / "test_ledger.db"
        monkeypatch.setenv("DIVINEOS_DB", str(test_db))

        from divineos.cli import cli

        runner = CliRunner()
        runner.invoke(cli, ["init"])
        # Get an expectation ID first
        result_p = runner.invoke(
            cli,
            ["expect", "predict", "claim", "--basis", "basis"],
        )
        # Extract the eid from output (looks for the "exp-" prefix)
        eid_token = next(
            (tok for tok in result_p.output.split() if tok.startswith("exp-")),
            None,
        )
        assert eid_token is not None

        # Close without --accurate or --inaccurate: should be rejected.
        result_c = runner.invoke(cli, ["expect", "close", eid_token, "what happened"])
        assert "accurate or --inaccurate is required" in result_c.output.lower() or (
            "required" in result_c.output.lower()
        )

    def test_expect_close_then_summary_reflects_record(self, tmp_path, monkeypatch):
        test_db = tmp_path / "test_ledger.db"
        monkeypatch.setenv("DIVINEOS_DB", str(test_db))

        from divineos.cli import cli

        runner = CliRunner()
        runner.invoke(cli, ["init"])

        # Predict
        result_p = runner.invoke(
            cli,
            ["expect", "predict", "claim", "--basis", "basis"],
        )
        eid_token = next(
            (tok for tok in result_p.output.split() if tok.startswith("exp-")),
            None,
        )
        assert eid_token is not None

        # Close as accurate
        result_c = runner.invoke(
            cli,
            ["expect", "close", eid_token, "as predicted", "--accurate"],
        )
        assert result_c.exit_code == 0
        assert "closed: accurate" in result_c.output.lower()

        # Summary should reflect the closed record
        result_s = runner.invoke(cli, ["expect", "summary"])
        assert result_s.exit_code == 0
        assert "Total closed" in result_s.output
