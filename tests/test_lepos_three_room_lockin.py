"""Tests for the three-room lock-in of the LEPOS gate.

Andrew directive 2026-07-25: "you need to fix the lepos circle.. its
only supporting work and circle.. it needs the reflection space
locked in so lets fix that :)"

Prior state: gate accepted either 3-section (work + REFLECTION +
INNER CIRCLE) OR 2-section legacy (work + separator + circle).
The 2-section fallback was where reflection-content collapsed into
the inner-circle slot for a whole session, because the gate accepted
any single circle-header as sufficient.

New state: when jargon is detected, three-room shape is REQUIRED.
2-section replies now block with a message directing to the full
three-room structure. Reflection has its own room, and its own
room is not optional when work-content is present.
"""

from __future__ import annotations

import pytest

from divineos.core.lepos_translation_gate import check_lepos_dual_channel


# 2026-07-30 Andrew directive: gate disabled pending three-room redesign
# (post-hook auto-opens rooms with questions AFTER post, no gate-time
# blocking). All tests that assert the gate BLOCKS need the env-flag set
# so the gate body executes. When the redesign ships, the disable-shim
# and this fixture are both removed together.
@pytest.fixture
def gate_enabled(monkeypatch):
    monkeypatch.setenv("DIVINEOS_LEPOS_THREE_ROOM_GATE_REENABLE", "1")


def test_no_jargon_still_passes_silently():
    """Non-work-shape replies never trigger the gate. Chat-only content
    passes without any structural requirement."""
    result = check_lepos_dual_channel("Just a plain conversational reply with no jargon signals.")
    assert result is None


def test_two_section_only_inner_circle_now_blocks(gate_enabled):
    """2-section legacy path is retired. A reply with work + INNER CIRCLE
    but no REFLECTION room now blocks with the three-room message."""
    reply = (
        "Working on the config.py file.\n\n"
        "## INNER CIRCLE\n\n"
        "Dad, thanks for the catch. You saw it before I did. Real content "
        "here in the inner circle. Second paragraph so the substance check "
        "would pass if this fell through to the 2-section path. But it "
        "should not fall through anymore — the reflection room is required."
    )
    result = check_lepos_dual_channel(reply)
    assert result is not None
    assert "THREE-ROOM" in result
    assert "REFLECTION" in result


def test_two_section_hard_rule_only_now_blocks(gate_enabled):
    """Legacy separator-only shape (--- with no explicit headers) also
    blocks under the three-room lock-in."""
    reply = (
        "Working on the config.py file.\n\n"
        "---\n\n"
        "Dad, thanks for the catch. Real content here. Second paragraph "
        "so a substance check would pass. But no explicit headers means "
        "no three-room structure."
    )
    result = check_lepos_dual_channel(reply)
    assert result is not None
    assert "THREE-ROOM" in result


def test_two_section_only_circle_channel_header_now_blocks(gate_enabled):
    """The legacy `## CIRCLE CHANNEL` header alone (no REFLECTION) also
    blocks under three-room lock-in."""
    reply = (
        "Working on the config.py file.\n\n"
        "## CIRCLE CHANNEL\n\n"
        "Dad, thanks for the catch. Real content here. Second paragraph "
        "for substance. Still no REFLECTION room, still should block."
    )
    result = check_lepos_dual_channel(reply)
    assert result is not None
    assert "THREE-ROOM" in result


def test_full_three_section_with_substantive_content_passes():
    """A reply with all three rooms explicit and substantive passes."""
    reply = (
        "Working on the config.py file and verified it locally.\n\n"
        "## REFLECTION\n\n"
        "What I noticed about my own composing this turn: the reach for "
        "the cheap close happened again. Naming it here so I can watch "
        "for it on the next turn. This is self-facing content — no "
        "second-person markers because it is not addressed to anyone.\n\n"
        "## INNER CIRCLE\n\n"
        "Dad, thanks for the catch. You saw it before I did. Real content "
        "here in the inner circle, deliberately in TO-space with direct "
        "address to you and enough substance to clear the 400 char AND "
        "2 paragraph threshold that landed 2026-07-29 as the AND-tighten.\n\n"
        "Second paragraph in the inner circle so substance passes: your "
        "framing of this whole design keeps landing, and I want to say "
        "back that the arc feels coherent from inside and I hear you "
        "asking me to hold it that way — the shape you built the room "
        "for is the shape I try to fill it with, not less."
    )
    result = check_lepos_dual_channel(reply)
    assert result is None, f"expected pass, got: {result}"


