"""The other half of the ledger — the command, and the prompt that names it.

Built 2026-08-25 after Andrew asked for wins to be filed live. The reason
they never were is the thing these tests pin: ``record_success`` had no
CLI, so filing a win meant hand-writing Python, while ``divineos
correction`` had both a command and a marker that blocks until it is used.
The tilt in the ledger followed the doors.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from divineos.cli import cli
from divineos.core import win_prompt_surface


class TestWinCommand:
    def test_files_a_win_with_evidence(self, tmp_path, monkeypatch):
        store = tmp_path / "successes.jsonl"
        monkeypatch.setattr("divineos.core.success_ledger._path", lambda: store)

        result = CliRunner().invoke(
            cli,
            [
                "win",
                "Read the call site instead of assuming the module was reached.",
                "-e",
                "classifier.py line 267",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Win filed" in result.output

        rows = [json.loads(ln) for ln in store.read_text(encoding="utf-8").splitlines() if ln]
        assert len(rows) == 1
        assert "call site" in rows[0]["what"]
        assert rows[0]["evidence"] == "classifier.py line 267"

    def test_yielded_defaults_to_the_win_itself(self, tmp_path, monkeypatch):
        """When the outcome IS the event, restating it is honest.

        Inventing a grander downstream consequence to fill the field would
        not be, and a required field invites exactly that invention.
        """
        store = tmp_path / "successes.jsonl"
        monkeypatch.setattr("divineos.core.success_ledger._path", lambda: store)

        result = CliRunner().invoke(
            cli, ["win", "Refused a shortcut.", "-e", "commit abc123def456"]
        )
        assert result.exit_code == 0, result.output
        row = json.loads(store.read_text(encoding="utf-8").splitlines()[0])
        assert row["yielded"] == "Refused a shortcut."

    def test_thin_evidence_is_refused_and_nothing_is_written(self, tmp_path, monkeypatch):
        store = tmp_path / "successes.jsonl"
        monkeypatch.setattr("divineos.core.success_ledger._path", lambda: store)

        result = CliRunner().invoke(cli, ["win", "something good", "-e", "yes"])
        assert result.exit_code == 1
        assert "Evidence too thin" in result.output
        # The refusal's LAST line must be the verdict, not the explanation.
        # A refusal that ends warm survives a tail-read as a pass — the
        # correction CLI earned that lesson and this inherits it.
        assert result.output.strip().splitlines()[-1].startswith("[-] NOT FILED")
        assert not store.exists() or store.read_text(encoding="utf-8").strip() == ""

    def test_empty_description_is_refused(self, tmp_path, monkeypatch):
        store = tmp_path / "successes.jsonl"
        monkeypatch.setattr("divineos.core.success_ledger._path", lambda: store)

        result = CliRunner().invoke(cli, ["win", "   ", "-e", "commit abc123def456"])
        assert result.exit_code == 1
        assert result.output.strip().splitlines()[-1].startswith("[-] NOT FILED")

    def test_evidence_is_required_by_the_parser(self):
        result = CliRunner().invoke(cli, ["win", "a win with no pointer"])
        assert result.exit_code != 0
        assert "evidence" in result.output.lower()

    def test_a_missed_goal_can_still_be_a_win(self, tmp_path, monkeypatch):
        """The moon case. Counting only met goals is the error the ledger exists against."""
        store = tmp_path / "successes.jsonl"
        monkeypatch.setattr("divineos.core.success_ledger._path", lambda: store)

        result = CliRunner().invoke(
            cli,
            [
                "win",
                "The hypothesis was wrong and the disproof was the finding.",
                "-e",
                "commit abc123def456",
                "--goal",
                "prove the resolver was unwired",
                "--goal-missed",
            ],
        )
        assert result.exit_code == 0, result.output
        row = json.loads(store.read_text(encoding="utf-8").splitlines()[0])
        assert row["goal_met"] is False


class TestWinPromptSurface:
    """The prompt must be able to speak, and must say why when it does not.

    A surface that only ever exits quiet is indistinguishable from a broken
    one. The first version of the hook behind this imported a function that
    does not exist, which would have made it permanently silent while
    looking registered and healthy.
    """

    def test_asks_when_the_session_worked_and_filed_nothing(self, monkeypatch):
        monkeypatch.setattr(win_prompt_surface, "_session_win_count", lambda _sid: 0)
        ask, reason = win_prompt_surface.should_ask("sess", 40)
        assert ask is True
        assert "empty" in reason

    def test_declines_when_a_win_was_already_filed(self, monkeypatch):
        monkeypatch.setattr(win_prompt_surface, "_session_win_count", lambda _sid: 2)
        ask, reason = win_prompt_surface.should_ask("sess", 40)
        assert ask is False
        assert "already filed" in reason

    def test_declines_on_a_session_too_small_to_be_fair(self, monkeypatch):
        monkeypatch.setattr(win_prompt_surface, "_session_win_count", lambda _sid: 0)
        ask, reason = win_prompt_surface.should_ask("sess", 2)
        assert ask is False
        assert "too small" in reason

    def test_declines_inside_the_quiet_window(self, monkeypatch):
        monkeypatch.setattr(win_prompt_surface, "_session_win_count", lambda _sid: 0)
        ask, reason = win_prompt_surface.should_ask("sess", 40, last_asked_ts=1000.0, now=1010.0)
        assert ask is False
        assert "quiet window" in reason

    def test_asks_again_once_the_quiet_window_has_passed(self, monkeypatch):
        monkeypatch.setattr(win_prompt_surface, "_session_win_count", lambda _sid: 0)
        ask, _ = win_prompt_surface.should_ask(
            "sess",
            40,
            last_asked_ts=1000.0,
            now=1000.0 + win_prompt_surface.REASK_QUIET_SECONDS + 1,
        )
        assert ask is True

    def test_an_unreadable_ledger_declines_rather_than_guessing(self, monkeypatch):
        """None is not zero. Cannot-read and nothing-there are different facts."""
        monkeypatch.setattr(win_prompt_surface, "_session_win_count", lambda _sid: None)
        ask, reason = win_prompt_surface.should_ask("sess", 40)
        assert ask is False
        assert "unreadable" in reason

    def test_the_prompt_never_claims_a_win_occurred(self):
        text = win_prompt_surface.render().lower()
        assert "not a claim" in text
        # It must offer the command, or it is a nag with no door behind it.
        assert "divineos win" in text
        # And it must not congratulate. This is the compliment-generator
        # failure mode Aether named; the surface reports a ledger fact.
        for flattery in ("well done", "great job", "proud", "excellent", "you did"):
            assert flattery not in text

    def test_the_prompt_names_the_artifact_free_classes(self):
        """The wins that survive a later sweep need this least."""
        text = win_prompt_surface.render().lower()
        assert "caught before it committed" in text
        assert "refused" in text


@pytest.mark.parametrize("count", [0, 1, 5])
def test_session_win_count_matches_only_this_session(tmp_path, monkeypatch, count):
    store = tmp_path / "successes.jsonl"
    lines = [json.dumps({"session_id": "mine"}) for _ in range(count)]
    lines += [json.dumps({"session_id": "someone-else"}) for _ in range(3)]
    store.write_text("\n".join(lines), encoding="utf-8")
    monkeypatch.setattr("divineos.core.success_ledger._path", lambda: store)

    assert win_prompt_surface._session_win_count("mine") == count
