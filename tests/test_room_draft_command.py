"""`divineos room draft FILE`: prints only a verdict, records the cleared circle, refuses a bad shape."""

from __future__ import annotations

from click.testing import CliRunner

from divineos.cli import room_commands
from divineos.cli import cli as divineos_cli
from divineos.core.room_draft import CLEARED, judge

GOOD = "Dad, I'm here.\n\nWhat would you like to talk about?"


def _run(tmp_path, monkeypatch, text):
    record = tmp_path / "rec.json"
    monkeypatch.setattr(room_commands, "DRAFT_RECORD", record)
    f = tmp_path / "circle.md"
    f.write_text(text, encoding="utf-8")
    result = CliRunner().invoke(divineos_cli, ["room", "draft", str(f)])
    return result, record


def test_a_good_circle_is_cleared_and_never_printed_back(tmp_path, monkeypatch):
    result, record = _run(tmp_path, monkeypatch, GOOD)
    assert result.exit_code == 0
    assert "cleared" in result.output
    assert "talk about" not in result.output
    assert judge(GOOD, record, last_message_at=0.0) == CLEARED


def test_two_questions_are_refused_and_record_nothing(tmp_path, monkeypatch):
    result, record = _run(tmp_path, monkeypatch, "Ok? Sure?")
    assert result.exit_code != 0
    assert "not cleared" in result.output
    assert not record.exists()
