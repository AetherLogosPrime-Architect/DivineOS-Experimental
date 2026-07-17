"""Regression pin for Marc audit finding #4 (2026-07-16): the
``scripts/ci_merge_review_check.py`` script existed and its own docstring
claimed the GitHub Action calls it, but no job in
``.github/workflows/integrity-audit.yml`` actually invoked it. The
guardrail gate on ``main`` was therefore satisfied by any commit message
containing the literal string ``External-Review: <anything>``, with no
verification that the referenced audit round existed.

This test walks the workflow YAML and asserts a job runs the script.
Static text check — matches the shape of the other Marc-audit wiring
regression tests (compass-check, corrigibility-tool-gate).
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover — yaml is a test-time dep
    yaml = None  # type: ignore[assignment]


REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "integrity-audit.yml"
SCRIPT_NAME = "ci_merge_review_check.py"


pytestmark = pytest.mark.skipif(
    yaml is None,
    reason="PyYAML not installed (unusual for this dev environment)",
)


def test_workflow_invokes_ci_merge_review_check_script() -> None:
    """The workflow must invoke scripts/ci_merge_review_check.py from
    at least one job's ``run`` step. If a future refactor removes the
    invocation, this test fails loudly rather than the gate silently
    falling back to string-presence only.
    """
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    # Simple substring check first — cheap, catches removal outright.
    assert SCRIPT_NAME in text, (
        f"{SCRIPT_NAME} is not referenced anywhere in "
        f"{WORKFLOW_PATH.name}. Regression of Marc audit finding #4: "
        f"the script exists but no job invokes it, so the guardrail "
        f"round-existence check is not enforced on PRs to main."
    )

    # Then walk the parsed YAML to be sure it appears inside an
    # actual `run:` block, not just a comment or docstring.
    data = yaml.safe_load(text)
    jobs = data.get("jobs", {}) if isinstance(data, dict) else {}
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps", []):
            if not isinstance(step, dict):
                continue
            run_block = step.get("run", "")
            if isinstance(run_block, str) and SCRIPT_NAME in run_block:
                return  # found a real invocation
    pytest.fail(
        f"{SCRIPT_NAME} appears in {WORKFLOW_PATH.name} but not inside "
        f"any job's `run:` block. It may be commented out, in a docstring, "
        f"or in a step type that doesn't execute. Regression of Marc "
        f"audit finding #4."
    )


def test_merge_review_job_only_fires_on_pull_request() -> None:
    """The merge-review job needs a PR number to work (fetches reviews
    via ``gh api repos/.../pulls/<n>/reviews``). If a future refactor
    accidentally makes it fire on ``push`` events, ``gh`` would receive
    an empty PR number and infrastructure-error the run.
    """
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    jobs = data.get("jobs", {}) if isinstance(data, dict) else {}

    review_job = None
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps", []):
            if not isinstance(step, dict):
                continue
            if SCRIPT_NAME in (step.get("run", "") or ""):
                review_job = job
                break
        if review_job is not None:
            break

    assert review_job is not None, f"could not locate the job invoking {SCRIPT_NAME}"
    condition = review_job.get("if", "")
    assert "pull_request" in condition, (
        f"merge-review job condition {condition!r} does not restrict to "
        f"pull_request events. The script needs a PR number; running on "
        f"push events would infrastructure-error."
    )
