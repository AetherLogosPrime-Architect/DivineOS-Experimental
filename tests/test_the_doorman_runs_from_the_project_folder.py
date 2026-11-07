"""The build-flow doorman always runs its gate from the project folder.

Dad 2026-11-07 (correction #419): my shell once wandered into a folder that was not a checkout, and the
doorman, which ran the gate from the shell's inherited folder, could not look: the `divineos` wrapper found no
marker and exited 2, exit 2 reads as a hold, and the hold covered every command, including the `cd` that would
have fixed it. A trap with no door.

These run the REAL ``work-item-doorman.sh`` with a stand-in ``divineos`` on the path that records the folder it
was called from and exits as told. The script under test is real; only the CLI it calls is replaced, because
the CLI is not what is being tested.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOORMAN = ROOT / ".claude" / "hooks" / "work-item-doorman.sh"


def _bash() -> str:
    for candidate in (
        "C:/Program Files/Git/bin/bash.exe",
        "C:/Program Files/Git/usr/bin/bash.exe",
        "/bin/bash",
    ):
        if Path(candidate).exists():
            return candidate
    found = shutil.which("bash")
    if not found:
        pytest.skip("no bash available to run the doorman")
    return found


def _as_bash_path(path: Path) -> str:
    """C:/x/y as bash on Windows spells it (/c/x/y); other platforms are left alone."""
    text = path.as_posix()
    if len(text) > 1 and text[1] == ":":
        return "/" + text[0].lower() + text[2:]
    return text


def _stand_in_cli(folder: Path, exit_code: int, message: str = "") -> Path:
    """A `divineos` on the path that writes where it was called from, then exits as told."""
    bin_dir = folder / "bin"
    bin_dir.mkdir()
    marker = folder / "called_from.txt"
    script = bin_dir / "divineos"
    script.write_text(
        "#!/usr/bin/env bash\n"
        f'pwd > "{marker.as_posix()}"\n'
        f'[ -n "{message}" ] && echo "{message}"\n'
        f"exit {exit_code}\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return bin_dir


def _run(tmp_path: Path, exit_code: int, message: str = ""):
    bin_dir = _stand_in_cli(tmp_path, exit_code, message)
    wandering = tmp_path / "not_a_checkout"
    wandering.mkdir()
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = ROOT.as_posix()
    # The stand-in must come FIRST on bash's own path, ahead of the real ~/bin/divineos wrapper. Done inside
    # bash, after it has converted the Windows path list, so the two spellings of a path never get mixed.
    shim = _as_bash_path(bin_dir)
    doorman = _as_bash_path(DOORMAN)
    proc = subprocess.run(
        [_bash(), "-c", f'export PATH="{shim}:$PATH"; exec bash "{doorman}"'],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "echo hi"}}),
        capture_output=True,
        text=True,
        cwd=str(wandering),
        env=env,
    )
    called = (tmp_path / "called_from.txt").read_text(encoding="utf-8").strip()
    return proc, called


def _same_folder(reported_by_bash: str) -> bool:
    """Compare the folder bash reports (/c/x) with ROOT (C:/x), whatever the platform spells it."""
    return reported_by_bash.rstrip("/") == _as_bash_path(ROOT).rstrip("/")


def test_the_gate_is_called_from_the_project_folder_not_the_wandering_shell(tmp_path):
    """The case that broke me: the shell stands outside any checkout."""
    proc, called = _run(tmp_path, exit_code=0)
    assert proc.returncode == 0
    assert _same_folder(called), f"gate ran from {called}, not the project folder"
    assert "not_a_checkout" not in called


def test_a_real_hold_from_the_cli_still_holds(tmp_path):
    """The fix must not hide a real answer: the CLI ran inside the project folder and said hold."""
    proc, called = _run(tmp_path, exit_code=2, message="HOLD: no open piece of work")
    assert proc.returncode == 2
    assert "HOLD" in proc.stderr
    assert _same_folder(called)


def test_the_script_actually_changes_folder_before_the_gate():
    """CONTROL: the text of the fix is in the file, so a clean run above cannot be an accident of the stand-in."""
    text = DOORMAN.read_text(encoding="utf-8")
    assert "CLAUDE_PROJECT_DIR" in text
    assert 'cd "$REPO_ROOT"' in text
