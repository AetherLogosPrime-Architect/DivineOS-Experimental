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


def test_the_review_job_runs_on_the_queue_and_only_answers_there():
    job = _load("integrity-audit.yml")["jobs"]["guardrail-trailer-check"]
    assert job["name"] == "multi-party-review"
    assert "merge_group" in job["if"]
    steps = job["steps"]
    answer = [s for s in steps if s.get("if") == "github.event_name == 'merge_group'"]
    assert len(answer) == 1, "exactly one step answers on the queue's run"
    real = [s for s in steps if s not in answer]
    assert real, "the real checking steps must still exist"
    for step in real:
        assert step.get("if") == "github.event_name != 'merge_group'", (
            f"step {step.get('name')!r} would run, or be skipped, on the queue by accident"
        )


def test_the_review_check_still_runs_on_pull_requests_and_pushes():
    triggers = _triggers(_load("integrity-audit.yml"))
    assert "pull_request" in triggers and "push" in triggers
