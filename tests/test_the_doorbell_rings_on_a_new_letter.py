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
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BELL = ROOT / "scripts" / "letter_doorbell.sh"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None, reason="no bash to run the bell with")


def _ring(home: Path, seconds: float = 6) -> tuple[str, bool]:
    """The bell's output, and whether it was still running when time ran out.

    The bell leaves silently when its starter is gone (kill -0 $PPID). Started
    straight from Python on Windows, its parent is not a pid bash can see, so it
    left at once and every "did not ring" passed vacuously. A bash parent that
    outlives it (the trailing ':' stops bash exec-ing the child) is the starter
    the harness gives it for real.
    """
    env = {**os.environ, "HOME": str(home)}
    try:
        p = subprocess.run(
            [BASH, "-c", f'bash "{BELL.as_posix()}" aether; :'],
            env=env,
            capture_output=True,
            text=True,
            timeout=seconds,
        )
        return p.stdout + p.stderr, False
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout or ""
        return (out.decode() if isinstance(out, bytes) else out), True


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
