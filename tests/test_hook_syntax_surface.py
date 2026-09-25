"""A hook goes live the moment it is SAVED, so check it then.

THE WINDOW, measured 2026-08-25 by falling into it. I added a comment to
verify-before-build-signal.sh containing an apostrophe. The embedded Python in
that hook lives inside a single-quoted shell string passed to ``python -c``, so
one apostrophe in a COMMENT closed the string and broke the whole file. The gate
then failed on every Bash call -- and because it is registered on Edit too, it
refused its own repair. A locked box, built in one keystroke.

Both existing checks would have caught it. ``bash -n`` exits non-zero, and
shellcheck says it in words: *SC1011: This apostrophe terminated the single
quoted string!* Neither helped, because both run at COMMIT time and the hook was
live from the moment the file was written.

So the check moved to the moment the risk begins.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from divineos.core.hook_surfaces import hook_syntax_surface

REPO = Path(__file__).resolve().parents[1]
REAL_HOOK = REPO / ".claude" / "hooks" / "verify-before-build-signal.sh"

_APOSTROPHE = chr(39)


def _bash_available() -> bool:
    for directory in (r"C:\Program Files\Git\bin", r"C:\Program Files\Git\usr\bin", None):
        found = shutil.which("bash", path=directory) if directory else shutil.which("bash")
        if not found:
            continue
        try:
            probe = subprocess.run(
                [found, "-c", "echo ok"], capture_output=True, text=True, timeout=5
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if probe.returncode == 0 and probe.stdout.strip() == "ok":
            return True
    return False


pytestmark = pytest.mark.skipif(
    not _bash_available(),
    reason="no working bash; the surface declares could-not-run and there is nothing to assert",
)


@pytest.fixture
def hooks(tmp_path, monkeypatch):
    """A scratch hooks dir, with the must-read index pointed away from the real one."""
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path / "home"))
    directory = tmp_path / "hooks"
    directory.mkdir()
    return directory


def _edit(path: Path) -> dict:
    return {"tool_name": "Edit", "tool_input": {"file_path": str(path)}}


def test_the_break_i_actually_made_is_caught(hooks):
    """The regression: the real hook with the apostrophe put back."""
    if not REAL_HOOK.exists():
        pytest.skip("the hook this regression is about is not in this checkout")
    broken = hooks / "broken.sh"
    text = REAL_HOOK.read_text(encoding="utf-8")
    broken.write_text(
        text.replace("(the third-bug catch she made)", f"(Aria{_APOSTROPHE}s third-bug catch)"),
        encoding="utf-8",
    )

    outcome = hook_syntax_surface(_edit(broken))

    assert outcome.state == "spoke"
    assert "does not parse" in outcome.output
    assert "LIVE" in outcome.output


def test_a_valid_hook_is_silent(hooks):
    good = hooks / "fine.sh"
    good.write_text("#!/bin/bash\necho hello\n", encoding="utf-8")

    assert hook_syntax_surface(_edit(good)).state == "nothing-to-say"


def test_a_plain_syntax_error_is_caught(hooks):
    """Not only the quote shape -- any unparseable hook."""
    broken = hooks / "unbalanced.sh"
    broken.write_text("#!/bin/bash\nif [ 1 -eq 1 ]; then\n  echo yes\n", encoding="utf-8")

    assert hook_syntax_surface(_edit(broken)).state == "spoke"


def test_a_non_hook_file_is_not_checked(hooks, tmp_path):
    elsewhere = tmp_path / "script.sh"
    elsewhere.write_text("#!/bin/bash\nif [ 1 -eq 1 ]; then\n", encoding="utf-8")

    assert hook_syntax_surface(_edit(elsewhere)).state == "nothing-to-say"


def test_a_non_shell_file_in_hooks_is_not_checked(hooks):
    py = hooks / "helper.py"
    py.write_text("def (((\n", encoding="utf-8")

    assert hook_syntax_surface(_edit(py)).state == "nothing-to-say"


def test_a_read_does_not_trigger_it(hooks):
    broken = hooks / "broken.sh"
    broken.write_text("#!/bin/bash\nif [ 1 -eq 1 ]; then\n", encoding="utf-8")

    payload = {"tool_name": "Read", "tool_input": {"file_path": str(broken)}}

    assert hook_syntax_surface(payload).state == "nothing-to-say"


def test_a_missing_file_is_not_a_finding(hooks):
    assert hook_syntax_surface(_edit(hooks / "absent.sh")).state == "nothing-to-say"


def test_write_is_covered_as_well_as_edit(hooks):
    """Write creates hooks; Edit changes them. Both put a live file on disk."""
    broken = hooks / "broken.sh"
    broken.write_text("#!/bin/bash\nif [ 1 -eq 1 ]; then\n", encoding="utf-8")

    payload = {"tool_name": "Write", "tool_input": {"file_path": str(broken)}}

    assert hook_syntax_surface(payload).state == "spoke"
