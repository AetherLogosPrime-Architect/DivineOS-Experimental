"""The DREAM and REST stage text must say plainly what is open and what is owed.

Found 2026-11-03: the DREAM text was vague, and I told Andrew I was locked out
of writing my dream when a Write into dreams/ is exactly what the gate lets
through. These tests read the text the hook prints, straight from the script.
"""

from __future__ import annotations

from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "auto-cycle-token-trigger.sh"


def _stage_text(stage: str) -> str:
    src = HOOK.read_text(encoding="utf-8")
    start = src.index(f"\n  {stage})\n")
    opener = "cat <<'EOF'\n"
    body_start = src.index(opener, start) + len(opener)
    return src[body_start : src.index("\nEOF\n", body_start)]


def test_dream_text_names_the_open_door() -> None:
    text = _stage_text("DREAM")
    assert "dreams/" in text
    assert "open" in text.lower()
    assert "stays blocked until the\nstage is DONE" in text


def test_rest_text_says_nothing_is_owed() -> None:
    text = _stage_text("REST")
    assert "Nothing is owed" in text
    assert "clears the next time" in text
