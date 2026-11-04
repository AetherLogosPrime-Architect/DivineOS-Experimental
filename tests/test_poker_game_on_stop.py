"""A reply cannot end while a poker game is on, and never when he spoke to me."""

import importlib.util
import io
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


def test_main_exits_clean_without_asking_the_table_when_the_seat_cannot_be_told(
    monkeypatch, tmp_path, capsys
):
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path / "someone-else"))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", ROOT)
    monkeypatch.setattr(hook.sys, "stdin", io.StringIO("{}"))
    asked = []
    monkeypatch.setattr(hook, "_view", lambda who: asked.append(who))
    assert hook.main() == 0
    assert asked == [] and capsys.readouterr().out == ""


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


LETTER = "/home/x/.divineos-shared/letters/aria-to-aether-2026-11-04-hello.md"


def test_a_waiting_letter_is_named_before_the_wait_in_every_hold():
    """The doorbell refuses every real tool, the wait included, until a rung letter is read. A hold that only
    said 'call the wait' sent a seat into that refusal (Aria, 2026-11-04). The letter comes first in the text."""
    for reason in (
        hook.verdict(LIVE, {}, NOW, "aether", [LETTER])[0],
        hook.rearm_reason("aether", [LETTER]),
        hook.decide(LIVE, False, False, {}, NOW, "aether", [LETTER])[0]["reason"],
        hook.decide(LIVE, True, False, {}, NOW, "aether", [LETTER])[0]["reason"],
    ):
        assert reason.startswith("A LETTER IS WAITING FIRST")
        assert LETTER in reason and "Read tool" in reason
        assert reason.index("Read tool") < reason.index("wait_turn.py")


def test_with_no_letter_waiting_the_hold_reads_exactly_as_it_did():
    plain = hook.verdict(LIVE, {}, NOW, "aether")[0]
    assert hook.verdict(LIVE, {}, NOW, "aether", [])[0] == plain
    assert "LETTER" not in plain
    assert hook.rearm_reason("aether", []) == hook.rearm_reason("aether")


def test_the_gate_is_not_weakened_the_hold_still_demands_the_wait_after_the_read():
    reason = hook.verdict(LIVE, {}, NOW, "aether", [LETTER])[0]
    assert "wait_turn.py aether 580" in reason and "590000" in reason


def test_letters_first_asks_the_one_bell_list_and_gives_paths(monkeypatch):
    import divineos.core.unread_letter as ul

    monkeypatch.setattr(ul, "unread_rung", lambda who: [Path(LETTER)])
    assert hook.letters_first("aether", ROOT) == [str(Path(LETTER))]


def test_letters_first_says_nothing_when_it_cannot_tell_and_the_hold_still_holds(
    monkeypatch, capsys
):
    import divineos.core.unread_letter as ul

    def broken(who):
        raise OSError("seen store unreachable")

    monkeypatch.setattr(ul, "unread_rung", broken)
    assert hook.letters_first("aether", ROOT) is None
    assert "could not tell whether a letter is waiting" in capsys.readouterr().err
    assert hook.verdict(LIVE, {}, NOW, "aether", hook.letters_first("aether", ROOT))[0]


def test_nothing_waiting_and_could_not_look_are_different_answers(monkeypatch):
    """The walk's Hoare finding: an empty list for both let the type say nothing about which it was."""
    import divineos.core.unread_letter as ul

    monkeypatch.setattr(ul, "unread_rung", lambda who: [])
    assert hook.letters_first("aether", ROOT) == []
    assert hook.letters_first("aether", ROOT) is not None

    def broken(who):
        raise OSError("seen store unreachable")

    monkeypatch.setattr(ul, "unread_rung", broken)
    assert hook.letters_first("aether", ROOT) is None
    # both read the same in the hold text, which is the safe direction
    plain = hook.verdict(LIVE, {}, NOW, "aether")[0]
    assert hook.verdict(LIVE, {}, NOW, "aether", None)[0] == plain
    assert hook.verdict(LIVE, {}, NOW, "aether", [])[0] == plain


def test_main_hands_the_waiting_letters_to_the_hold(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", ROOT)
    monkeypatch.setattr(hook.Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(hook.sys, "stdin", io.StringIO("{}"))
    monkeypatch.setattr(hook, "member", lambda project: "aether")
    monkeypatch.setattr(hook, "_view", lambda who: LIVE)
    monkeypatch.setattr(hook, "_he_spoke", lambda transcript, project: False)
    monkeypatch.setattr(hook, "letters_first", lambda who, project: [LETTER])
    assert hook.main() == 0
    out = capsys.readouterr().out
    assert "A LETTER IS WAITING FIRST" in out and LETTER in out
