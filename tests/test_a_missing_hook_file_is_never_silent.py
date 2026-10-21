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
import re
import subprocess
from pathlib import Path

import pytest

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


HOOK_FILE = re.compile(r"\.claude/hooks/([^\s\"';]+)")


def _hook_commands() -> list[str]:
    return [c for c in _all_commands() if HOOK_FILE.search(c)]


def test_the_scan_sees_every_hook_command_and_the_six_python_ones():
    """Control for the parametrized test below: if the scan found nothing, every case would pass."""
    commands = _hook_commands()
    assert len(commands) >= 70, len(commands)
    assert sum(1 for c in commands if 'python "$f"' in c) >= 6


@pytest.mark.parametrize("command", _hook_commands(), ids=lambda c: HOOK_FILE.search(c).group(1))
def test_every_hook_command_reports_a_missing_file_with_exit_127(command, tmp_path):
    """Aria's hold on #694: the first version ran only the first question_hold command, so five of
    the six could regress to a silent or exit-0 shape and nothing failed. Every command is run here,
    against a project with no hooks, from another folder, and each must say so on stderr."""
    project = tmp_path / "project"
    (project / ".claude" / "hooks").mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    env["CLAUDE_PROJECT_DIR"] = project.as_posix()
    name = HOOK_FILE.search(command).group(1)
    out = subprocess.run(
        [BASH, "-c", command], cwd=elsewhere, env=env, capture_output=True, text=True, timeout=60
    )
    assert out.returncode == 127, (out.returncode, out.stdout, out.stderr)
    assert "NOT RUNNING" in out.stderr and name in out.stderr, out.stderr
    assert out.stdout == "", out.stdout


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
