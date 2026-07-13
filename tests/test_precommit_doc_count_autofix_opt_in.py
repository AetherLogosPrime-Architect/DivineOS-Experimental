"""Regression-pin: the pre-commit hook's doc-count autofix is DEFAULT-ON
with an opt-OUT env var (Andrew 2026-06-12, PR #161).

History — the 2026-06-09 opt-in design was a valid response to cross-
branch rebase conflicts on the count line: every branch auto-bumped
to slightly different numbers, then collided on rebase. But it cost
the operator a manual ``--fix`` step on every commit and bit during
the 2026-06-12 structural-fix session.

The better fix landed as monotonic-only-raise inside
``check_doc_counts.py``: two branches with different higher counts no
longer conflict because the lower-count branch becomes a no-op once
main has the higher count. With monotonic auto-fix safe, default-ON
removes the "remember to opt in" tax that Andrew 2026-06-10 PR-marathon
teaching called out as the wrong structural shape (
"auto-generate or remove, not always run").

These tests now pin the NEW shape:
- The opt-OUT env var name ``DIVINEOS_DOC_COUNT_NO_AUTOFIX`` appears.
- The ``--fix`` call IS unconditional under drift detection (because
  the gate is now default-on; the env var only suppresses the call).
- A regression that restores ``DIVINEOS_DOC_COUNT_AUTOFIX`` (the
  prior opt-in name) would re-introduce the manual-step tax this PR
  closed; the test flags it as a name-collision regression.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_setup_hooks_pre_commit_autofix_is_default_on() -> None:
    """The setup-hooks.sh source — the canonical pre-commit template —
    must use the opt-OUT env var DIVINEOS_DOC_COUNT_NO_AUTOFIX (not the
    old opt-IN DIVINEOS_DOC_COUNT_AUTOFIX). The old name is a regression
    flag — its presence means someone restored the manual-step tax."""
    src = (REPO_ROOT / "setup" / "setup-hooks.sh").read_text(encoding="utf-8")
    # The new opt-OUT env var name must be present.
    assert "DIVINEOS_DOC_COUNT_NO_AUTOFIX" in src, (
        "setup-hooks.sh must reference the opt-OUT env var "
        "DIVINEOS_DOC_COUNT_NO_AUTOFIX. Without it the operator has no "
        "way to suppress auto-fix on the rare case they want to "
        "investigate drift manually."
    )
    # The OLD opt-in name must NOT be present (would mean a regression
    # restored the manual-step tax).
    assert "DIVINEOS_DOC_COUNT_AUTOFIX" not in src, (
        "setup-hooks.sh contains DIVINEOS_DOC_COUNT_AUTOFIX, the old "
        "opt-in env var. PR #161 replaced it with the opt-OUT "
        "DIVINEOS_DOC_COUNT_NO_AUTOFIX. If you restored it, you "
        "re-introduced the every-commit manual-fix tax."
    )
    # The --fix call must still be present.
    assert "python scripts/check_doc_counts.py --fix" in src, (
        "setup-hooks.sh no longer contains the --fix call — auto-fix "
        "doesn't run, the discipline regresses to manual-only."
    )


def test_setup_hooks_names_opt_out_path_when_drift_fires() -> None:
    """When drift fires the hook must name the opt-out path so the
    operator knows how to suppress auto-fix."""
    src = (REPO_ROOT / "setup" / "setup-hooks.sh").read_text(encoding="utf-8")
    assert "Auto-fix suppressed via DIVINEOS_DOC_COUNT_NO_AUTOFIX" in src, (
        "setup-hooks.sh must surface the opt-out path to the operator "
        "so suppressed runs are discoverable."
    )
    # The drift-detection diagnostic stays.
    assert "Doc-count drift detected" in src
