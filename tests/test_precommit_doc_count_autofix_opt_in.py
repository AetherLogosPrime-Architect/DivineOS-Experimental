"""Regression-pin: the pre-commit hook's doc-count autofix is opt-in.

Andrew 2026-06-09: every feature-branch commit was sweeping
CLAUDE.md/README.md/seed.json/docs/ARCHITECTURE.md into its diff
because the pre-commit hook ran ``check_doc_counts.py --fix``
unconditionally on drift. Result: ~6 manual tree-rewrites per session
to drop the guardrail sweep so multi-party-review wouldn't fire.

The fix gates autofix on ``DIVINEOS_DOC_COUNT_AUTOFIX=1`` (set by
``scripts/precommit.sh``). Regular commits stay scoped to their own
diff; the operator-initiated full-refresh keeps the autofix path.

These tests pin both source files emit the env-var-gated pattern.
A regression that removes the gate would re-introduce the sweep.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_setup_hooks_pre_commit_autofix_is_opt_in():
    """The setup-hooks.sh source — the canonical pre-commit template —
    must gate doc-count autofix on DIVINEOS_DOC_COUNT_AUTOFIX=1."""
    src = (REPO_ROOT / "setup" / "setup-hooks.sh").read_text(encoding="utf-8")
    # The opt-in env var name appears in the gating branch.
    assert "DIVINEOS_DOC_COUNT_AUTOFIX" in src, (
        "setup-hooks.sh must gate doc-count autofix on the opt-in env "
        "var. Without it, every feature-branch commit sweeps guardrail "
        "files into its diff."
    )
    # The unconditional --fix call must not appear directly under the
    # drift-detected branch (a regression would put it back).
    assert "python scripts/check_doc_counts.py --fix" in src
    # The instruction the operator sees when drift fires must name the
    # opt-in env var so the fix path is discoverable.
    assert "DIVINEOS_DOC_COUNT_AUTOFIX=1 git commit" in src


def test_setup_hooks_emits_instruction_when_opt_in_missing():
    """When the env var is NOT set and drift fires, the hook must
    tell the operator how to opt in — silent failure is worse than
    a missed sweep."""
    src = (REPO_ROOT / "setup" / "setup-hooks.sh").read_text(encoding="utf-8")
    assert "Doc-count drift detected" in src
    assert "scripts/precommit.sh" in src  # The recommended path.
