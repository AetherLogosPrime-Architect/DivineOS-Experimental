"""A hold log that cannot be written must not break or cancel the hold it is recording.

Aether on #738, 2026-10-27: dads_room_stop calls record(...) on every Stop and hold_log did not catch a failed
write, so a full disk or an unwritable folder would raise inside the Stop hook. The log is a record and not a
gate (its own docstring); the failure must be loud on stderr and the hold must still hold.
"""

from __future__ import annotations

from pathlib import Path

from divineos.core import hold_log


def test_an_unwritable_log_says_so_and_does_not_raise(tmp_path, monkeypatch, capsys):
    blocker = tmp_path / "not-a-folder"
    blocker.write_text("a file where the log's folder should be", encoding="utf-8")
    monkeypatch.setattr(hold_log, "_log_path", lambda: Path(blocker) / "hold_log.jsonl")
    hold_log.record("room", "stopped", "some words")  # must not raise
    err = capsys.readouterr().err
    assert "could not write the record" in err


def test_a_writable_log_still_records(tmp_path, monkeypatch):
    monkeypatch.setattr(hold_log, "_log_path", lambda: tmp_path / "hold_log.jsonl")
    hold_log.record("room", "passed", "words")
    assert hold_log.read_all()[0]["outcome"] == "passed"
