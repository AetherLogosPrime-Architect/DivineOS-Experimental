"""A long reply must open with a plain-language summary.

Andrew 2026-08-06: "i just need more of a summary section as well when you go
off on tears like this so im not lost." The load-bearing tests are the two that
keep it from becoming a tax on ordinary replies: short replies must never be
asked for one, and adding a summary must be able to SATISFY the rule rather
than pushing the reply further past the threshold.
"""

from __future__ import annotations

from divineos.core import summary_room as sr

LONG_WORK = "This is technical work content that runs on and on. " * 60
SHORT_WORK = "Fixed the thing. One line."


class TestWhenItIsOwed:
    def test_long_reply_without_a_summary_is_missing_one(self):
        v = sr.assess(LONG_WORK + "\n\n## REFLECTION\nsomething interior")
        assert v.missing is True
        assert "SUMMARY ROOM MISSING" in sr.render_block(v)

    def test_short_reply_is_never_asked_for_one(self):
        """The rule exists for tears, not for every reply."""
        v = sr.assess(SHORT_WORK + "\n\n## REFLECTION\nx")
        assert v.needed is False and sr.render_block(v) == ""

    def test_adding_a_summary_satisfies_it(self):
        v = sr.assess("## SUMMARY\nI fixed a thing and it works now.\n\n" + LONG_WORK)
        assert v.present is True and v.missing is False

    def test_length_is_measured_without_the_summary(self):
        """Otherwise a summary could push a borderline reply over the line and
        the rule would demand what it had just been given."""
        body = "x" * (sr._LONG_REPLY_CHARS - 50)
        v = sr.assess("## SUMMARY\n" + "plain words here. " * 20 + "\n\n" + body)
        assert v.needed is False

    def test_interior_rooms_do_not_count_toward_length(self):
        """REFLECTION and INNER CIRCLE are already plain-language rooms."""
        v = sr.assess(SHORT_WORK + "\n\n## REFLECTION\n" + LONG_WORK)
        assert v.needed is False


class TestRegister:
    def test_a_summary_in_the_works_own_register_is_flagged(self):
        v = sr.assess(
            "## SUMMARY\nI changed hook_router.py and summary_room.py, ran "
            "divineos prereg file, and commit 84fccf55 landed the self_demotion "
            "detector.\n\n" + LONG_WORK
        )
        assert v.too_technical is True
        assert "table of contents" in sr.render_block(v)

    def test_plain_summary_passes(self):
        v = sr.assess(
            "## SUMMARY\nI found that one of my own checks was printing a number "
            "that could not be true, and fixed it so it names the sentence it is "
            "actually talking about.\n\n" + LONG_WORK
        )
        assert v.too_technical is False and sr.render_block(v) == ""

    def test_a_few_identifiers_are_allowed(self):
        """Loose on purpose -- this catches a summary written in the work's
        register, not a stray name that genuinely belongs."""
        v = sr.assess(
            "## SUMMARY\nI fixed the thing that reads letters, in letter_claims, "
            "so it finds files named the way people actually say them.\n\n" + LONG_WORK
        )
        assert v.too_technical is False

    def test_alternate_headers_are_accepted(self):
        for header in ("## SUMMARY", "## WHAT I DID", "## IN SHORT"):
            assert sr.assess(header + "\nplain words.\n\n" + LONG_WORK).present is True


def test_title_case_headers_are_recognised():
    """Andrew 2026-08-08: 'this is too much jargon for me to parse dear'.

    The reply he could not read HAD a summary -- written '## Summary', title
    case. Both header patterns were case-sensitive, so the mechanism saw
    neither room. Title case is how I actually write; a pattern that cannot
    match my real output is an absent check that reports as a passing one.
    """
    reply = (
        "## Summary\n\n"
        "`origin/main...HEAD` returned `0 144`, and the `GIT_DIR` scrub in "
        "`check_push_readiness.sh` is wired at all three pytest handoffs; "
        "`system_load_gate` and `parallel_sizing` are settled.\n\n"
        "## Reflection\n\nSomething interior.\n"
    )
    v = sr.assess(reply)

    # The summary room is seen at all -- the bug made this False.
    assert v.present is True

    # Reflection bounds the work section, so interior text is not counted
    # as work Andrew must follow.
    assert "Something interior" not in sr._work_section(reply)

    # And now that present is True, the jargon check is actually reachable.
    assert v.too_technical is True
    assert v.jargon_terms
    assert "SUMMARY ROOM IS WRITTEN IN THE WORK'S OWN REGISTER" in sr.render_block(v)


def test_uppercase_headers_still_work():
    """The fix widens; it must not trade one case for the other."""
    reply = "## SUMMARY\n\nPlain words about what changed.\n\n## REFLECTION\n\nInterior.\n"
    v = sr.assess(reply)
    assert v.present is True
    assert v.too_technical is False
