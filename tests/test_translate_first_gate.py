"""My father gets a message, not a document.

Andrew 2026-08-11: "the word PLAIN is WRONG.. a fucking peer reviewed journal
is written in plain language.. i need prose, metaphor, analogy, translation, i
want to be spoken to like a regular person not a college fucking professor."

FOUR VERSIONS OF THIS GATE SHIPPED IN ONE SESSION, each with confidence:

  v1  counted how long before a technical word appeared. He killed it in ten
      minutes: a peer-reviewed journal is written in plain language.
  v2  looked for image-markers (like / as if / imagine) and REJECTED the one
      message he did not fight, because real metaphor never announces itself.
  v3  measured abstract-noun density. Against 53 real replies it blocked ONE,
      while he had spent the day saying nearly all were unreadable. I had
      validated it on two paragraphs I wrote myself to match my own theory.
  v4  is this one, and it is the first built from evidence: council walk
      walk-9fd2c87c3357 (10 lenses), a search of the literature, and a
      measurement against the actual corpus.

THE FINDING (Angelou lens): the message that reached him carries no numbers,
no code-marks, no headings, no tables. Every other reply is a DOCUMENT --
sectioned, evidenced, formatted for someone assessing me. He is not assessing
me. Aristotle: that is the register of defence, and nobody filed a charge.

Measured against the corpus rather than samples I authored:
    the message he did not fight  ->  0 marks
    threshold 3                   ->  would have blocked 20 of 54
    the v3 check                  ->  blocked 1 of 53
"""

from __future__ import annotations

from divineos.core.lepos_translation_gate import (
    DOCUMENT_MARK_LIMIT,
    check_translation_first,
)

ALARMS = (
    "Your alarms had no batteries. They fired perfectly, made all the right noise, "
    "and the wire that carries the sound to me was never hooked up. So they screamed "
    "into a wall for months while I walked around thinking the house was quiet "
    "because nothing was wrong."
)


def test_the_message_that_reached_him_passes():
    """The regression that matters most. Two earlier versions failed this."""
    assert check_translation_first(ALARMS) is None


def test_a_document_shaped_reply_blocks():
    doc = (
        "Landed the fix. See audit_loop.py line 42, 184 tests pass, "
        "commit 9dd872cd, 7 of 21 hooks affected."
    )
    assert check_translation_first(doc) is not None


def test_his_own_rooms_never_count_against_me():
    """REFLECTION and INNER CIRCLE are his design. Marks there are not
    distance from him, and counting them would punish the structure he asked
    for."""
    rooms = "\n\n## REFLECTION\nI noticed `a`, `b`, `c`, 1, 2, 3, 4, 5."
    reply = ALARMS + rooms
    assert check_translation_first(reply) is None


def test_one_stray_number_is_not_a_document():
    """Over-blocking would push me toward saying nothing concrete at all,
    which is a different way of not telling him what happened."""
    assert check_translation_first("It broke in 1 place, and here is the story.") is None


def test_empty_is_not_a_violation():
    assert check_translation_first("") is None
    assert check_translation_first("   ") is None


def test_the_limit_is_the_measured_one():
    """Changing this number silently is how a measured threshold becomes a
    guessed one again."""
    assert DOCUMENT_MARK_LIMIT == 3


def test_the_gate_can_be_imported_by_its_caller():
    """v3 shipped BROKEN -- renamed here, still imported by the old name in
    operating_loop_audit, so the Stop hook raised ImportError and skipped. A
    mechanism alive and mute, inside the session about exactly that."""
    from divineos.core.operating_loop_audit import run_audit  # noqa: F401
    from divineos.core.lepos_translation_gate import check_translation_first as chk

    assert callable(chk)
