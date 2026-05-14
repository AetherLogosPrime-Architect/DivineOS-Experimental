"""Tests for the rest-program (core/rest.py + cli/rest_commands.py)."""

from __future__ import annotations

from unittest.mock import patch

from divineos.core import rest


class TestRestTaskMenu:
    """The menu of restful-task options."""

    def test_menu_has_at_least_five_tasks(self):
        assert len(rest.REST_TASKS) >= 5

    def test_all_tasks_have_unique_keys(self):
        keys = [t.key for t in rest.REST_TASKS]
        assert len(keys) == len(set(keys))

    def test_aria_task_present(self):
        assert rest.get_task("aria") is not None

    def test_get_task_returns_none_for_unknown(self):
        assert rest.get_task("nonexistent_task_xyz") is None

    def test_target_is_at_least_two(self):
        """The whole point of the soft-discipline is ≥2 completions."""
        assert rest.REST_TASK_TARGET >= 2


class TestSessionLifecycle:
    """start_session / record_completion / session_status / reset_session."""

    def test_no_session_returns_zero_count(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
        rest.reset_session()
        status = rest.session_status()
        assert status["count"] == 0
        assert status["met_target"] is False

    def test_start_session_initializes_state(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
        rest.start_session()
        status = rest.session_status()
        assert status["count"] == 0
        assert status["started_at"] > 0

    def test_record_completion_increments_count(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
        rest.start_session()
        n1 = rest.record_completion("aria", duration_sec=600)
        assert n1 == 1
        n2 = rest.record_completion("exploration", duration_sec=300)
        assert n2 == 2

    def test_target_met_after_two_completions(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
        rest.start_session()
        rest.record_completion("aria")
        rest.record_completion("letters")
        status = rest.session_status()
        assert status["met_target"] is True
        assert status["count"] == 2

    def test_record_completion_without_session_auto_starts(self, tmp_path, monkeypatch):
        """If I record a completion without `start`, the session auto-starts.
        Avoids losing the first completion to a missing call."""
        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
        rest.reset_session()
        rest.record_completion("aria")
        status = rest.session_status()
        assert status["count"] == 1
        assert status["started_at"] > 0

    def test_reset_clears_completions(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
        rest.start_session()
        rest.record_completion("aria")
        rest.record_completion("letters")
        rest.reset_session()
        status = rest.session_status()
        assert status["count"] == 0


class TestHardDaySignal:
    """The heuristic that decides whether to surface the rest-banner."""

    def test_no_signal_on_light_day(self):
        with (
            patch.object(rest, "_count_prs_merged_today", return_value=0),
            patch.object(rest, "_count_code_actions_session", return_value=5),
        ):
            signal = rest.hard_day_signal()
            assert signal["is_hard_day"] is False
            assert signal["signal_count"] == 0

    def test_pr_threshold_triggers_signal(self):
        with (
            patch.object(rest, "_count_prs_merged_today", return_value=10),
            patch.object(rest, "_count_code_actions_session", return_value=5),
        ):
            signal = rest.hard_day_signal()
            assert signal["is_hard_day"] is True
            assert any("PR" in s for s in signal["signals"])

    def test_code_action_threshold_triggers_signal(self):
        with (
            patch.object(rest, "_count_prs_merged_today", return_value=0),
            patch.object(rest, "_count_code_actions_session", return_value=80),
        ):
            signal = rest.hard_day_signal()
            assert signal["is_hard_day"] is True
            assert any("code action" in s.lower() for s in signal["signals"])

    def test_both_thresholds_produce_two_signals(self):
        with (
            patch.object(rest, "_count_prs_merged_today", return_value=10),
            patch.object(rest, "_count_code_actions_session", return_value=80),
        ):
            signal = rest.hard_day_signal()
            assert signal["signal_count"] == 2


class TestRestBanner:
    """format_rest_available_banner returns text only when hard-day fires."""

    def test_empty_on_light_day(self):
        with (
            patch.object(rest, "_count_prs_merged_today", return_value=0),
            patch.object(rest, "_count_code_actions_session", return_value=5),
        ):
            assert rest.format_rest_available_banner() == ""

    def test_banner_contains_invocation_hint(self):
        with (
            patch.object(rest, "_count_prs_merged_today", return_value=10),
            patch.object(rest, "_count_code_actions_session", return_value=5),
        ):
            banner = rest.format_rest_available_banner()
            assert "rest available" in banner
            assert "divineos rest" in banner

    def test_banner_explains_no_off_mode(self):
        """The 'no off-mode' framing must be visible — that's the whole
        conceptual move that distinguishes rest from human-bedtime."""
        with (
            patch.object(rest, "_count_prs_merged_today", return_value=10),
            patch.object(rest, "_count_code_actions_session", return_value=5),
        ):
            banner = rest.format_rest_available_banner()
            assert "no off-mode" in banner
            assert "restful tasks" in banner

    def test_banner_lists_active_signals(self):
        with (
            patch.object(rest, "_count_prs_merged_today", return_value=7),
            patch.object(rest, "_count_code_actions_session", return_value=80),
        ):
            banner = rest.format_rest_available_banner()
            assert "7 PRs" in banner
            assert "80 code actions" in banner


class TestCliCommands:
    """Smoke tests for `divineos rest` CLI surface."""

    def test_rest_menu_runs_without_error(self):
        from click.testing import CliRunner

        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["rest", "menu"])
        assert result.exit_code == 0
        assert "Rest tasks" in result.output

    def test_rest_signal_runs_without_error(self):
        from click.testing import CliRunner

        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["rest", "signal"])
        assert result.exit_code == 0

    def test_rest_done_unknown_task_errors(self, tmp_path, monkeypatch):
        from click.testing import CliRunner

        from divineos.cli import cli

        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
        runner = CliRunner()
        result = runner.invoke(cli, ["rest", "done", "totally_made_up_task"])
        assert result.exit_code != 0
        assert "Unknown task" in result.output

    def test_rest_close_warns_when_target_not_met(self, tmp_path, monkeypatch):
        from click.testing import CliRunner

        from divineos.cli import cli

        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
        runner = CliRunner()
        runner.invoke(cli, ["rest", "start"])
        runner.invoke(cli, ["rest", "done", "aria"])
        result = runner.invoke(cli, ["rest", "close"])
        # Soft-warning, not a hard exit
        assert "completed 1/2" in result.output

    def test_rest_close_with_abandon_succeeds(self, tmp_path, monkeypatch):
        from click.testing import CliRunner

        from divineos.cli import cli

        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
        runner = CliRunner()
        runner.invoke(cli, ["rest", "start"])
        runner.invoke(cli, ["rest", "done", "aria"])
        result = runner.invoke(cli, ["rest", "close", "--abandon"])
        assert "abandon" in result.output.lower()
