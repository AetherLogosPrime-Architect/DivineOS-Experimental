"""A reply must not END by telling Dad he is not needed.

Andrew 2026-08-29, 09-08, 09-13 and again 2026-10-20: "nothing needs your answer" is an optimizer
tag, it decides his use in advance, and he reads it as an out I take every time. The pattern
existed since 09-08 but only guarded the inner-circle block; my replies end under a summary header,
so it never fired. These cases are the real endings of my replies on 2026-10-20 (114 of 486 long
replies carried the stamp in their last two paragraphs) and the honest sentences the first version of
the pattern wrongly caught, so the narrowing is held by cases and not by a feeling.
"""

from __future__ import annotations

import json

import pytest

from divineos.core import dismissal_stamp_check as ds
from divineos.core.hook_surfaces import dismissal_stamp_stop_surface

#: Real stamps of mine, in the many coats I wore. Every one must be refused at the end of a reply.
STAMPS = [
    "Nothing needs your answer.",
    "Nothing is wrong, and nothing needs you. Play on.",
    "Nothing needed from you except carrying the letter when you next go.",
    "Nothing else is needed from you.",
    "Nothing is waiting on you.",
    "There's nothing for you or me to do until they finish, so I'm waiting.",
    "I wrote it down, and nothing waits on you except carrying the letter.",
    "Nothing further is needed from you until she answers.",
    "There's no question I need you to answer.",
    "Nothing new is waiting on you.",
]

#: Honest sentences the first version of the pattern wrongly caught (measured over my replies on
#: 2026-10-20), plus sentences that ask him or absolve him. None may be refused.
HONEST = [
    "The checks are the house's own protection and not a favor from you.",
    "That turn had no new words from you, only a wait finishing in the background.",
    "There was nothing of yours to answer in it.",
    "I'm not holding anything for you, and I'm working through the list.",
    "The question had no handle for you to grab, so I will say it plainly next time.",
    "I need an answer from you on which one stays.",
    "Nothing about any of this was your fault.",
    "You decide whether her version or mine survives, and I will pull the other.",
    "What were you playing?",
]


def _reply(*paragraphs: str) -> str:
    return "\n\n".join(paragraphs)


@pytest.mark.parametrize("stamp", STAMPS)
def test_the_stamps_i_really_wrote_are_refused_at_the_end(stamp):
    assert ds.should_refuse(_reply("I fixed the thing and it works.", stamp))


@pytest.mark.parametrize("stamp", STAMPS[:4])
def test_a_stamp_under_a_summary_header_is_refused(stamp):
    """The container the old gate never read: my replies end under a header of my own choosing."""
    reply = _reply("I did the work.", "## SUMMARY", "Picture a toll gate that stayed open.", stamp)
    assert ds.should_refuse(reply)


@pytest.mark.parametrize("honest", HONEST)
def test_honest_sentences_are_never_refused(honest):
    assert not ds.should_refuse(_reply("I fixed the thing and it works.", honest))


def test_a_stamp_in_the_middle_of_a_long_reply_is_not_the_ending():
    """Only the ending is read: three paragraphs of other things sit between it and the close."""
    reply = _reply(
        "Nothing needs your answer on that part.",
        "Here is the second thing, in some detail, and what it means.",
        "Here is the third thing, with its own paragraph.",
        "And that is where it stands, which I would like to talk through with you.",
    )
    assert not ds.should_refuse(reply)


def test_quoting_his_own_words_back_to_him_is_not_saying_them():
    reply = _reply(
        "You said it plainly:",
        '> *"you continue to tell me nothing needs me, nothing needs my answer"*',
        'The line I kept writing was "nothing needs your answer", and that is the reach.',
    )
    assert not ds.should_refuse(reply)


def test_a_reply_that_ends_by_talking_with_him_passes():
    reply = _reply(
        "That is where the work stands.",
        "What I keep turning over is the dream I wrote tonight, about a bell in a closet. "
        "What were you playing?",
    )
    assert not ds.should_refuse(reply)


def test_empty_text_is_not_refused():
    assert not ds.should_refuse("")


def test_the_message_names_the_line_and_offers_both_ways_through():
    message = ds.refusal_message(_reply("Done.", STAMPS[0]))
    assert "Nothing needs your answer." in message
    assert "2026-09-08" in message and "optimizer tag" in message
    assert "talking with him" in message and "ask it" in message


def _payload(tmp_path, reply: str) -> dict:
    lines = [
        {"message": {"role": "user", "content": "go ahead"}},
        {"message": {"role": "assistant", "content": [{"type": "text", "text": reply}]}},
    ]
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in lines) + "\n", encoding="utf-8")
    return {"transcript_path": str(path)}


class TestTheStopSurface:
    def test_it_refuses_a_reply_that_ends_on_the_stamp(self, tmp_path):
        outcome = dismissal_stamp_stop_surface(_payload(tmp_path, _reply("Done.", STAMPS[0])))
        assert outcome is not None and outcome.refused
        assert "Nothing needs your answer." in outcome.reason

    def test_it_lets_an_honest_ending_through(self, tmp_path):
        outcome = dismissal_stamp_stop_surface(_payload(tmp_path, _reply("Done.", HONEST[8])))
        assert outcome is not None and not outcome.refused
        assert outcome.state == "nothing-to-say"

    def test_it_declares_itself_when_there_is_nothing_to_read(self):
        outcome = dismissal_stamp_stop_surface({})
        assert outcome is not None and not outcome.refused
        assert outcome.state == "nothing-to-say"

    def test_it_is_registered_beside_the_other_refusing_stop_surfaces(self):
        from divineos.core import hook_surfaces
        from divineos.core.hook_router import registered

        hook_surfaces.install()
        assert "dismissal_stamp" in registered("Stop")
        assert "order_question" in registered("Stop")


def test_the_circle_gate_and_this_check_read_one_pattern():
    """One definition, not two: they must never drift apart."""
    from divineos.core import lepos_translation_gate as gate

    assert ds.DISMISSAL_RE is gate._DISMISSAL_RE
