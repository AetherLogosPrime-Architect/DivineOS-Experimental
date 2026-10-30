"""The workflows that carry the required checks must answer the merge queue.

A merge queue asks for the required checks on the combined result. A check whose workflow does
not listen for ``merge_group`` never starts, so a queued piece waits forever and nothing merges.
Nothing reminded anyone of that; a one-line edit removing the trigger would have been a silent
denial of every merge (walk-681b6441dade, Hoare: the caller was obliged to remember, and nothing
enforced it). This turns the memory into a constraint.
"""

from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"


def _load(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def _triggers(doc: dict) -> dict:
    # PyYAML reads the bare key `on` as the boolean True.
    return doc.get(True) or doc.get("on") or {}


def test_both_workflows_listen_for_the_merge_queue():
    for name in ("tests.yml", "integrity-audit.yml"):
        assert "merge_group" in _triggers(_load(name)), f"{name} does not listen for merge_group"


def test_the_test_job_runs_on_the_queue():
    job = _load("tests.yml")["jobs"]["test"]
    assert "merge_group" in job["if"]


def test_the_review_job_runs_in_full_on_the_queue_too():
    """Aletheia, 2026-10-28: the queue must not be the one path where the review line goes
    unchecked at merge time. No step of the job may be skipped on the queue's run, and the
    verify step must take the range and the pull request from the merge group."""
    job = _load("integrity-audit.yml")["jobs"]["guardrail-trailer-check"]
    assert job["name"] == "multi-party-review"
    assert "merge_group" in job["if"]
    for step in job["steps"]:
        assert "merge_group" not in str(step.get("if", "")), (
            f"step {step.get('name')!r} is conditioned on the queue; the check must run in full"
        )
    verify = next(s for s in job["steps"] if "Verify" in s.get("name", ""))
    script = verify["run"]
    for needle in (
        "merge_group.base_sha",
        "merge_group.head_sha",
        "MERGE_GROUP_HEAD_REF",
        "scripts/ci_check_guardrail_trailer.sh",
    ):
        assert needle in script or needle in str(verify.get("env", "")), needle


def test_the_pull_request_number_is_read_from_the_queue_ref_by_the_real_line():
    """Runs the workflow's own extraction line on real-shaped queue refs, so a change to the
    line or to GitHub's ref shape fails here and not on the first queued piece."""
    import subprocess

    from tests.test_a_merge_cannot_commit_past_its_own_tests import BASH

    if BASH is None:
        import pytest

        pytest.skip("no working bash on this machine")
    verify = next(
        s
        for s in _load("integrity-audit.yml")["jobs"]["guardrail-trailer-check"]["steps"]
        if "Verify" in s.get("name", "")
    )
    line = next(ln for ln in verify["run"].splitlines() if "PR_NUMBER=$(echo" in ln).strip()
    for ref, want in (
        ("gh-readonly-queue/main/pr-737-77d28c7aa5e00b2b64a9c28fde3e6264fd7667c6", "737"),
        ("gh-readonly-queue/main/pr-5-abc", "5"),
        ("gh-readonly-queue/main/nothing", ""),
    ):
        out = subprocess.run(
            [BASH, "-c", f'MERGE_GROUP_HEAD_REF="{ref}"\n{line}\necho "$PR_NUMBER"'],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert out == want, (ref, out)


def test_the_coverage_measurement_stays_ungated():
    """Aether's hold on #737: moving --cov into the main test command would let pyproject's
    fail_under (75) fail every required test job. The measurement must not become a gate
    before anyone has measured it."""
    steps = _load("tests.yml")["jobs"]["test"]["steps"]
    main = next(s for s in steps if "--cov=" in s.get("run", ""))
    assert "--cov-fail-under=0" in main["run"]


def test_the_review_check_still_runs_on_pull_requests_and_pushes():
    triggers = _triggers(_load("integrity-audit.yml"))
    assert "pull_request" in triggers and "push" in triggers