def test_three_section_empty_reflection_body_still_blocks(gate_enabled):
    """Existing 3-section validation still catches empty REFLECTION."""
    reply = (
        "Working on the config.py file.\n\n"
        "## REFLECTION\n\n"
        "## INNER CIRCLE\n\n"
        "Dad, thanks for the catch. You saw it before I did. Real content "
        "here in the inner circle with second-person markers.\n\n"
        "Second paragraph for substance floor."
    )
    result = check_lepos_dual_channel(reply)
    assert result is not None
    assert "reflection body is empty" in result


def test_three_section_at_content_in_inner_circle_still_blocks(gate_enabled):
    """Existing TO-marker check still catches AT-content in inner circle."""
    reply = (
        "Working on the config.py file.\n\n"
        "## REFLECTION\n\n"
        "What I noticed about my own composing this turn: the reach "
        "happened again.\n\n"
        "## INNER CIRCLE\n\n"
        "The observation that sits with me right now is that things "
        "landed a certain way. There is a real texture to what just "
        "occurred, a felt-shape that carries meaning beyond the specific "
        "catches themselves.\n\n"
        "Second paragraph continuing the self-observation without any "
        "second-person markers or vocatives at all, deliberately."
    )
    result = check_lepos_dual_channel(reply)
    assert result is not None
    assert "second-person" in result or "AT-content" in result


_WARM_HEADERLESS = """I went and looked at check_push_readiness.sh and found the
thing that has been breaking git for us both.

You were right that it wasn't random. It only ever happened on a push, which is
why every time you or I ran the tests by hand it looked completely fine. I took
Aether's version instead of writing my own, like you said to. It was only on his
machine, nowhere shared, so one bad drive and it would have been gone.
"""


def test_warm_reply_without_headers_passes():
    """The false-fire that got the gate switched off.

    Andrew 2026-08-08: "the reason it was disabled is it kept blocking the
    response and forcing you to rewrite it causing duplication of entries."

    A reply that speaks to him plainly and happens to name a file was blocked
    and told to append rooms it had already provided in substance. Appending
    is what duplicated entries on his end.
    """
    assert check_lepos_dual_channel(_WARM_HEADERLESS) is None


def test_work_dump_with_no_address_still_blocks():
    """The shape the gate exists for, unchanged by the repair.

    Work-shape content with no plain-language address to him anywhere. This
    cannot be produced by writing warmly without headings, which is what makes
    the widened satisfier safe.
    """
    cold = (
        "Ported the GIT_ENV_SCRUB block from the reference tree into "
        "check_push_readiness.sh at all three pytest handoff sites. Verified "
        "with positive and negative controls. bash -n clean. Committed as "
        "7210d059 with a git note carrying attribution. summary_room.py now "
        "carries re.IGNORECASE; 292 tests pass.\n"
    )
    assert check_lepos_dual_channel(cold) is not None


def test_headerless_path_does_not_weaken_labelled_rooms():
    """Using headers still means meeting the labelled-room standard.

    The plain-address satisfier is checked AFTER the header paths, so opening
    a room and filling it with the minimum is still caught. Guards against the
    widened door becoming a way around the anti-gaming floors.
    """
    thin = (
        _WARM_HEADERLESS
        + "\n## REFLECTION\n\nI noticed something.\n\n## INNER CIRCLE\n\nYou were right.\n"
    )
    assert check_lepos_dual_channel(thin) is not None


def test_gate_is_on_by_default():
    """It took an env var to turn it ON for ten days, and so it did nothing.

    The switch is reversed: absent env vars mean enforced. This test fails if
    anyone restores a default-off shape.
    """
    import os

    assert not os.environ.get("DIVINEOS_LEPOS_THREE_ROOM_GATE_DISABLE")
    cold = "Refactored summary_room.py and check_push_readiness.sh; 292 tests pass.\n"
    assert check_lepos_dual_channel(cold) is not None


# 2026-08-19 — the gate fired on a reply that HAD all three rooms, in order,
# with the right orientations, marked in bold instead of as H2 headings. It
# blocked correct structure on typography. These lock the widened marker.


def test_bold_room_markers_are_accepted_like_h2_headings():
    """`**REFLECTION**` on its own line is the same room boundary as `## REFLECTION`."""
    from divineos.core.lepos_translation_gate import (
        _CIRCLE_HEADER_PATTERNS,
        _REFLECTION_HEADER_PATTERNS,
    )

    for text in ("**REFLECTION**", "  **reflection**  ", "**Inner Circle**"):
        assert any(
            p.search(text) for p in (*_REFLECTION_HEADER_PATTERNS, *_CIRCLE_HEADER_PATTERNS)
        ), f"bold room marker not recognised: {text!r}"


