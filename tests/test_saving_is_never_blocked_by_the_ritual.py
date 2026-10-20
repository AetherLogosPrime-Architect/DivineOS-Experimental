"""The ritual's hard stop never blocks a write into my memory folder.

Dad, 2026-10-19: "saving should never be a blocked action at any point whatsoever."
The stop held the in-flight note hostage at the moment it was meant to be written.
The pair is the point: a memory write passes, and an ordinary write at the same
stage is still refused, so the first cannot pass merely because nothing blocks.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / ".claude" / "hooks" / "auto-cycle-token-trigger.sh"


def _bash() -> str | None:
    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        "/usr/bin/bash",
        shutil.which("bash") or "",
    ):
        if candidate and Path(candidate).exists() and "System32" not in candidate:
            return candidate
    return None


BASH = _bash()
pytestmark = pytest.mark.skipif(
    not HOOK.exists() or BASH is None,
    reason="hook or a POSIX bash absent here -- could-not-look, which is not a pass",
)

PAST_THE_WALL = 990_000


def _write_attempt(tmp_path: Path, target: str, *, config_var: bool = True) -> int:
    transcript = tmp_path / "session.jsonl"
    row = {"type": "assistant", "message": {"usage": {"input_tokens": PAST_THE_WALL}}}
    transcript.write_text(json.dumps(row) + "\n", encoding="utf-8")
    env = {
        **os.environ,
        "AUTO_CYCLE_STATE_DIR": str(tmp_path),
        "AUTO_CYCLE_HOOK_EVENT": "PreToolUse",
        "DIVINEOS_PYTHON": sys.executable,
        "CLAUDE_CONFIG_DIR": str(_config_dir(tmp_path)),
    }
    if not config_var:
        # The real-life case: no CLAUDE_CONFIG_DIR, so the hook must default to <home>/.claude.
        env.pop("CLAUDE_CONFIG_DIR")
        env["HOME"] = env["USERPROFILE"] = str(tmp_path / "home")
    env.pop("AUTO_CYCLE_RITUAL_UNBLOCK", None)
    payload = json.dumps(
        {
            "transcript_path": str(transcript),
            "tool_name": "Write",
            "tool_input": {"file_path": target, "content": "x"},
        }
    )
    done = subprocess.run(
        [BASH, str(HOOK)],
        input=payload.encode(),
        capture_output=True,
        env=env,
        cwd=REPO,
        timeout=120,
    )
    return done.returncode


def _config_dir(tmp_path: Path) -> Path:
    """Stands in for the harness's .claude folder; the hook reads it from CLAUDE_CONFIG_DIR."""
    return tmp_path / "home" / ".claude"


def _memory(tmp_path: Path, name: str = "a.md") -> str:
    return (_config_dir(tmp_path) / "projects" / "C--proj" / "memory" / name).as_posix()


def test_an_ordinary_write_is_still_stopped_at_the_wall(tmp_path):
    assert _write_attempt(tmp_path, "C:/work/src/some_module.py") == 2


def test_a_path_that_climbs_out_of_the_memory_folder_is_still_stopped(tmp_path):
    target = _memory(tmp_path, "../../../../../work/src/a.py")
    assert _write_attempt(tmp_path, target) == 2


def test_a_folder_merely_named_memory_elsewhere_is_still_stopped(tmp_path):
    inside = _config_dir(tmp_path) / "projects" / "C--proj" / "src" / "memory" / "a.py"
    assert _write_attempt(tmp_path, inside.as_posix()) == 2
    assert _write_attempt(tmp_path, "C:/work/memory/a.py") == 2


def test_the_pattern_under_some_other_tree_is_still_stopped(tmp_path):
    """Aletheia's tightening: .claude/projects/x/memory/ anywhere in a path used to pass."""
    lookalike = tmp_path / "repo" / "src" / ".claude" / "projects" / "x" / "memory" / "evil.py"
    assert _write_attempt(tmp_path, lookalike.as_posix()) == 2


def test_the_memory_folder_itself_and_a_bare_projects_file_are_still_stopped(tmp_path):
    base = _config_dir(tmp_path) / "projects"
    assert _write_attempt(tmp_path, (base / "C--proj" / "memory").as_posix()) == 2
    assert _write_attempt(tmp_path, (base / "settings.json").as_posix()) == 2


def test_a_memory_folder_that_is_a_link_pointing_outside_is_still_stopped(tmp_path):
    """Aria's gap on #695: realpath is what stops this, and nothing pinned it.

    A junction makes `memory` resolve outside the config tree. Skipped cleanly when a junction
    cannot be made here, so it reads as could-not-look and not as a pass.
    """
    if os.name != "nt":
        pytest.skip("needs a Windows junction; could-not-look, which is not a pass")
    project = _config_dir(tmp_path) / "projects" / "C--proj"
    project.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    made = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(project / "memory"), str(tmp_path / "outside")],
        capture_output=True,
        text=True,
    )
    if made.returncode != 0:
        pytest.skip(f"a junction could not be made here ({made.stderr.strip()}); could-not-look")
    assert (project / "memory").resolve() == outside.resolve()  # control: the link really leaves
    assert _write_attempt(tmp_path, (project / "memory" / "evil.py").as_posix()) == 2


def test_a_memory_folder_that_is_a_symlink_pointing_outside_is_still_stopped(tmp_path):
    """Aletheia's twin: the junction test above only runs on Windows, so the CI runners (Linux)
    would pass a weakened realpath. A symlink makes the same trap on every platform; skipped only
    where one cannot be made, so it reads as could-not-look and not as a pass.
    """
    project = _config_dir(tmp_path) / "projects" / "C--proj"
    project.mkdir(parents=True)
    (tmp_path / "outside").mkdir()
    try:
        os.symlink(tmp_path / "outside", project / "memory", target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"a symlink could not be made here ({exc}); could-not-look")
    assert (project / "memory").resolve() == (tmp_path / "outside").resolve()  # control
    assert _write_attempt(tmp_path, (project / "memory" / "evil.py").as_posix()) == 2


def test_the_default_home_folder_is_used_when_the_config_variable_is_unset(tmp_path):
    assert _write_attempt(tmp_path, _memory(tmp_path), config_var=False) == 0
    assert _write_attempt(tmp_path, "C:/work/src/a.py", config_var=False) == 2


def test_a_write_into_the_memory_folder_always_passes(tmp_path):
    assert _write_attempt(tmp_path, _memory(tmp_path, "project_in_flight.md")) == 0
