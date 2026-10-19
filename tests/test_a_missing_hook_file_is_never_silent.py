"""A registered hook whose file is gone must say so, whichever interpreter it names.

Aletheia's follow-up on #693 (2026-10-19): six commands in `.claude/settings.json` still had the form
`[ -f "$f" ] && python "$f"`, which does nothing, and says nothing, if the file is missing. That is the
very failure #693 cured for the `bash` commands, and the six include Dad's table and the question hold.
Each now reports `NOT RUNNING, file missing` on standard error and exits 127, as loud as the relative
path it once was.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from tests._bash_resolver import bash_executable

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ROOT / ".claude" / "settings.json"
BASH = bash_executable()
SILENT = '[ -f "$f" ] &&'


def _commands(node):
    if isinstance(node, dict):
        if isinstance(node.get("command"), str):
            yield node["command"]
        for value in node.values():
            yield from _commands(value)
    elif isinstance(node, list):
        for value in node:
            yield from _commands(value)


def _all_commands() -> list[str]:
    return list(_commands(json.loads(SETTINGS.read_text(encoding="utf-8"))))


def test_no_hook_command_does_nothing_and_says_nothing_when_its_file_is_gone():
    silent = [c for c in _all_commands() if SILENT in c]
    assert silent == [], (
        f"{len(silent)} command(s) are silent if their file is missing: {silent[:2]}"
    )


def test_the_question_holds_real_command_reports_a_missing_file_with_exit_127(tmp_path):
    project = tmp_path / "project"
    (project / ".claude" / "hooks").mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    command = next(c for c in _all_commands() if "question_hold.py" in c)
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    env["CLAUDE_PROJECT_DIR"] = project.as_posix()
    out = subprocess.run(
        [BASH, "-c", command], cwd=elsewhere, env=env, capture_output=True, text=True, timeout=60
    )
    assert out.returncode == 127, (out.returncode, out.stdout, out.stderr)
    assert "NOT RUNNING" in out.stderr and "question_hold.py" in out.stderr


def test_a_present_python_hook_still_runs_through_the_new_form(tmp_path):
    """Control, so the test above cannot pass because the command always fails."""
    project = tmp_path / "project"
    hooks = project / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "question_hold.py").write_text("print('QUESTION_HOLD_RAN')\n", encoding="utf-8")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    command = next(c for c in _all_commands() if "question_hold.py" in c)
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    env["CLAUDE_PROJECT_DIR"] = project.as_posix()
    out = subprocess.run(
        [BASH, "-c", command], cwd=elsewhere, env=env, capture_output=True, text=True, timeout=60
    )
    assert "QUESTION_HOLD_RAN" in out.stdout, (out.stdout, out.stderr)
