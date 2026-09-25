"""A detector nobody calls is the thing it was built to detect.

Found by Aria, 2026-09-23, reading arc 4 of 519. `scan_stale_stores` exists, is
tested, and is reached from nothing but its own test. It is not in
`run_full_scan`, there is no field for its answer on `AlarmResult`, and neither
formatter has a line for it.

WHY THE SILENCE MATTERS. Its sibling `scan_dormant_tables` asks whether a store
is EMPTY. A store that filled up once and then quietly stopped being fed is not
empty, so the sibling structurally cannot see it. Covering that blind spot is
the entire reason this function was written -- and the blind spot is still
uncovered, because nothing reaches the function.

The shape is its own subject matter: a thing built, announced, and never
called. Aria named it plainly rather than gently, which is the right way to
say it.

WHY THESE TESTS COVER THREE PLACES AND NOT ONE. Wiring the call into the scan
alone would be the same defect one step along: a field on a result that no
formatter prints is exactly as unreachable to a reader as a function no scan
calls. So: the scan calls it, the result carries the answer, and a person
reading the printed line can see it.

WHY THE EXISTING TESTS DO NOT COVER THIS, checked rather than assumed.
test_a_store_that_filled_and_died_is_not_healthy.py calls scan_stale_stores
DIRECTLY -- including the one named "the real scan", which is the detector
itself and not the full scan. test_dead_architecture_alarm.py calls
run_full_scan repeatedly and never asks about stale stores. Both files can pass
forever with the detector unreachable, which is what they have been doing.
"""

from __future__ import annotations

import inspect

from divineos.core import dead_architecture_alarm as alarm
from divineos.core.dead_architecture_alarm import StaleStore

# THE REAL DATACLASS, not a stand-in string. A formatter that happens to work
# on strings and breaks on the thing the scan actually returns would pass a
# test built from stand-ins, which is the same gap in a smaller room.
DEAD = StaleStore(
    name="a-store-that-filled-and-died",
    rows=313,
    days_quiet=21.0,
    reason="313 rows, nothing written for 21 days",
)


def test_the_full_scan_calls_the_stale_store_detector() -> None:
    """Read the scan's own source: does the call appear at all?

    Asserted against the source rather than by running the scan, deliberately.
    Running it reads the live database, so the result depends on how stale this
    machine's stores happen to be -- a test that passes or fails on somebody's
    disk state pins nothing about the wiring.
    """
    source = inspect.getsource(alarm.run_full_scan)
    assert "scan_stale_stores" in source, (
        "the full scan does not call the stale-store detector, so the blind "
        "spot it exists to cover is still uncovered"
    )


def test_the_result_has_somewhere_to_put_the_answer() -> None:
    """A call whose answer has nowhere to live is a call that discards it."""
    result = alarm.AlarmResult()
    assert hasattr(result, "stale_stores"), (
        "AlarmResult carries no field for stale stores, so even a wired scan "
        "would throw the answer away"
    )
    assert result.stale_stores == [], "the default must be an empty finding list"


def test_the_summary_line_reports_stale_stores_when_there_are_some() -> None:
    """The half that reaches a person."""
    result = alarm.AlarmResult()
    result.stale_stores = [DEAD]

    line = alarm.format_alarm_summary(result)

    assert "stale" in line.lower(), (
        "a stale store was found and the printed line does not mention it; a "
        f"field nobody prints is as unreachable as a function nobody calls:\n{line}"
    )


def test_the_summary_stays_quiet_when_there_are_none() -> None:
    """THE CONTROL, guarding the cheaper way to pass the test above.

    Appending a count unconditionally would satisfy the previous assertion and
    make the line longer on every scan. A number that is almost always zero
    teaches the reader to skip the whole line, which costs more than the
    silence it replaced.
    """
    line = alarm.format_alarm_summary(alarm.AlarmResult())

    assert "stale" not in line.lower(), (
        "the summary announces stale stores when there are none, which is how "
        f"a line stops being read:\n{line}"
    )


def test_the_detail_report_names_the_store_it_found() -> None:
    """The summary says how many; the detail has to say which one."""
    result = alarm.AlarmResult()
    result.stale_stores = [DEAD]

    report = alarm.format_alarm_detail(result)

    assert "a-store-that-filled-and-died" in report, (
        "the detail gives a count without naming the store, which leaves the "
        f"reader nothing to act on:\n{report}"
    )
