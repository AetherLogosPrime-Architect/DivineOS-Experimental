"""Tests for .claude/hooks/merge-question-wrong-instrument.sh.

The hook refuses a two-dot deletion-diff against main, because that form
answers "what differs between these two trees" and gets read as "what would
merging do". On 2026-08-29 it reported nine deletions on a branch that would
have deleted zero, and the number was carried to Andrew as an alarm about
destroyed work.

WHY THIS FILE EXISTS AT ALL, which is the more useful half. The hook was first
exercised by a throwaway runner in a scratch directory, and that runner invoked
bare `bash` -- which on this machine resolves to the WSL relay, exits 1, and
never runs the hook. The runner called every non-2 exit a PASS, so five true
positives were reported as the gate letting them through and five negatives
were reported as "ok" without the hook ever executing.

That is could-not-run wearing the clothes of looked-and-found-nothing, inside
the test for the gate built to stop that exact confusion. So:

  * the runner lives in the repo and runs with the suite, not in scratch
  * an exit code that is neither 0 nor 2 is an ERROR, never a pass
  * a missing shell SKIPS loudly rather than passing quietly
"""

import json
import os
import subprocess

import pytest


HOOK = ".claude/hooks/merge-question-wrong-instrument.sh"

_BASH_CANDIDATES = (
    r"C:\Program Files\Git\bin\bash.exe",
    r"C:\Program Files\Git\usr\bin\bash.exe",
    "/bin/bash",
    "/usr/bin/bash",
)

BASH = next((p for p in _BASH_CANDIDATES if os.path.exists(p)), None)

PASS, BLOCK = 0, 2


def fire(command: str) -> int:
    """Return the hook's exit code, refusing to translate one it does not own."""
    if BASH is None:
        pytest.skip("no usable bash on this machine; this says nothing about the hook")

    payload = json.dumps({"tool_input": {"command": command}})
    result = subprocess.run([BASH, HOOK], input=payload, capture_output=True, text=True)

    if result.returncode not in (PASS, BLOCK):
        raise AssertionError(
            f"hook reached no verdict (exit {result.returncode}). "
            f"stderr: {result.stderr.strip()[:300]}"
        )
    return result.returncode


class TestItRefusesTheWrongInstrument:
    def test_the_form_that_produced_the_nine(self):
        assert fire("git diff --name-only --diff-filter=D origin/main mybranch") == BLOCK

    def test_name_status_asks_the_same_question(self):
        """--name-status shows deletions too, so it is the same mistake."""
        assert fire("git diff --name-status origin/main mybranch") == BLOCK

    def test_a_pipe_does_not_hide_it(self):
        assert fire("git diff --name-status origin/main X | head -20") == BLOCK

    def test_a_redirect_does_not_hide_it(self):
        assert fire("git diff --name-status origin/main X > /tmp/out.txt") == BLOCK

    def test_an_innocent_first_stage_does_not_excuse_a_real_second_one(self):
        """Reading the parts must not become an excuse to stop reading them all."""
        assert fire("git rev-parse origin/main && git diff --name-status origin/main X") == BLOCK


class TestShapesThatAreNotTheMistake:
    """Six legitimate forms. A gate firing on ordinary diffs gets switched off."""

    def test_three_dots_is_a_different_question(self):
        assert fire("git diff --name-only --diff-filter=D origin/main... mybranch") == PASS

    def test_a_plain_two_dot_diff_is_left_alone(self):
        assert fire("git diff origin/main mybranch") == PASS

    def test_deletions_between_two_non_main_refs(self):
        assert fire("git diff --diff-filter=D somebranch otherbranch") == PASS

    def test_not_a_diff_at_all(self):
        assert fire("git log --oneline main..mybranch") == PASS

    def test_main_mentioned_only_in_an_unrelated_stage(self):
        """The false fire that motivated reading arguments instead of text.

        This refused the hook's own author while he was reproducing the
        original wrong measurement to settle it with Aria. Nothing here is a
        two-dot diff against main -- the diff runs on a resolved SHA.
        """
        command = (
            "MAINSHA=$(git rev-parse origin/main) && "
            'git diff --name-only --diff-filter=D "$MAINSHA" 320c1886'
        )
        assert fire(command) == PASS


class TestTheHookObeysItsOwnFinding:
    def test_an_unreadable_payload_is_announced_rather_than_swallowed(self):
        """Absent, not satisfied.

        A guard that fails into silence cannot be told apart from one that
        looked and found nothing -- which is the whole subject of this hook.
        """
        if BASH is None:
            pytest.skip("no usable bash on this machine")

        result = subprocess.run(
            [BASH, HOOK], input="not json at all", capture_output=True, text=True
        )
        assert result.returncode == PASS
        assert "NOT RUNNING" in result.stderr