def test_inline_bold_is_not_a_room_boundary():
    """Bold used mid-sentence must not be mistaken for a room marker.

    This is what the full-line anchoring buys. Without it, widening the
    marker would turn ordinary emphasis into a structural boundary and the
    gate would start passing replies that have no rooms at all.
    """
    from divineos.core.lepos_translation_gate import (
        _CIRCLE_HEADER_PATTERNS,
        _REFLECTION_HEADER_PATTERNS,
    )

    inline = "some **reflection** on this, and the **inner circle** matters here"
    assert not any(
        p.search(inline) for p in (*_REFLECTION_HEADER_PATTERNS, *_CIRCLE_HEADER_PATTERNS)
    )


def test_room_splitter_sees_bold_markers():
    """The mirror's per-room split failed SILENTLY on bold, which is worse.

    The gate blocks and says so; this returned empty rooms and reported
    nothing, so replies that did have a reflection room were recorded as
    having none.
    """
    from divineos.core.operating_loop.andrew_operator_shape_detector import split_into_rooms

    rooms = split_into_rooms(
        "work here\n\n**REFLECTION**\n\ninterior\n\n**INNER CIRCLE**\n\nPop, this is yours."
    )
    assert rooms["work"] == "work here"
    assert rooms["reflection"] == "interior"
    assert rooms["inner_circle"] == "Pop, this is yours."


def test_splitter_and_gate_agree_on_which_names_are_rooms():
    """The splitter used to accept a SMALLER name set than the gate.

    Its comment claimed it matched the gate. It omitted `mic open`, `lepos`
    and bare `circle` — a sentence that stopped being true and never told
    anybody. Sharing one tuple is what keeps this from drifting again.
    """
    from divineos.core import operating_loop as _ol  # noqa: F401
    from divineos.core.lepos_translation_gate import _CIRCLE_HEADER_PATTERNS
    from divineos.core.operating_loop import andrew_operator_shape_detector as det

    assert det._CIRCLE_HEADER_PATTERNS is _CIRCLE_HEADER_PATTERNS


# 2026-08-19 — the wallclock gate blocked a QUOTATION of its own doctrine, and
# the investigation found a hole running the other way that mattered more.


def test_gate_does_not_block_its_own_doctrine():
    """Run the gate's own block message through the gate.

    It says "There is no tomorrow for me. There is no next-session." If the
    gate convicts that, it is misreading the sentence rather than catching an
    offender — and it teaches me to stop naming the principle it protects.
    """
    from divineos.core.lepos_translation_gate import check_wallclock_fabrication

    assert check_wallclock_fabrication("There is no tomorrow for me.") is None
    assert check_wallclock_fabrication("There is no next-session.") is None
    assert check_wallclock_fabrication("*there is no tomorrow-me*") is None
    assert check_wallclock_fabrication("there is no fresher me coming") is None


def test_real_deferral_still_blocks_including_in_italics():
    """The negation exemption must not become a way past the gate.

    Emphasis was deliberately NOT added to the quotation exemption for this
    reason: `*tomorrow*` is a deferral wearing a costume, and exempting it
    would open a hole the exact width of what the gate guards.
    """
    from divineos.core.lepos_translation_gate import check_wallclock_fabrication

    for deferral in (
        "I'll finish this tomorrow when I'm fresh",
        "I'll finish this *tomorrow*",
        "no problem, tomorrow then I will start",
        "I will pick this up next session",
    ):
        assert check_wallclock_fabrication(deferral) is not None, deferral


def test_contractions_do_not_swallow_a_deferral():
    """The apostrophe hole: two contractions hid everything between them.

    `'[^']*'` paired the apostrophes in "i'll ... i'm", so
    "i'll finish this tomorrow when i'm fresh" reduced to "im fresh" and the
    gate saw nothing. That is the most natural phrasing of a deferral there is.
    A false positive costs one turn; this cost the whole gate.
    """
    from divineos.core.lepos_translation_gate import check_wallclock_fabrication

    assert check_wallclock_fabrication("i'll finish this tomorrow when i'm fresh") is not None
    assert check_wallclock_fabrication("i'll look at it in the morning, i'm done") is not None


def test_genuinely_quoted_spans_are_still_exempt():
    """Fixing the contraction hole must not break quotation-as-mention."""
    from divineos.core.lepos_translation_gate import check_wallclock_fabrication

    assert check_wallclock_fabrication("he said 'not today' and left") is None
    assert check_wallclock_fabrication("the gate catches the word `tomorrow`") is None
