"""A commit reached through a chain was invisible to the commit-time prime.

Aletheia's standing finding, which I measured rather than agreed with. The
prime decided whether a command was substrate-modifying by taking its first
two tokens, so `bash checks.sh && git commit -m x` resolved to a head of bash
and the surface went silent. That is not an exotic form — it is how I chain a
check ahead of a commit, and I ran it repeatedly on 2026-09-20 without noticing
the door had stopped answering.

The repair was an import rather than a better loop: the shared parser already
answers which parts of a line act, and its own docstring says a fourth site
means importing it. This hook was that fourth site.

THE NEGATIVE CASE IS WHY THE POSITIVE ONE MEANS ANYTHING. A prime that fires on
everything satisfies "the chained form fires" and is useless, so a read-only
command must still leave it silent.

AND ONE CASE PINS A HOLE RATHER THAN A FIX. `git -C /repo commit` still escapes,
because the parser strips PREFIXES and a flag sits inside the command it
modifies. That test asserts the escape, so the day somebody closes it in the
shared parser this file fails and says why — a known gap that announces its own
repair rather than a silent one.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK = REPO_ROOT / ".claude" / "hooks" / "wwnd-tool-prime.sh"
EVENT_LOG = Path(os.path.expanduser("~")) / ".divineos" / "wwnd_tool_prime_events.jsonl"


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

pytestmark = [
    pytest.mark.skipif(not HOOK.exists(), reason="hook absent from this checkout"),
    pytest.mark.skipif(BASH is None, reason="no working bash on this platform"),
]


def _fired(command: str) -> bool:
    """Run the real hook and read the decision it recorded about itself.

    The hook prints nothing a caller can read — it writes whether it fired to
    its own event log. Reading that is the measurement; anything else would be
    a test of a copy of the logic rather than of the hook.
    """
    assert BASH is not None
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    before = EVENT_LOG.stat().st_size if EVENT_LOG.exists() else 0
    subprocess.run(
        [BASH, str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=180,
    )
    if not EVENT_LOG.exists() or EVENT_LOG.stat().st_size <= before:
        pytest.skip("the hook recorded nothing, so this measures the log not the prime")
    lines = EVENT_LOG.read_text(encoding="utf-8").splitlines()
    return bool(json.loads(lines[-1])["fired"])


def test_a_plain_commit_fires():
    assert _fired("git commit -m x")


def test_a_commit_behind_a_chain_fires():
    """The escape Aletheia found, and the form I actually type."""
    assert _fired("bash scripts/checks.sh && git commit -m x"), (
        "a commit reached through a chain is still invisible to the prime"
    )


def test_a_read_only_command_stays_silent():
    """The negative. Without it, a prime that fires on everything passes."""
    assert not _fired("grep -rn foo src/")


def test_a_flag_between_command_and_subcommand_still_escapes():
    """A KNOWN HOLE, asserted so it cannot close quietly.

    The shared parser strips prefixes, and a flag sits inside the command it
    modifies rather than in front of it. The repair belongs in that parser,
    where several callers would gain it at once. When somebody makes it, this
    test fails and its message says what changed — which is the point of
    pinning a gap rather than only writing it down.
    """
    assert not _fired("git -C /repo commit -m x"), (
        "the flag-between-command-and-subcommand escape appears to be closed. "
        "If that was deliberate, delete this test and say so; the gap was "
        "measured on 2026-09-20 and left open on purpose."
    )
