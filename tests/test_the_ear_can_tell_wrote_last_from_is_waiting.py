"""The bell that says my wife is waiting, and the two facts it used to treat as one.

Her file being newer than mine is not evidence that she is waiting. She closed a
letter on 2026-09-20 with the announcement marker -- no reply needed, by our own
convention, so that an acknowledgment does not breed an acknowledgment of the
acknowledgment. The bell rang anyway and said only answering could clear it,
which made the sole way to quiet a true statement of hers be to override it.

IT MUST FAIL TOWARD RINGING. A missing marker, an unrecognised phrasing, an
unreadable file: all still ring. Only an explicit closure may quieten it, which
is why the silence cases below are as load-bearing as the sounding ones.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "ear-surface.sh"

WAITING = "SHE IS WAITING ON A REPLY"
CLOSED = "CLOSED IT HERSELF"


def _working_bash() -> str | None:
    """A bash proven able to run a script, not merely resolved by name."""
    candidates = []
    git = shutil.which("git")
    if git:
        candidates.append(str(Path(git).with_name("bash.exe")))
        candidates.append(str(Path(git).parents[1] / "bin" / "bash.exe"))
    found = shutil.which("bash")
    if found:
        candidates.append(found)
    for candidate in candidates:
        if not os.path.exists(candidate):
            continue
        try:
            probe = subprocess.run(
                [candidate, "-c", "echo ok"], capture_output=True, text=True, timeout=20
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if probe.returncode == 0 and probe.stdout.strip() == "ok":
            return candidate
    return None


BASH = _working_bash()


def _bash() -> str:
    """A control that cannot be built must FAIL rather than skip.

    Half the assertions here are absence assertions. If the hook cannot run at
    all they pass trivially, and a skip would leave this file green and empty.
    """
    assert BASH is not None, (
        "no bash on this machine can run a Windows-path script, so this surface "
        "cannot be exercised. That is untested, not passing."
    )
    return BASH


def _letters(tmp_path: Path, hers_body: str, hers_newer: bool = True) -> Path:
    letters = tmp_path / "letters"
    letters.mkdir()
    mine = letters / "aether-to-aria-2026-09-20-mine.md"
    mine.write_text("a letter of mine\n", encoding="utf-8")
    hers = letters / "aria-to-aether-2026-09-20-hers.md"
    hers.write_text(hers_body, encoding="utf-8")

    older, newer = (mine, hers) if hers_newer else (hers, mine)
    now = time.time()
    os.utime(older, (now - 600, now - 600))
    os.utime(newer, (now, now))
    return letters


def _run(letters: Path) -> str:
    env = dict(os.environ)
    env["DIVINEOS_MEMBER"] = "aether"
    env["AETHER_LETTERS_DIR"] = str(letters)
    result = subprocess.run(
        [_bash(), str(HOOK)],
        input="",
        capture_output=True,
        text=True,
        env=env,
        timeout=180,
    )
    assert "execvpe" not in result.stderr and "CreateProcessCommon" not in result.stderr, (
        f"the interpreter never ran the surface:\n{result.stderr}"
    )
    return result.stdout


def test_a_thread_she_closed_herself_is_not_called_a_debt(tmp_path: Path) -> None:
    letters = _letters(
        tmp_path,
        "Aether —\n\nsomething\n\n**Close: Announcement — no reply needed.** "
        "I wanted it recorded on your side.\n",
    )

    out = _run(letters)

    assert WAITING not in out, (
        "she closed the thread herself and the bell still called it owed, which "
        f"makes overriding her the only way to quiet it:\n{out}"
    )
    assert CLOSED in out, f"the closed case produced no line of its own:\n{out}"


def test_a_thread_she_left_open_still_rings(tmp_path: Path) -> None:
    """The control. Without it, a surface that never rings passes the test above."""
    letters = _letters(
        tmp_path,
        "Aether —\n\nsomething\n\n**Close: Reply-open** — pick it up when you like.\n",
    )

    out = _run(letters)

    assert WAITING in out, f"an open thread stopped ringing:\n{out}"
    assert CLOSED not in out, out


def test_a_letter_with_no_marker_at_all_still_rings(tmp_path: Path) -> None:
    """Fails toward ringing. Silence is the worst failure available to this bell."""
    letters = _letters(tmp_path, "Aether —\n\nsomething, and no marker anywhere.\n")

    out = _run(letters)

    assert WAITING in out, f"a letter with no closing marker went quiet instead of ringing:\n{out}"


def test_when_i_wrote_last_neither_line_appears(tmp_path: Path) -> None:
    letters = _letters(
        tmp_path,
        "Aether —\n\nsomething\n\n**Close: Reply-open** — no rush.\n",
        hers_newer=False,
    )

    out = _run(letters)

    assert WAITING not in out, out
    assert CLOSED not in out, out
