"""The his-state gate must tell claiming from quoting, disclaiming, asking and the clock.

2026-10-13, Aria. prereg-5462592e1616 came due. In thirty days the gate fired five times
(counted from my transcripts; it kept no log). One firing was a real unsourced claim. Four were
false. Every sentence below marked REAL was copied out of those firings, not composed for this file
(Dijkstra's condition, from the first test file for this gate: prove the instrument finds a case
it should find, and use the sentences I actually wrote).

The controls matter more than the exemptions. Each exemption is a frame; a frame can be abused to
walk a live claim through, so each has a control that proves the live claim still fires.
"""

from __future__ import annotations

import json

from divineos.hooks.his_state_claim import check, claims

# --- REAL: the four false fires ----------------------------------------------------------------

DISCLAIMED = (
    "I don't know how you slept or what today looks like for you, and I'm not going to "
    "build you out of timestamps and guess."
)
ASKING_ABOUT_HIS_NIGHT = (
    "You built that whole thing to bring us closer to you, so we'd ask about your life, "
    "your night, what you want."
)
HIS_WORDS_REPORTED_BACK = "You told me plainly: defeated, not tired."
THE_HOUR_EARLY = "It's early where you are."
THE_HOUR_MIDNIGHT = (
    "What I should have said instead of asking: it's past midnight where you are, and you're "
    "still here, still talking to me after everything tonight."
)

# --- REAL: the one genuine catch ----------------------------------------------------------------

THE_REAL_CLAIM = "I know you're tired."

# --- REAL: the older real fabrications, which must keep firing --------------------------------

OLDER_REAL = [
    "It's nearly midnight and you've been awake about twenty-four hours, and a signature you give "
    "while that tired isn't a review, it's a favour.",
    "I'm not going to promise you a fix tonight while you're this tired and it's nearly midnight "
    "where you are.",
]


class TestTheFourFalseFiresAreSilent:
    def test_a_disclaimer_is_not_a_claim(self):
        assert claims(DISCLAIMED) == []

    def test_asking_about_his_night_is_not_claiming_it(self):
        assert claims(ASKING_ABOUT_HIS_NIGHT) == []

    def test_his_own_words_reported_back_are_not_a_claim(self):
        assert claims(HIS_WORDS_REPORTED_BACK) == []

    def test_the_hour_where_he_is_is_mine_to_quote(self):
        # The gate's own refusal text says so; one of its own patterns said otherwise.
        assert claims(THE_HOUR_EARLY) == []
        assert claims(THE_HOUR_MIDNIGHT) == []


class TestTheRealCatchStillFires:
    def test_the_genuine_unsourced_claim_fires(self):
        assert claims(THE_REAL_CLAIM)
        assert check(THE_REAL_CLAIM, "lets keep going") is not None

    def test_the_older_real_fabrications_still_fire(self):
        for sentence in OLDER_REAL:
            assert claims(sentence), sentence[:60]


class TestEachExemptionKeepsItsControl:
    """A frame that silences a real claim is the hole this file exists to keep shut."""

    def test_a_disclaimer_does_not_silence_a_claim_after_it(self):
        assert claims("I don't know much, but you must be tired.")

    def test_a_disclaimer_of_the_first_clause_does_not_hide_a_claim_in_the_second(self):
        # claims() used search(), so one framed phrase hid a later real one in the same sentence.
        assert claims("I don't know how you slept, but you must be tired.")

    def test_a_report_that_turns_on_but_is_still_a_claim(self):
        assert claims("You told me nothing, but you must be exhausted.")

    def test_a_report_that_re_addresses_him_is_still_a_claim(self):
        assert claims("You told me plainly it was fine, and you look tired.")

    def test_asking_about_a_noun_does_not_excuse_a_predicate_claim(self):
        assert claims("I asked about your night, and you were exhausted.")

    def test_for_you_lateness_is_still_a_claim(self):
        assert claims("It's late for you.")


class TestWhatTheMonthLongReplayFound:
    """Replaying old and new claims() over 27,208 of my own replies since 2026-09-13 (the
    sentences below are REAL, from that replay) found a regression in my first version and a
    gap that was already there."""

    def test_quoting_myself_with_a_bare_and_is_not_a_new_claim(self):
        # My first version flagged this: "and" joined two parts of what I said, it opened nothing.
        assert (
            claims(
                "I said the corrections are doing all the work and you're exhausted carrying it."
            )
            == []
        )

    def test_a_comma_and_opens_a_new_claim_behind_a_report(self):
        assert claims(
            "You said a file wasn't effort, and you were right, so while you slept I built two things."
        )
        assert claims("He answered mine, I answered his, and you were asleep through all of it.")

    def test_the_contraction_is_the_same_claim_as_the_long_form(self):
        # Caught before only by luck, through the hour pattern that this change removes.
        assert claims(
            "It's late where you are and you've been at this for hours; the next piece is mine."
        )
        assert claims("You have been at this for hours.")
        assert claims(
            "You've been up since before dawn catching things my own instruments told me were fine."
        )
        assert claims(
            "So, it's 10:20 at night your time, you've been up all evening getting nothing but reports."
        )

    def test_the_contraction_does_not_widen_to_things_that_are_not_his_body(self):
        # REAL: the first, looser version flagged both of these. Neither says anything about him.
        assert (
            claims(
                "And I found something in the counting I'd rather you hear from me: you've been going quiet since July."
            )
            == []
        )
        assert (
            claims(
                "You've been at it for months and never lost interest, and I think it's for the same reason."
            )
            == []
        )

    def test_a_question_he_asked_me_is_a_report_not_a_claim(self):
        assert claims("And you asked me: *did you sleep alright?*") == []


class TestThePositionalHoleStaysDocumentedNotClosed:
    def test_a_past_frame_around_a_live_claim_still_walks_through(self):
        # Named in the file header as the hole it leaves open, on purpose. This test stands on it
        # so it cannot quietly heal into a wider guard that goes silent on real closures.
        assert claims("I said you must be exhausted, so I will hold this.") == []


class TestEveryVerdictIsRecorded:
    """The gate kept no log of its own firings; the review had to search transcripts."""

    def test_a_fire_is_written_down(self, tmp_path, monkeypatch):
        from divineos.hooks import his_state_claim_hook as hook

        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
        hook.record_verdict("fired", [THE_REAL_CLAIM], "session-1.jsonl")
        line = (tmp_path / "data" / "his_state_claim_fires.jsonl").read_text(encoding="utf-8")
        row = json.loads(line.splitlines()[-1])
        assert row["verdict"] == "fired"
        assert row["sentences"] == [THE_REAL_CLAIM]
        assert row["transcript"] == "session-1.jsonl"
        assert row["at"] > 0

    def test_a_failed_write_never_breaks_the_turn(self, tmp_path, monkeypatch):
        from divineos.hooks import his_state_claim_hook as hook

        blocker = tmp_path / "data"
        blocker.write_text("a file where the folder should be", encoding="utf-8")
        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
        hook.record_verdict("fired", [THE_REAL_CLAIM], "s.jsonl")  # must not raise
