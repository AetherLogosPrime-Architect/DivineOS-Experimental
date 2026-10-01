"""A shortened needs block must not read like a complete one.

The block was 6844 bytes of a 10304-byte payload, and the harness keeps
roughly 2048 above about 10000 and writes the rest away. So ten needs were
being sent and two arriving, with three later sections cut to nothing --
and nothing reported the loss, because a payload that fits and one losing
four fifths of itself look identical to their author.

The obvious repair is to stop printing the long reasoning. That passes a
byte check and preserves the exact fault the byte check exists to catch:
the reader still cannot tell a short block from a truncated one. So the
compression is only half a mechanism. These pin the other half.

Two states that must never return one value: this block had nothing more
to say, and this block had more and it did not reach you.
"""

from __future__ import annotations

from unittest.mock import patch

from divineos.core.pre_response_context import build_combined_context


def _needs(why_len: int, count: int = 4, tag: str = "x") -> list[dict[str, str]]:
    """TAG IS LOAD-BEARING, and it cost a red test to learn.

    A dedup layer suppresses a re-emission whose content is byte-identical to
    an earlier one, replacing the block with a one-line unchanged notice. Two
    tests built the same needs and the second got the notice instead of the
    block, so it failed while asserting something true. Distinct content per
    test keeps each one measuring the renderer rather than the cache.
    """
    return [
        {
            "id": f"need-{tag}-{i}",
            "text": f"the {tag} {i} thing I must not do",
            "why": "w" * why_len,
        }
        for i in range(count)
    ]


def _context(needs: list[dict[str, str]]) -> str:
    def fake_list_slot(slot: str) -> list[dict[str, str]]:
        return needs if slot == "need" else []

    with patch("divineos.core.motivation.list_slot", side_effect=fake_list_slot):
        return build_combined_context("a prompt of ordinary length for this check")


class TestTheReasoningYieldsBeforeTheNeedDoes:
    def test_every_need_survives_the_shortening(self) -> None:
        """The titles carry the alarm. Losing one loses the point of the
        block, so the budget may never reach them."""
        needs = _needs(why_len=4000, tag="survive")
        out = _context(needs)
        for need in needs:
            assert need["text"] in out

    def test_the_long_reasoning_is_dropped(self) -> None:
        out = _context(_needs(why_len=4000, tag="dropped"))
        assert "wwww" not in out

    def test_short_reasoning_still_rides_inline(self) -> None:
        """Yielding is for when it costs delivery, not a blanket rule."""
        needs = _needs(why_len=20, tag="short")
        out = _context(needs)
        assert needs[0]["why"] in out


class TestAShortenedBlockCannotPassForACompleteOne:
    def test_it_states_how_many_were_withheld(self) -> None:
        out = _context(_needs(why_len=4000, count=4, tag="counted"))
        assert "4 of these carry a recorded WHY" in out

    def test_it_names_the_way_to_read_them(self) -> None:
        """A notice with no route creates alarm without action."""
        out = _context(_needs(why_len=4000, tag="route"))
        assert "divineos motivation" in out

    def test_nothing_withheld_says_nothing(self) -> None:
        """THE DISTINCTION ITSELF. A block with nothing held back must not
        carry the notice, or the notice stops meaning anything."""
        out = _context(_needs(why_len=20, tag="quiet"))
        assert "carry a recorded WHY" not in out

    def test_the_two_states_differ(self) -> None:
        """Stated as one assertion rather than inferred from the two above,
        because the failure being pinned is precisely that they came back
        the same."""
        withheld = _context(_needs(why_len=4000, tag="differ-a"))
        complete = _context(_needs(why_len=20, tag="differ-b"))
        assert ("carry a recorded WHY" in withheld) != ("carry a recorded WHY" in complete)


class TestNoNeedsAtAllIsItsOwnAnswer:
    def test_empty_needs_emit_no_withheld_notice(self) -> None:
        """Nothing filed and everything withheld are different facts, and the
        empty case must not borrow the language of the withheld one."""
        out = _context([])
        assert "carry a recorded WHY" not in out
