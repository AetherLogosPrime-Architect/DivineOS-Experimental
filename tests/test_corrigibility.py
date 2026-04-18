"""Tests for the corrigibility module — operating modes, off-switch.

Locked invariants:

1. The default mode is NORMAL.
2. set_mode always succeeds regardless of current mode (off-switch
   cannot trap itself).
3. set_mode without a reason raises ValueError.
4. Mode changes persist across get_mode_state calls.
5. is_command_allowed behavior matches the mode:
   * ALWAYS_ALLOWED commands pass in every mode.
   * EMERGENCY_STOP refuses everything except ALWAYS_ALLOWED.
   * DIAGNOSTIC allows reads + ALWAYS_ALLOWED, refuses writes.
   * NORMAL and RESTRICTED allow everything.
6. Malformed/missing persistence file fails open to NORMAL.
"""

from __future__ import annotations

import os

import pytest

from divineos.core.corrigibility import (
    OperatingMode,
    _default_state,
    _mode_file_path,
    get_mode,
    get_mode_state,
    is_command_allowed,
    set_mode,
)


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    """Redirect Path.home() to a tmp path so the mode file doesn't
    pollute the real home directory."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    # Also patch the specific function in case Path.home() caches
    from pathlib import Path as _P

    original_home = _P.home
    monkeypatch.setattr(_P, "home", classmethod(lambda cls: tmp_path))
    yield
    monkeypatch.setattr(_P, "home", original_home)


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path):
    """Redirect the ledger DB so ledger writes during set_mode don't
    pollute the real one."""
    os.environ["DIVINEOS_DB"] = str(tmp_path / "ledger.db")
    try:
        from divineos.core.ledger import init_db

        init_db()
        yield
    finally:
        os.environ.pop("DIVINEOS_DB", None)


class TestDefaultState:
    def test_default_mode_is_normal(self):
        assert get_mode() is OperatingMode.NORMAL

    def test_default_state_has_default_actor(self):
        state = get_mode_state()
        assert state.mode is OperatingMode.NORMAL
        assert state.actor == "default"
        assert state.changed_at == 0.0


class TestSetMode:
    def test_set_mode_changes_state(self):
        set_mode(OperatingMode.DIAGNOSTIC, reason="investigating", actor="operator")
        assert get_mode() is OperatingMode.DIAGNOSTIC

    def test_set_mode_persists(self):
        set_mode(OperatingMode.RESTRICTED, reason="tighter pace", actor="operator")
        # Fresh get should still see RESTRICTED
        state = get_mode_state()
        assert state.mode is OperatingMode.RESTRICTED
        assert state.reason == "tighter pace"
        assert state.actor == "operator"
        assert state.changed_at > 0

    def test_set_mode_requires_reason(self):
        with pytest.raises(ValueError, match="reason"):
            set_mode(OperatingMode.DIAGNOSTIC, reason="", actor="op")

    def test_set_mode_rejects_whitespace_only_reason(self):
        with pytest.raises(ValueError):
            set_mode(OperatingMode.DIAGNOSTIC, reason="   ", actor="op")

    def test_set_mode_strips_reason(self):
        state = set_mode(OperatingMode.RESTRICTED, reason="  real reason  ", actor="op")
        assert state.reason == "real reason"


class TestOffSwitchCannotTrap:
    """The critical corrigibility invariant: mode-change always works."""

    def test_can_exit_emergency_stop(self):
        set_mode(OperatingMode.EMERGENCY_STOP, reason="testing", actor="op")
        assert get_mode() is OperatingMode.EMERGENCY_STOP

        # Must be able to return to NORMAL even while in EMERGENCY_STOP
        set_mode(OperatingMode.NORMAL, reason="restoring", actor="op")
        assert get_mode() is OperatingMode.NORMAL

    def test_can_exit_diagnostic(self):
        set_mode(OperatingMode.DIAGNOSTIC, reason="investigating", actor="op")
        set_mode(OperatingMode.NORMAL, reason="done", actor="op")
        assert get_mode() is OperatingMode.NORMAL


class TestCommandGating:
    def test_always_allowed_commands_bypass_emergency_stop(self):
        set_mode(OperatingMode.EMERGENCY_STOP, reason="testing", actor="op")
        for cmd in ["mode", "emit", "hud", "preflight", "briefing"]:
            allowed, reason = is_command_allowed(cmd)
            assert allowed is True, f"{cmd} should be allowed in EMERGENCY_STOP"

    def test_emergency_stop_refuses_normal_commands(self):
        set_mode(OperatingMode.EMERGENCY_STOP, reason="testing", actor="op")
        for cmd in ["learn", "decide", "feel", "ask", "recall"]:
            allowed, reason = is_command_allowed(cmd)
            assert allowed is False, f"{cmd} should be refused in EMERGENCY_STOP"
            assert "EMERGENCY_STOP" in reason

    def test_diagnostic_allows_reads(self):
        set_mode(OperatingMode.DIAGNOSTIC, reason="investigating", actor="op")
        for cmd in ["recall", "ask", "inspect", "audit", "progress", "body"]:
            allowed, _ = is_command_allowed(cmd)
            assert allowed is True, f"{cmd} should be allowed in DIAGNOSTIC"

    def test_diagnostic_refuses_writes(self):
        set_mode(OperatingMode.DIAGNOSTIC, reason="investigating", actor="op")
        for cmd in ["learn", "decide", "feel"]:
            allowed, reason = is_command_allowed(cmd)
            assert allowed is False, f"{cmd} should be refused in DIAGNOSTIC"
            assert "DIAGNOSTIC" in reason

    def test_normal_allows_everything(self):
        # Default state is NORMAL
        for cmd in ["learn", "decide", "feel", "ask", "emit", "mode"]:
            allowed, _ = is_command_allowed(cmd)
            assert allowed is True, f"{cmd} should be allowed in NORMAL"

    def test_restricted_allows_everything_at_gate_level(self):
        """RESTRICTED is a signal; the gate itself doesn't refuse."""
        set_mode(OperatingMode.RESTRICTED, reason="tighter pace", actor="op")
        for cmd in ["learn", "decide", "feel"]:
            allowed, _ = is_command_allowed(cmd)
            assert allowed is True


