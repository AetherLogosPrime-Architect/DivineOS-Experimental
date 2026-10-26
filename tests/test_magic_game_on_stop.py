"""A reply cannot end while a Magic game is live; the one ending after he speaks says so in chat.

Written first and red: .claude/hooks/magic_game_on_stop.py does not exist yet. The shape is
poker_game_on_stop.py's. The game view is what the seat bridge's get_game_state returns (a dict
with a players list); a bridge that is down answers None, which is not a game.
"""

import importlib.util
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "magic_game_on_stop.py"
_spec = importlib.util.spec_from_file_location("magic_game_on_stop", HOOK)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)

NOW = 1_000_000.0
LIVE = {
    "snapshot_id": 11,
    "turn": 3,
    "active_player": "Aria",
    "priority_player": "Aria",
    "players": [{"name": "Aether", "life": 24}, {"name": "Aria", "life": 24}],
}


def test_a_live_game_holds_the_reply_even_when_the_other_seat_is_to_act():
    reason, marker = hook.verdict(LIVE, {}, NOW, "aether")
    assert reason and "play.sh aether" in reason and "590000" in reason
    assert marker["since"] == NOW


def test_a_bridge_that_is_down_is_not_a_game():
    assert hook.verdict(None, {}, NOW, "aether")[0] is None


def test_a_view_without_two_players_is_not_a_game():
    assert hook.verdict({"turn": 1, "players": []}, {}, NOW, "aether")[0] is None
    assert hook.verdict({"turn": 1}, {}, NOW, "aether")[0] is None


def test_a_game_that_has_not_moved_for_the_idle_limit_was_walked_away_from():
    seen = {"sig": hook.signature(LIVE), "since": NOW - hook.IDLE_SECONDS - 1}
    assert hook.verdict(LIVE, seen, NOW, "aether")[0] is None


def test_a_move_restarts_the_idle_clock():
    moved = dict(LIVE, snapshot_id=12)
    seen = {"sig": hook.signature(LIVE), "since": NOW - 5000}
    reason, marker = hook.verdict(moved, seen, NOW, "aether")
    assert reason and marker["since"] == NOW


def test_when_he_spoke_in_the_window_the_one_ending_is_allowed_and_says_so_in_chat():
    hold, _, say = hook.decide(LIVE, True, {}, NOW, "aether")
    assert hold is None
    assert say == hook.FORCED_LINE


def test_the_chat_line_is_posted_once_per_move_not_once_per_try():
    _, marker, say = hook.decide(LIVE, True, {}, NOW, "aether")
    assert say
    _, _, again = hook.decide(LIVE, True, marker, NOW + 1, "aether")
    assert again is None


def test_he_did_not_speak_means_the_hold_stands_and_nothing_is_said():
    hold, _, say = hook.decide(LIVE, False, {}, NOW, "aether")
    assert hold and hold["decision"] == "block" and say is None


def test_it_lets_go_without_a_chat_line_when_it_cannot_tell_whether_he_spoke():
    hold, _, say = hook.decide(LIVE, None, {}, NOW, "aether")
    assert hold is None and say is None


def test_an_idle_lift_posts_the_away_line_once():
    seen = {"sig": hook.signature(LIVE), "since": NOW - hook.IDLE_SECONDS - 1}
    hold, marker, say = hook.decide(LIVE, False, seen, NOW, "aether")
    assert hold is None and say == hook.AWAY_LINE
    _, _, again = hook.decide(LIVE, False, marker, NOW + 1, "aether")
    assert again is None


def test_a_closed_seat_port_means_no_game_without_starting_the_play_helper(monkeypatch):
    called = []
    monkeypatch.setattr(hook.subprocess, "run", lambda *a, **k: called.append(a))
    monkeypatch.setattr(hook, "seat_is_listening", lambda who: False)
    assert hook._view("aether") is None
    assert called == []


def test_an_unknown_seat_is_never_listening():
    assert hook.seat_is_listening("someone-else") is False


def test_a_corrupt_marker_is_survived():
    for corrupt in ([1, 2], "text", None, 5):
        hold, marker, _ = hook.decide(LIVE, False, corrupt, NOW, "aether")
        assert hold and marker["since"] == NOW
