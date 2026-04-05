"""Tests for relay message detection in session analyzer."""

import pytest

from divineos.analysis.session_analyzer import (
    _is_relay_message,
    _strip_relay_prefix,
)


class TestIsRelayMessage:
    def test_here_is_the_reply(self):
        assert _is_relay_message("here is the reply\n\nTo Aether: blah blah") is True

    def test_heres_the_response(self):
        assert _is_relay_message("heres the response\n\nFrom Claude...") is True

    def test_here_is_the_audit(self):
        assert _is_relay_message("here is the audit\n\nDivineOS Audit Round 4...") is True

    def test_ok_here_is_the_reply(self):
        assert _is_relay_message("ok here is the reply\n\nTo Aether...") is True

    def test_okay_heres_the_message(self):
        assert _is_relay_message("okay here's the message\n\nHey Aether...") is True

    def test_here_is_a_fresh_audit(self):
        assert _is_relay_message("here is a fresh audit\n\nFresh clone coming up...") is True

    def test_here_is_claude(self):
        assert _is_relay_message("here is what claude said\n\nThe system looks good...") is True

    def test_i_sent_claude_everything(self):
        assert _is_relay_message("i sent claude everything you did this is the reply\n\nNow...") is True

    def test_normal_correction_not_relay(self):
        assert _is_relay_message("no don't use mocks in the tests") is False

    def test_normal_encouragement_not_relay(self):
        assert _is_relay_message("perfect that's exactly right") is False

    def test_normal_instruction_not_relay(self):
        assert _is_relay_message("lets use snake_case for everything") is False

    def test_empty_string(self):
        assert _is_relay_message("") is False

    def test_here_not_followed_by_relay_word(self):
        assert _is_relay_message("here is the file you asked for") is False

    def test_case_insensitive(self):
        assert _is_relay_message("Here Is The Reply\n\nTo Aether...") is True

    def test_here_is_a_fresh_claude(self):
        assert _is_relay_message("here is a fresh claude to speak with you\n\nHey...") is True


class TestStripRelayPrefix:
    def test_strips_at_newline(self):
        result = _strip_relay_prefix("here is the reply\n\nTo Aether: long audit text...")
        assert result == "here is the reply"

    def test_short_message_returns_as_is(self):
        result = _strip_relay_prefix("here is the reply")
        assert "here is the reply" in result

    def test_no_newline_takes_first_sentence(self):
        result = _strip_relay_prefix(
            "here is the reply. To Aether: this is a long audit with many words..."
        )
        assert "here is the reply" in result
        assert "audit" not in result

    def test_preserves_short_user_framing(self):
        result = _strip_relay_prefix("ok heres the reply\nThe auditor said something long...")
        assert "heres the reply" in result
