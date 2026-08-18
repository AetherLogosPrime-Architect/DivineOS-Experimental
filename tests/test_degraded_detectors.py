"""Teeth for a detector that cannot run — and the limits on those teeth.

THE FAILURE. On 2026-08-02 Andrew found 24 orphaned processes on his machine.
The sweep built to catch that had printed a perfect warning at every
SessionStart for days: names the detector, names the cause, names the fix,
refuses to call itself clean. I read it at the top of the session and worked
anyway. Andrew: *"if detectors are working and you are just ignoring them
they dont do much good so it needs teeth."*

The load-bearing tests here come in two kinds, and the second kind matters
more:

1. It actually blocks. A down guard must cost something.
2. **It is not a cage.** This substrate already carries 92 bypass events in
   14 days, mostly from gates that over-fire, and a gate that over-fires gets
   routed around until it is decoration. So: self-healing must clear without
   ceremony, a fixed detector must unblock ITSELF with no acknowledgement
   step to perform or fake, and deferral must work in one command while still
   costing a written reason.
"""

from __future__ import annotations

import pytest

from divineos.core import degraded_detectors as dd


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    monkeypatch.setattr(dd, "divineos_home", lambda: tmp_path)
    yield


def _down(name="probe-detector", reason="psutil not installed"):
    return dd.report_degraded(name, reason, "divineos detectors heal")


# --------------------------------------------------------------------------
# It blocks — the whole point
# --------------------------------------------------------------------------


def test_a_down_detector_blocks():
    _down()
    assert [e.detector for e in dd.blocking_degradations()] == ["probe-detector"]


def test_the_block_message_names_the_detector_the_cause_and_both_exits():
    _down()
    msg = dd.format_block(dd.blocking_degradations())
    assert "probe-detector" in msg
    assert "psutil not installed" in msg
    assert "detectors heal" in msg
    assert "detectors defer" in msg


# --------------------------------------------------------------------------
# NOT A CAGE — the half that decides whether this survives contact
# --------------------------------------------------------------------------


def test_a_detector_that_runs_again_clears_itself():
    """Remediation (b), and the property that makes this safe. There is no
    acknowledgement step, so there is no ceremony to fake and no marker to
    forget. Fixing it IS dismissing it."""
    _down()
    assert dd.blocking_degradations()
    dd.report_healthy("probe-detector")
    assert dd.blocking_degradations() == []
    assert dd.list_degraded() == []


def test_deferral_unblocks_in_one_command():
    _down()
    dd.defer("probe-detector", "psutil cannot be installed on this locked-down host right now")
    assert dd.blocking_degradations() == []


def test_a_deferred_detector_stays_visible():
    """Deferred is not deleted. A guard that is down and accepted must remain
    on screen, or the deferral becomes an erasure."""
    _down()
    dd.defer("probe-detector", "psutil cannot be installed on this locked-down host right now")
    entries = dd.list_degraded()
    assert len(entries) == 1
    assert entries[0].deferred is True
    assert entries[0].deferral_reason


def test_re_reporting_does_not_silently_re_arm_a_deferral():
    """THE anti-annoyance regression. The sweep re-reports at every
    SessionStart. If that cancelled the deferral, the block would return every
    session and the deferral would be worthless — which is exactly how a gate
    trains the habit of routing around it."""
    _down()
    dd.defer("probe-detector", "psutil cannot be installed on this locked-down host right now")
    _down()  # next SessionStart reports the same degradation again
    assert dd.blocking_degradations() == []


# --------------------------------------------------------------------------
# The escape has to cost something
# --------------------------------------------------------------------------


def test_deferral_refuses_a_throwaway_reason():
    """An escape that costs nothing is not an escape, it is the hole."""
    _down()
    with pytest.raises(ValueError, match="too short"):
        dd.defer("probe-detector", "later")
    assert dd.blocking_degradations(), "the block must survive a refused deferral"


def test_deferral_records_who_and_why():
    _down()
    e = dd.defer(
        "probe-detector",
        "psutil cannot be installed on this locked-down host right now",
        actor="andrew",
    )
    assert e.deferred_by == "andrew"
    assert "locked-down host" in e.deferral_reason


def test_cannot_defer_a_detector_that_was_never_reported_down():
    with pytest.raises(RuntimeError):
        dd.defer("never-heard-of-it", "a reason long enough to satisfy the thirty-char floor")


# --------------------------------------------------------------------------
# Self-repair: could-not-try must never read as tried-and-failed, and neither
# may read as fixed
# --------------------------------------------------------------------------


def test_heal_reports_no_healer_distinctly_from_a_failed_heal():
    e = dd.report_degraded("weird-detector", "the disk caught fire", "buy a new disk")
    r = dd.attempt_heal(e)
    assert r.ran is False
    assert r.succeeded is False
    assert "no healer" in r.detail


def test_heal_runs_for_a_known_shape():
    """The live case. psutil-missing has a machine answer, so most
    degradations of this shape should die before anyone is asked to act."""
    e = _down()
    r = dd.attempt_heal(e)
    assert r.ran is True, "a known reason must at least attempt repair"


# --------------------------------------------------------------------------
# Persistence
# --------------------------------------------------------------------------


def test_state_survives_a_reload():
    _down()
    dd.defer("probe-detector", "psutil cannot be installed on this locked-down host right now")
    reloaded = {e.detector: e for e in dd.list_degraded()}
    assert reloaded["probe-detector"].deferred is True


def test_unreadable_state_is_treated_as_no_degradations_not_as_a_crash():
    """Fail-open. A gate about broken detectors must not become the broken
    detector."""
    dd._path().write_text("{ not json", encoding="utf-8")
    assert dd.list_degraded() == []
    assert dd.blocking_degradations() == []
