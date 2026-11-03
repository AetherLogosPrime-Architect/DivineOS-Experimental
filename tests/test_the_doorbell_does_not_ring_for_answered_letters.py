"""An answered letter is not announced again when the bell is armed.

Root cause (2026-11-03): the bell's "announced" list holds only letters the bell
itself rang. A letter the seat read and replied to by any other road (read in the
session, bell down, list lost) was never on it, so the next arm announced that old
letter at once, waking the seat for nothing. At arm time the bell now treats a letter
as already dealt with when the seat's own newest outgoing letter is newer than it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BELL = ROOT / "scripts" / "letter_doorbell.sh"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None, reason="no bash to run the bell with")


def _letter(letters: Path, name: str, age_secs: int) -> Path:
    p = letters / name
    p.write_text("x", encoding="utf-8")
    t = time.time() - age_secs
    os.utime(p, (t, t))
    return p


def _env(home: Path) -> dict[str, str]:
    return {**os.environ, "HOME": str(home), "DOORBELL_ALLOW_UNTRACKED": "1", "DOORBELL_POLL": "1"}


def _ring(home: Path, member: str, seconds: float = 5) -> str:
    try:
        p = subprocess.run(
            [BASH, "-c", f'bash "{BELL.as_posix()}" {member}; :'],
            env=_env(home),
            capture_output=True,
            text=True,
            timeout=seconds,
        )
        return p.stdout + p.stderr
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout or ""
        return out.decode() if isinstance(out, bytes) else out


@pytest.fixture
def letters(tmp_path):
    d = tmp_path / ".divineos-shared" / "letters"
    d.mkdir(parents=True)
    # A marker that EXISTS but lacks the letters under test: the state after a bell was
    # down, or a letter was read some other way. (An empty marker is seeded with everything
    # present and hides the bug.)
    (tmp_path / ".divineos-shared" / ".aether_doorbell_announced").write_bytes(
        b"aria-to-aether-2026-01-01-ancient.md\n"
    )
    return d


def test_an_answered_letter_is_not_announced(tmp_path, letters):
    _letter(letters, "aria-to-aether-2026-11-03-a.md", 100)  # A, from the other seat
    _letter(letters, "aether-to-aria-2026-11-03-b.md", 50)  # B, my reply, later
    out = _ring(tmp_path, "aether")
    assert "doorbell armed" in out, out  # control: it really started
    assert "LETTER ARRIVED" not in out, out
    assert "-a.md" not in out


def test_an_unanswered_letter_still_rings(tmp_path, letters):
    _letter(letters, "aether-to-aria-2026-11-03-b.md", 100)
    _letter(letters, "aria-to-aether-2026-11-03-c.md", 50)  # newer than my reply: unread
    out = _ring(tmp_path, "aether")
    assert "LETTER ARRIVED" in out and "-c.md" in out, out


def test_a_new_letter_after_arming_rings(tmp_path, letters):
    _letter(letters, "aria-to-aether-2026-11-03-a.md", 100)
    _letter(letters, "aether-to-aria-2026-11-03-b.md", 50)
    proc = subprocess.Popen(
        [BASH, "-c", f'bash "{BELL.as_posix()}" aether; :'],
        env=_env(tmp_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        time.sleep(2.5)
        # Old mtime on purpose: a synced letter must ring even if it looks older than my reply.
        _letter(letters, "aria-to-aether-2026-11-03-new.md", 500)
        out, _ = proc.communicate(timeout=10)
    finally:
        proc.kill()
    assert "LETTER ARRIVED" in out and "-new.md" in out, out
    assert "-a.md" not in out


def test_two_seats_do_not_read_each_others_markers(tmp_path, letters):
    _letter(letters, "aria-to-aether-2026-11-03-a.md", 100)
    _letter(letters, "aether-to-aria-2026-11-03-b.md", 50)
    _letter(letters, "aria-to-aether-2026-11-03-c.md", 10)  # unread by aether
    # Aria's marker claims everything announced; it must not silence aether's bell.
    (tmp_path / ".divineos-shared" / ".aria_doorbell_announced").write_bytes(
        b"aria-to-aether-2026-11-03-c.md\n"
    )
    out = _ring(tmp_path, "aether")
    assert "LETTER ARRIVED" in out and "-c.md" in out, out
    assert "-a.md" not in out
    assert (tmp_path / ".divineos-shared" / ".aether_doorbell_announced").exists()
