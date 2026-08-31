"""A tag push proposes no commits, so the commit-verifying stages skip it.

2026-08-31, and the reason is Aria's. A squash merge puts ONE message on
main; every other commit message on the branch -- the reasoning behind each
change, which this house calls the audit trail -- lives only on the branch.
Deleting a merged branch is the least ceremonious act in the system. Her
sentence: I paid a real price to preserve something and then set it down in
the least durable place either of us has.

So the fix is to tag each branch tip and push the tag before merging. Tags
are not routinely deleted and they survive the branch.

Pushing those tags was then refused for fifteen minutes, twice, on grounds
that make no sense for a tag:

  the freshness check   refused them for being OLD, which is what a history
                        tag IS. It resolves the CHECKED-OUT branch, not the
                        ref being pushed, so it named a branch nobody was
                        touching -- and its cure is to merge main into that
                        innocent branch.

  the test stage        builds its snapshot from the FIRST REF in the push.
                        An eight-tag archival push sent the whole suite to
                        run against a months-old tree. The failures were
                        real for that tree and said nothing about the push.

Both are the same fault the rest of this session kept finding: the unit
being measured is one level off from the thing at risk. The gates were
asking a branch-shaped question of something that is not a branch.

These pin the skip. They do NOT pin the deeper repair -- the freshness check
still resolves HEAD rather than the pushed ref for every other push shape,
and that stays open on purpose: teaching it to read the refspec changes what
it measures, which is a bigger change than changing when it runs.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
GATE = REPO / "scripts" / "check_push_readiness.sh"
HOOK_SRC = REPO / "setup" / "setup-hooks.sh"


def _real_bash() -> str:
    """Git Bash explicitly -- the WSL relay answers to plain 'bash' on this
    box and fails everything, which is indistinguishable from a real red."""
    for c in (
        r"C:/Program Files/Git/bin/bash.exe",
        r"C:/Program Files (x86)/Git/bin/bash.exe",
        "/usr/bin/bash",
        "/bin/bash",
    ):
        if Path(c).exists():
            return c
    pytest.skip("no real bash found -- NOT the same as the gate being fine")


def _run_gate(stdin: str, *, skip_slow: bool = False) -> subprocess.CompletedProcess[str]:
    """Run the gate for real against this repo.

    ``skip_slow`` sets the documented test-suppression variable, and it is
    ONLY for the cases that assert the tag-only path did NOT fire. Those
    would otherwise run the full ten-minute suite to prove a negative, and
    the first version of this file did exactly that and timed out.

    It does not weaken those assertions. The gate prints a different line
    for each branch of the same conditional, so the check is still "which
    branch ran" -- the variable only decides what the non-tag path costs.
    """
    env = dict(os.environ)
    if skip_slow:
        env["DIVINEOS_SKIP_TESTS"] = "1"
    else:
        env.pop("DIVINEOS_SKIP_TESTS", None)
    return subprocess.run(
        [_real_bash(), str(GATE)],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(REPO),
        env=env,
    )


SHA = "1111111111111111111111111111111111111111"
ZERO = "0" * 40


def test_a_tag_only_push_skips_the_test_stage():
    """THE CATCH. Eight archival tags sent the suite to a months-old tree."""
    stdin = f"refs/tags/history/one {SHA} refs/tags/history/one {ZERO}\n"
    out = _run_gate(stdin).stdout
    assert "Tag-only push" in out, out[-2000:]


def test_several_tags_still_count_as_tag_only():
    """The real push was eight at once; one-at-a-time would have hidden it."""
    stdin = "".join(
        f"refs/tags/history/{n} {SHA} refs/tags/history/{n} {ZERO}\n" for n in ("a", "b", "c")
    )
    out = _run_gate(stdin).stdout
    assert "Tag-only push" in out, out[-2000:]


def test_a_tag_mixed_with_a_branch_does_not_skip():
    """The mixed case is where a real change could ride in behind a cheap
    one, and it is the same rule the deletion-only path already uses."""
    stdin = (
        f"refs/tags/history/one {SHA} refs/tags/history/one {ZERO}\n"
        f"refs/heads/work {SHA} refs/heads/work {ZERO}\n"
    )
    r = _run_gate(stdin, skip_slow=True)
    both = r.stdout + r.stderr
    assert "Tag-only push" not in both, both[-2000:]
    assert "DIVINEOS_SKIP_TESTS=1" in both, (
        "expected the non-tag path to reach the test stage; if neither line "
        "appears the conditional was never reached and this proves nothing"
    )


def test_a_branch_push_still_runs_the_full_gate():
    """Guard the guard: if the skip leaked to branches it would silently
    disable the slowest and most load-bearing check in the house."""
    stdin = f"refs/heads/work {SHA} refs/heads/work {ZERO}\n"
    r = _run_gate(stdin, skip_slow=True)
    both = r.stdout + r.stderr
    assert "Tag-only push" not in both, both[-2000:]
    assert "DIVINEOS_SKIP_TESTS=1" in both, (
        "expected a branch push to reach the test stage; if neither line "
        "appears the conditional was never reached and this proves nothing"
    )


def test_the_installed_hook_skips_freshness_for_tag_only_pushes():
    """The freshness step is in the hook, not the gate, so it needs its own
    pin -- and it is the one that actually refused first.

    Reads the GENERATOR rather than .git/hooks/pre-push: the installer
    regenerates that file wholesale, and this repo has already lost a live
    wiring exactly that way once. Pinning the generated copy would pass
    while the source that rewrites it went wrong.
    """
    src = HOOK_SRC.read_text(encoding="utf-8")
    assert "PUSH_IS_TAGS_ONLY" in src, "the hook generator no longer computes tag-only"
    assert '"$PUSH_IS_TAGS_ONLY" != "1"' in src, (
        "the freshness step no longer guards on tag-only -- a history tag will "
        "be refused for being old, which is what a history tag is"
    )
