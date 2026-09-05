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

    def test_the_literal_two_dot_spelling_the_refusal_text_names(self):
        """Aria's probe, 2026-08-31, and it walked the gate's own subject through.

        The refusal text says "this is a two-dot diff against main". The
        condition required main followed by WHITESPACE, so `main..HEAD` -- a
        DOT after the ref name -- failed it and the segment was skipped before
        the two-dot test ever ran.

        She measured four spellings rather than reading the regex and calling
        it suspicious, which is why this is a finding and not a worry. I
        reproduced all four on my side before touching anything: the
        whitespace forms refused, both two-dot forms silent at exit zero.

        The unit was `main followed by a space`. The risk is `main used as a
        two-dot endpoint`. Same fault as everything else this week, sitting
        inside the gate built during it.
        """
        assert fire("git diff --diff-filter=D main..HEAD") == BLOCK

    def test_the_same_spelling_with_the_remote_prefix(self):
        assert fire("git diff --diff-filter=D origin/main..HEAD") == BLOCK

    def test_name_status_in_the_two_dot_spelling(self):
        assert fire("git diff --name-status origin/main..mybranch") == BLOCK


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

    def test_a_file_named_after_the_branch_is_not_a_diff_against_it(self):
        """The false fire the WIDER repair would have introduced.

        Letting any dot follow the ref name closes the two-dot hole and also
        starts refusing an ordinary diff of a file called main.py. Aria's own
        rule from her checker -- widening a condition to make a mismatch go
        away is how a gate stops catching what it exists for -- applies in this
        direction too, so the fix matches TWO dots specifically.

        This pins the narrowness. Without it, the next person closing a hole
        here has nothing telling them which way not to reach.
        """
        assert fire("git diff --name-status main.py") == PASS

    def test_maintenance_is_not_main(self):
        """The boundary that was always there, kept by the same change."""
        assert fire("git diff --diff-filter=D maintenance otherbranch") == PASS


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
