"""Stamp-ready checks whether it can push BEFORE it rewrites history.

Companion to test_stamp_ready_tree_binding.py, which covers WHICH round may be
stamped onto which tree. This covers WHEN the stamping is allowed to start.

`run_push_ready` amends every guardrail-touching commit to carry the review
trailer -- which rewrites their identities -- and only THEN attempts the push.
So a push that was never going to be accepted still costs a full rewrite, and
leaves the branch diverged from origin with the PR body unwritten: a
half-finished state that looks like nothing happened until the next ordinary
push is refused for reasons unrelated to what the person was doing.

Observed 2026-08-17 on PR #412: seven commits amended, then "[freshness-check]
BLOCKED: branch is 2 commit(s) behind origin/main". Every individual step was
correct; the ORDER was not. The module already held the principle -- "Order is
load-bearing: a failure between the two leaves a draft carrying a valid
trailer, which is recoverable" -- and had not extended it past the body/ready
pair to the rewrite itself.

THE PROPERTY THESE TESTS EXIST FOR is not "is the count right". It is that
COULD-NOT-DETERMINE never reads as SAFE-TO-PROCEED. `_commits_behind_base`
returns the answer and the reason-it-has-no-answer as separate values for
exactly that reason, and the first version of this preflight is why:

it shelled out to a script, treated any non-zero exit as "branch is behind",
and printed "the branch cannot be pushed as it stands". Dogfooding produced
precisely that message when `bash` resolved to WSL's bash and the check never
ran at all -- blaming the branch for a missing shell. That is the same
misattribution repaired in build_flow's station 8 hours earlier the same day,
reproduced by me while writing a repair for something else. Knowing the
pattern by name did not prevent instantiating it; running the thing did.

Two values instead of one makes the collapse unrepresentable. The shell is
gone too: this is `git fetch` plus `git rev-list --count`, which have no
PATH-resolution surface to get wrong.
"""

from __future__ import annotations

import subprocess

import pytest

from divineos.cli import stamp_ready_command as src


class TestUnknownIsNotZero:
    """The whole point: a count of 0 means 'not behind, safe to proceed'."""

    def test_a_failed_fetch_reports_a_reason_and_does_not_claim_zero(self, monkeypatch):
        def fake_run(args, **kwargs):
            return subprocess.CompletedProcess(args, 1, "", "could not resolve host")

        monkeypatch.setattr(src.subprocess, "run", fake_run)
        behind, why = src._commits_behind_base()
        assert why, "a failed fetch must report WHY, not silently answer"
        assert "could not fetch" in why
        # `behind` is 0 here, which is exactly why the caller branches on `why`
        # FIRST. Zero-with-a-reason is not zero.
        assert behind == 0

    def test_a_failed_revlist_reports_a_reason(self, monkeypatch):
        def fake_run(args, **kwargs):
            if "fetch" in args:
                return subprocess.CompletedProcess(args, 0, "", "")
            return subprocess.CompletedProcess(args, 128, "", "bad revision")

        monkeypatch.setattr(src.subprocess, "run", fake_run)
        _, why = src._commits_behind_base()
        assert "rev-list failed" in why

    def test_a_missing_git_reports_a_reason_rather_than_raising(self, monkeypatch):
        """The WSL case in its general form: the tool is not where we looked.

        It must not crash the stamp, and it must not read as 'nothing behind'.
        """

        def fake_run(args, **kwargs):
            raise FileNotFoundError("git not found")

        monkeypatch.setattr(src.subprocess, "run", fake_run)
        behind, why = src._commits_behind_base()
        assert "FileNotFoundError" in why
        assert behind == 0

    def test_unparseable_output_reports_a_reason(self, monkeypatch):
        """A count that is not a number is not a count."""

        def fake_run(args, **kwargs):
            if "fetch" in args:
                return subprocess.CompletedProcess(args, 0, "", "")
            return subprocess.CompletedProcess(args, 0, "not-a-number\n", "")

        monkeypatch.setattr(src.subprocess, "run", fake_run)
        _, why = src._commits_behind_base()
        assert "ValueError" in why


class TestTheAnswerWhenItIsKnown:
    def test_up_to_date_is_zero_with_no_reason(self, monkeypatch):
        def fake_run(args, **kwargs):
            if "fetch" in args:
                return subprocess.CompletedProcess(args, 0, "", "")
            return subprocess.CompletedProcess(args, 0, "0\n", "")

        monkeypatch.setattr(src.subprocess, "run", fake_run)
        assert src._commits_behind_base() == (0, "")

    @pytest.mark.parametrize("n", [1, 2, 47])
    def test_behind_returns_the_count_with_no_reason(self, monkeypatch, n):
        def fake_run(args, **kwargs):
            if "fetch" in args:
                return subprocess.CompletedProcess(args, 0, "", "")
            return subprocess.CompletedProcess(args, 0, f"{n}\n", "")

        monkeypatch.setattr(src.subprocess, "run", fake_run)
        assert src._commits_behind_base() == (n, "")

    def test_empty_output_is_treated_as_zero(self, monkeypatch):
        """git prints nothing for an empty range under some configurations."""

        def fake_run(args, **kwargs):
            if "fetch" in args:
                return subprocess.CompletedProcess(args, 0, "", "")
            return subprocess.CompletedProcess(args, 0, "\n", "")

        monkeypatch.setattr(src.subprocess, "run", fake_run)
        assert src._commits_behind_base() == (0, "")


def test_no_shell_dependency():
    """The check must not reach for a shell.

    `bash` on this machine resolves to WSL's, which cannot see the Windows
    filesystem. The original preflight shelled out and failed with an execvpe
    error that said nothing about branches. Pinned so the dependency cannot
    quietly return.

    THE DOCSTRING IS STRIPPED BEFORE SCANNING, and the first version of this
    test is why: it scanned the whole source, and the function's own docstring
    explains why bash is not used. So the test failed BECAUSE THE FIX WAS
    DOCUMENTED, and the better the explanation the louder the false alarm.

    A text-matching check cannot tell a thing from a description of the thing.
    Scanning executable code only is the narrow fix; the transferable one is
    that prose about a hazard reads identically to the hazard — the same limit
    already recorded on the foundational-truths surface.
    """
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(src._commits_behind_base).strip())
    fn = tree.body[0]
    assert isinstance(fn, ast.FunctionDef)
    body = fn.body[1:] if ast.get_docstring(fn) else fn.body
    code = "\n".join(ast.unparse(node) for node in body)

    assert "bash" not in code, "the check must not shell out"
    assert "shell=True" not in code
    assert "git" in code, "and it must still actually ask git"
