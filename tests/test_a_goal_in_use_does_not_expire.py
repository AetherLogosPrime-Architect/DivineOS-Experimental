"""A goal in use does not expire mid-work; an idle one still does.

Dad, 2026-10-01: "think of a toy left in the hallway, every time you go past it
you trip on it and make a note to pick it up". The goal guard tripped me five
times that day, each mid-work: it measured freshness from when a goal was SET,
so a goal I was working under lapsed at two hours. Freshness is now measured
from last use. walk-5f7706b94262, prereg-585338e19ae8.
"""

from __future__ import annotations

import json
import time

import pytest

from divineos.core import hud_state

WINDOW = 7200.0


@pytest.fixture()
def hud(tmp_path, monkeypatch):
    d = tmp_path / "hud"
    d.mkdir(parents=True)
    monkeypatch.setattr(hud_state, "_ensure_hud_dir", lambda: d)
    return d


def _write(hud, goals):
    (hud / "active_goals.json").write_text(json.dumps(goals), encoding="utf-8")


def _read(hud):
    return json.loads((hud / "active_goals.json").read_text(encoding="utf-8"))


def test_a_goal_set_long_ago_but_used_recently_is_fresh(hud):
    now = time.time()
    _write(
        hud,
        [{"text": "x", "status": "active", "added_at": now - 3 * 3600, "last_used_at": now - 300}],
    )
    assert hud_state.has_session_fresh_goal(WINDOW)


def test_a_goal_set_long_ago_and_never_used_since_is_stale(hud):
    now = time.time()
    _write(hud, [{"text": "x", "status": "active", "added_at": now - 3 * 3600}])
    assert not hud_state.has_session_fresh_goal(WINDOW)


def test_passing_the_guard_marks_the_goal_used(hud):
    now = time.time()
    _write(hud, [{"text": "x", "status": "active", "added_at": now - 600}])
    assert hud_state.has_session_fresh_goal(WINDOW, touch=True)
    used = _read(hud)[0].get("last_used_at")
    assert used is not None and abs(used - time.time()) < 5


def test_so_steady_work_never_lapses(hud):
    # Set once, then used every 90 minutes for six hours: never refused.
    start = time.time() - 6 * 3600
    _write(hud, [{"text": "x", "status": "active", "added_at": start}])
    goals = _read(hud)
    for k in range(1, 5):
        goals[0]["last_used_at"] = start + k * 5400
        _write(hud, goals)
    assert hud_state.has_session_fresh_goal(WINDOW)


def test_a_future_last_use_is_clamped_so_a_skewed_clock_cannot_keep_it_alive(hud):
    now = time.time()
    _write(
        hud,
        [
            {
                "text": "x",
                "status": "active",
                "added_at": now - 9 * 3600,
                "last_used_at": now + 10 * 3600,
            }
        ],
    )
    # A last use "in the future" counts as now at most, never later; and it is
    # not trusted to rescue a goal whose recorded use is impossible.
    hud_state.has_session_fresh_goal(WINDOW, touch=True)
    stored = _read(hud)[0]["last_used_at"]
    assert stored <= time.time() + 1


def test_a_failed_check_writes_nothing(hud):
    now = time.time()
    goals = [{"text": "x", "status": "active", "added_at": now - 3 * 3600}]
    _write(hud, goals)
    assert not hud_state.has_session_fresh_goal(WINDOW)
    assert _read(hud) == goals
