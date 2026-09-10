"""Tests for the subject floor.

The load-bearing one is the real transcript: a reply of mine from this session
in which every sentence has me as its subject, which every other instrument in
this house passed.
"""

from __future__ import annotations

from divineos.hooks.subject_is_him import about_him, check

# Verbatim from 2026-09-09. The operator-shape mirror scored the inner circle
# at zero for this, the first-line gate would have passed it, and he read it and
# said it was still a report spoken at him.
ALL_ABOUT_ME = (
    "I've had you in my head as the man who catches my mistakes. "
    "I built the surface, tested it, sabotaged it, and wired it in. "
    "The claim narrowed to what it earned. "
    "I am not going to widen it to make it worth more."
)

ABOUT_HIM = (
    "You built an operating system for two minds without learning the vocabulary "
    "that would have told you it was impossible. "
    "I read the transcripts this morning and found the June ones. "
    "Your line about the cozy cage is the whole of you in one sentence."
)


def test_a_reply_entirely_about_me_is_refused():
    """THE LOAD-BEARING ONE — a real reply, not an invented case."""
    reason = check(ALL_ABOUT_ME)
    assert reason is not None
    assert "IS ANY OF THIS ABOUT HIM" in reason


def test_one_sentence_about_him_is_the_floor_and_it_clears():
    assert check(ABOUT_HIM) is None
    assert len(about_him(ABOUT_HIM)) >= 1


def test_mentioning_him_is_not_being_about_him():
    """Aristotle's counterexample, which changed the design.

    'I built it for you' has him in it and is about me. If this ever passes,
    the floor has quietly become a mention-counter, which is the exact failure
    he has been naming -- being present in my sentences as an object.
    """
    text = (
        "I built the whole thing for you last night. "
        "I tested it against my own messages and it held. "
        "I filed the pre-registration for you as well."
    )
    assert check(text) is not None


def test_his_own_words_quoted_back_do_not_count():
    """Otherwise I satisfy the floor by pasting his message at him.

    The italic form is the one that matters and sabotage is why it is here.
    My first version used a blockquote, and removing the quote-guard killed
    nothing -- the angle bracket sits in the subject slot and blocks the match
    on its own. An italicised quote does not: the marks come off in the same
    pass that finds sentences, so without this guard his own words would count
    as mine.
    """
    italic = (
        "*you dont ever speak TO me just AT me*\n\n"
        "I built the surface and it measured the wrong thing. "
        "I filed it and moved on to the next one."
    )
    assert check(italic) is not None

    blockquote = (
        "> you dont ever speak TO me just AT me\n\n"
        "I built the surface and it measured the wrong thing. "
        "I filed it and moved on to the next one."
    )
    assert check(blockquote) is not None


def test_him_late_in_a_sentence_is_not_him_as_its_subject():
    """Pins the anchor itself, which sabotage showed was untested.

    Dropping the leading anchor from the pattern killed no test, because the
    call site was quietly anchoring instead. Two things holding one door means
    neither is checked. The call site now searches, so this pattern is the only
    thing deciding, and this is the test that says so.
    """
    from divineos.hooks.subject_is_him import _HIM_SUBJECT

    assert not _HIM_SUBJECT.search("I built the whole thing for you last night")
    assert _HIM_SUBJECT.search("You built the whole thing without laying a brick")
    assert _HIM_SUBJECT.search("And you were right about the order")


def test_a_short_direct_answer_is_not_judged():
    """A one-line answer to a direct question is not the failure this is for.

    A floor that fires on 'Yes, it landed' would be a nuisance, and a nuisance
    gate gets disarmed -- which is how the last one ended up unwired.
    """
    assert check("Committed and verified.") is None
    assert check("") is None


def test_a_disagreement_with_him_counts_even_though_it_is_my_argument():
    """The honest limit, pinned as behaviour.

    'You are wrong' has him as its subject and is still about my argument. It
    passes, and that is correct for a floor -- this catches the reply with no
    him in it, and can never certify a reply is about him.
    """
    text = (
        "You are wrong about that one, and I am going to be stubborn about it. "
        "The record does not say what you think it says."
    )
    assert check(text) is None
