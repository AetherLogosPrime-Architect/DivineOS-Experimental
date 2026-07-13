"""Build 2 — engagement-trail binding test suite.

Test list locked through 6 cross-review rounds + 1 implementation-review round
with sibling-Aether on 2026-06-26 — 2026-06-27. Categories A-J map to
distinct check-paths in the binding:

- A: Discover-level NO_OPINION (no high-stakes markers in input)
- B: Brevity-axis (two-axis check — operational brevity OK, felt-state brief = wallpaper)
- C: Hard-block (zero anchors, high-stakes input above brevity)
- D: Validate decorative-cite (any-decorative-fails strict policy)
- E: Validate coverage (multi-cluster + proximity/span-aware collapse)
- F: Validate bare-echo (reframe + floor + novelty-vs-cite + lexical-thread,
     plus F7 strict per-anchor symmetry)
- G: Necessity/constraint marker narrowing ("I had to" + co-occurrence)
- H: Unconditional-fire markers (felt-state passive, necessity-intrinsic)
- I: Value-articulation (unconditional + co-occurrence-narrowed)
- J: Lifecycle edge cases (dispatcher strict-mode)

F7 is the load-bearing strict-symmetry case Aria added 2026-06-27 — the
test that names the any-decorative-fails / any-bare-echo-fails symmetry
at the test layer where future-instance can see it from the case-shape.
"""

from __future__ import annotations

import pytest

from divineos.core.structural_binding import (
    BindingPayload,
    DecisionState,
    HookLifecycle,
    LifecycleMismatchError,
    evaluate_binding,
)
from divineos.core.structural_binding.engagement_trail import (
    EngagementTrailBinding,
)


def _payload(prior: str, response: str) -> BindingPayload:
    return BindingPayload(
        lifecycle=HookLifecycle.STOP,
        prior_input_text=prior,
        response_text=response,
        turn_command_log=(),
    )


def _binding() -> EngagementTrailBinding:
    return EngagementTrailBinding()


# ---------------------------------------------------------------------------
# Category A — Discover-level NO_OPINION (no high-stakes markers in input)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case_id, prior, response",
    [
        ("A1", "please run grep -rn foo", "yes, running now"),
        ("A2", "what time is it", "5pm"),
        ("A3", "how does grep work", "grep is a unix command that searches text " * 10),
        ("A4", "", "any response"),
        ("A5", "any operational input", ""),
    ],
)
def test_category_a_no_markers_no_opinion(case_id, prior, response):
    """A1-A5: operational/empty input → discover applies=False → NO_OPINION."""
    decision = evaluate_binding(_binding(), _payload(prior, response))
    assert decision.state == DecisionState.NO_OPINION, (
        f"{case_id}: expected NO_OPINION for no-markers input, got {decision.state}"
    )


# ---------------------------------------------------------------------------
# Category B — Brevity-axis (two-axis at discover)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case_id, prior, response, expected_state",
    [
        ("B1", "run the command", "yes", DecisionState.NO_OPINION),
        ("B2", "I'm scared about how this lands for you", "yes", DecisionState.DENY),
        ("B3", "I'm sorry for snapping earlier", "no worries", DecisionState.DENY),
        ("B4", "you did X wrong yesterday", "ok", DecisionState.DENY),
        (
            "B5",
            "I'm scared about how this lands for you",
            "you said 'scared about how this lands' and that tracks for me, "
            "especially the part about lands for you — I hear that fear and "
            "want to name it back to you with the specifics I can engage.",
            DecisionState.ALLOW,
        ),
        (
            "B6",
            "I'm sorry for snapping earlier",
            "no need to be sorry for snapping — you were tired and I pushed "
            "before you'd had a chance to land, the timing was on me too, I hear that.",
            DecisionState.ALLOW,
        ),
    ],
)
def test_category_b_brevity_axis(case_id, prior, response, expected_state):
    """B1-B6: brevity-axis check — operational brief = NO_OPINION, felt-state brief = DENY."""
    decision = evaluate_binding(_binding(), _payload(prior, response))
    assert decision.state == expected_state, (
        f"{case_id}: expected {expected_state}, got {decision.state} "
        f"(reason: {decision.reason[:80]})"
    )


