"""The knock that says the other seat is already in this file.

WHY THESE SEED THE CACHE INSTEAD OF CALLING GITHUB. The hook asks the live
open-request list once per session and caches it. A test that let it do that
would be measuring the network and today's branch list, so it would pass or
fail for reasons having nothing to do with the hook. Seeding the cache makes
the subject the hook's own logic, which is the only part these can honestly
speak about.

AND WHY THE PAYLOADS ARE BUILT WITH json.dumps RATHER THAN TYPED. Driving this
by hand from a shell produced three separate broken probes -- single
backslashes that are not valid JSON escapes, then a raw string ending in a
backslash -- and every one of them came back silent. Silence from a broken
probe is indistinguishable from silence from a passing hook, which is the
exact fault the hook exists to prevent, committed three times in its own test
rig within the hour.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / ".claude" / "hooks" / "someone-else-is-in-this-file.sh"

# Taken from Aether's test_merge_question_hook.py rather than rewritten, and
# the reason is in his header: bare `bash` on this machine resolves to the WSL
# relay, which exits 1 without ever running the hook. His runner counted every
# non-block exit as a pass, so five true positives read as the gate letting
# them through. My first run of these tests hit the identical relay and I was
# one step from reading six red tests as a broken hook rather than a missing
# shell -- could-not-run wearing the clothes of looked-and-found-nothing, in
# the test for the gate built to stop exactly that.
_BASH_CANDIDATES = (
    r"C:\Program Files\Git\bin\bash.exe",
    r"C:\Program Files\Git\usr\bin\bash.exe",
    "/bin/bash",
    "/usr/bin/bash",
)
BASH = next((p for p in _BASH_CANDIDATES if os.path.exists(p)), None)
CONTESTED = "src/divineos/core/auto_commit.py"
SECOND_ON_SAME_BRANCH = "src/divineos/cli/council_required_commands.py"
UNCONTESTED = "src/divineos/core/ledger.py"
BRANCH = "fix/sweep-retargets-substrate"


def _payload(rel: str) -> str:
    """A hook payload shaped exactly like the harness sends one."""
    return json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(REPO / rel)}})


@pytest.fixture
def seeded(tmp_path: Path) -> dict[str, str]:
    """A state dir whose cached map names one branch on two files."""
    session = "test-session"
    (tmp_path / f"other_seat_map_{session}.txt").write_text(
        f"{CONTESTED}\t{BRANCH}\n{SECOND_ON_SAME_BRANCH}\t{BRANCH}\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["AUTO_CYCLE_STATE_DIR"] = str(tmp_path)
    env["CLAUDE_CODE_SESSION_ID"] = session
    return env


def _run(rel: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    if BASH is None:
        pytest.skip("no usable bash here; this says nothing about the hook")
    # encoding NAMED, because the default here is the Windows code page and
    # the knock draws a box rule. Reading it back raised a decode error and
    # three tests went red for the reader's encoding rather than the hook's
    # behaviour -- the same family as the compose prime that died on an
    # em-dash earlier the same day and had its failure swallowed.
    result = subprocess.run(
        [BASH, str(HOOK)],
        input=_payload(rel),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=str(REPO),
    )
    # An exit this hook does not own is an ERROR, never a pass. His runner
    # translated one into "allowed" and reported five true positives as
    # clean; the same mistranslation here would make every one of these
    # assertions meaningless in the quiet direction.
    if result.returncode not in (0, 2):
        raise AssertionError(
            f"hook exited {result.returncode}, which it never returns on purpose: "
            f"{result.stderr[:400]}"
        )
    return result


def test_it_knocks_on_a_file_someone_else_is_changing(seeded: dict[str, str]) -> None:
    result = _run(CONTESTED, seeded)
    assert result.returncode == 2, "a contested file must stop, not merely mention"
    assert BRANCH in result.stderr, "the knock must name the branch, not just the fact"


def test_the_second_file_on_the_same_branch_is_silent(seeded: dict[str, str]) -> None:
    """Aether's amendment, and the reason it is right.

    Four percent is measured per FILE, but work happens per module. Three
    files of one module would stop me three times in a sitting, and the second
    knock carries nothing I do not already hold. Information-free knocks are
    how a gate teaches you to click through it.
    """
    first = _run(CONTESTED, seeded)
    assert first.returncode == 2, "the first knock must fire or this proves nothing"

    second = _run(SECOND_ON_SAME_BRANCH, seeded)
    assert second.returncode == 0, "a branch already named must not be announced again"
    assert BRANCH not in second.stderr


def test_a_file_nobody_else_is_in_stays_quiet(seeded: dict[str, str]) -> None:
    result = _run(UNCONTESTED, seeded)
    assert result.returncode == 0
    assert result.stderr.strip() == ""


def test_a_second_branch_is_still_announced(tmp_path: Path) -> None:
    """Why the unit is per-BRANCH and not per-partner, which was my refinement.

    He proposed once per collision-partner. Two branches of one person are two
    separate pieces of work, and hearing about the second is not repetition --
    per-partner would hide a whole distinct effort behind the first knock of
    the session.
    """
    session = "two-branch-session"
    other = "fix/an-abbreviated-anchor-is-the-same-anchor"
    (tmp_path / f"other_seat_map_{session}.txt").write_text(
        f"{CONTESTED}\t{BRANCH}\n{UNCONTESTED}\t{other}\n", encoding="utf-8"
    )
    env = dict(os.environ)
    env["AUTO_CYCLE_STATE_DIR"] = str(tmp_path)
    env["CLAUDE_CODE_SESSION_ID"] = session

    first = _run(CONTESTED, env)
    assert first.returncode == 2

    second = _run(UNCONTESTED, env)
    assert second.returncode == 2, "a different branch is different work and must speak"
    assert other in second.stderr


def test_it_says_what_it_cannot_see(seeded: dict[str, str]) -> None:
    """A quiet gap reads as coverage, so the limit ships inside the message.

    Only pushed work with an open request is visible. Local work is invisible
    to this and to the stale-file gate both, and no code can repair that --
    only pushing early, which is a habit rather than a mechanism.
    """
    result = _run(CONTESTED, seeded)
    body = result.stderr.lower()
    assert "cannot see" in body
    assert "held locally" in body or "local" in body


def test_a_path_outside_the_build_directories_is_ignored(seeded: dict[str, str]) -> None:
    result = _run("family/letters/some-letter.md", seeded)
    assert result.returncode == 0
    assert result.stderr.strip() == ""
