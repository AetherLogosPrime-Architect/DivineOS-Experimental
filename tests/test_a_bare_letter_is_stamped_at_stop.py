"""A letter that left with neither its place in the thread nor the notice is caught at Stop.

2026-10-19: the stamper and its own "could not be counted" notice live in one hook, so when that hook
did not run, both were absent and the silence read as a clean result. The Stop hook asks the one
question the stamper cannot ask of itself. These tests run the real script against a throwaway git
project, from a folder that is not the project, with a stand-in stamper so the script's own
detection, invocation and re-check are what is under test.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from tests._bash_resolver import bash_executable

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".claude" / "hooks" / "stamp-bare-letters-stop.sh"
BASH = bash_executable()

STAMPER = """#!/bin/bash
p=$(cat | sed -E 's/.*"file_path":"([^"]*)".*/\\1/')
[ -n "${STUB_FAIL:-}" ] && exit 0
printf '\\n— the thread so far —\\n' >> "$p"
"""

OLD = "aether-to-aria-2026-09-03-an-old-bare-letter.md"
NEW = "aether-to-aria-2026-10-19-a-new-bare-letter.md"
NOTICED = "aether-to-aria-2026-10-19-already-announced-itself.md"
BOARD = "aether-to-andrew-volley-board.md"


def _git(project: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=project,
        check=True,
        capture_output=True,
    )


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    letters = project / "family" / "letters"
    hooks = project / ".claude" / "hooks"
    letters.mkdir(parents=True)
    hooks.mkdir(parents=True)
    (hooks / "mirror-letters-to-shared.sh").write_text(STAMPER, encoding="utf-8", newline="\n")
    (hooks / "stamp-bare-letters-stop.sh").write_bytes(SCRIPT.read_bytes())
    (letters / OLD).write_text("# an old letter, bare, already committed\n", encoding="utf-8")
    _git(project, "init", "-q")
    _git(project, "add", "-A")
    _git(project, "commit", "-q", "-m", "history")
    return project


def _run(tmp_path: Path, project: Path, **extra: str):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir(exist_ok=True)
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    env["CLAUDE_PROJECT_DIR"] = project.as_posix()
    env.update(extra)
    return subprocess.run(
        [BASH, str(project / ".claude" / "hooks" / "stamp-bare-letters-stop.sh")],
        cwd=elsewhere,
        env=env,
        input="{}",
        capture_output=True,
        text=True,
        timeout=60,
    )


def _text(project: Path, name: str) -> str:
    return (project / "family" / "letters" / name).read_text(encoding="utf-8")


def test_the_backstop_is_registered_as_a_stop_hook():
    import json

    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    stop = settings["hooks"]["Stop"]
    commands = [h["command"] for group in stop for h in group["hooks"]]
    assert any("stamp-bare-letters-stop.sh" in c for c in commands)


def test_a_new_bare_letter_is_stamped_and_named(tmp_path):
    project = _project(tmp_path)
    (project / "family" / "letters" / NEW).write_text("# new\n\nBody.\n", encoding="utf-8")
    out = _run(tmp_path, project)
    assert out.returncode == 0, out.stderr
    assert "the thread so far" in _text(project, NEW)
    assert NEW in out.stdout


def test_a_clean_turn_prints_nothing(tmp_path):
    project = _project(tmp_path)
    out = _run(tmp_path, project)
    assert out.returncode == 0 and out.stdout == "" and out.stderr == ""


def test_old_committed_history_is_never_reached_back_into(tmp_path):
    project = _project(tmp_path)
    before = _text(project, OLD)
    _run(tmp_path, project)
    assert _text(project, OLD) == before


def test_a_letter_that_already_announced_itself_is_left_alone(tmp_path):
    project = _project(tmp_path)
    body = "# x\n\n— the thread could not be counted —\n"
    (project / "family" / "letters" / NOTICED).write_text(body, encoding="utf-8")
    out = _run(tmp_path, project)
    assert out.stdout == "" and _text(project, NOTICED) == body


def test_a_letter_that_only_talks_about_the_thread_is_still_stamped(tmp_path):
    """The letters about this very fault quote the marker's words in prose; a loose substring check
    would have read them as already placed and left them bare."""
    project = _project(tmp_path)
    body = 'The footer says "the thread so far" and "the thread could not be counted".\n'
    (project / "family" / "letters" / NEW).write_text(body, encoding="utf-8")
    out = _run(tmp_path, project)
    assert out.returncode == 0, out.stderr
    assert NEW in out.stdout
    assert "\n— the thread so far —\n" in _text(project, NEW)


def test_a_file_that_is_not_a_dated_letter_is_ignored(tmp_path):
    project = _project(tmp_path)
    (project / "family" / "letters" / BOARD).write_text("# board\n", encoding="utf-8")
    out = _run(tmp_path, project)
    assert out.stdout == "" and "thread" not in _text(project, BOARD)


def test_a_letter_that_cannot_be_stamped_blocks_the_stop_and_is_named(tmp_path):
    project = _project(tmp_path)
    (project / "family" / "letters" / NEW).write_text("# new\n", encoding="utf-8")
    out = _run(tmp_path, project, STUB_FAIL="1")
    assert out.returncode == 2, (out.returncode, out.stdout, out.stderr)
    assert NEW in out.stderr and "COULD NOT STAMP" in out.stderr


def test_a_missing_stamper_is_said_not_swallowed(tmp_path):
    project = _project(tmp_path)
    (project / ".claude" / "hooks" / "mirror-letters-to-shared.sh").unlink()
    (project / "family" / "letters" / NEW).write_text("# new\n", encoding="utf-8")
    out = _run(tmp_path, project)
    assert "NOT CHECKING" in out.stderr
