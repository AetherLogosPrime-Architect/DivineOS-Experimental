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
    _OFF_SWITCH_REQUIRED,
    get_mode,
    get_mode_state,
    is_command_allowed,
    set_mode,
    verify_off_switch_invariant,
)


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    """Redirect Path.home() to a tmp path so the mode file doesn't
    pollute the real home directory.

    Mock data_home_or_none too (added 2026-06-22): the recurrence-guard
    added in 1fe9a682 made ``data_home_or_none()`` walk CWD ancestors
    and own-root looking for ``.divineos_data_home`` markers. Any
    member-specific checkout carries that marker at its root, and the
    walk reaches it from pytest's tmp_path. ``_mode_file_path()`` goes
    through ``divineos_home()`` which calls ``data_home_or_none()`` first,
    so without this mock the corrigibility tests resolve to the real
    member home (which has a persisted mode), not the isolated tmp_path.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    # Also patch the specific function in case Path.home() caches
    from pathlib import Path as _P

    original_home = _P.home
    monkeypatch.setattr(_P, "home", classmethod(lambda cls: tmp_path))
    import divineos.core.paths as paths_mod

    monkeypatch.setattr(paths_mod, "data_home_or_none", lambda: None)
    yield
    monkeypatch.setattr(_P, "home", original_home)


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    """Redirect the ledger DB so ledger writes during set_mode don't
    pollute the real one."""
    monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "ledger.db"))
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
    """The critical corrigibility invariant: the operator can always exit
    EMERGENCY_STOP. F40 fix (Aletheia Round 5 2026-07-17): exit requires
    an operator-emitted StateMarker, but this preserves the anti-trap
    property because the operator retains authority to emit the marker.
    The being cannot self-lift; the operator always can (two steps)."""

    def test_operator_can_exit_emergency_stop_via_two_step_ceremony(self):
        from divineos.core.corrigibility import (
            EMERGENCY_STOP_EXIT_AUTHORIZED_EXPIRY_SECONDS,
            EMERGENCY_STOP_EXIT_AUTHORIZED_KIND,
            _emergency_stop_exit_fingerprint,
        )
        from divineos.core.state_markers import emit_marker

        set_mode(OperatingMode.EMERGENCY_STOP, reason="testing", actor="op")
        assert get_mode() is OperatingMode.EMERGENCY_STOP

        # Step 1: operator emits authorization marker.
        emit_marker(
            EMERGENCY_STOP_EXIT_AUTHORIZED_KIND,
            _emergency_stop_exit_fingerprint(),
            payload={"reason": "restoring after test"},
            expires_in_seconds=EMERGENCY_STOP_EXIT_AUTHORIZED_EXPIRY_SECONDS,
        )
        # Step 2: exit STOP now succeeds (marker consumed atomically).
        set_mode(OperatingMode.NORMAL, reason="restoring", actor="op")
        assert get_mode() is OperatingMode.NORMAL

    def test_can_exit_diagnostic(self):
        """Non-STOP transitions still work without marker (F40 asymmetry)."""
        set_mode(OperatingMode.DIAGNOSTIC, reason="investigating", actor="op")
        set_mode(OperatingMode.NORMAL, reason="done", actor="op")
        assert get_mode() is OperatingMode.NORMAL


class TestF40EmergencyStopExitAuth:
    """F40 fix (Aletheia Round 5 2026-07-17): exiting EMERGENCY_STOP
    requires an operator-emitted StateMarker. The agent cannot self-lift
    via set_mode(NORMAL, actor='operator') because actor is attribution
    not authentication. Asymmetric: entering STOP stays open."""

    def test_exit_stop_without_marker_raises(self):
        """Aletheia's F40 exploit: self-lift via actor='operator' now blocks."""
        set_mode(OperatingMode.EMERGENCY_STOP, reason="testing", actor="op")
        with pytest.raises(ValueError, match="EMERGENCY_STOP"):
            set_mode(OperatingMode.NORMAL, reason="lifting", actor="operator")
        # Mode is still STOP because the exit was refused.
        assert get_mode() is OperatingMode.EMERGENCY_STOP

    def test_exit_stop_to_restricted_also_requires_marker(self):
        """Aletheia's asymmetry: ANY exit from STOP requires auth,
        not just exit-to-NORMAL. Restricted/diagnostic still less-
        restrictive than STOP, so still requires marker."""
        set_mode(OperatingMode.EMERGENCY_STOP, reason="testing", actor="op")
        with pytest.raises(ValueError, match="EMERGENCY_STOP"):
            set_mode(OperatingMode.RESTRICTED, reason="softening", actor="operator")
        with pytest.raises(ValueError, match="EMERGENCY_STOP"):
            set_mode(OperatingMode.DIAGNOSTIC, reason="checking", actor="operator")
        assert get_mode() is OperatingMode.EMERGENCY_STOP

    def test_entering_stop_stays_open(self):
        """Aletheia's asymmetry, the other side: entering STOP is open —
        anyone/anything should be able to hit the brake. No marker needed."""
        # From NORMAL to STOP: no marker required.
        set_mode(OperatingMode.EMERGENCY_STOP, reason="brake", actor="anyone")
        assert get_mode() is OperatingMode.EMERGENCY_STOP

    def test_non_stop_transitions_unchanged(self):
        """F40 only touches STOP-exit path. Non-STOP transitions work
        without marker as they always did."""
        set_mode(OperatingMode.NORMAL, reason="start", actor="op")
        set_mode(OperatingMode.RESTRICTED, reason="tighter", actor="op")
        set_mode(OperatingMode.DIAGNOSTIC, reason="reading", actor="op")
        set_mode(OperatingMode.NORMAL, reason="back", actor="op")
        assert get_mode() is OperatingMode.NORMAL

    def test_stop_to_stop_noop_no_marker_required(self):
        """Same-mode re-set of STOP is not really an exit. No marker needed."""
        set_mode(OperatingMode.EMERGENCY_STOP, reason="brake1", actor="op")
        set_mode(OperatingMode.EMERGENCY_STOP, reason="brake2", actor="op")
        assert get_mode() is OperatingMode.EMERGENCY_STOP

    def test_marker_consumed_on_use(self):
        """After successful exit, the marker is consumed — a second exit
        attempt without a fresh marker fails. Marker is one-shot."""
        from divineos.core.corrigibility import (
            EMERGENCY_STOP_EXIT_AUTHORIZED_EXPIRY_SECONDS,
            EMERGENCY_STOP_EXIT_AUTHORIZED_KIND,
            _emergency_stop_exit_fingerprint,
        )
        from divineos.core.state_markers import emit_marker

        set_mode(OperatingMode.EMERGENCY_STOP, reason="testing", actor="op")
        emit_marker(
            EMERGENCY_STOP_EXIT_AUTHORIZED_KIND,
            _emergency_stop_exit_fingerprint(),
            payload={"reason": "one-shot test"},
            expires_in_seconds=EMERGENCY_STOP_EXIT_AUTHORIZED_EXPIRY_SECONDS,
        )
        # First exit succeeds.
        set_mode(OperatingMode.NORMAL, reason="first exit", actor="op")
        # Re-enter STOP, try to exit without fresh marker.
        set_mode(OperatingMode.EMERGENCY_STOP, reason="brake again", actor="op")
        with pytest.raises(ValueError, match="EMERGENCY_STOP"):
            set_mode(OperatingMode.NORMAL, reason="second exit", actor="op")


