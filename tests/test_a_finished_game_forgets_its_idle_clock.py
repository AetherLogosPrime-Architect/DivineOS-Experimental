"""A game that has ended must not leave its idle clock behind for the next game.

The hook lets go of a table whose move counter has not moved for IDLE_SECONDS. That
clock was kept in a marker file, and the hook returned before touching the file whenever
no game was on, so the last game's marker survived into the next one. If the next game's
first counter value matched the old one, the stale 'since' made a brand-new game look
walked away from and the hold let go, which is the seat dropping out of a live hand, the
exact failure this hook exists to prevent.
"""

import importlib.util
import io
import json
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "poker_game_on_stop.py"
_spec = importlib.util.spec_from_file_location("poker_game_on_stop", HOOK)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)


def _run_main_with(monkeypatch, tmp_path, view):
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr(hook, "member", lambda project: "aether")
    monkeypatch.setattr(hook, "_view", lambda who: view)
    monkeypatch.setattr(hook.sys, "stdin", io.StringIO("{}"))
    return hook.main()


def _marker(tmp_path) -> Path:
    shared = tmp_path / ".divineos-shared"
    shared.mkdir(exist_ok=True)
    return shared / ".poker_idle_aether.json"


def test_a_table_with_no_game_clears_the_old_idle_marker(monkeypatch, tmp_path):
    marker = _marker(tmp_path)
    marker.write_text(json.dumps({"turn": 7, "since": 1.0}), encoding="utf-8")
    assert _run_main_with(monkeypatch, tmp_path, {"hand": 3, "live": False, "deal_in": None}) == 0
    assert json.loads(marker.read_text(encoding="utf-8")) == {}


def test_a_table_that_is_down_clears_the_old_idle_marker_too(monkeypatch, tmp_path):
    marker = _marker(tmp_path)
    marker.write_text(json.dumps({"turn": 7, "since": 1.0}), encoding="utf-8")
    assert _run_main_with(monkeypatch, tmp_path, None) == 0
    assert json.loads(marker.read_text(encoding="utf-8")) == {}


def test_no_marker_file_is_created_when_there_was_none(monkeypatch, tmp_path):
    marker = _marker(tmp_path)
    assert _run_main_with(monkeypatch, tmp_path, None) == 0
    assert not marker.exists()
