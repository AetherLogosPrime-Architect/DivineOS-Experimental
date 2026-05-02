"""Tests for anti-substitution labels on cognitive-named CLI commands.

Falsifiability:
  - emit_label prints the configured label for known keys.
  - emit_label is silent for unknown keys (never raises).
  - Council default is lens mode (prints methodologies, not synthesis label).
  - Council --as-code emits the AS-CODE warning.
  - Cognitive commands emit their labels on invocation.

Labels are a teaching surface; these tests lock in their presence so
refactors don't silently drop the distinction-naming.
"""

from __future__ import annotations

import os

import pytest
from click.testing import CliRunner

from divineos.cli._anti_substitution import LABELS, emit_label


class TestEmitLabel:
    def test_known_keys_all_have_labels(self) -> None:
        expected = {
            "ask",
            "recall",
            "decide",
            "learn",
            "feel",
            "compass-observe",
            "claim",
            "opinion",
        }
        assert expected <= set(LABELS), f"missing labels: {expected - set(LABELS)}"

    def test_unknown_key_is_silent(self, capsys) -> None:
        # Must not raise; must not print when unmapped.
        emit_label("nonexistent")
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_known_key_prints_label_text(self, capsys) -> None:
        emit_label("ask")
        captured = capsys.readouterr()
        assert "[ask]" in captured.out
        assert LABELS["ask"].split()[0] in captured.out


@pytest.mark.skip(reason="mansion / council commands stripped in Lite")
class TestCouncilModeSplit:
    """Council/mansion stripped in Lite. Full DivineOS retains."""

    def test_default_is_lens_mode(self) -> None:
        pass

    def test_as_code_emits_warning(self) -> None:
        pass


class TestCognitiveCommandsEmitLabel:
    """Each labeled cognitive command prints its label when run."""

    @pytest.fixture(autouse=True)
    def _fresh_db(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        from divineos.core.knowledge import init_knowledge_table
        from divineos.core.ledger import init_db
        from divineos.core.moral_compass import init_compass

        init_db()
        init_knowledge_table()
        init_compass()
        try:
            yield
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_ask_emits_label(self) -> None:
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["ask", "anything"])
        # The command may or may not find hits, but the label must print.
        assert "[ask]" in result.output

    def test_recall_emits_label(self) -> None:
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["recall"])
        assert "[recall]" in result.output

    def test_decide_emits_label(self) -> None:
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["decide", "a test decision", "--why", "testing the label"])
        assert "[decide]" in result.output

    def test_learn_emits_label(self) -> None:
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["learn", "a test lesson for the label gate"])
        assert "[learn]" in result.output

    def test_feel_emits_label(self) -> None:
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["feel", "-v", "0.3", "-a", "0.2", "-d", "testing"])
        assert "[feel]" in result.output

    def test_compass_observe_emits_label(self) -> None:
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "compass-ops",
                "observe",
                "humility",
                "-p",
                "0.0",
                "-e",
                "test label invocation",
            ],
        )
        assert "[compass-observe]" in result.output

    def test_claim_emits_label(self) -> None:
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["claim", "a test claim for the label gate"])
        assert "[claim]" in result.output

    @pytest.mark.skip(reason="opinion command stripped in Lite (insight_commands)")
    def test_opinion_emits_label(self) -> None:
        pass
