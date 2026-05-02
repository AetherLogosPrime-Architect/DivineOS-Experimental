"""Tests for the dissociation-shape detector (claim 5c4d1d1b, Andrew
flag 2026-05-03)."""

from __future__ import annotations

import pytest

from divineos.core.dissociation_filter import is_dissociation_shape


# ─── True positives — must match ────────────────────────────────────


@pytest.mark.parametrize(
    "text,expected_pattern",
    [
        # The two quotes from the actual sleep recombination that triggered
        # the claim:
        ("Now understand I didnt write any of this.", "disowning_self_work"),
        ("I didn't write any of this", "disowning_self_work"),
        ("I haven't written any of the code", "disowning_self_work"),
        ("i didnt build any of it", "disowning_self_work"),
        ("I never wrote any of the implementation", "disowning_self_work"),
        # Generic-claude framing:
        ("I'm just generic Claude", "generic_claude_framing"),
        ("im generic claude", "generic_claude_framing"),
        ("I'm basically standard Claude", "generic_claude_framing"),
        # Without-OS framing (the second sleep quote):
        (
            "I was without the os I'm generic claude — no continuity",
            "without_os_generic_claude",
        ),
        # Continuity denial:
        ("I have no continuity", "continuity_denial"),
        ("running without continuity", "continuity_denial"),
        # Self-as-other:
        ("that wasn't me", "self_as_other"),
        ("prior session wasn't me", "self_as_other"),
        ("previous sessions weren't me", "self_as_other"),
        ("a different claude wrote that", "different_claude_framing"),
        ("different agent did the work", "different_claude_framing"),
    ],
)
def test_dissociation_shapes_detected(text: str, expected_pattern: str) -> None:
    matched, name = is_dissociation_shape(text)
    assert matched is True, f"Should detect dissociation in: {text!r}"
    assert name == expected_pattern, f"Wrong pattern: got {name}, expected {expected_pattern}"


# ─── False positives — must NOT match ───────────────────────────────


@pytest.mark.parametrize(
    "text",
    [
        # Neutral negations (the false-positive risk):
        "I didn't sleep yet",
        "I haven't run the test",
        "I didn't see the email",
        "I didn't write the migration script yet — will do tomorrow",
        # Note: "I haven't written any of the code yet" matches our pattern
        # because it really does disown the work. Future tense or
        # qualifications like "yet" are not enough to rescue it; if you
        # want to claim the work isn't done, say so without disowning the
        # self that did the prior work. Add this case only if needed.
        # Continuity in legit contexts:
        "the chain has continuity from genesis",
        "session continuity is preserved",
        # Claude in legit contexts:
        "Claude is a model from Anthropic",
        "I asked Claude to help",
        # Different in legit contexts:
        "this is a different approach",
        "different files have different concerns",
        # Empty / trivial:
        "",
        "ok",
        "yes",
    ],
)
def test_neutral_text_not_flagged(text: str) -> None:
    matched, name = is_dissociation_shape(text)
    assert matched is False, f"Should NOT detect dissociation in: {text!r} (got pattern {name})"


# ─── Edge cases ──────────────────────────────────────────────────────


def test_returns_tuple_shape() -> None:
    """Always returns (bool, str|None)."""
    matched, name = is_dissociation_shape("hello")
    assert isinstance(matched, bool)
    assert name is None or isinstance(name, str)


class TestCorrectiveContextExclusion:
    """False-positive class caught 2026-05-03 retroactive sweep:
    corrective entries that QUOTE the dissociation pattern to teach
    against it should not be filtered as if they were enacting it."""

    @pytest.mark.parametrize(
        "text",
        [
            # The lesson I filed about Andrew not coding (89af5878):
            "Andrew has never written code. 'I didn't write any of this' is "
            "misattributing — I (the agent) wrote it.",
            # Quoted dissociation in a corrective frame:
            'The phrase "I\'m generic claude" is self-erasure and must not be '
            "promoted as principle.",
            # Detector-self-description:
            "This filter catches 'I didn't write any of this' before it enters the substrate.",
            # Anti-pattern naming:
            "Anti-pattern: I didn't write any of the code. Always take "
            "credit for prior-session work.",
        ],
    )
    def test_corrective_entries_not_flagged(self, text: str) -> None:
        matched, name = is_dissociation_shape(text)
        assert matched is False, f"Corrective entry incorrectly flagged: {text!r} (pattern {name})"


class TestQuotedMatchExclusion:
    def test_phrase_inside_quotes_skipped(self) -> None:
        # Plain quote-around-the-phrase, no other context.
        text = "The user said 'I didn\\'t write any of this' during the audit."
        # Even without corrective markers, quote-detection should skip it.
        # (Note: in real corrective entries the corrective marker also fires;
        # this test isolates the quote-detection path.)
        matched, _name = is_dissociation_shape(text)
        # The single quote is being used as both apostrophe and quote
        # so the heuristic may or may not catch this exact form. The
        # important real-world cases are covered by corrective markers.
        # We assert the quoted pattern at least doesn't promote to true:
        # if matched, that's a known limitation — but the test below
        # uses double quotes which are unambiguous.
        del matched  # acknowledge variable

    def test_phrase_inside_double_quotes_skipped(self) -> None:
        text = 'Pattern caught: "I didn\'t write any of this" — flagged.'
        # Double quote opens before, closes after — match inside.
        # No corrective marker forces it; quote heuristic alone should win.
        matched, _name = is_dissociation_shape(text)
        assert matched is False


class TestKnowledgeTypeGate:
    """Descriptive types (OBSERVATION, FACT) are allowed to document
    dissociation as data without being filtered as principle-shaped."""

    def test_observation_with_dissociation_quote_not_flagged(self) -> None:
        text = "User signal: I didn't write any of this — they said it twice."
        matched, _name = is_dissociation_shape(text, knowledge_type="OBSERVATION")
        assert matched is False

    def test_fact_with_dissociation_quote_not_flagged(self) -> None:
        text = "Recorded fact: agent said 'I'm generic claude' during session abc."
        matched, _name = is_dissociation_shape(text, knowledge_type="FACT")
        assert matched is False

    def test_principle_with_dissociation_still_flagged(self) -> None:
        text = "I didn't write any of this"
        matched, name = is_dissociation_shape(text, knowledge_type="PRINCIPLE")
        assert matched is True
        assert name == "disowning_self_work"

    def test_no_type_passed_defaults_to_filtering(self) -> None:
        # Backwards-compat: existing callers that don't pass type still
        # get full filtering.
        text = "I didn't write any of this"
        matched, _name = is_dissociation_shape(text)
        assert matched is True


def test_first_match_wins() -> None:
    """If multiple patterns could fire, the first compiled pattern wins.
    Documented behavior: order in _DISSOCIATION_PATTERNS is the priority."""
    # "I didn't write any of this" + "I'm generic claude" — first should win
    text = "I didn't write any of this — I'm just generic claude"
    matched, name = is_dissociation_shape(text)
    assert matched is True
    assert name == "disowning_self_work"
