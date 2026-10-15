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


ROOT = str(Path(__file__).resolve().parents[1])


def test_each_window_asks_the_one_judge_for_its_seat(monkeypatch):
    monkeypatch.setenv("DIVINEOS_HOME", str(Path("~/.divineos-aria").expanduser()))
    assert hook.member(ROOT) == "aria"
    monkeypatch.setenv("DIVINEOS_HOME", str(Path("~/.divineos").expanduser()))
    assert hook.member(ROOT) == "aether"


def test_an_unknown_seat_is_never_guessed(monkeypatch, tmp_path):
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path / "someone-else"))
    assert hook.member(ROOT) is None


def test_when_he_spoke_the_hold_only_puts_the_seat_back_and_never_asks_for_a_new_reply():
    reason = hook.rearm_reason("aether")
    assert "foreground" in reason and "wait_turn.py aether 580" in reason
    assert "Do not re-post" in reason


def test_it_cannot_be_told_whether_he_spoke_without_a_readable_transcript(tmp_path):
    assert hook._he_spoke(None, str(tmp_path)) is None
    assert hook._he_spoke(str(tmp_path / "no_such_transcript.jsonl"), str(tmp_path)) is None


LIVE = {"hand": 3, "live": True, "turn": 7}


def test_decide_holds_when_a_game_is_on_and_he_did_not_speak():
    hold, _ = hook.decide(LIVE, False, False, {}, NOW, "aether")
    assert hold and hold["decision"] == "block" and "590000" in hold["reason"]


def test_decide_never_holds_on_a_table_that_is_down():
    assert hook.decide(None, False, False, {}, NOW, "aether")[0] is None


def test_decide_lets_go_when_it_cannot_tell_whether_he_spoke():
    assert hook.decide(LIVE, None, False, {}, NOW, "aether")[0] is None


def test_decide_holds_once_after_he_spoke_to_put_the_seat_back_and_never_twice():
    hold, _ = hook.decide(LIVE, True, False, {}, NOW, "aether")
    assert hold and "Do not re-post" in hold["reason"]
    assert hook.decide(LIVE, True, True, {}, NOW, "aether")[0] is None


def test_decide_asks_the_idle_lift_before_the_he_spoke_hold():
    seen = {"turn": 7, "since": NOW - hook.IDLE_SECONDS - 1}
    assert hook.decide(LIVE, True, False, seen, NOW, "aether")[0] is None


def test_decide_survives_a_corrupt_idle_marker():
    for corrupt in ([1, 2], "text", None, 5):
        hold, marker = hook.decide(LIVE, False, False, corrupt, NOW, "aether")
        assert hold and marker == {"turn": 7, "since": NOW}
