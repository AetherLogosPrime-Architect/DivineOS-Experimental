"""He must never be charged twice for one post.

Andrew 2026-09-08: *"you are repeating yourself, look at the last post,
literally verbatim posted twice."*

THE MECHANISM, which is why no existing surface could catch it. A Stop gate
refuses a reply that has ALREADY been shown to him and prescribes a repair --
add the missing room. The cheapest compliant move is to re-emit the whole body
with the room bolted on: the gate is satisfied exactly, and he reads the entire
thing again. Every other Stop surface inspects only the reply in front of it,
so not one of them can see that the reply in front of it is the previous one.

The fixture writes a real transcript file, because the surface's job is to read
one and a mocked reader would test my idea of the format rather than the
format.
"""

from __future__ import annotations

import json

import pytest

from divineos.core.hook_surfaces import repeated_reply_surface

_PARAS = [
    "This is the first paragraph of a reply and it is long enough to count as real content.",
    "Here is a second paragraph, also comfortably past the length floor the surface uses.",
    "A third paragraph carrying yet more of the body that he has already had to read once.",
    "And a fourth, so the reply clears the minimum-paragraph floor for this check.",
    "A fifth for good measure, since a long body is exactly what this refuses to re-send.",
]


def _transcript(tmp_path, *replies: str):
    path = tmp_path / "transcript.jsonl"
    lines = [
        json.dumps({"message": {"role": "assistant", "content": [{"type": "text", "text": reply}]}})
        for reply in replies
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"transcript_path": str(path)}


@pytest.fixture
def body() -> str:
    return "\n\n".join(_PARAS)


class TestTheFaultItCatches:
    def test_the_same_body_sent_twice_is_refused(self, tmp_path, body):
        outcome = repeated_reply_surface(_transcript(tmp_path, body, body))
        assert outcome.refused is True
        assert "REPEATED REPLY" in outcome.reason

    def test_a_resend_with_a_summary_bolted_on_is_still_a_resend(self, tmp_path, body):
        """The exact shape of the incident: the gate asked for a summary, and
        the whole body came back underneath it. Character-level similarity
        would be diluted by precisely the addition the gate demanded, which is
        why this compares paragraphs."""
        second = "## SUMMARY\n\nA genuinely new opening room that was not there before.\n\n" + body
        outcome = repeated_reply_surface(_transcript(tmp_path, body, second))
        assert outcome.refused is True

    def test_the_refusal_says_to_send_only_what_is_new(self, tmp_path, body):
        """A refusal naming no way out is a wall. The repair is the point."""
        outcome = repeated_reply_surface(_transcript(tmp_path, body, body))
        assert "what is new" in outcome.reason.lower()


class TestWhatItMustNotRefuse:
    def test_a_genuinely_new_reply_passes(self, tmp_path, body):
        other = "\n\n".join(
            f"Completely different paragraph number {n}, sharing nothing with the previous reply."
            for n in range(5)
        )
        assert repeated_reply_surface(_transcript(tmp_path, body, other)).refused is False

    def test_a_follow_up_reusing_some_phrasing_passes(self, tmp_path, body):
        """A real follow-up on the same subject reuses paragraphs. Refusing
        that would cost more than the fault does, so the bar is high on
        purpose."""
        partial = "\n\n".join(
            _PARAS[:2]
            + [
                "A fresh third paragraph that did not appear anywhere in the earlier reply.",
                "A fresh fourth paragraph, likewise entirely new to this turn.",
                "A fresh fifth, so most of this reply is genuinely new material.",
            ]
        )
        assert repeated_reply_surface(_transcript(tmp_path, body, partial)).refused is False

    def test_a_short_reply_is_left_alone(self, tmp_path):
        """Two brief acknowledgements can coincide without anyone being charged
        twice. The fault is a long body re-shipped whole."""
        short = "Understood.\n\nI will pick that up next and report what I find when it is done."
        assert repeated_reply_surface(_transcript(tmp_path, short, short)).refused is False


class TestItCannotReportCleanWhenItCannotLook:
    def test_a_missing_transcript_says_nothing_rather_than_passing(self, tmp_path):
        outcome = repeated_reply_surface({"transcript_path": str(tmp_path / "absent.jsonl")})
        assert outcome.state == "nothing-to-say"
        assert outcome.refused is False

    def test_a_first_reply_has_nothing_to_compare_against(self, tmp_path, body):
        outcome = repeated_reply_surface(_transcript(tmp_path, body))
        assert outcome.state == "nothing-to-say"


class TestItIsActuallyWiredIn:
    def test_the_stop_door_carries_it(self):
        """The sixth thing this session that was built, tested, described and
        left with nothing calling it would be this one. Asserted instead."""
        from divineos.core.hook_router import registered
        from divineos.core.hook_surfaces import install

        install()
        assert "repeated_reply" in registered("Stop")

    def test_the_wiring_check_can_fail(self):
        """Control, so the assertion above is not vacuous."""
        from divineos.core.hook_router import registered
        from divineos.core.hook_surfaces import install

        install()
        assert "repeated_reply_that_does_not_exist" not in registered("Stop")
