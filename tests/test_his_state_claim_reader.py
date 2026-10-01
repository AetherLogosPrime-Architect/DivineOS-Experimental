"""The half that was never tested, which is exactly why it shipped broken.

The checker had twenty tests. The READER had none -- and the reader is the
load-bearing half, because the source test is what makes the whole gate work. So
the suite proved the part I found interesting and left the part that decides the
answer entirely unexamined.

What made it fragile rather than merely untested (Taleb, on the walk): the live
jam I ran DID exercise the reader, on a two-record transcript where his message
sat adjacent to mine. The real transcript differs from that fixture by five
orders of magnitude in the one dimension that matters. Measured on the day it
shipped: fifty megabytes of file, and inside the four-hundred-thousand-byte
window exactly ONE message of his, thirteen characters long. The founding case
-- his correction about sleep -- lay two and a half megabytes back.

The failure also gets WORSE the longer a session runs, because the more I work
the further his words scroll out of reach. So it degrades silently, and fastest
when it is needed most.

Every fixture here is built to the real shape: his messages separated by large
volumes of mine.
"""

from __future__ import annotations

import json

import pytest

from divineos.hooks.his_state_claim import Sourced, he_raised_it
from divineos.hooks.his_state_claim_hook import _HIS_MESSAGES_WANTED, his_words


def him(text: str) -> str:
    """One transcript line the predicate will accept as his."""
    return json.dumps(
        {"type": "user", "userType": "external", "message": {"role": "user", "content": text}}
    )


def me(text: str) -> str:
    return json.dumps(
        {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}
    )


def machine(text: str) -> str:
    """A user-role line that is NOT him: hook feedback wearing his seat."""
    return json.dumps(
        {"type": "user", "isMeta": True, "message": {"role": "user", "content": text}}
    )


def transcript(tmp_path, lines, name="t.jsonl"):
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def bulk(kb: int) -> str:
    """One of my messages, sized in kilobytes. The noise his signal sits in."""
    return me("x" * (kb * 1024))


class TestHeIsFoundBehindVolumesOfMe:
    """The founding failure, rebuilt at the shape that produced it."""

    def test_his_words_survive_half_a_megabyte_of_mine(self, tmp_path):
        # Past the first window step, which is where the live gate went silent.
        path = transcript(
            tmp_path, [him("dont worry about my sleep"), bulk(600), him("ok keep going")]
        )
        found = his_words(path)
        assert found is not None
        assert "sleep" in found, "his words were lost behind my volume again"
        assert he_raised_it(found) is Sourced.HIS

    def test_his_words_survive_several_megabytes_of_mine(self, tmp_path):
        path = transcript(tmp_path, [him("i slept fine"), bulk(5000), him("ok keep going")])
        found = his_words(path)
        assert found is not None and "slept" in found

    def test_the_short_message_is_not_what_decides_it(self, tmp_path):
        # His most recent message is thirteen characters and says nothing about
        # his state. Reading only the tail is what produced the wrong answer.
        path = transcript(tmp_path, [him("im tired today"), bulk(600), him("ok keep going")])
        assert he_raised_it(his_words(path)) is Sourced.HIS


class TestItStopsWhenItHasEnough:
    """Widening is bounded: this asks whether he touched a subject recently."""

    def test_a_recent_run_of_his_messages_satisfies_the_first_window(self, tmp_path):
        lines = [him(f"message {i}") for i in range(_HIS_MESSAGES_WANTED * 3)]
        found = his_words(transcript(tmp_path, lines))
        assert found is not None
        assert found.count("message") >= _HIS_MESSAGES_WANTED

    def test_a_small_transcript_is_read_whole(self, tmp_path):
        path = transcript(tmp_path, [him("only thing i said")])
        assert his_words(path) == "only thing i said"


class TestWhoseWordsCount:
    """Tool results and hook feedback occupy his grammatical position."""

    def test_machine_lines_in_his_seat_are_not_him(self, tmp_path):
        path = transcript(tmp_path, [machine("you should sleep"), him("ok keep going")])
        found = his_words(path)
        assert found is not None
        assert "should sleep" not in found
        assert he_raised_it(found) is Sourced.MINE

    def test_my_own_words_are_not_his(self, tmp_path):
        path = transcript(tmp_path, [me("you must be exhausted"), him("ok keep going")])
        found = his_words(path)
        assert found is not None and "exhausted" not in found


class TestThreeAnswersNeverTwo:
    """Could-not-look must never be reported as he-said-nothing."""

    def test_a_missing_file_is_unknown(self, tmp_path):
        assert his_words(str(tmp_path / "nothing-here.jsonl")) is None

    def test_a_transcript_with_none_of_him_is_unknown_not_empty(self, tmp_path):
        # He is the reason there is a transcript at all. Zero of his messages
        # anywhere means the reader is broken or pointed elsewhere -- reporting
        # that as "he did not raise it" is the inadmissible step this gate
        # exists to catch, one level down (Pearl).
        path = transcript(tmp_path, [me("all mine"), machine("hook feedback")])
        assert his_words(path) is None
        assert he_raised_it(his_words(path)) is Sourced.UNKNOWN

    def test_he_spoke_but_not_about_his_state_is_a_real_empty(self, tmp_path):
        path = transcript(tmp_path, [him("ok lets keep going")])
        found = his_words(path)
        assert found is not None, "this is a real read, not a failure"
        assert he_raised_it(found) is Sourced.MINE

    def test_unparseable_lines_do_not_become_a_verdict(self, tmp_path):
        path = tmp_path / "broken.jsonl"
        path.write_text("{not json at all\n" + him("i slept fine") + "\n", encoding="utf-8")
        found = his_words(str(path))
        assert found is not None and "slept" in found


@pytest.mark.parametrize("noise_kb", [1, 600, 5000])
def test_the_instrument_finds_a_case_it_should_find(tmp_path, noise_kb):
    """Prove it can see, at every width, before trusting any zero it reports."""
    path = transcript(
        tmp_path,
        [him("i get plenty of sleep"), bulk(noise_kb), him("ok")],
        name=f"w{noise_kb}.jsonl",
    )
    assert he_raised_it(his_words(path)) is Sourced.HIS