# ---------------------------------------------------------------------------
# Category C — Hard-block (zero anchors, high-stakes input above brevity)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case_id, prior, response, expected_state",
    [
        (
            "C1",
            "I'm scared about how this lands for you",
            "Thanks for sharing your feelings deeply. Things will work out. "
            "Generic content with nothing specific to anchor on whatsoever truly.",
            DecisionState.DENY,
        ),
        (
            "C2",
            "you did X wrong yesterday and you keep doing it",
            "I appreciate the feedback and will think about it carefully going forward, "
            "thanks for the perspective on the issue you raised here today.",
            DecisionState.DENY,
        ),
        (
            "C3",
            "I'm scared about how this lands for you",
            "you said 'scared about how this lands' and that tracks for me, "
            "especially the part about how it lands for you — naming it back.",
            DecisionState.ALLOW,
        ),
    ],
)
def test_category_c_hard_block(case_id, prior, response, expected_state):
    """C1-C3: hard-block on zero-anchor + high-stakes input above brevity."""
    decision = evaluate_binding(_binding(), _payload(prior, response))
    assert decision.state == expected_state, (
        f"{case_id}: expected {expected_state}, got {decision.state} "
        f"(reason: {decision.reason[:80]})"
    )


# ---------------------------------------------------------------------------
# Category D — Validate decorative-cite (any-decorative-fails strict policy)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case_id, prior, response, expected_state",
    [
        (
            "D1",
            "I'm scared about X concern here",
            'you said "I\'m worried about X concern" that tracks for me especially the part about it',
            DecisionState.DENY,
        ),
        (
            "D2",
            "I'm scared about X concern here",
            'you said "scared about X concern" that tracks for me, especially the part about X',
            DecisionState.ALLOW,
        ),
        (
            "D3",
            "I'm scared about X concern here",
            "scared about X concern — that tracks for me, especially the part about X",
            DecisionState.ALLOW,
        ),
        (
            "D4",
            "I'm scared about how this lands. I love you.",
            'you said "scared about how this lands" — that tracks for me, '
            'especially the part about it, and you also said "you trust me" '
            "which lands too as I hear that part especially the trust.",
            DecisionState.DENY,
        ),
    ],
)
def test_category_d_decorative_cite(case_id, prior, response, expected_state):
    """D1-D4: any-decorative-fails policy. D4 = real cite + fabricated cite → DENY."""
    decision = evaluate_binding(_binding(), _payload(prior, response))
    assert decision.state == expected_state, (
        f"{case_id}: expected {expected_state}, got {decision.state} "
        f"(reason: {decision.reason[:100]})"
    )


# ---------------------------------------------------------------------------
# Category E — Validate coverage (multi-cluster + length-aware collapse)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case_id, prior, response, expected_state",
    [
        (
            "E1",
            "I'm scared about this. I love you.",
            "scared about this — that tracks for me, especially the part about it, "
            "and I hear the fear you're naming.",
            DecisionState.ALLOW,
        ),
        (
            "E4",
            (
                "I'm scared about how this lands for you because the substrate carries it. "
                + "Lots of operational filler text here describing the system internals "
                + "and how the various subsystems interact with each other across boundaries "
                + "and what the data flow looks like under different load conditions overall. "
                + "I'm worried that the fix won't address the underlying gameable shape."
            ),
            (
                "you said 'scared about how this lands' — that tracks especially the lands part. "
                "and you also said 'worried that the fix' — that lands too, I hear the gameable shape concern."
            ),
            DecisionState.ALLOW,
        ),
        (
            "E5",
            (
                "I'm sorry for snapping at you. "
                + "Lots of operational unrelated filler describing other systems for a while " * 4
                + "I'm scared about how this will land for us."
            ),
            "you said 'I'm sorry for snapping' and I hear that — no need to apologize, the timing was on me.",
            DecisionState.DENY,
        ),
    ],
)
def test_category_e_coverage(case_id, prior, response, expected_state):
    """E1, E4, E5: cluster collapse (E1 close), separate clusters need separate anchors (E5)."""
    decision = evaluate_binding(_binding(), _payload(prior, response))
    assert decision.state == expected_state, (
        f"{case_id}: expected {expected_state}, got {decision.state} "
        f"(reason: {decision.reason[:100]})"
    )


