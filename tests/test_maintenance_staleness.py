"""Regression-pin tests for the maintenance-staleness wiring-gap fix.

Aletheia round-d59eb4570f3f Finding find-49fcfed876ea (WIRING GAP
class): 5 substrate-maintenance commands (admin maintenance,
admin compress, admin knowledge-compress, admin knowledge-hygiene,
admin distill) were built to run automatically but had no
scheduling cadence and no surface flagging when they hadn't run.

Fix:
  1. All 5 added to _HEADLESS_WHITELIST so they CAN run via
     `divineos scheduled run <cmd>`.
  2. _MAINTENANCE_CADENCE declares expected cadence per command
     (daily for hygiene+distill; weekly for the others).
  3. maintenance_staleness() walks SCHEDULED_RUN_END events and
     reports per-command state.
  4. _row_maintenance_staleness surfaces stale commands in the
     briefing with preview lines naming each.

If these tests fail, the wiring-gap fix has regressed and silent
substrate-health degradation is possible again.
"""

from __future__ import annotations

from divineos.core.scheduled_run import (
    _HEADLESS_WHITELIST,
    _MAINTENANCE_CADENCE,
    maintenance_staleness,
)


_EXPECTED_MAINTENANCE_COMMANDS = {
    "admin maintenance",
    "admin compress",
    "admin knowledge-compress",
    "admin knowledge-hygiene",
    "admin distill",
}


def test_all_maintenance_commands_in_headless_whitelist() -> None:
    """LOAD-BEARING: every maintenance command must be in the
    headless whitelist or `divineos scheduled run <cmd>` denies."""
    missing = _EXPECTED_MAINTENANCE_COMMANDS - _HEADLESS_WHITELIST
    assert not missing, (
        f"Maintenance commands missing from _HEADLESS_WHITELIST: "
        f"{sorted(missing)}. They cannot run on cadence without this."
    )


def test_all_maintenance_commands_have_cadence() -> None:
    """LOAD-BEARING: every maintenance command must have a declared
    cadence in _MAINTENANCE_CADENCE or the staleness check has
    no threshold to compare against."""
    missing = _EXPECTED_MAINTENANCE_COMMANDS - set(_MAINTENANCE_CADENCE.keys())
    assert not missing, (
        f"Maintenance commands missing from _MAINTENANCE_CADENCE: "
        f"{sorted(missing)}."
    )


def test_maintenance_staleness_returns_one_entry_per_command() -> None:
    """LOAD-BEARING: maintenance_staleness() reports one dict per
    declared maintenance command."""
    states = maintenance_staleness()
    commands = {s["command"] for s in states}
    assert commands == _EXPECTED_MAINTENANCE_COMMANDS, (
        f"maintenance_staleness() command set drifted from cadence map: "
        f"got {commands}, expected {_EXPECTED_MAINTENANCE_COMMANDS}"
    )


def test_maintenance_staleness_state_has_required_keys() -> None:
    """Each state dict must carry the documented keys."""
    states = maintenance_staleness()
    required = {
        "command",
        "cadence_seconds",
        "last_run_ts",
        "age_seconds",
        "is_stale",
        "last_clean",
    }
    for s in states:
        assert required <= set(s.keys()), (
            f"Maintenance state missing keys: {required - set(s.keys())}"
        )


def test_never_run_commands_report_stale() -> None:
    """A command that has never run is by definition stale."""
    states = maintenance_staleness()
    for s in states:
        if s["last_run_ts"] is None:
            assert s["is_stale"] is True, (
                f"Command {s['command']!r} never ran but is_stale=False"
            )


def test_row_maintenance_staleness_in_briefing_routing() -> None:
    """LOAD-BEARING: the new row function must be wired into
    _ROW_FNS so render_dashboard actually invokes it."""
    from divineos.core.briefing_dashboard import (
        _ROW_FNS,
        _row_maintenance_staleness,
    )

    assert _row_maintenance_staleness in _ROW_FNS, (
        "_row_maintenance_staleness defined but not in _ROW_FNS — "
        "briefing won't render it. Wiring-gap regressed."
    )


def test_row_hides_when_all_maintenance_fresh(monkeypatch) -> None:
    """LOAD-BEARING: when all 5 maintenance commands are fresh and
    clean, the row hides (no noise on quiet days)."""
    import divineos.core.briefing_dashboard as bd
    import divineos.core.scheduled_run as sr
    import time as _time

    now = _time.time()
    fresh_states = [
        {
            "command": cmd,
            "cadence_seconds": cadence,
            "last_run_ts": now - 60,  # ran a minute ago
            "age_seconds": 60,
            "is_stale": False,
            "last_clean": True,
        }
        for cmd, cadence in sr._MAINTENANCE_CADENCE.items()
    ]
    monkeypatch.setattr(sr, "maintenance_staleness", lambda: fresh_states)
    row = bd._row_maintenance_staleness()
    assert row is None, (
        "Maintenance row surfaced when all commands fresh — "
        "should be silent on clean state."
    )


def test_row_surfaces_when_any_stale(monkeypatch) -> None:
    """LOAD-BEARING: when any maintenance command is stale, the row
    surfaces with preview lines naming the stale ones."""
    import divineos.core.briefing_dashboard as bd
    import divineos.core.scheduled_run as sr

    mixed_states = [
        {
            "command": "admin maintenance",
            "cadence_seconds": 7 * 24 * 3600,
            "last_run_ts": None,
            "age_seconds": None,
            "is_stale": True,
            "last_clean": None,
        },
        {
            "command": "admin distill",
            "cadence_seconds": 24 * 3600,
            "last_run_ts": 100.0,
            "age_seconds": 3 * 24 * 3600,
            "is_stale": True,
            "last_clean": False,
        },
        {
            "command": "admin compress",
            "cadence_seconds": 7 * 24 * 3600,
            "last_run_ts": 200.0,
            "age_seconds": 60,
            "is_stale": False,
            "last_clean": True,
        },
    ]
    monkeypatch.setattr(sr, "maintenance_staleness", lambda: mixed_states)
    row = bd._row_maintenance_staleness()
    assert row is not None
    assert row.area == "Maintenance"
    assert row.stale_count == 2  # never-run + stale-by-cadence
    # Never-run should appear FIRST in preview.
    assert row.preview[0].startswith("[never-run]")
    assert "admin maintenance" in row.preview[0]
    # The failed-clean state must be tagged.
    failed_lines = [p for p in row.preview if "[failed]" in p]
    assert failed_lines, "Failed-run state was not tagged in preview."
