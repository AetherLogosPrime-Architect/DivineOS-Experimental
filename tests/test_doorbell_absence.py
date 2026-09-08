"""When a doorbell cannot load the OS, it says so instead of exiting quiet.

This is the dissent from the 2026-09-08 council walk, made into a test before
anything else moves behind a doorbell.

Holmes' question was *what would I expect to find that is not here*, and the
answer was this file. Consolidating 105 registrations behind seven doorbells
converts the failure mode from **one surface breaks** into **the import breaks
and every surface on that event is silently absent**. The doorbell's defence
against that is a pair of print statements, and searching the suite found
nothing exercising them -- so the protection existed only as an intention
written in a shell script.

The forcing method is a shadowing package: a temp directory holding a
``divineos`` that raises on import, prepended to ``PYTHONPATH``. That is a real
import failure, not a mocked one, and it is the exact shape the doorbell's own
comment predicts -- surfaces living on an unmerged branch while hooks resolve
the OS from the main clone.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from tests._bash_resolver import bash_executable

ROOT = Path(__file__).resolve().parents[1]
DOORBELLS = ("doorbell-pre-tool-use.sh", "doorbell-post-tool-use.sh")

# Presence is not evidence: the bare name resolves to the WSL relay stub on this
# machine, which cannot execute anything. The shared resolver probes each
# candidate rather than trusting the PATH -- found by searching the suite
# instead of writing a sixth private copy of the same literal paths.
BASH = bash_executable()

pytestmark = pytest.mark.skipif(
    BASH is None, reason="doorbells are bash; no working interpreter on this box"
)


def _run(script: str, env_extra: dict[str, str]) -> subprocess.CompletedProcess:
    env = {**os.environ, **env_extra}
    return subprocess.run(
        [BASH, f".claude/hooks/{script}"],
        cwd=ROOT,
        input="{}",
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )


@pytest.fixture
def broken_os(tmp_path: Path) -> str:
    pkg = tmp_path / "divineos"
    pkg.mkdir()
    (pkg / "__init__.py").write_text(
        'raise ImportError("shimmed: the OS is unreachable from this doorbell")\n',
        encoding="utf-8",
    )
    return str(tmp_path)


@pytest.mark.parametrize("script", DOORBELLS)
def test_a_doorbell_that_cannot_import_the_os_says_so_loudly(script, broken_os):
    proc = _run(script, {"PYTHONPATH": broken_os})
    assert proc.returncode == 0, "a broken doorbell must never wall in the work"
    assert "NOT RUNNING" in proc.stderr
    # The distinction that matters, in the doorbell's own words: absent is not
    # the same as passing. If this phrase is ever edited out, the failure goes
    # back to looking like health.
    assert "not passing, absent" in proc.stderr


@pytest.mark.parametrize("script", DOORBELLS)
def test_the_same_doorbell_is_silent_when_the_os_loads(script):
    """The control. Without it the assertions above pass on a doorbell that
    shouts on every single call, which would be its own defect."""
    proc = _run(script, {})
    assert proc.returncode == 0
    assert "NOT RUNNING" not in proc.stderr


def test_the_absence_message_names_the_event_so_two_doorbells_are_distinguishable(broken_os):
    pre = _run("doorbell-pre-tool-use.sh", {"PYTHONPATH": broken_os}).stderr
    post = _run("doorbell-post-tool-use.sh", {"PYTHONPATH": broken_os}).stderr
    assert "PreToolUse" in pre and "PostToolUse" not in pre
    assert "PostToolUse" in post and "PreToolUse" not in post