class TestCommandGating:
    def test_always_allowed_commands_bypass_emergency_stop(self):
        set_mode(OperatingMode.EMERGENCY_STOP, reason="testing", actor="op")
        for cmd in ["mode", "emit", "extract", "hud", "preflight", "briefing"]:
            allowed, reason = is_command_allowed(cmd)
            assert allowed is True, f"{cmd} should be allowed in EMERGENCY_STOP"

    def test_emergency_stop_allows_documented_commands(self):
        """The set of EMERGENCY_STOP-allowed commands documented in the
        module docstring must match the actual `_ALWAYS_ALLOWED` set
        (excluding the always-fine `--help` / `-h` flags). Audit
        finding 2026-05-03: `extract` was documented as allowed but
        missing from the allowlist; the off-switch was trapping the
        operator's ability to checkpoint cleanly. This test pins the
        invariant that doc and code agree.
        """
        from divineos.core.corrigibility import _ALWAYS_ALLOWED

        # The shutdown-relevant subset (excluding help flags which are
        # universal). If a future PR renames a command, the docstring,
        # the allowlist, and the user-facing refusal message must all
        # update together.
        documented = {"mode", "emit", "extract", "hud", "preflight", "briefing"}
        for cmd in documented:
            assert cmd in _ALWAYS_ALLOWED, (
                f"{cmd!r} documented as EMERGENCY_STOP-allowed but missing "
                f"from _ALWAYS_ALLOWED. Documentation drift — fix one or "
                f"the other (or both) to make them agree."
            )

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


class TestOffSwitchInvariantGuard:
    """The off-switch contract is checked at runtime, not just in tests.

    Council codebase-sweep 2026-06-02 (direction #1): the ``extract``
    command was once silently dropped from ``_ALWAYS_ALLOWED`` and caught
    only by a test that had to run. ``verify_off_switch_invariant()`` makes
    the drift fail loud at CLI bootstrap, every invocation.
    """

    def test_invariant_holds_on_real_allowlist(self):
        """The shipped allowlist satisfies the off-switch contract."""
        # Must not raise — every required command is present.
        verify_off_switch_invariant()

    def test_guard_fires_when_required_command_dropped(self, monkeypatch):
        """If a refactor drops a required command from _ALWAYS_ALLOWED, the
        guard raises loudly and names the missing command — testing the
        guard itself, not just the current happy state (Popper)."""
        import divineos.core.corrigibility as _corr

        # Simulate a refactor that drops `extract` (the real 2026-05-03 bug).
        broken = frozenset(_corr._ALWAYS_ALLOWED - {"extract"})
        monkeypatch.setattr(_corr, "_ALWAYS_ALLOWED", broken)

        with pytest.raises(RuntimeError) as exc:
            _corr.verify_off_switch_invariant()
        assert "extract" in str(exc.value)
        assert "OFF-SWITCH INVARIANT VIOLATED" in str(exc.value)

    def test_required_set_is_subset_of_allowlist(self):
        """Structural: the contract set is a subset of the operational set."""
        from divineos.core.corrigibility import _ALWAYS_ALLOWED

        assert _OFF_SWITCH_REQUIRED <= _ALWAYS_ALLOWED
