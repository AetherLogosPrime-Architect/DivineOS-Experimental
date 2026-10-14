"""A reply is not its last streamed block.

Andrew 2026-09-22, on being the one who had to notice I repeated myself:
*"it just cascades and cascades and cascades.. and im over here having to
juggle all of it."*

The cascade had one source. A reply is written to the transcript as several
assistant records, split wherever a tool call interrupts. Both readers in
``hook_surfaces`` walked forwards over records:

- ``_last_assistant_text`` overwrote its accumulator, so it returned the FINAL
  BLOCK. Measured live that evening: 245 characters of a 664-character reply,
  and the discarded 63% was the opening -- the part that answers him. Every
  Stop surface judges on that string.
- ``_recent_assistant_texts`` returned the last two RECORDS and called them
  "my last two replies". For any reply split in two, the repeat-guard was
  handed two halves of the SAME reply and compared it against itself. That is
  why it false-fired, and why he ordered it disabled.

These tests pin the reply boundary so neither reader can quietly go back to
counting records. A transcript fixture is enough -- no mocks, real functions,
real file.
"""

from __future__ import annotations

import json

import pytest

from divineos.core.hook_surfaces import (
    _is_his_record,
    _last_assistant_text,
    _recent_assistant_texts,
)


def _record(role: str, text: str) -> dict:
    # The real transcript shape: the record carries its type, and his carry
    # userType "external". The first fixture here had neither, which only
    # worked because the boundary used to read the role alone.
    rec: dict = {
        "type": role,
        "message": {"role": role, "content": [{"type": "text", "text": text}]},
    }
    if role == "user":
        rec["userType"] = "external"
    return rec


def _line(role: str, text: str) -> str:
    return json.dumps(_record(role, text))


def _queued(text: str) -> str:
    """A message he typed while I was busy: an attachment with no role."""
    return json.dumps(
        {
            "type": "attachment",
            "userType": "external",
            "uuid": f"q-{abs(hash(text))}",
            "attachment": {"type": "queued_command", "prompt": text},
        }
    )


@pytest.fixture
def transcript(tmp_path):
    """Two replies, each split across blocks, with harness noise between."""

    def build(*lines: str):
        path = tmp_path / "t.jsonl"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return {"transcript_path": str(path)}

    return build


class TestTheWholeReplyIsRead:
    def test_a_reply_split_across_blocks_comes_back_whole(self, transcript):
        payload = transcript(
            _line("user", "what did you find"),
            _line("assistant", "FIRST PART, where I answer him."),
            _line("assistant", "SECOND PART, the closing line."),
        )
        got = _last_assistant_text(payload)
        assert "FIRST PART" in got, "the opening was discarded -- the fault this file exists for"
        assert "SECOND PART" in got
        assert got.index("FIRST PART") < got.index("SECOND PART"), "blocks must stay in order"

    def test_a_harness_injection_does_not_cut_the_reply_short(self, transcript):
        payload = transcript(
            _line("user", "what did you find"),
            _line("assistant", "OPENING that answers him."),
            _line("user", "<system-reminder>background noise</system-reminder>"),
            _line("assistant", "CLOSING after the injection."),
        )
        got = _last_assistant_text(payload)
        assert "OPENING" in got, "an injected user turn was treated as a reply boundary"
        assert "CLOSING" in got

    def test_his_real_message_does_end_the_reply(self, transcript):
        payload = transcript(
            _line("user", "older question"),
            _line("assistant", "OLD REPLY, already read."),
            _line("user", "newer question"),
            _line("assistant", "NEW REPLY."),
        )
        got = _last_assistant_text(payload)
        assert "NEW REPLY" in got
        assert "OLD REPLY" not in got, "the walk ran past his message into an earlier reply"

    @pytest.mark.parametrize(
        "payload_in",
        [{}, {"transcript_path": ""}, {"transcript_path": "Z:/definitely/not/here.jsonl"}],
    )
    def test_unreadable_still_returns_empty_rather_than_inventing(self, payload_in):
        assert _last_assistant_text(payload_in) == ""