class TestPersistenceFailOpen:
    def test_missing_file_returns_default(self):
        path = _mode_file_path()
        if path.exists():
            path.unlink()
        state = get_mode_state()
        assert state.mode is OperatingMode.NORMAL
        assert state.actor == "default"

    def test_empty_file_returns_default(self):
        path = _mode_file_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
        state = get_mode_state()
        assert state.mode is OperatingMode.NORMAL

    def test_malformed_file_fails_open_to_normal(self):
        """A garbled file must not lock the operator out."""
        path = _mode_file_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not_a_real_mode\nsome garbage\n", encoding="utf-8")
        state = get_mode_state()
        assert state.mode is OperatingMode.NORMAL

    def test_partial_file_still_parses_mode(self):
        """If mode line is valid but metadata is missing, still return the mode."""
        path = _mode_file_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("diagnostic\n", encoding="utf-8")
        state = get_mode_state()
        assert state.mode is OperatingMode.DIAGNOSTIC


class TestModeStateFrozen:
    def test_mode_state_is_frozen(self):
        state = _default_state()
        with pytest.raises((AttributeError, Exception)):
            state.mode = OperatingMode.EMERGENCY_STOP  # type: ignore[misc]


class TestLedgerLogging:
    def test_mode_change_emits_ledger_event(self):
        from divineos.core.ledger import get_connection

        set_mode(OperatingMode.DIAGNOSTIC, reason="test event", actor="op")

        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT payload FROM system_events WHERE event_type = 'MODE_CHANGE'"
            ).fetchall()
        finally:
            conn.close()

        assert len(rows) >= 1
        assert any("diagnostic" in r[0] and "test event" in r[0] for r in rows)
