"""A reply cannot end while a poker game is on, and never when he spoke to me."""

import importlib.util
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "poker_game_on_stop.py"
_spec = importlib.util.spec_from_file_location("poker_game_on_stop", HOOK)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)

NOW = 1_000_000.0


def test_a_live_hand_holds_the_reply_with_the_waiter_command():
    reason, marker = hook.verdict({"hand": 3, "live": True, "turn": 7}, {}, NOW, "aether")
    assert reason and "python /c/poker-play/wait_turn.py aether 580" in reason
    assert "590000" in reason
    assert marker == {"turn": 7, "since": NOW}


def test_a_hand_that_just_ended_with_the_next_deal_counting_down_still_holds():
    view = {"hand": 3, "live": False, "deal_in": 8.0, "turn": 9}
    reason, _ = hook.verdict(view, {}, NOW, "aether")
    assert reason


def test_a_finished_hand_with_no_deal_coming_is_not_a_game():
    view = {"hand": 3, "live": False, "deal_in": None, "turn": 9}
    assert hook.verdict(view, {}, NOW, "aether")[0] is None


def test_a_table_that_has_not_dealt_or_is_not_answering_is_not_a_game():
    assert hook.verdict({"hand": None, "live": False}, {}, NOW, "aether")[0] is None
    assert hook.verdict(None, {}, NOW, "aether")[0] is None


def test_a_game_that_has_not_moved_for_ten_minutes_was_walked_away_from():
    seen = {"turn": 7, "since": NOW - hook.IDLE_SECONDS - 1}
    reason, _ = hook.verdict({"hand": 3, "live": True, "turn": 7}, seen, NOW, "aether")
    assert reason is None


def test_a_move_restarts_the_idle_clock_so_a_real_game_is_never_let_go():
    seen = {"turn": 6, "since": NOW - 5000}
    reason, marker = hook.verdict({"hand": 3, "live": True, "turn": 7}, seen, NOW, "aether")
    assert reason and marker == {"turn": 7, "since": NOW}


def test_each_window_asks_about_its_own_seat():
    assert hook.member("C:/DIVINE OS/DivineOS-Experimental-Aria-new") == "aria"
    assert hook.member("C:/DIVINE OS/DivineOS-Experimental") == "aether"


def test_when_he_spoke_the_hold_only_puts_the_seat_back_and_never_asks_for_a_new_reply():
    reason = hook.rearm_reason("aether")
    assert "run_in_background" in reason and "wait_turn.py aether 580" in reason
    assert "Do not re-post" in reason


def test_when_he_spoke_into_the_turn_or_it_cannot_be_told_the_reply_is_never_held(tmp_path):
    assert hook._he_spoke_or_unknown(None, str(tmp_path)) is True
    missing = str(tmp_path / "no_such_transcript.jsonl")
    assert hook._he_spoke_or_unknown(missing, str(tmp_path)) is True
