"""The runway meter must count down to the point where the ritual actually fires.

Until 2026-09-22 ``divineos context-heartbeat`` computed its fire point from a
literal 0.92 while the ritual itself fired at ``auto_cycle.TRIGGER_THRESHOLD``
(0.88 since 2026-09-18). So between 880k and 920k the meter printed a positive
"N to go" after the ritual had already fired -- overstating the runway by
40,000 tokens, during exactly the stretch Andrew was reporting that the ritual
fires too late.

These tests drive the real command with a real reading placed in that band.
They were run against the unfixed line first and failed there; a test that has
only ever passed has not yet shown it can see the fault.
"""

from __future__ import annotations

import time

from click.testing import CliRunner

from divineos.cli import cli
from divineos.core import context_heartbeat as ch
from divineos.core.auto_cycle import TRIGGER_THRESHOLD


def _beat_at(total: int) -> ch.Beat:
    return ch.Beat(seen=True, ts=time.time(), total_tokens=total, session_id="probe", note="")


def _run_meter(monkeypatch, total: int) -> str:
    monkeypatch.setattr(ch, "read_latest", lambda: _beat_at(total))
    result = CliRunner().invoke(cli, ["context-heartbeat"])
    assert result.exit_code == 0, result.output
    return result.output


def test_meter_fire_point_is_the_ritual_trigger(monkeypatch):
    fire_at = int(ch.CONTEXT_WINDOW_TOKENS * TRIGGER_THRESHOLD)
    out = _run_meter(monkeypatch, 100_000)
    assert f"fires at {fire_at:,}" in out, out


def test_a_reading_past_the_trigger_is_reported_reached(monkeypatch):
    # Squarely inside the band the old literal got wrong: past where the
    # ritual fires, short of where the meter used to think it would.
    fire_at = int(ch.CONTEXT_WINDOW_TOKENS * TRIGGER_THRESHOLD)
    inside_the_old_band = fire_at + 20_000
    out = _run_meter(monkeypatch, inside_the_old_band)
    assert "REACHED" in out, out
    assert "to go" not in out, out


def test_the_meter_carries_no_copy_of_the_trigger():
    # One number read in both places cannot disagree. A literal fraction
    # multiplied into the window here is the shape that went stale once.
    import inspect

    from divineos.cli import context_tokens_commands

    src = inspect.getsource(context_tokens_commands)
    assert "CONTEXT_WINDOW_TOKENS * 0." not in src
    assert "TRIGGER_THRESHOLD" in src
