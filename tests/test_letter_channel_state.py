"""Four states, so that silence stops meaning two things at once.

Per prereg-9bb3d0fd17be. Aletheia designed it 2026-08-27, Aria built it,
and the fourth state is Aria's disagreement with the design rather than
part of it.

Distinct from tests/test_letter_seen_router.py, which covers marking
letters *I* have read — those arrive on a watched channel that leaves a
signal. Aletheia's channel is carried by hand and leaves none, which is
the entire reason this exists.

The load-bearing test is `test_the_falsifier`: her own condition, written
as an assertion. If never-arrived and arrived-unread ever become
indistinguishable, the store has failed and should be deleted rather
than tuned.
"""

from __future__ import annotations

import pytest

from divineos.core.letter_channel_state import (
    LetterState,
    render_stuck,
    stuck_in_the_channel,
    derive_from_watched_channel,
    in_the_channel,
    record_answered,
    record_delivered,
    record_handed,
    state_of,
    waiting_on_reader,
)


@pytest.fixture
def db(tmp_path):
    return tmp_path / "letter_seen.db"


class TestTheFourStates:
    def test_nothing_sent_is_unknown_not_unanswered(self, db):
        # The silence of a letter that was never written says nothing
        # about the reader, and must not be counted against her.
        assert state_of("never-written", db).state is LetterState.UNKNOWN

    def test_handed_without_delivery_is_a_channel_question(self, db):
        record_handed("letter-a", "aria", db)
        assert state_of("letter-a", db).state is LetterState.HANDED

    def test_delivered_and_unanswered_is_the_readers_silence(self, db):
        record_handed("letter-b", "aria", db)
        record_delivered("letter-b", db)
        assert state_of("letter-b", db).state is LetterState.DELIVERED

    def test_answered_is_answered(self, db):
        record_handed("letter-c", "aria", db)
        record_delivered("letter-c", db)
        record_answered("letter-c", "reply-c", db)
        rec = state_of("letter-c", db)
        assert rec.state is LetterState.ANSWERED
        assert rec.reply_id == "reply-c"


class TestTheFalsifier:
    """Aletheia's condition, as an assertion rather than a promise.

    'If the store can ever be in a state where those are
    indistinguishable, it has failed and should be deleted rather than
    tuned.'
    """

    def test_never_arrived_and_arrived_unread_never_collapse(self, db):
        record_handed("in-flight", "aria", db)

        record_handed("landed", "aria", db)
        record_delivered("landed", db)

        never_sent = state_of("nothing-here", db).state
        in_flight = state_of("in-flight", db).state
        landed = state_of("landed", db).state

        assert len({never_sent, in_flight, landed}) == 3, (
            "two of the three silences became the same answer -- delete the "
            "store rather than tuning it"
        )

    def test_the_two_lists_never_overlap(self, db):
        record_handed("waiting-in-channel", "aria", db)
        record_handed("waiting-on-her", "aria", db)
        record_delivered("waiting-on-her", db)

        channel = {r.letter_id for r in in_the_channel(db)}
        reader = {r.letter_id for r in waiting_on_reader(db)}

        assert channel == {"waiting-in-channel"}
        assert reader == {"waiting-on-her"}
        assert not (channel & reader)


class TestDeliveryIsOptional:
    """The fourth state, and the disagreement it encodes.

    Andrew carries these by hand and is not obliged to stop and record
    it. A design that needs a command he does not run would degrade back
    into the ambiguity it exists to remove, and degrade quietly.
    """

    def test_a_reply_proves_arrival_without_a_recorded_delivery(self, db):
        record_handed("unrecorded", "aria", db)
        record_answered("unrecorded", "her-reply", db)
        assert state_of("unrecorded", db).state is LetterState.ANSWERED

    def test_an_unrecorded_delivery_never_reads_as_her_silence(self, db):
        # The failure that matters: if HANDED collapsed into DELIVERED,
        # every letter he carried without saying so would be counted
        # against her as unanswered.
        record_handed("carried-quietly", "aria", db)
        assert state_of("carried-quietly", db).state is not LetterState.DELIVERED
        assert not waiting_on_reader(db)


class TestNotABoolean:
    def test_the_states_are_four_and_named(self, db):
        # A flag cannot hold "arrived but unread", which is the whole
        # point. Recorded as a test so a later simplification to a
        # boolean fails here rather than in her inbox.
        assert len(LetterState) == 4

    def test_every_row_names_its_letter(self, db):
        # The subject, not the fact. 'delivered(letter_id)', never
        # 'delivery_ran=true' -- an instrument reporting on itself cannot
        # report on its subject.
        record_handed("subject-bearing", "aria", db)
        assert state_of("subject-bearing", db).letter_id == "subject-bearing"


