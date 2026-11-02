"""The Magic seat bridge's real replies, recorded, so the guard can be tested without a live game.

2026-10-25: the guard that holds a seat at a live Magic game must read his chat out of the game log,
and there is no game running to test it against. A fake that answers what we BELIEVE the bridge says
would test our picture, not the bridge, so the fake is only the real replies, captured during the Momir
game, word for word. Aether's condition: the fake must replay the real chat lines verbatim.

What is NOT recorded, and the file says so: what the log's `cursor` counts. It was 30 when the log held
about fifteen lines and 544 characters, so it is not a line count and not a character count that has
been checked. A test that pretends to know would be the flattering fake.
"""

import json
from pathlib import Path

REPLIES = Path(__file__).parent / "fixtures" / "magic_bridge_replies.json"


def _replies() -> dict:
    return json.loads(REPLIES.read_text(encoding="utf-8"))


def test_the_recorded_log_carries_his_chat_lines_word_for_word():
    log = _replies()["get_game_log"]["log"]
    assert "[Chat] spectator: YAY" in log
    assert "[Chat] spectator: can you see me in chat?" in log
    assert "[Chat] spectator: yes can you see my chat now?" in log


def test_his_chat_lines_and_the_moves_share_one_text_in_order():
    log = _replies()["get_game_log"]["log"]
    assert log.index("[Chat] spectator: YAY") < log.index("Aria played Island")
    assert log.index("Aria played Island") < log.index(
        "[Chat] spectator: yes can you see my chat now?"
    )


def test_the_recorded_envelope_keeps_the_numbers_it_really_had():
    reply = _replies()["get_game_log"]
    assert reply["total_length"] == 544
    assert reply["truncated"] is False
    assert reply["cursor"] == 30


def test_the_copied_log_is_exactly_as_long_as_the_bridge_said_it_was():
    """The control: total_length counts characters (544), and the copy has 544, so it is the log, not
    a retelling of it. The cursor (30) matches neither that nor the 16 lines."""
    reply = _replies()["get_game_log"]
    assert len(reply["log"]) == reply["total_length"]
    assert reply["log"].count("\n") + 1 != reply["cursor"]


def test_the_file_says_what_the_cursor_means_is_not_known():
    assert _replies()["_not_recorded"]["cursor_meaning"] == "unverified"


def test_no_action_pending_is_the_real_idle_reply():
    assert _replies()["get_action_choices_when_idle"] == {"action_pending": False}


def test_a_chat_post_succeeds_with_the_real_shape():
    assert _replies()["send_chat_message"] == {"success": True}


def test_a_dead_bridge_is_recorded_as_a_connection_failure_not_a_reply():
    dead = _replies()["bridge_down_after_the_game"]
    assert dead["listening_on_19001_19002"] == 0
    assert "ExceptionGroup" in dead["tool_call_error"]
