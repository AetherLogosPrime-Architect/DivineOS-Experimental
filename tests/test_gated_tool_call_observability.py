"""The rudder-failure detector could never fire. These pin that it can.

THE DEFECT (2026-08-01). `_count_gated_tool_calls` queried `system_events`
for TOOL_CALL rows. The tool wrapper stopped writing there on 2026-05-05 —
its own migration note says "the wrapper writes to `tool_logbook` instead of
`system_events`" — and this reader was never updated.

Measured on the live substrate:
    system_events TOOL_CALL rows : 0
    tool_logbook  TOOL_CALL rows : 1176

That constant 0 fell through the `gated_activity < threshold` guard and
returned early on every call, so `rudder_infrastructure_failure` — whose
only job is noticing the rudder has died — was structurally unable to fire
for three months. `detect_uncalibrated_baselines` sits behind the same value.

WHY THE OBVIOUS FIX WAS NOT ENOUGH. Repointing at the right table still
returns 0 today, because `Agent` and `Task` appear nowhere in tool_logbook's
1201 rows. That zero is honest — those tools were not called — but it was
INDISTINGUISHABLE from the blindness above. Both produced the same silence.
So the counter now returns (gated, total) and the caller reports blindness
loudly instead of quietly returning nothing.
"""

from __future__ import annotations

import sqlite3
import time

import pytest

from divineos.core import compliance_audit as ca


@pytest.fixture
def logbook(tmp_path, monkeypatch):
    """Isolated tool_logbook + a controllable rudder-event stream."""
    db = tmp_path / "logbook.db"

    def _conn():
        c = sqlite3.connect(str(db))
        c.execute("""
            CREATE TABLE IF NOT EXISTS tool_logbook (
                log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   REAL NOT NULL,
                event_type  TEXT NOT NULL,
                tool_name   TEXT,
                payload     TEXT
            )
        """)
        c.commit()
        return c

    monkeypatch.setattr("divineos.core.ledger.get_connection", _conn)
    return _conn


def _add_call(conn_factory, tool_name: str, *, age_hours: float = 1.0) -> None:
    c = conn_factory()
    c.execute(
        "INSERT INTO tool_logbook (timestamp, event_type, tool_name) VALUES (?, ?, ?)",
        (time.time() - age_hours * 3600, "TOOL_CALL", tool_name),
    )
    c.commit()
    c.close()


def _no_rudder_events(monkeypatch) -> None:
    """Rudder emitted nothing — the gate-dead condition."""
    monkeypatch.setattr("divineos.core.ledger.get_events", lambda **kw: [])


def test_counter_reads_tool_logbook_not_system_events(logbook, monkeypatch):
    """The core repointing. Rows written where the wrapper actually writes
    must be counted."""
    monkeypatch.setattr("divineos.core.compass_rudder.GATED_TOOL_NAMES", {"Agent", "Task"})
    _add_call(logbook, "Agent")
    _add_call(logbook, "Agent")
    _add_call(logbook, "Bash")

    gated, total = ca._count_tool_calls_split(time.time() - 86400)
    assert gated == 2, "both Agent calls must be seen"
    assert total == 3, "all TOOL_CALL rows must be counted for observability"


def test_rudder_infrastructure_failure_can_now_fire(logbook, monkeypatch):
    """THE POINT. Active gated session + zero rudder events must produce the
    anomaly. Before the fix the count was always 0, so this path was
    unreachable no matter what the rudder did."""
    monkeypatch.setattr("divineos.core.compass_rudder.GATED_TOOL_NAMES", {"Agent", "Task"})
    for _ in range(20):
        _add_call(logbook, "Agent")
    _no_rudder_events(monkeypatch)

    anomalies = ca._detect_block_allow_anomalies(86400, None)
    names = [a.name for a in anomalies]
    assert "rudder_infrastructure_failure" in names, (
        "the detector whose job is noticing a dead rudder must be able to fire"
    )


def test_blindness_is_reported_when_it_contradicts_rudder_activity(logbook, monkeypatch):
    """Rudder events prove work ran; zero recorded tool calls says none did.
    Both cannot be true, so the recording path is broken and that must be
    loud. Silence on this contradiction is what hid the defect."""
    monkeypatch.setattr("divineos.core.compass_rudder.GATED_TOOL_NAMES", {"Agent", "Task"})
    fires = [{"timestamp": time.time(), "payload": {}} for _ in range(5)]
    monkeypatch.setattr(
        "divineos.core.ledger.get_events",
        lambda **kw: fires if kw.get("event_type") == "COMPASS_RUDDER_FIRED" else [],
    )

    anomalies = ca._detect_block_allow_anomalies(86400, None)
    names = [a.name for a in anomalies]
    assert "tool_call_observability_lost" in names
    assert "rudder_infrastructure_failure" not in names, (
        "must not claim the rudder is dead when we cannot see whether it ran"
    )


def test_empty_machine_does_not_false_alarm(logbook, monkeypatch):
    """A fresh install has no tool calls and no rudder events. Absence is
    not contradiction. A first pass fired here and turned 13 existing tests
    red — an alarm on an empty machine is a false-alarm generator, which is
    what this whole audit exists to remove."""
    monkeypatch.setattr("divineos.core.compass_rudder.GATED_TOOL_NAMES", {"Agent", "Task"})
    _no_rudder_events(monkeypatch)

    anomalies = ca._detect_block_allow_anomalies(86400, None)
    assert anomalies == [], "nothing has happened yet; that is not a defect"


def test_quiet_session_stays_silent(logbook, monkeypatch):
    """The other direction. Real traffic with no gated calls is a genuine
    quiet session — visible, and correctly not an anomaly. A fix that
    reported here would just be a new false alarm."""
    monkeypatch.setattr("divineos.core.compass_rudder.GATED_TOOL_NAMES", {"Agent", "Task"})
    for _ in range(50):
        _add_call(logbook, "Bash")
    _no_rudder_events(monkeypatch)

    anomalies = ca._detect_block_allow_anomalies(86400, None)
    assert anomalies == [], "traffic without gated calls is quiet, not broken"


def test_window_is_respected(logbook, monkeypatch):
    """Old calls outside the window must not count as current activity."""
    monkeypatch.setattr("divineos.core.compass_rudder.GATED_TOOL_NAMES", {"Agent", "Task"})
    _add_call(logbook, "Agent", age_hours=500)

    gated, total = ca._count_tool_calls_split(time.time() - 86400)
    assert (gated, total) == (0, 0)


def test_back_compat_wrapper_still_returns_gated_count(logbook, monkeypatch):
    """Existing callers of the single-value function keep working."""
    monkeypatch.setattr("divineos.core.compass_rudder.GATED_TOOL_NAMES", {"Agent", "Task"})
    _add_call(logbook, "Task")
    assert ca._count_gated_tool_calls(time.time() - 86400) == 1