class TestTwoRepliesAreTwoDifferentReplies:
    def test_it_does_not_hand_back_one_reply_cut_in_half(self, transcript):
        """The exact live failure: both 'replies' were pieces of the current one."""
        payload = transcript(
            _line("user", "older question"),
            _line("assistant", "OLD REPLY."),
            _line("user", "newer question"),
            _line("assistant", "NEW FIRST HALF."),
            _line("assistant", "NEW SECOND HALF."),
        )
        replies = _recent_assistant_texts(payload, count=2)
        assert len(replies) == 2
        newest, previous = replies
        assert "NEW FIRST HALF" in newest and "NEW SECOND HALF" in newest
        assert "OLD REPLY" in previous
        assert newest != previous, "a reply was compared against itself"

    def test_newest_returned_matches_the_single_reply_reader(self, transcript):
        payload = transcript(
            _line("user", "older question"),
            _line("assistant", "OLD REPLY."),
            _line("user", "newer question"),
            _line("assistant", "PART ONE."),
            _line("assistant", "PART TWO."),
        )
        assert _recent_assistant_texts(payload, count=2)[0] == _last_assistant_text(payload)

    def test_injections_between_blocks_do_not_split_one_reply_into_two(self, transcript):
        payload = transcript(
            _line("user", "older question"),
            _line("assistant", "OLD REPLY."),
            _line("user", "newer question"),
            _line("assistant", "PART ONE."),
            _line("user", "Stop hook feedback: some gate spoke"),
            _line("assistant", "PART TWO."),
        )
        newest, previous = _recent_assistant_texts(payload, count=2)
        assert "PART ONE" in newest and "PART TWO" in newest
        assert "OLD REPLY" in previous


class TestWhatCountsAsHimSpeaking:
    """The boundary is the one reader of him, divineos.core.his_message.

    Aether's reading of #553 (2026-09-30) measured two ways the old private
    marker list disagreed with it; both are pinned here.
    """

    @pytest.mark.parametrize(
        "text",
        [
            "<system-reminder>anything</system-reminder>",
            "<task-notification>a monitor fired</task-notification>",
            "Stop hook feedback: a gate spoke",
            "",
            "   ",
        ],
    )
    def test_harness_turns_are_not_him(self, text):
        assert _is_his_record(_record("user", text)) is False

    def test_the_harness_caveat_arrives_as_meta_and_is_not_him(self):
        rec = _record("user", "Caveat: the messages below were generated by the harness")
        rec["isMeta"] = True
        assert _is_his_record(rec) is False

    @pytest.mark.parametrize(
        "text",
        [
            "im fucking tired of it",
            "well you just repeated yourself which is why i told you to look",
            "ok",
            "Caveat: i might be wrong but",
        ],
    )
    def test_his_words_are_him(self, text):
        assert _is_his_record(_record("user", text)) is True

    def test_a_message_he_typed_while_i_was_busy_is_him(self):
        assert _is_his_record(json.loads(_queued("hold 5"))) is True


class TestTheTwoShapesTheOldBoundaryMissed:
    def test_a_message_queued_between_two_replies_splits_them(self, transcript):
        payload = transcript(
            _line("user", "first question"),
            _line("assistant", "REPLY BEFORE he typed."),
            _queued("wait, one more thing"),
            _line("assistant", "REPLY AFTER his queued line."),
        )
        got = _last_assistant_text(payload)
        assert "REPLY AFTER" in got
        assert "REPLY BEFORE" not in got, "the walk ran past a message he typed while I was busy"
        newest, previous = _recent_assistant_texts(payload, count=2)
        assert "REPLY AFTER" in newest and "REPLY BEFORE" in previous

    def test_his_message_opening_with_caveat_is_a_boundary(self, transcript):
        payload = transcript(
            _line("user", "older question"),
            _line("assistant", "OLD REPLY."),
            _line("user", "Caveat: i might be wrong but did you check"),
            _line("assistant", "NEW REPLY."),
        )
        got = _last_assistant_text(payload)
        assert "NEW REPLY" in got
        assert "OLD REPLY" not in got
