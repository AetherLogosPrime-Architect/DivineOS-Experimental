"""`divineos volley start|stop|status`: Dad says he is going to bed, the seat reads his words with
judgment and calls this; the same quiet the midnight-to-6am clock gives starts now.

No phrase list lives here (Dad, 2026-11-03). The marker is read by question_hold.is_away(), the
one reader every away-check already consults, and ORed with the clock, which stays as it was.
"""

from __future__ import annotations

import json
import time

import click
import pytest
from click.testing import CliRunner

from divineos.core import question_hold as qh
from divineos.core import volley_now


@pytest.fixture(autouse=True)
def _marker(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_VOLLEY_FILE", str(tmp_path / "volley_now.json"))
    monkeypatch.setattr(qh, "AWAY", tmp_path / "away.json")
    monkeypatch.setenv("DIVINEOS_HIS_ASKS_DB", str(tmp_path / "none.db"))  # could-not-look
    return tmp_path / "volley_now.json"


def _local(day: int, hour: int) -> float:
    return time.mktime((2026, 11, day, hour, 0, 0, 0, 0, -1))


def test_start_flips_status_on_and_stop_flips_it_off():
    assert volley_now.active() is None
    volley_now.start()
    got = volley_now.active()
    assert got is not None and got["by"] == "volley"
    assert volley_now.stop() is True
    assert volley_now.active() is None


def test_stop_with_nothing_running_says_so():
    assert volley_now.stop() is False


def test_the_existing_reader_sees_it():
    assert (
        qh.is_away() is None
    )  # control: the instrument can say "not away" (clock is off in tests)
    volley_now.start()
    away = qh.is_away()
    assert away is not None and away["by"] == "volley"
    volley_now.stop()
    assert qh.is_away() is None


def test_a_question_is_carried_while_it_runs():
    assert qh._carry_now() == ""
    volley_now.start()
    assert qh._carry_now() == "volley"


def test_the_clock_window_alone_still_works_with_no_marker():
    assert not volley_now.path().exists()
    got = qh._scheduled_away(_local(3, 3))
    assert got is not None and got["by"] == "schedule"
    assert qh._scheduled_away(_local(3, 12)) is None


def test_a_marker_from_a_previous_day_is_ignored(_marker):
    volley_now.start(now=_local(2, 22))
    assert volley_now.active(now=_local(2, 23)) is not None  # same day: on
    assert volley_now.active(now=_local(3, 8)) is None  # next day: ignored
    assert json.loads(_marker.read_text())["day"] == "2026-11-02"


def test_a_broken_marker_means_not_away(_marker):
    _marker.write_text("{not json", encoding="utf-8")
    assert volley_now.active() is None


def test_start_twice_keeps_the_first_moment():
    first = volley_now.start(now=_local(2, 21))
    again = volley_now.start(now=_local(2, 22))
    assert again["since"] == first["since"]


def test_cli_start_status_stop_and_where_the_letter_goes():
    from divineos.cli.volley_commands import register

    cli = click.Group()
    register(cli)
    r = CliRunner()
    assert "not running" in r.invoke(cli, ["volley", "status"]).output
    out = r.invoke(cli, ["volley", "start"]).output
    assert "the-night-letter-to-andrew-" in out and "## From" in out and "never rewrite" in out
    assert "is running" in r.invoke(cli, ["volley", "status"]).output
    assert "ended" in r.invoke(cli, ["volley", "stop"]).output
    assert "not running" in r.invoke(cli, ["volley", "status"]).output
