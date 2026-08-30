"""His clock is not my fabrication.

The wallclock gate exists because I borrow days I do not have -- "tomorrow",
"next session" -- almost always for RHYTHM rather than meaning, in a closing
beat where a sentence wants one more stress.

First false positive, 2026-08-11. Andrew wrote "its only tuesday and im at 52%
and it resets on saturday". I reflected his own week back to him and the gate
fired on "by tuesday" as if I had invented a day. The wallclock prime says the
opposite in its own text: his day is sourceable, and quotable when the reply
needs a time. Casting MY time onto him is the failure. Repeating the day he
just told me he is living in is grounding.
"""

from __future__ import annotations

from divineos.core.lepos_translation_gate import check_wallclock_fabrication

HIS = "its only tuesday and im at 52% and it resets on saturday"


def test_reflecting_his_day_back_is_grounded():
    reply = "Half the week gone by tuesday, reset on saturday. That is not a comfortable margin."
    assert check_wallclock_fabrication(reply, HIS) is None


def test_my_own_borrowed_day_still_blocks():
    """The gate must keep its teeth. This is the whole reason it exists."""
    assert check_wallclock_fabrication("I will look at it tomorrow.", HIS) is not None
    assert check_wallclock_fabrication("I will pick this up next session.", HIS) is not None


def test_without_his_words_the_gate_is_unchanged():
    """Absence of his message must never be read as permission."""
    reply = "Half the week gone by tuesday."
    assert check_wallclock_fabrication(reply, None) is not None
    assert check_wallclock_fabrication(reply, "") is not None


def test_anchor_matching_not_whole_phrase():
    """The first draft compared whole phrases and never fired.

    He said "its only tuesday"; I said "by tuesday". Same day, different
    connector. A correct idea shipped as a check that could never match --
    which is the shape of half the failures in this substrate.
    """
    assert check_wallclock_fabrication("done by tuesday", "tuesday is rough") is None
    assert check_wallclock_fabrication("done by friday", "tuesday is rough") is not None
