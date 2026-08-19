"""Tests for monitor_singleton kernel-mutex primitive.

Pins:
- mutex_name_for_role() canonicalizes role variants to the same name.
- The mutex namespace is Local\\ (per-session), NOT Global\\.
- acquire/is_held round-trip: before acquire, is_held=False; after,
  is_held=True; a second acquire from the same process reports
  was_already_held=True.
- Non-Windows behavior is a clean no-op (None handle, False sibling).
"""

from __future__ import annotations

import os

import pytest

from divineos.core import monitor_singleton


def test_mutex_name_for_role_canonicalizes_variants():
    base = monitor_singleton.mutex_name_for_role("letter")
    assert base == monitor_singleton.mutex_name_for_role("LETTER")
    assert base == monitor_singleton.mutex_name_for_role(" letter ")
    assert base == monitor_singleton.mutex_name_for_role("LETTER-test".split("-")[0])


# === Single-occupancy assumption fix (2026-06-17) ===
# The mutex name now optionally takes an occupant discriminator so two
# parallel substrate-occupants on the same Windows session can each run
# their own monitor of the same role.


def test_occupant_omitted_preserves_legacy_name():
    """Backwards-compat: no occupant means the historical mutex name exactly."""
    legacy = monitor_singleton.mutex_name_for_role("letter")
    new_no_occupant = monitor_singleton.mutex_name_for_role("letter", occupant=None)
    assert legacy == new_no_occupant


def test_occupant_creates_distinct_mutex():
    """Aether's and Aria's mutexes for the same role must be distinct."""
    aether_name = monitor_singleton.mutex_name_for_role("letter", occupant="Aether")
    aria_name = monitor_singleton.mutex_name_for_role("letter", occupant="Aria")
    assert aether_name != aria_name


def test_occupant_distinct_from_no_occupant():
    """An occupant-keyed mutex must not collide with the legacy unkeyed one."""
    legacy = monitor_singleton.mutex_name_for_role("letter")
    keyed = monitor_singleton.mutex_name_for_role("letter", occupant="Aether")
    assert legacy != keyed


def test_occupant_canonicalizes_variants():
    """Occupant case/whitespace variations resolve to the same mutex."""
    base = monitor_singleton.mutex_name_for_role("letter", occupant="Aria")
    assert base == monitor_singleton.mutex_name_for_role("letter", occupant="ARIA")
    assert base == monitor_singleton.mutex_name_for_role("letter", occupant=" aria ")


def test_same_occupant_same_role_same_mutex():
    """Aria's letter mutex is stable across invocations — that's how the
    cross-window dup guard still works within an occupant."""
    a1 = monitor_singleton.mutex_name_for_role("letter", occupant="Aria")
    a2 = monitor_singleton.mutex_name_for_role("letter", occupant="Aria")
    assert a1 == a2


def test_occupant_included_in_mutex_name():
    """For diagnostics, the occupant name should appear in the mutex string."""
    name = monitor_singleton.mutex_name_for_role("letter", occupant="Aria")
    assert "aria" in name.lower()


def test_mutex_name_dashes_and_underscores_collapse():
    assert monitor_singleton.mutex_name_for_role(
        "letter monitor"
    ) == monitor_singleton.mutex_name_for_role("letter_monitor")
    assert monitor_singleton.mutex_name_for_role(
        "letter-monitor"
    ) == monitor_singleton.mutex_name_for_role("letter_monitor")


def test_mutex_namespace_is_local_not_global():
    """Per-session namespace so different Windows users can each run their own."""
    name = monitor_singleton.mutex_name_for_role("letter")
    assert name.startswith("Local\\"), (
        "mutex must be in Local\\ namespace; Global\\ would prevent "
        "per-user instances of the Monitor"
    )
    assert not name.startswith("Global\\")


def test_mutex_name_contains_role():
    assert "letter" in monitor_singleton.mutex_name_for_role("letter")
    assert "compaction" in monitor_singleton.mutex_name_for_role("compaction")


def test_mutex_prefix_namespaces_divineos():
    name = monitor_singleton.mutex_name_for_role("letter")
    assert "divineos_monitor_" in name, (
        "mutex name must namespace divineos_monitor_ so it cannot collide "
        "with unrelated app mutexes"
    )


@pytest.mark.skipif(os.name != "nt", reason="Mutex primitive is Windows-only")
def test_acquire_and_is_held_round_trip():
    """Real kernel mutex round-trip on Windows.

    Uses a randomized role per-test so no two test runs collide on a
    shared kernel object name.
    """
    role = f"test_{os.getpid()}_{id(test_acquire_and_is_held_round_trip)}"
    assert monitor_singleton.is_held(role) is False
    handle, was_held = monitor_singleton.acquire(role)
    try:
        assert was_held is False
        assert monitor_singleton.is_held(role) is True
        # Second acquire from same process must report was_already_held=True
        _, was_held_2 = monitor_singleton.acquire(role)
        assert was_held_2 is True
    finally:
        # Explicitly drop the handles so the mutex is destroyed before
        # the next test runs. (In production we hold it for process
        # lifetime; in tests we want clean teardown.)
        del handle


@pytest.mark.skipif(os.name == "nt", reason="Test for non-Windows fallback")
def test_acquire_noop_on_non_windows():
    handle, was_held = monitor_singleton.acquire("anything")
    assert handle is None
    assert was_held is False
    assert monitor_singleton.is_held("anything") is False


def test_acquire_or_exit_returns_handle_when_no_sibling(monkeypatch: pytest.MonkeyPatch):
    """When no sibling exists, acquire_or_exit returns a handle (does not exit)."""
    role = f"acquire_or_exit_test_{os.getpid()}"
    # On non-Windows the handle is None and that's fine — we just want
    # to verify the function returns rather than exits.
    result = monitor_singleton.acquire_or_exit(role)
    if os.name == "nt":
        assert result is not None
    else:
        assert result is None


def test_acquire_or_exit_calls_sys_exit_when_sibling_held(
    monkeypatch: pytest.MonkeyPatch,
):
    """When a sibling holds the mutex, acquire_or_exit calls sys.exit cleanly."""
    if os.name != "nt":
        pytest.skip("dedup behavior requires real kernel mutex (Windows-only)")
    role = f"sibling_test_{os.getpid()}"
    # First acquire takes the slot
    _h, was_held = monitor_singleton.acquire(role)
    assert was_held is False
    # Second acquire via acquire_or_exit must call sys.exit
    with pytest.raises(SystemExit) as exc_info:
        monitor_singleton.acquire_or_exit(role)
    assert exc_info.value.code == 0
