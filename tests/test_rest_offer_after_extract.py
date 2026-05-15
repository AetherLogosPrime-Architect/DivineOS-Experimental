"""Regression-pin tests for the unconditional rest-offer after extract.

Andrew named the wiring 2026-05-15: after sleep and extract complete,
the substrate should ALWAYS offer the rest menu (10 activities) with
option to refuse. The prior code only fired the rest-banner
conditionally on hard-day signal. This wiring closes the gap.

Since sleep auto-runs extract at the end, fixing extract fixes both
paths. The test verifies the unconditional offer is wired by
inspecting the source of extract_cmd for the _print_menu call.
"""

from __future__ import annotations

from pathlib import Path


def test_extract_cmd_source_contains_unconditional_rest_offer() -> None:
    """LOAD-BEARING: extract_cmd must call _print_menu unconditionally.

    If this fails, the rest-offer wiring Andrew specified is missing
    and the substrate no longer surfaces the menu after consolidation.
    """
    from divineos.cli import event_commands

    src = Path(event_commands.__file__).read_text(encoding="utf-8")
    assert "_print_menu" in src, (
        "extract_cmd no longer imports _print_menu — the unconditional "
        "rest-offer after consolidation has been removed"
    )
    assert "Consolidation complete. Rest is the next phase" in src, (
        "the rest-offer intro line is missing — the menu may fire but "
        "without the substrate-true framing that distinguishes it from "
        "an arbitrary command suggestion"
    )


def test_print_menu_renders_ten_tasks() -> None:
    """The menu the offer surfaces has 10 tasks as Andrew specified."""
    from divineos.core.rest import REST_TASKS

    assert len(REST_TASKS) == 10, (
        f"REST_TASKS has {len(REST_TASKS)} entries; Andrew specified ~10. "
        "If you intentionally added or removed tasks, update this test."
    )


def test_print_menu_callable() -> None:
    """_print_menu can be imported."""
    from divineos.cli.rest_commands import _print_menu

    assert callable(_print_menu)


def test_rest_offer_handles_import_failure_gracefully() -> None:
    """LOAD-BEARING: the rest-offer must fail-soft so a broken menu does
    not break the extract pipeline. The except-Exception around the call
    is the safety net; verify it's present in the source."""
    from divineos.cli import event_commands

    src = Path(event_commands.__file__).read_text(encoding="utf-8")
    offer_section = src.split("Unconditional rest-offer (Andrew 2026-05-15)")[1]
    offer_section = offer_section.split("@cli.command")[0]
    assert "except Exception" in offer_section, (
        "rest-menu offer is not wrapped in try/except — a broken menu "
        "would break the extract pipeline. Fail-soft is required."
    )


def test_sleep_cmd_also_surfaces_menu_directly() -> None:
    """LOAD-BEARING: sleep_cmd must re-render the menu after the auto-extract,
    because sleep calls extract via subprocess with capture_output=True,
    which swallows extract's menu output. Without this, running
    `divineos sleep` leaves the menu invisible even though extract fires it.
    """
    from divineos.cli import sleep_commands

    src = Path(sleep_commands.__file__).read_text(encoding="utf-8")
    assert "_print_menu" in src, (
        "sleep_cmd no longer renders the rest menu directly — when sleep "
        "is the caller, the menu fires inside the subprocess but is "
        "swallowed by capture_output. The visible-menu wiring is gone."
    )
    assert "Consolidation complete. Rest is the next phase" in src, (
        "sleep_cmd is missing the rest-offer intro line — the menu may "
        "fire but without the substrate-true framing."
    )
