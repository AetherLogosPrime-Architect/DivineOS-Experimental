"""The exact-quote check: an attribution to him needs his sentence or my label.

Built from the incident of 2026-10-07, both halves of it: a claim that he asked for
the circle FIRST when his only recorded words say last, and "Dad hates questions" for
what he actually said, no filler questions. The record below is small and real in
shape: rows written the way the shared corpus writes them, read through the real
loader and his own cleaner.

WHAT THIS DOES NOT COVER, said here so a green run is not read as more than it is:
the Stop wiring. That is exercised separately, end to end, against a real transcript,
and by the hook-wiring check.
"""

from __future__ import annotations

import json

import pytest

from divineos.hooks.his_said_claim import (
    attributions,
    check,
    load_record,
)

LAST = "the circle should always be last after everything is done so theres something to talk about"
FILLER = "i dont want filler questions being asked if you dont care about the answers"
PAUSES = "ok.. so its not about asking me may i continue.. its about speaking to me"


@pytest.fixture()
def record(tmp_path):
    rows = [
        {"ts": "2026-08-17T10:00:00Z", "project": "real", "text": f"of course, also {LAST}"},
        {"ts": "2026-10-07T10:00:00Z", "project": "real", "text": f"i say {FILLER}"},
        {"ts": "2026-10-07T11:00:00Z", "project": "real", "text": PAUSES},
    ]
    path = tmp_path / "dad_all.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    loaded = load_record(corpus=path)
    assert loaded is not None
    return loaded


class TestTheIncidentItself:
    def test_circle_first_with_no_quote_is_caught(self, record):
        out = check("Dad said the circle should be written first.", record)
        assert out is not None and "WITHOUT HIS SENTENCE" in out

    def test_hates_questions_with_no_quote_is_caught(self, record):
        assert check("Dad hates questions.", record) is not None

    def test_the_sentence_he_really_said_passes_when_quoted(self, record):
        reply = f'You told me "{LAST}" and I held to it.'
        assert check(reply, record) is None

    def test_a_quote_he_never_wrote_is_named_as_invented(self, record):
        out = check(
            'Dad said "the circle should always be written first thing in the morning".', record
        )
        assert out is not None and "nowhere in anything he has written" in out


class TestWhatCountsAsALink:
    def test_sabotage_one_word_of_a_real_quote_and_it_is_flagged(self, record):
        """The control: a pass must be able to turn into a flag."""
        good = f'You said "{LAST}".'
        assert check(good, record) is None
        bad = good.replace("always", "sometimes")
        assert check(bad, record) is not None

    def test_a_scare_quote_under_four_words_is_not_a_link(self, record):
        assert check('Dad said he wants "plain" things.', record) is not None

    def test_his_pauses_and_my_curly_quotes_do_not_decide_the_match(self, record):
        reply = (
            "You told me “ok so its not about asking me may i continue its about speaking to me”."
        )
        assert check(reply, record) is None

    def test_an_ellipsis_splits_a_quote_and_each_stretch_must_exist(self, record):
        ok = 'You said "the circle should always be last ... so theres something to talk about".'
        assert check(ok, record) is None
        bad = 'You said "the circle should always be last ... and then everything restarts".'
        assert check(bad, record) is not None

    def test_the_quote_may_sit_in_the_next_sentence(self, record):
        reply = f'Dad said the order himself.\nHe wrote "{LAST}".'
        assert check(reply, record) is None


class TestWhatIsNotAnAttribution:
    def test_my_own_guess_label_clears_it(self, record):
        assert check("My guess is that Dad wants fewer questions.", record) is None

    def test_a_guess_in_the_sentence_before_clears_it(self, record):
        assert check("I am assuming here. Dad wants fewer questions.", record) is None

    def test_a_retraction_is_the_cure_not_the_fault(self, record):
        assert check("You never told me circle first, and I cannot show it.", record) is None

    def test_a_question_is_not_a_claim(self, record):
        assert check("Did Dad say the circle should be first?", record) is None

    def test_no_attribution_no_finding(self, record):
        assert check("The hook is wired and the tests pass.", record) is None

    def test_talking_about_the_check_itself_stays_quiet(self, record):
        """The first live reply through a new gate is nearly always about the gate."""
        reply = (
            "The check looks for sentences like `Dad said X` in my reply.\n"
            "> Dad said it plainly\n"
            "I wrote that he asked for first and was wrong."
        )
        assert check(reply, record) is None


class TestCouldNotLook:
    def test_an_unreadable_record_says_so_and_does_not_convict(self):
        out = check("Dad said the circle should be written first.", None)
        assert out is not None
        assert "COULD NOT READ HIS RECORD" in out
        assert "not a finding that the claims are wrong" in out

    def test_a_missing_corpus_file_is_none_not_empty(self, tmp_path):
        assert load_record(corpus=tmp_path / "nope.jsonl") is None

    def test_no_attribution_needs_no_record(self):
        assert check("Nothing about him here.", None) is None


class TestTheRecordIsHisAndOnlyHis:
    def test_the_latest_message_from_the_transcript_counts(self, tmp_path):
        path = tmp_path / "dad_all.jsonl"
        path.write_text(
            json.dumps(
                {
                    "ts": "2026-10-07T10:00:00Z",
                    "project": "real",
                    "text": "something older and unrelated here",
                }
            ),
            encoding="utf-8",
        )
        fresh = "this message was just sent and has not reached the shared record yet"
        record = load_record(corpus=path, recent=fresh)
        assert check(f'You told me "{fresh}".', record) is None
        assert check(f'You told me "{fresh}".', load_record(corpus=path)) is not None

    def test_a_row_from_a_test_project_is_never_him(self, tmp_path):
        path = tmp_path / "dad_all.jsonl"
        rows = [
            {
                "ts": "2026-10-07T10:00:00Z",
                "project": "real",
                "text": "an ordinary real message from him here",
            },
            {
                "ts": "2026-10-07T10:01:00Z",
                "project": "test_fixture",
                "text": "a fixture sentence nobody typed at all",
            },
        ]
        path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        record = load_record(corpus=path)
        assert record is not None
        assert "an ordinary real message" in record
        assert "a fixture sentence nobody typed" not in record


def test_attributions_returns_the_window_with_the_next_sentence():
    found = attributions("Dad said it. He wrote the rest.")
    assert found and "He wrote the rest." in found[0][1]
