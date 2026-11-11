"""The letter doorbell itself, run against a temporary home.

Its listing moved from ``ls | grep`` (refused by shellcheck, which failed every
precommit on main) to one glob function used for both "announced" and "here
now" (2026-10-01). These run the real script, so a listing that changed what
counts as new, or let an unreadable folder pass as an empty one, shows up here.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BELL = ROOT / "scripts" / "letter_doorbell.sh"


def _git_bash() -> str | None:
    """Git's bash first: plain `bash` on a Windows PATH may be WSL, which cannot read C:/ paths."""
    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
    ):
        if Path(candidate).exists():
            return candidate
    return shutil.which("bash")


BASH = _git_bash()

pytestmark = pytest.mark.skipif(BASH is None, reason="no bash to run the bell with")


def _ring(home: Path, seconds: float = 6, bell: Path = BELL) -> tuple[str, bool]:
    """The bell's output, and whether it was still running when time ran out.

    The bell leaves silently when its starter is gone (kill -0 $PPID). Started
    straight from Python on Windows, its parent is not a pid bash can see, so it
    left at once and every "did not ring" passed vacuously. A bash parent that
    outlives it (the trailing ':' stops bash exec-ing the child) is the starter
    the harness gives it for real.
    """
    # These run the bell with its output piped to Python, which is not a watched background
    # task, so they declare that on purpose. What the bell does when it is NOT declared is
    # pinned in test_the_doorbell_refuses_to_arm_unwatched.py.
    env = {**os.environ, "HOME": str(home), "DOORBELL_ALLOW_UNTRACKED": "1"}
    p = subprocess.Popen(
        [BASH, "-c", f'bash "{bell.as_posix()}" aether; :'],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    # Read on a thread so what the bell said before time ran out is kept: killing only the
    # starter leaves the sleeping bell holding the pipe open, and reading to the end then
    # never returns (seen with Git's bash on Windows), so the whole tree is killed.
    chunks: list[str] = []

    def _drain() -> None:
        assert p.stdout is not None
        for line in p.stdout:
            chunks.append(line)

    reader = threading.Thread(target=_drain, daemon=True)
    reader.start()
    try:
        p.wait(timeout=seconds)
        reader.join(timeout=10)
        return "".join(chunks), False
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True, check=False
            )
        else:
            p.kill()
        reader.join(timeout=10)
        return "".join(chunks), True


def test_a_letter_not_yet_announced_rings(tmp_path):
    letters = tmp_path / ".divineos-shared" / "letters"
    letters.mkdir(parents=True)
    (letters / "aria-to-aether-2026-10-01-old.md").write_text("x", encoding="utf-8")
    (letters / "aria-to-aether-2026-10-01-new.md").write_text("x", encoding="utf-8")
    (letters / "aether-to-aria-2026-10-01-mine.md").write_text("x", encoding="utf-8")
    # Bytes, not text: Python's text mode writes \r\n on Windows, which the bell
    # (which writes this file itself, with \n) would read as a different name.
    (tmp_path / ".divineos-shared" / ".aether_doorbell_announced").write_bytes(
        b"aria-to-aether-2026-10-01-old.md\n"
    )
    out, _ = _ring(tmp_path)
    assert "LETTER ARRIVED" in out, out
    rang = out.split("LETTER ARRIVED", 1)[1]
    assert "aria-to-aether-2026-10-01-new.md" in rang
    assert "-old.md" not in rang
    assert "aether-to-aria" not in out  # a letter FROM me is not one TO me


def test_an_empty_folder_does_not_ring_on_the_bare_pattern(tmp_path):
    (tmp_path / ".divineos-shared" / "letters").mkdir(parents=True)
    out, still_listening = _ring(tmp_path, seconds=4)
    assert "doorbell armed" in out, out  # the control: it really started
    assert still_listening, out  # and it was still watching when time ran out
    assert "LETTER ARRIVED" not in out
    assert "*" not in out


def test_a_folder_it_cannot_read_faults_instead_of_staying_quiet(tmp_path):
    (tmp_path / ".divineos-shared").mkdir()
    out, _ = _ring(tmp_path)
    assert "DOORBELL FAULT" in out, out


def test_the_bell_rings_from_a_folder_with_a_space_in_its_name(tmp_path):
    """A checkout at a path like '/tmp/a b/repo' must not break the bell's start.

    The bell is copied under a folder whose name has a space and rung from
    there. The line that moves into the repo (`cd "$REPO"`, REPO resolved from
    the script's own location) fails with "cd: too many arguments" when its
    quotes are removed, not "No such file or directory", so the check is on the
    `cd:` complaint, plus a stub baton module proving the move really landed in
    the spaced folder.
    """
    repo = tmp_path / "a b"
    spaced = repo / "scripts"
    shutil.copytree(BELL.parent, spaced)
    stub = repo / "divineos" / "core"
    stub.mkdir(parents=True)
    (repo / "divineos" / "__init__.py").write_text("", encoding="utf-8")
    (stub / "__init__.py").write_text("", encoding="utf-8")
    (stub / "baton.py").write_text(
        "import os, sys\n"
        "print('STUB-BATON-RAN-IN ' + os.path.basename(os.getcwd()))\n"
        "print('STUB-BATON-ARGS ' + '|'.join(sys.argv[1:]))\n",
        encoding="utf-8",
    )
    letters = tmp_path / "home" / ".divineos-shared" / "letters"
    letters.mkdir(parents=True)
    (letters / "aria-to-aether-2026-10-01-old.md").write_text("x", encoding="utf-8")
    (letters / "aria-to-aether-2026-10-01-new.md").write_text("x", encoding="utf-8")
    (tmp_path / "home" / ".divineos-shared" / ".aether_doorbell_announced").write_bytes(
        b"aria-to-aether-2026-10-01-old.md\n"
    )
    out, _ = _ring(tmp_path / "home", bell=spaced / "letter_doorbell.sh")
    assert "LETTER ARRIVED" in out, out
    assert "cd:" not in out, out
    assert "No such file or directory" not in out, out
    assert "STUB-BATON-RAN-IN a b" in out, out
    # The baton call's own arguments: the subcommand, the letter path and the repo path, the repo
    # path whole. An unquoted "$REPO" splits at the space into three arguments.
    arg_line = next(ln for ln in out.splitlines() if "STUB-BATON-ARGS " in ln)
    args = arg_line.split("STUB-BATON-ARGS ", 1)[1].strip().split("|")
    assert len(args) == 3, args
    assert args[0] == "letter", args
    assert args[1].endswith("aria-to-aether-2026-10-01-new.md"), args
    assert args[2].replace("\\", "/").endswith("/a b"), args
