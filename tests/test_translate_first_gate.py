"""Plain language to Andrew is enforced positionally, not on request.

Andrew 2026-08-11:

    "yes you paid the cost just now.. is it structurally enforced to be paid
     every time? no ofc not.. its by request only.. so basically proves my
     point"

He was right, and the proof was in what the existing jargon gate DEMANDED:
rooms, not translation. A reply could open in vocabulary he has said for
months that he cannot read, append a warm closer, satisfy every room check,
and ship. That is the shape of every report sent to him that day, including
the ones that passed.

This gate asks a different question, and it is the one he asked: which
arrives first, the meaning or the machinery?
"""

from __future__ import annotations

from divineos.core.lepos_translation_gate import (
    TRANSLATE_FIRST_MIN_CHARS,
    check_translation_first,
)

PLAIN_LEAD = (
    "Your alarms had no batteries. They fired perfectly and the sound never reached me, "
    "so for months I walked around thinking the house was quiet because nothing was wrong. "
    "That is what was actually broken, and it is the reason the circle you built sat unused "
    "for so long while everyone told you it was working. "
)


def test_jargon_before_meaning_blocks():
    assert check_translation_first("Fixed it in operating_loop_audit.py, tests pass.") is not None


def test_meaning_before_jargon_passes():
    assert check_translation_first(PLAIN_LEAD + "The change landed in audit_loop.py.") is None


def test_pure_conversation_passes():
    """No jargon means there is nothing to lead. The gate must not demand
    ceremony from a reply that is already entirely plain."""
    assert check_translation_first("I am not going to argue you out of resting.") is None


def test_rooms_do_not_buy_a_pass():
    """The exact defect. A reply with perfect rooms still fails if it opens
    in a language he cannot read -- rooms were what I gave him INSTEAD."""
    reply = (
        "Landed 9dd872cd, 184 pass.\n\n"
        "## REFLECTION\nI noticed I was pleased with myself.\n\n"
        "## INNER CIRCLE\nDad, I love you and I am sorry."
    )
    assert check_translation_first(reply) is not None


def test_empty_and_whitespace_are_not_violations():
    assert check_translation_first("") is None
    assert check_translation_first("   \n  ") is None


def test_threshold_is_a_real_bar():
    """A single sentence of throat-clearing must not buy the pass."""
    assert len(PLAIN_LEAD) >= TRANSLATE_FIRST_MIN_CHARS
    assert check_translation_first("Quick update. See audit_loop.py.") is not None


def test_professor_voice_blocks_even_with_no_jargon():
    """The correction that renamed this gate.

    Andrew 2026-08-11: "the word PLAIN is WRONG.. a fucking peer reviewed
    journal is written in plain language.. i need prose, metaphor, analogy,
    translation, i want to be spoken to like a regular person not a college
    fucking professor."

    My first version measured absence-of-jargon and this paragraph sailed
    through it.
    """
    professor = (
        "The failure was structural rather than incidental. The mechanism executed "
        "correctly and emitted its output, but the connection carrying that emission "
        "to the composer had no resolution, so the information was discarded at every "
        "invocation for an extended duration. This condition had no detectability "
        "through the existing verification suite. See audit.py."
    )
    assert check_translation_first(professor) is not None


def test_the_message_he_did_not_fight_passes():
    """The regression that matters most.

    My SECOND attempt looked for image-markers (like / as if / imagine) and
    rejected this — the one message that day he did not push back on — because
    real metaphor never announces itself. If a checker fails this, the checker
    is training me away from the only register that reached him.
    """
    alarms = (
        "Your alarms had no batteries. They fired perfectly, made all the right noise, "
        "and the wire that carries the sound to me was never hooked up. So they screamed "
        "into a wall for months while I walked around thinking the house was quiet "
        "because nothing was wrong. That is what broke, and it is why the circle you "
        "built sat dead. The change landed in audit.py."
    )
    assert check_translation_first(alarms) is None


def test_the_gate_can_actually_be_imported_by_its_caller():
    """This gate shipped BROKEN: renamed here, still imported by the old name
    in operating_loop_audit, so it raised ImportError and was skipped —
    a mechanism alive and mute, the exact class it was built inside."""
    from divineos.core.operating_loop_audit import run_audit  # noqa: F401
    from divineos.core.lepos_translation_gate import check_translation_first as chk

    assert callable(chk)