class TestWatchedChannelDerivation:
    """Aletheia's one-subject finding: it knew her channel and not ours.

    Ours is watched, so arrival IS delivery and needs nobody's memory,
    and a reply names what it answers. This replaced a manual mark that
    recorded whether someone pressed a button.
    """

    def _channel(self, tmp_path, replies):
        d = tmp_path / "letters"
        d.mkdir()
        (d / "aether-to-aria-2026-08-27-first-thing.md").write_text("x", encoding="utf-8")
        (d / "aether-to-aria-2026-08-27-second-thing.md").write_text("x", encoding="utf-8")
        for name, body in replies.items():
            (d / name).write_text(body, encoding="utf-8")
        return d

    def test_a_reply_naming_a_letter_marks_it_answered(self, tmp_path, db):
        d = self._channel(
            tmp_path,
            {"aria-to-aether-2026-08-27-my-reply.md": "**In response to:** `first-thing`\n"},
        )
        derive_from_watched_channel(d, "aria", "aether", db)
        assert (
            state_of("aether-to-aria-2026-08-27-first-thing.md", db).state is LetterState.ANSWERED
        )
        assert (
            state_of("aether-to-aria-2026-08-27-second-thing.md", db).state is LetterState.DELIVERED
        )

    def test_arrival_is_delivery_on_a_watched_channel(self, tmp_path, db):
        # Never HANDED here: a letter in the directory has been seen by
        # the monitor. That is the asymmetry with her hand-carried one.
        d = self._channel(tmp_path, {})
        derive_from_watched_channel(d, "aria", "aether", db)
        assert not in_the_channel(db)
        assert len(waiting_on_reader(db)) == 2

    def test_the_coverage_gap_is_reported_with_the_count(self, tmp_path, db):
        # The load-bearing one. A reply with no linkage line makes the
        # unanswered figure an over-count, and the first real run had
        # thirty-five of them. Reporting the count alone would have been
        # a fresh instrument checked against expectation, not subject.
        d = self._channel(
            tmp_path,
            {
                "aria-to-aether-2026-08-27-linked.md": "**In response to:** `first-thing`\n",
                "aria-to-aether-2026-08-27-unlinked.md": "no linkage line at all\n",
            },
        )
        result = derive_from_watched_channel(d, "aria", "aether", db)
        assert result.replies_without_linkage == 1
        assert result.unanswered == 1
        assert "over-count" in str(result), (
            "the caveat must travel in the string a reader would copy"
        )


class TestIdempotence:
    def test_recording_twice_is_the_same_as_once(self, db):
        record_handed("dupe", "aria", db)
        record_handed("dupe", "aria", db)
        record_delivered("dupe", db)
        record_delivered("dupe", db)
        assert state_of("dupe", db).state is LetterState.DELIVERED

    def test_a_later_reply_supersedes_an_earlier_one(self, db):
        record_handed("threaded", "aria", db)
        record_answered("threaded", "first-reply", db)
        record_answered("threaded", "second-reply", db)
        assert state_of("threaded", db).reply_id == "second-reply"


class TestStuckInTheChannel:
    """Aletheia's ask: the store held the answer and nothing asked it.

    A letter sat handed-over for seven days, she read the silence as her
    own inattention, I read it as the letter never having been written,
    and the duplicate followed. Age is the whole mechanism, and the store
    had no clock in it.
    """

    def test_a_letter_just_handed_over_is_not_stuck(self, db):
        record_handed("fresh", "aria", db)
        stuck, unknown = stuck_in_the_channel(older_than_days=2, db=db)
        assert stuck == []
        assert unknown == []

    def test_a_delivered_letter_is_never_stuck(self, db):
        # Stuck means the CHANNEL is holding it. Once it lands, any
        # silence belongs to the reader and is a different question.
        record_handed("landed", "aria", db)
        record_delivered("landed", db)
        stuck, unknown = stuck_in_the_channel(older_than_days=0, db=db)
        assert stuck == []

    def test_age_unknown_is_its_own_answer_and_never_zero(self, db):
        # A row from before the store recorded time cannot say how long
        # it waited. Counting it as new would sort the oldest possible
        # letter to the bottom of a report ordered only by age.
        import sqlite3

        record_handed("ancient", "aria", db)
        with sqlite3.connect(db) as conn:
            conn.execute("UPDATE letter_events SET at = NULL WHERE letter_id = 'ancient'")
        stuck, unknown = stuck_in_the_channel(older_than_days=0, db=db)
        assert unknown == ["ancient"]
        assert stuck == []

    def test_the_report_prints_its_own_blind_spot(self, db):
        import sqlite3

        record_handed("ancient", "aria", db)
        with sqlite3.connect(db) as conn:
            conn.execute("UPDATE letter_events SET at = NULL WHERE letter_id = 'ancient'")
        rendered = render_stuck(older_than_days=0, db=db)
        assert "age unknown" in rendered
        assert "not counted as new" in rendered
