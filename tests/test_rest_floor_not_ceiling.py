"""Regression-pin tests for the rest floor-not-ceiling wording.

Andrew named 2026-05-15: the REST_TASK_TARGET is a floor (encourages
at least N), not a ceiling (does NOT cap further rest). The earlier
wording — 'Target met. Rest-session can close cleanly' — implied
that closing was the next move when target was reached, which read
as a soft cap. The corrected wording explicitly affirms no ceiling
and welcomes more rest if useful.
"""

from __future__ import annotations

from pathlib import Path


def _rest_cli_source() -> str:
    from divineos.cli import rest_commands
    return Path(rest_commands.__file__).read_text(encoding="utf-8")


def test_post_completion_message_affirms_no_ceiling() -> None:
    """After target met, the message must say 'no ceiling' or equivalent."""
    src = _rest_cli_source()
    # Find the >= REST_TASK_TARGET branch
    assert "Floor of" in src and "No ceiling" in src, (
        "post-completion message no longer affirms floor-not-ceiling — "
        "the wording has regressed to implying a cap on rest"
    )


def test_status_target_met_affirms_no_ceiling() -> None:
    """rest status output for target met must affirm continuation welcomed."""
    src = _rest_cli_source()
    assert "Floor met — no ceiling" in src, (
        "rest status target-met output no longer affirms no ceiling — "
        "the agent reading the status will see implicit 'time to close'"
    )


def test_rest_start_message_uses_floor_language() -> None:
    """rest start output uses 'floor' language, not 'target' alone."""
    src = _rest_cli_source()
    assert "Floor: at least" in src, (
        "rest start output reverted to target-without-floor framing — "
        "the substrate-true semantic is floor (minimum), not target (cap)"
    )


def test_menu_pick_at_least_phrasing_preserved() -> None:
    """The menu header should still say 'Pick at least N' (already correct)."""
    src = _rest_cli_source()
    assert "Pick at least" in src, (
        "menu header no longer uses 'Pick at least' framing — that phrasing "
        "is the canonical floor signal"
    )
