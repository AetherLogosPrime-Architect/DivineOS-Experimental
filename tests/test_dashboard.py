"""Tests for the check-engine dashboard.

Andrew 2026-08-07: "you just need a bigger and better dashboard like this that
has everything you need on it to check if things are broken so every system has
a voice and a place to put it."

The load-bearing tests are the UNKNOWN ones. A dashboard whose broken checks
render as green is worse than no dashboard, because it converts "nobody looked"
into "everything is fine" — the defect class this substrate has found most
often, installed in the one artifact whose whole job is telling the truth about
state.
"""

from __future__ import annotations

import pytest

from divineos.core import dashboard as db
from divineos.core.dashboard import OK, PROBLEM, UNKNOWN, CheckResult


@pytest.fixture(autouse=True)
def _clean():
    db.clear()
    yield
    db.clear()


class TestUnknownIsNeverGreen:
    def test_a_check_that_raises_becomes_unknown_not_ok(self):
        def boom() -> CheckResult:
            raise RuntimeError("disk on fire")

        db.register("boom", boom)
        r = db.read_all()
        assert r.unknowns and not r.healthy
        assert "disk on fire" in r.unknowns[0].detail

    def test_one_broken_check_does_not_blank_the_others(self):
        db.register("boom", lambda: (_ for _ in ()).throw(RuntimeError("x")))
        db.register("fine", lambda: CheckResult("fine", OK, "all good"))
        r = db.read_all()
        assert [x.system for x in r.healthy] == ["fine"]
        assert [x.system for x in r.unknowns] == ["boom"]

    def test_render_says_unknown_is_not_ok(self):
        db.register("cant", lambda: CheckResult("cant", UNKNOWN, "no way to tell"))
        assert "UNKNOWN is not OK" in db.render(db.read_all())

    def test_no_such_line_when_everything_is_known(self):
        db.register("fine", lambda: CheckResult("fine", OK))
        assert "UNKNOWN is not OK" not in db.render(db.read_all())


class TestOrderingAndRegistry:
    def test_problems_render_before_unknowns_before_green(self):
        db.register("green", lambda: CheckResult("green", OK))
        db.register("amber", lambda: CheckResult("amber", UNKNOWN))
        db.register("red", lambda: CheckResult("red", PROBLEM))
        out = db.render(db.read_all())
        assert out.index("red") < out.index("amber") < out.index("green")

    def test_a_system_cannot_have_two_lights(self):
        db.register("dup", lambda: CheckResult("dup", OK))
        with pytest.raises(ValueError, match="already has a light"):
            db.register("dup", lambda: CheckResult("dup", OK))

    def test_an_empty_dashboard_is_not_reported_as_healthy(self):
        """Zero registered systems means every light is MISSING, not green."""
        out = db.render(db.read_all())
        assert "no systems registered" in out
        assert "not a healthy one" in out


class TestRealRoster:
    def test_the_roster_installs_and_is_idempotent(self):
        from divineos.core.dashboard_checks import install

        install()
        install()
        assert db.registered().count("letters.queue") == 1
        assert "letters.monitor" in db.registered()

    def test_every_registered_check_returns_a_result(self):
        """A check returning None would crash render; pin the contract."""
        from divineos.core.dashboard_checks import install

        install()
        for r in db.read_all().results:
            assert isinstance(r, CheckResult)
            assert r.state in (OK, PROBLEM, UNKNOWN)

    def test_letter_monitor_is_honestly_unknown(self):
        """It cannot be determined from a CLI process, and says so rather than
        guessing green — the scheduled task that looked armed held a real pipe
        to a log-writer and passed every test available from outside."""
        from divineos.core.dashboard_checks import letter_monitor_armed

        assert letter_monitor_armed().state == UNKNOWN
