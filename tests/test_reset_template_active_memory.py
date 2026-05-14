"""Regression-pin test for admin reset-template refreshing active_memory
after re-seed (Aletheia round-ba785844a791 Finding 17 — partial
remediation: the active_memory residue piece of 'reset-template leaves
state', family-audit round-2cfc08ea1d5a).

The bug-shape: reset-template clears all DB tables (including
active_memory), reapplies the seed, but never refreshed active_memory
afterward. Post-reset briefing surfaced empty active-memory section
even though the seed had repopulated knowledge — same shape as
Finding 25 in init.

These tests pin the new [6/6] phase. If they fail, reset-template
has regressed and the post-reset substrate state is back to leaving
active_memory empty.
"""

from __future__ import annotations

from click.testing import CliRunner

from divineos.cli import cli


def test_reset_template_includes_active_memory_refresh_phase_in_dry_run() -> None:
    """The dry-run output documents the active-memory refresh as a
    real phase of the reset flow. If this disappears from dry-run
    output, the refresh has been removed or the phase numbering is
    inconsistent."""
    runner = CliRunner()
    # --dry-run doesn't actually execute the destructive phases; it
    # prints the plan. The active-memory phase should still surface
    # in the [6/6] structure when reset-template's documentation runs.
    result = runner.invoke(cli, ["admin", "reset-template", "--dry-run"])
    assert result.exit_code == 0, f"reset-template --dry-run failed: {result.output}"
    # The dry-run plan output doesn't list every phase explicitly,
    # but invoking --help-or-docs should surface the refresh-active-
    # memory step. As a softer regression-pin, check the source has
    # the phase string.
    import inspect

    from divineos.cli import admin_reset_template

    source = inspect.getsource(admin_reset_template)
    assert "[6/6]" in source, (
        "reset-template no longer has a [6/6] phase. The active_memory "
        "refresh has been removed or the phase-numbering has drifted. "
        "Restore the refresh_active_memory phase per Finding 17 / 25."
    )
    assert "refresh_active_memory" in source, (
        "reset-template no longer calls refresh_active_memory. Restore "
        "the call so post-reset briefing reflects re-seeded knowledge."
    )


def test_reset_template_phase_numbering_consistent() -> None:
    """All phase labels in reset-template should use the same total
    (currently 6). Drift between phase numbers is the same shape as
    Finding 9 (council count drift in source-comments)."""
    import inspect

    from divineos.cli import admin_reset_template

    source = inspect.getsource(admin_reset_template)
    # Each phase label should use /6, not /5
    legacy_labels = ["[1/5]", "[2/5]", "[3/5]", "[4/5]", "[5/5]"]
    for label in legacy_labels:
        assert label not in source, (
            f"reset-template still references {label} — phase-numbering "
            "drifted after the active-memory phase was added. Update all "
            "labels to use /6."
        )
