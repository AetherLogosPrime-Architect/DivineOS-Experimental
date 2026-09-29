"""An unauthenticated lookup called a real pull request absent.

2026-09-21. Two tests in the correction tracker failed on CI and passed on
every developer machine. The tracker was right both times: it refuses evidence
whose pointer names nothing real, and it was handed a wrong answer. The runner
has the GitHub CLI on PATH but no credentials, so the lookup could not run,
returned non-zero, and the verifier read non-zero as "this pull request does
not exist."

Non-zero covers at least five situations -- genuinely absent, unauthenticated,
offline, rate-limited, and not-inside-a-repository -- and only the first is a
finding. Collapsing them meant a correction integrated with a perfectly real
pointer was refused, and the refusal said the evidence named nothing.

WHICH DIRECTION TO FAIL, stated rather than assumed. A wrong could-not-check
costs one row recorded as unverified, and the recording keeps it honest. A
wrong not-found refuses work that was really done and tells its author their
evidence was invented.

Nothing here touches the network, and that is the point: the condition being
reproduced is the ABSENCE of a working lookup, which is exactly what a stand-in
provides. Before this file the pull-request path had no test of any kind.
"""

from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from divineos.core import closure_verification as cv


def _fake_gh(returncode: int, stderr: str):
    def run(*_a, **_k):
        return SimpleNamespace(returncode=returncode, stdout="", stderr=stderr)

    return run


@pytest.fixture(autouse=True)
def _gh_on_path(monkeypatch):
    monkeypatch.setattr(cv.shutil, "which", lambda _n: "/usr/bin/gh")


def test_an_unauthenticated_lookup_withholds_the_verdict(monkeypatch):
    """The exact condition the runner was in. This is the carrying test."""
    monkeypatch.setattr(
        cv.subprocess, "run", _fake_gh(1, "gh: To use GitHub CLI in a GitHub Actions workflow...")
    )
    result = cv.verify_citation("#189")
    assert not result.ok
    assert result.could_not_check, "an unauthenticated lookup was read as the PR being absent"


def test_an_offline_lookup_withholds_the_verdict(monkeypatch):
    monkeypatch.setattr(
        cv.subprocess, "run", _fake_gh(1, "dial tcp: lookup api.github.com: no such host")
    )
    assert cv.verify_citation("#189").could_not_check


def test_an_unrecognised_failure_withholds_the_verdict(monkeypatch):
    """Anything unrecognised must not become a finding. A new message from a
    future release of the CLI is not evidence about the pull request."""
    monkeypatch.setattr(cv.subprocess, "run", _fake_gh(1, "something nobody has seen before"))
    assert cv.verify_citation("#189").could_not_check


def test_a_genuinely_absent_pr_is_still_reported_absent(monkeypatch):
    """THE CONTROL, and without it this repair is indistinguishable from
    switching the check off. A pointer at nothing must still be refusable, or
    any invented number passes."""
    monkeypatch.setattr(
        cv.subprocess,
        "run",
        _fake_gh(1, "GraphQL: Could not resolve to a PullRequest with the number of 99999."),
    )
    result = cv.verify_citation("#99999")
    assert not result.ok
    assert not result.could_not_check, "a genuinely absent PR stopped being reportable as absent"


def test_a_resolving_pr_is_found(monkeypatch):
    """The other control: the happy path still answers yes."""
    monkeypatch.setattr(cv.subprocess, "run", _fake_gh(0, ""))
    assert cv.verify_citation("#189").ok


def test_a_missing_cli_was_already_could_not_check(monkeypatch):
    """Always handled; pinned so a later edit cannot regress it quietly while
    the new cases keep passing."""
    monkeypatch.setattr(cv.shutil, "which", lambda _n: None)
    assert cv.verify_citation("#189").could_not_check


def test_a_timeout_is_still_could_not_check(monkeypatch):
    def _boom(*_a, **_k):
        raise subprocess.TimeoutExpired(cmd="gh", timeout=15)

    monkeypatch.setattr(cv.subprocess, "run", _boom)
    assert cv.verify_citation("#189").could_not_check


def test_the_three_answers_stay_distinct(monkeypatch):
    """Found, absent and could-not-tell must remain three answers. Collapsing
    any pair is the whole fault this file exists for."""
    monkeypatch.setattr(cv.subprocess, "run", _fake_gh(0, ""))
    found = cv.verify_citation("#1")
    monkeypatch.setattr(
        cv.subprocess, "run", _fake_gh(1, "Could not resolve to a PullRequest with the number of 2")
    )
    absent = cv.verify_citation("#2")
    monkeypatch.setattr(cv.subprocess, "run", _fake_gh(1, "HTTP 401: Bad credentials"))
    unknown = cv.verify_citation("#3")

    assert (found.ok, found.could_not_check) == (True, False)
    assert (absent.ok, absent.could_not_check) == (False, False)
    assert (unknown.ok, unknown.could_not_check) == (False, True)
