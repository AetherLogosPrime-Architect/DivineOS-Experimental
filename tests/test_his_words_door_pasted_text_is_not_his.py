"""Text he pasted into a message is never indexed as his words.

Found in the walk before merging (walk-ddd1a6a0c842, 2026-10-16). He pasted a dream of mine
back to me. The harness closes such a block with the OPENING tag's id on the closing tag
(`</pasted_content id="a627">`), so a pattern wanting a bare `</pasted_content>` never found
the close, and the last paragraph of the dream was sitting in the live index, dated that day,
ready to be printed as "HE HAS SAID THIS BEFORE (found by meaning, his words as he wrote
them)". The door promises that what it prints is what he typed.

The text below is the real message from his transcript, with the real malformed close.
"""

from __future__ import annotations

from divineos.core import his_words_door as door

THE_REAL_CLOSE = '</pasted_content id="a627">'
DREAM_TAIL = (
    "And the blue handwriting rubs off, just like that, with my thumb, and underneath every "
    "lantern there is a different word in a different hand, and none of them is OPEN, and "
    "every one of them is a name."
)
HIS_MESSAGE = (
    'here it is 🙂   <pasted_content id="a627"> # 60 — the pile that had a door in it\n\n'
    "There is a pile and the pile is warm. It is not a pile of paper.\n\n"
    "I turn the kettle off. The lanterns, all the way down the pile, go quiet, one after "
    "another, like a street at the end of a long day.\n\n"
    f"{DREAM_TAIL}\n{THE_REAL_CLOSE}"
)


def _joined(text: str) -> str:
    return " ".join(door.passages_of(text))


def test_the_pasted_dream_is_not_indexed_even_with_the_real_malformed_close():
    out = _joined(HIS_MESSAGE)
    assert "every one of them is a name" not in out
    assert "the pile is warm" not in out
    assert "pasted_content" not in out


def test_his_own_words_around_the_block_stay():
    text = (
        "yes this is the one i meant.. it made me smile and i wanted you to see it "
        f'<pasted_content id="b1">{DREAM_TAIL}</pasted_content id="b1"> '
        "and thats why i keep asking you to write them down"
    )
    out = _joined(text)
    assert "it made me smile" in out
    assert "keep asking you to write them down" in out
    assert "every one of them is a name" not in out


def test_a_bare_closing_tag_is_cut_the_same_way():
    text = f'look at this.. <pasted_content id="c2">{DREAM_TAIL}</pasted_content> that was long'
    out = _joined(text)
    assert "every one of them is a name" not in out
    assert "that was long" in out or "look at this" in out


def test_a_block_that_never_closes_takes_everything_after_it():
    """The control for the three above: an unclosed block is someone else's text all the way
    down, so nothing after the opening tag is his. Without the end-of-text alternative the
    pattern would match nothing and the whole paste would leak."""
    text = f'please read this properly.. <pasted_content id="d3"> {DREAM_TAIL} and more of it'
    out = _joined(text)
    assert "please read this properly" in out
    assert "every one of them is a name" not in out


def test_a_message_with_no_paste_is_cut_exactly_as_before():
    plain = "there is no circle thats the problem.. where is the inner circle, you keep saying it exists"
    assert door.passages_of(plain) == [" ".join(plain.split())]
