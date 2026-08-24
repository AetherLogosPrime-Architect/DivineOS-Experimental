"""Tests for ``has_session_fresh_goal`` — register item N.

The load-bearing one is ``test_fresh_but_completed_goal_still_counts``. That
case blocked me repeatedly on 2026-08-05 and it looked like a caching bug for
most of the night:

  1. I set a goal describing the work I was about to do.
  2. I did the work and committed it.
  3. ``auto_close_from_message`` matched the commit text against the goal text
     — they overlap heavily, because the goal DESCRIBED that work — and
     correctly marked it done.
  4. The next tool call found no *active* goal and blocked with
     "No goal set for this session."

Measured at diagnosis: a goal added 1.3 minutes earlier already carried
status='done'. Nothing was stale and nothing was skipped. The discipline had
worked perfectly and the gate read it as absence.

The staleness cases below are equally load-bearing in the other direction: the
fix must not turn a real gate into a no-op.
"""

from __future__ import annotations

import json
import time

import pytest

from divineos.core import hud_state


@pytest.fixture()
def goals_file(tmp_path, monkeypatch):
    hud = tmp_path / "hud"
    hud.mkdir(parents=True)
    monkeypatch.setattr(hud_state, "_ensure_hud_dir", lambda: hud)

    def _write(goals):
        (hud / "active_goals.json").write_text(json.dumps(goals), encoding="utf-8")

    return _write


def test_fresh_but_completed_goal_still_counts(goals_file):
    """The false block. A goal set and finished two minutes ago answers the
    gate's actual question — did I declare what I am working on this session."""
    goals_file([{"goal": "x", "added_at": time.time() - 60, "status": "done"}])
    assert hud_state.has_session_fresh_goal() is True


def test_fresh_active_goal_counts(goals_file):
    goals_file([{"goal": "x", "added_at": time.time() - 60, "status": "active"}])
    assert hud_state.has_session_fresh_goal() is True


def test_stale_active_goal_still_blocks(goals_file):
    """Freshness is the real guard and must survive the fix."""
    goals_file([{"goal": "x", "added_at": time.time() - 99999, "status": "active"}])
    assert hud_state.has_session_fresh_goal() is False


def test_stale_completed_goal_still_blocks(goals_file):
    goals_file([{"goal": "x", "added_at": time.time() - 99999, "status": "done"}])
    assert hud_state.has_session_fresh_goal() is False


def test_no_goals_blocks(goals_file):
    goals_file([])
    assert hud_state.has_session_fresh_goal() is False


def test_missing_file_blocks(tmp_path, monkeypatch):
    monkeypatch.setattr(hud_state, "_ensure_hud_dir", lambda: tmp_path / "nowhere")
    assert hud_state.has_session_fresh_goal() is False


def test_unreadable_file_blocks(tmp_path, monkeypatch):
    """Fail toward blocked. A gate that cannot read its own state must not
    conclude the state is satisfied."""
    hud = tmp_path / "hud"
    hud.mkdir()
    (hud / "active_goals.json").write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(hud_state, "_ensure_hud_dir", lambda: hud)
    assert hud_state.has_session_fresh_goal() is False


def test_one_fresh_goal_among_stale_ones_counts(goals_file):
    now = time.time()
    goals_file(
        [
            {"goal": "old", "added_at": now - 99999, "status": "done"},
            {"goal": "old2", "added_at": now - 88888, "status": "active"},
            {"goal": "new", "added_at": now - 30, "status": "done"},
        ]
    )
    assert hud_state.has_session_fresh_goal() is True