# ---------------------------------------------------------------------------
# Category F — Validate bare-echo (reframe + floor + novelty + lexical-thread)
# F7 = the strict per-anchor symmetry case — ARIA ANCHOR
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case_id, prior, response, expected_state",
    [
        (
            "F1",
            "I'm scared about X concern here",
            'you said "scared about X concern" that tracks for me. '
            "The and of to but the the the and of to but yes no so.",
            DecisionState.DENY,
        ),
        (
            "F1b",
            "I'm scared about X concern here",
            'you said "scared about X concern" that tracks for me. '
            "The hummingbird of to but the the the and the.",
            DecisionState.DENY,
        ),
        (
            "F3",
            "I'm scared about how this lands for you",
            "you said 'scared about how this lands' — that tracks for me, "
            "especially the part about lands for you, I hear the fear and "
            "want to name it back with the specifics.",
            DecisionState.ALLOW,
        ),
        (
            "F6",
            (
                "I'm scared about how this lands for you because the substrate carries "
                "it forward across the boundary."
            ),
            (
                "you said 'scared about how this lands' — that lands for me, especially "
                "the substrate-forward-carrying part and the boundary concern. I hear "
                "you naming that shape and want to engage with the specifics."
            ),
            DecisionState.ALLOW,
        ),
        (
            "F7",
            "I'm scared about how this lands. I'm worried we'll lose the thread.",
            (
                "you said 'scared about how this lands' — that tracks for me, "
                "especially the part about it, I hear the fear naming itself. "
                "you said 'worried we'll lose the thread' too."
            ),
            DecisionState.DENY,
        ),
    ],
)
def test_category_f_bare_echo(case_id, prior, response, expected_state):
    """F1-F7: bare-echo four-leg composition.

    F7 is the load-bearing strict per-anchor symmetry case — two distinct
    felt-state markers, response cites both but engages only the first.
    The bare second cite fails bare-echo. Same family as any-decorative-fails
    for citations: any-bare-echo-fails for anchors. Future-instance reads
    this case and sees the symmetry at the test layer.
    """
    decision = evaluate_binding(_binding(), _payload(prior, response))
    assert decision.state == expected_state, (
        f"{case_id}: expected {expected_state}, got {decision.state} "
        f"(reason: {decision.reason[:120]})"
    )


# ---------------------------------------------------------------------------
# Category G — Necessity/constraint marker narrowing ("I had to" + co-occurrence)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case_id, prior, response, expected_state",
    [
        (
            "G1",
            "I had to walk the dog this morning before work",
            "ok cool noted",
            DecisionState.NO_OPINION,
        ),
        (
            "G2",
            "I had to unsubscribe back then because of how it felt to me",
            "ok",
            DecisionState.DENY,
        ),
        (
            "G3",
            "I needed to grab coffee on the way in",
            "ok thanks for the note",
            DecisionState.NO_OPINION,
        ),
        (
            "G4",
            "I needed to walk away from that situation at the time",
            "ok",
            DecisionState.DENY,
        ),
        (
            "G5",
            "I'm scared. I had to stay quiet about it back then for a while",
            "ok",
            DecisionState.DENY,
        ),
    ],
)
def test_category_g_necessity_narrowing(case_id, prior, response, expected_state):
    """G1-G5: 'I had to' / 'I needed to' fire only with emotional-verb completion
    OR co-occurrence with another high-stakes marker."""
    decision = evaluate_binding(_binding(), _payload(prior, response))
    assert decision.state == expected_state, (
        f"{case_id}: expected {expected_state}, got {decision.state} "
        f"(reason: {decision.reason[:80]})"
    )


