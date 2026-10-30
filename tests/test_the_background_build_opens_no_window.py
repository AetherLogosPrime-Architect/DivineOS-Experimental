"""The index build runs where Dad cannot see it.

A parent with no console of its own makes the venv launcher's child open a fresh visible one on
every message (Dad 2026-10-29). The no-window flag gives a hidden console the children inherit."""

from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src/divineos/core/his_words_bundle.py"


def test_the_build_launch_asks_for_no_window_and_not_detached():
    text = SOURCE.read_text(encoding="utf-8")
    assert "NO_WINDOW" in text
    assert "DETACHED" not in text
