"""The reply-side words door: it must hold its tongue where it should, and a
failure of it must be heard.

The hook (.claude/hooks/his_words_stop.py) searches my reply against his own past
words before the reply reaches him. Its search is covered in test_his_words_door
(owed_in_reply). What is pinned here is the edge: when it must say nothing, and
that a break is not silent -- it used to write a note nothing read, so a dead hook
looked like a quiet one (walk-14f1a5a2567e).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".claude" / "hooks" / "his_words_stop.py"
SURFACE = ROOT / ".claude" / "hooks" / "his-words-door-surface.sh"


def _run_hook(payload: dict, mark: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, HIS_WORDS_STOP_MARK=str(mark), PYTHONIOENCODING="utf-8")
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )


def test_the_reply_side_door_stays_plugged_in():
    """It sat unregistered for nine days and nothing noticed. Read the REAL
    settings.json: the Stop list must hold his-words-stop.sh, with a timeout that
    survives the model load (about 4 seconds; the old 10 would risk it under load)."""
    stop_groups = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))[
        "hooks"
    ]["Stop"]
    commands = [h for g in stop_groups for h in g["hooks"]]
    assert commands, (
        "read an empty Stop list: the control must exist before the finding means anything"
    )
    ours = [h for h in commands if "his-words-stop.sh" in h["command"]]
    assert len(ours) == 1, f"his-words-stop.sh must be registered exactly once, found {len(ours)}"
    assert ours[0]["timeout"] >= 30
    assert (ROOT / ".claude" / "hooks" / "his-words-stop.sh").exists()


def test_the_hold_names_its_way_out():
    """The one block this hook can make must say how to clear it, and the wording
    is what the remedy meta-test leans on when it declares the wrapper non-gating.
    Read the real function, with a real passage, so a rewording that drops the
    exit fails here rather than silently stranding me at a hold."""
    from divineos.core.his_words_door import Hit, Passage, hold_reason

    passage = Passage(
        text="check what is eating up all the memory",
        day="2026-10-05",
        ts="2026-10-05T12:00:00Z",
    )
    text = hold_reason(Hit(passage=passage, score=0.7))
    assert "check what is eating up all the memory" in text  # control: the fixture reached the text
    assert "Quote him, then say what you have to say about it" in text
    assert "Append only that; do not re-post the reply" in text


def test_a_hold_already_in_progress_is_never_held_again(tmp_path):
    out = _run_hook({"stop_hook_active": True, "transcript_path": "unused"}, tmp_path / "m.txt")
    assert out.returncode == 0
    assert out.stdout.strip() == ""


def test_no_transcript_means_nothing_to_search(tmp_path):
    out = _run_hook({}, tmp_path / "m.txt")
    assert out.returncode == 0
    assert out.stdout.strip() == ""
    assert not (tmp_path / "m.txt").exists()


def test_a_break_exits_zero_and_leaves_a_note(tmp_path):
    """A missing transcript file makes the hook raise; it must not take the reply
    down with it, and it must say so somewhere a reader can find."""
    mark = tmp_path / "broke.txt"
    out = _run_hook({"transcript_path": str(tmp_path / "does_not_exist.jsonl")}, mark)
    assert out.returncode == 0
    assert "his_words_stop broke" in mark.read_text(encoding="utf-8")


# Bare "bash" on this box is the WSL relay, which exits without running the hook:
# that is could-not-look, and it must never be read as "the door said nothing".
def _bash() -> str | None:
    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        "/usr/bin/bash",
        shutil.which("bash") or "",
    ):
        if candidate and Path(candidate).exists() and "System32" not in candidate:
            return candidate
    return None


@pytest.mark.skipif(_bash() is None, reason="needs a real bash, not the WSL relay")
def test_the_door_surface_says_the_break_once(tmp_path):
    """Both sides of the file-exists boundary: with a note it speaks and keeps a
    .seen copy; the next run finds nothing and says nothing."""
    mark = tmp_path / "broke.txt"
    mark.write_text("his_words_stop broke: TestError: on purpose\n", encoding="utf-8")
    env = dict(os.environ, HIS_WORDS_STOP_MARK=str(mark), PYTHONIOENCODING="utf-8")

    def run() -> str:
        return subprocess.run(
            [_bash(), str(SURFACE)],
            input='{"prompt":"hello"}',
            capture_output=True,
            text=True,
            env=env,
            cwd=ROOT,
            timeout=300,
        ).stdout

    first = run()
    assert "THE REPLY-SIDE WORDS DOOR BROKE LAST TURN" in first
    assert "TestError: on purpose" in first
    assert (tmp_path / "broke.txt.seen").exists()
    assert not mark.exists()

    assert "BROKE LAST TURN" not in run()
