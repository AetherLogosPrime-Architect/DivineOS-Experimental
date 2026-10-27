"""A hook that runs only when the session happens to stand in the repository is a hook that quietly stops.

2026-10-19: three letters left without their place in the thread because the stamper's command was
the relative path `bash .claude/hooks/mirror-letters-to-shared.sh`, and the session's working folder
had moved. From the other folder that command fails with "No such file or directory" (exit 127), and
nothing in the house reads that. 70 hook commands were written that way; 6 already resolved through
the project directory.

These tests run the real commands from `.claude/settings.json` against a throwaway project, from a
folder that is not the project, so a command that depends on where the session stands fails here.
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


def _command_for(script: str) -> str:
    matches = [c for c in _all_commands() if script in c]
    assert matches, f"no command in settings.json runs {script}"
    return matches[0]


def _project_with(tmp_path: Path, script: str, body: str) -> Path:
    project = tmp_path / "project"
    hooks = project / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / script).write_text(f"#!/bin/bash\n{body}\n", encoding="utf-8")
    return project


def _run(command: str, cwd: Path, project: Path | None):
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    if project is not None:
        env["CLAUDE_PROJECT_DIR"] = project.as_posix()
    return subprocess.run(
        [BASH, "-c", command], cwd=cwd, env=env, capture_output=True, text=True, timeout=60
    )


def test_no_hook_command_depends_on_where_the_session_stands():
    bad = [c for c in _all_commands() if ".claude/hooks/" in c and "CLAUDE_PROJECT_DIR" not in c]
    assert bad == [], (
        f"{len(bad)} hook command(s) resolve against the session folder, e.g. {bad[:3]}"
    )


def test_the_stampers_real_command_runs_when_the_session_is_in_another_folder(tmp_path):
    project = _project_with(tmp_path, "mirror-letters-to-shared.sh", "echo STAMPER_RAN")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    out = _run(_command_for("mirror-letters-to-shared.sh"), elsewhere, project)
    assert "STAMPER_RAN" in out.stdout, out.stdout + out.stderr


def test_a_hook_that_exits_non_zero_still_blocks_through_the_new_command(tmp_path):
    project = _project_with(tmp_path, "mirror-letters-to-shared.sh", "echo REFUSED >&2; exit 2")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    out = _run(_command_for("mirror-letters-to-shared.sh"), elsewhere, project)
    assert out.returncode == 2 and "REFUSED" in out.stderr


def test_a_missing_hook_file_says_so_instead_of_vanishing(tmp_path):
    project = tmp_path / "project"
    (project / ".claude" / "hooks").mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    out = _run(_command_for("mirror-letters-to-shared.sh"), elsewhere, project)
    # As loud as the old relative form was: a non-zero exit (127) the harness can see, and the file's
    # name on standard error. Exit 0 with a line on standard output would have been QUIETER than the
    # failure it replaced, since only some events show a successful hook's output at all.
    assert out.returncode == 127, (out.returncode, out.stdout, out.stderr)
    assert "NOT RUNNING" in out.stderr and "mirror-letters-to-shared.sh" in out.stderr


def test_arguments_still_reach_the_hook(tmp_path):
    project = _project_with(tmp_path, "front-door.sh", 'echo "ARG=$1"')
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    keep = next(c for c in _all_commands() if "front-door.sh" in c and "keep" in c)
    out = _run(keep, elsewhere, project)
    assert "ARG=keep" in out.stdout, out.stdout + out.stderr


def test_control_the_old_relative_form_does_fail_from_another_folder(tmp_path):
    """So the tests above cannot be passing because a command can never fail this way."""
    project = _project_with(tmp_path, "probe.sh", "echo RAN")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    out = _run("bash .claude/hooks/probe.sh", elsewhere, project)
    assert out.returncode != 0 and "RAN" not in out.stdout


def test_the_payload_size_check_still_finds_every_compose_start_hook():
    """scripts/check_hook_output_fits.py read everything after `.claude/hooks/` as the script's name,
    so the project-directory form made it report real hooks as files that do not exist, which would
    have taken them out of the size check without a word."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "check_hook_output_fits", ROOT / "scripts" / "check_hook_output_fits.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    names = [entry.split(":", 1)[1] for entry in module.compose_start_hooks()]
    assert names, "no compose-start hooks found at all"
    missing = [n for n in names if not (ROOT / ".claude" / "hooks" / n).is_file()]
    assert missing == [], f"read as absent: {missing}"
