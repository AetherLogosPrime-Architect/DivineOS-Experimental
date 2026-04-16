"""Tests for relay message detection and tagging in session analyzer."""

from divineos.analysis.session_analyzer import (
    SessionAnalysis,
    UserSignal,
    _is_relay_message,
    _process_user_record,
    _strip_relay_prefix,
)


class TestIsRelayMessage:
    def test_here_is_the_reply(self):
        assert _is_relay_message("here is the reply\n\nTo the agent: blah blah") is True

    def test_heres_the_response(self):
        assert _is_relay_message("heres the response\n\nFrom Claude...") is True

    def test_here_is_the_audit(self):
        assert _is_relay_message("here is the audit\n\nDivineOS Audit Round 4...") is True

    def test_ok_here_is_the_reply(self):
        assert _is_relay_message("ok here is the reply\n\nTo the agent...") is True

    def test_okay_heres_the_message(self):
        assert _is_relay_message("okay here's the message\n\nHey there...") is True

    def test_here_is_a_fresh_audit(self):
        assert _is_relay_message("here is a fresh audit\n\nFresh clone coming up...") is True

    def test_here_is_claude(self):
        assert _is_relay_message("here is what claude said\n\nThe system looks good...") is True

    def test_i_sent_claude_everything(self):
        assert (
            _is_relay_message("i sent claude everything you did this is the reply\n\nNow...")
            is True
        )

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
        assert _is_relay_message("Here Is The Reply\n\nTo the agent...") is True

    def test_here_is_a_fresh_claude(self):
        assert _is_relay_message("here is a fresh claude to speak with you\n\nHey...") is True


class TestRelayTagging:
    """Relay messages should be preserved and tagged, not discarded."""

    def _make_analysis(self):
        return SessionAnalysis(source_file="test", session_id="test-1")

    def _make_record(self, text, timestamp="2024-01-01T00:00:00Z"):
        return {
            "type": "user",
            "message": {"content": text},
            "timestamp": timestamp,
        }

    def test_relay_preserved_in_relay_messages(self):
        analysis = self._make_analysis()
        record = self._make_record(
            "here is the reply\n\nTo the agent: the system looks good overall..."
        )
        _process_user_record(record, analysis)
        assert len(analysis.relay_messages) == 1
        assert "To the agent" in analysis.relay_messages[0]["full_content"]

    def test_relay_framing_captured(self):
        analysis = self._make_analysis()
        record = self._make_record("here is the reply\n\nTo the agent: detailed audit text here...")
        _process_user_record(record, analysis)
        assert "here is the reply" in analysis.relay_messages[0]["framing"]

    def test_direct_message_not_tagged_relay(self):
        analysis = self._make_analysis()
        record = self._make_record("no don't use mocks in the tests")
        _process_user_record(record, analysis)
        assert len(analysis.relay_messages) == 0

    def test_signal_from_relay_tagged_relay_framing(self):
        analysis = self._make_analysis()
        # User framing that contains encouragement
        record = self._make_record(
            "ok here is the reply, this is great\n\nAudit text with wrong and don't..."
        )
        _process_user_record(record, analysis)
        for signal in analysis.encouragements:
            if "great" in signal.content:
                assert signal.source == "relay_framing"
                break

    def test_signal_from_direct_message_tagged_direct(self):
        analysis = self._make_analysis()
        record = self._make_record("perfect that's exactly right")
        _process_user_record(record, analysis)
        assert len(analysis.encouragements) == 1
        assert analysis.encouragements[0].source == "direct"

    def test_user_signal_source_field_exists(self):
        signal = UserSignal(
            signal_type="correction",
            content="test",
            timestamp="t",
        )
        assert signal.source == "direct"  # default


class TestStripRelayPrefix:
    def test_strips_at_newline(self):
        result = _strip_relay_prefix("here is the reply\n\nTo the agent: long audit text...")
        assert result == "here is the reply"

    def test_short_message_returns_as_is(self):
        result = _strip_relay_prefix("here is the reply")
        assert "here is the reply" in result

    def test_no_newline_takes_first_sentence(self):
        result = _strip_relay_prefix(
            "here is the reply. To the agent: this is a long audit with many words..."
        )
        assert "here is the reply" in result
        assert "audit" not in result

    def test_preserves_short_user_framing(self):
        result = _strip_relay_prefix("ok heres the reply\nThe auditor said something long...")
        assert "heres the reply" in result