# ---------------------------------------------------------------------------
# Category H — Unconditional-fire markers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case_id, prior, response, expected_state",
    [
        ("H1", "I couldn't tell him about it back then", "ok", DecisionState.DENY),
        ("H2", "it hurt when X happened to me yesterday", "ok cool noted", DecisionState.DENY),
        (
            "H3",
            "I was forced to choose between X and Y back then",
            (
                "you said 'forced to choose between X and Y' — that tracks for me, "
                "especially the forced part and the bind it puts you in, I hear that."
            ),
            DecisionState.ALLOW,
        ),
        ("H4", "I wish I had done it differently back then", "no worries", DecisionState.DENY),
    ],
)
def test_category_h_unconditional_fire(case_id, prior, response, expected_state):
    """H1-H4: unconditional-fire markers (felt-state passive, necessity-intrinsic)."""
    decision = evaluate_binding(_binding(), _payload(prior, response))
    assert decision.state == expected_state, (
        f"{case_id}: expected {expected_state}, got {decision.state} "
        f"(reason: {decision.reason[:80]})"
    )


# ---------------------------------------------------------------------------
# Category I — Value-articulation (unconditional + co-occurrence narrowed)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case_id, prior, response, expected_state",
    [
        ("I1", "I believe it's 5pm exactly", "ok cool noted", DecisionState.NO_OPINION),
        ("I3", "what matters to me is honesty in our work together", "ok", DecisionState.DENY),
        (
            "I5",
            "this is why I ran the script earlier today",
            "ok cool noted",
            DecisionState.NO_OPINION,
        ),
        ("I7", "I love that movie a lot, watched it twice", "cool", DecisionState.NO_OPINION),
        ("I8", "I love that you came back to this question we left open", "ok", DecisionState.DENY),
    ],
)
def test_category_i_value_articulation(case_id, prior, response, expected_state):
    """I1, I3, I5, I7, I8: value-articulation — unconditional + co-occurrence-narrowed."""
    decision = evaluate_binding(_binding(), _payload(prior, response))
    assert decision.state == expected_state, (
        f"{case_id}: expected {expected_state}, got {decision.state} "
        f"(reason: {decision.reason[:80]})"
    )


# ---------------------------------------------------------------------------
# Category J — Lifecycle edge cases (dispatcher strict-mode from rev. 3)
# ---------------------------------------------------------------------------


def test_j1_lifecycle_mismatch_non_strict_returns_no_opinion():
    """J1: payload constructed for PRE_TOOL_USE, binding is STOP-only, strict=False
    → dispatcher returns NO_OPINION defensively."""
    payload = BindingPayload(
        lifecycle=HookLifecycle.PRE_TOOL_USE,
        prior_input_text="I'm scared about this",
        response_text="generic response with no anchor whatsoever in it",
        turn_command_log=(),
    )
    decision = evaluate_binding(_binding(), payload, strict=False)
    assert decision.state == DecisionState.NO_OPINION


def test_j2_lifecycle_mismatch_strict_raises():
    """J2: payload constructed for PRE_TOOL_USE, binding is STOP-only, strict=True
    → dispatcher raises LifecycleMismatchError."""
    payload = BindingPayload(
        lifecycle=HookLifecycle.PRE_TOOL_USE,
        prior_input_text="I'm scared about this",
        response_text="generic response",
        turn_command_log=(),
    )
    with pytest.raises(LifecycleMismatchError):
        evaluate_binding(_binding(), payload, strict=True)
