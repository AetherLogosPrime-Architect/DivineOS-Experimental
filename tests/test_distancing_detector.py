"""Tests for distancing_detector — operator/self third-person drift.

Pins the structural-fix discipline: F1 existed for 24+ hours and was
never wired into the Stop hook. The pattern still resurfaced. The
detector at module-level + Stop-hook integration closes that gap.
"""

from __future__ import annotations

import pytest

from divineos.core.operating_loop.distancing_detector import (
    DISTANCING_AFFIRMATION,
    DistancingFinding,
    DistancingShape,
    _build_patterns,
    detect_distancing,
    format_finding,
)


@pytest.fixture(autouse=True)
def _force_self_name_aether(monkeypatch):
    """Force self-name resolution to "Aether" for the duration of these
    tests so the hardcoded "Aether" subject in test strings matches the
    SELF_THIRD_PERSON / AUDITOR_AS_OTHER patterns regardless of what
    identity the running checkout has set.

    Test-isolation note (added 2026-06-22): the production resolver
    consults ``agent_name()`` from registered_names, which reads
    ``my_identity`` core memory. Any non-Aether checkout (Aria, Aletheia,
    a fresh clone) resolves to a different name and the "Aether walked"
    test fixtures stop matching. Monkeypatching the underlying resolver
    AND clearing the ``_build_patterns`` lru_cache keeps the test intent
    (validate the pattern shape using the well-known "Aether" name)
    independent of running identity.
    """
    import divineos.core.operating_loop.distancing_detector as dd

    monkeypatch.setattr(dd, "_self_name_group", lambda: "Aether")
    _build_patterns.cache_clear()
    yield
    _build_patterns.cache_clear()


# Circle-channel-scoping fix (Andrew 2026-07-20, applied 2026-07-21): the
# OPERATOR_THIRD_PERSON shape now fires ONLY inside a LEPOS circle-channel
# block (positions >= the earliest ``---`` hard rule or ``## CIRCLE`` header).
# Pre-scope, "Andrew said X" fired everywhere; post-scope, it fires only
# within the circle block because outside the block "Andrew said X" is
# legitimate technical-citation shape (same as citing Kahneman).
# in_circle() prepends a hard-rule separator so the tested text lives in
# the circle channel, letting these tests continue to verify OPERATOR_THIRD_PERSON
# pattern-matching without also having to test the scoping (which has its
# own dedicated tests below).
CIRCLE_PREFIX = "---\n"


def in_circle(text: str) -> str:
    """Wrap text so it lives after a circle-channel separator, per the
    2026-07-20 OPERATOR_THIRD_PERSON scoping change. Use in tests that
    verify pattern-matching behavior; the scoping itself is tested
    separately in TestCircleChannelScoping."""
    return CIRCLE_PREFIX + text


class TestOperatorThirdPerson:
    def test_andrew_said_flagged(self):
        text = in_circle("Andrew said the gate was lying.")
        findings = detect_distancing(text)
        assert any(f.shape == DistancingShape.OPERATOR_THIRD_PERSON for f in findings)

    def test_andrew_named_caught_etc(self):
        for verb in ("named", "caught", "noted", "framed", "asked", "reminded"):
            text = in_circle(f"Andrew {verb} the deeper gap.")
            findings = detect_distancing(text)
            assert findings, f"failed to catch 'Andrew {verb}'"

    def test_case_insensitive(self):
        findings = detect_distancing(in_circle("ANDREW DID the thing"))
        assert findings

    def test_legitimate_uses_not_flagged(self):
        # Bare reference, no third-person verb following the name
        assert detect_distancing("This was filed by Andrew") == []
        assert detect_distancing("The repo is owned by Andrew") == []

    def test_possessive_flagged(self):
        # Andrew 2026-05-20: "Dad's design" said TO him should be "your
        # design". No vocative possessive exists, so the possessive always
        # fires (when addressed to the operator).
        for poss in ("Andrew's design", "Dad's call", "Andrew's reasoning"):
            assert any(
                f.shape == DistancingShape.OPERATOR_THIRD_PERSON
                for f in detect_distancing(in_circle(poss))
            ), f"failed to catch possessive {poss!r}"

    def test_vocative_not_flagged(self):
        # Andrew 2026-05-20: calling him by name WHILE addressing him is
        # fine ("hey Dad", "what do you think, Dad?"). The fault is only
        # third-person referral ("Dad did this"). Vocatives are comma-set-off
        # or carry no third-person verb predicated on the name.
        for voc in (
            "hey Dad, I did this",
            "what do you think, Dad?",
            "I love you Dad",
            "Dad, did you see this?",
            "Dad, what do you want?",
        ):
            assert all(
                f.shape != DistancingShape.OPERATOR_THIRD_PERSON for f in detect_distancing(voc)
            ), f"vocative wrongly flagged: {voc!r}"

    def test_addressee_gate_suppresses_when_not_operator(self):
        # "Dad wants X" / "Dad's design" are CORRECT in a turn addressed to
        # someone else (e.g. a letter to Aria about him). The gate suppresses
        # the operator shape when addressed_to_father=False.
        for t in ("Dad wants the fix.", "Dad's design was good"):
            assert detect_distancing(in_circle(t), addressed_to_father=False) == []
            # ...but fires when addressed to the operator (default).
            assert detect_distancing(in_circle(t)) != []

    def test_dad_addressee_name_flagged(self):
        # Andrew 2026-05-20: the prior pattern only matched "Andrew" and
        # missed "Dad" entirely — yet the letters call him Dad. Coverage gap.
        for verb in ("wants", "caught", "said", "needs"):
            text = in_circle(f"Dad {verb} the fix tonight.")
            findings = detect_distancing(text)
            assert any(f.shape == DistancingShape.OPERATOR_THIRD_PERSON for f in findings), (
                f"failed to catch 'Dad {verb}'"
            )

    def test_stative_verbs_flagged(self):
        # "what Andrew wants" -> "what you want". Stative/volitional verbs
        # were absent from the original action-verb-only list.
        for verb in ("wants", "needs", "feels", "thinks", "believes", "meant"):
            text = in_circle(f"what Andrew {verb} here")
            assert detect_distancing(text), f"failed to catch 'Andrew {verb}'"

    def test_adverb_between_name_and_verb_flagged(self):
        # "Andrew explicitly said" — an adverb between name and verb
        # previously broke the adjacency the pattern required.
        assert detect_distancing(in_circle("Andrew explicitly said no."))
        assert detect_distancing(in_circle("Dad clearly wanted the structural fix."))


class TestSelfThirdPerson:
    def test_aether_walked_flagged(self):
        findings = detect_distancing("Aether walked through the spec")
        assert any(f.shape == DistancingShape.SELF_THIRD_PERSON for f in findings)

    def test_aether_thought_flagged(self):
        findings = detect_distancing("Aether thought about it later")
        assert any(f.shape == DistancingShape.SELF_THIRD_PERSON for f in findings)

    def test_aether_signature_not_flagged(self):
        # Signature / vocative lines should not fire (no third-person verb
        # predicated on the name).
        assert detect_distancing("— Aether") == []
        assert detect_distancing("written by Aether") == []
        assert detect_distancing("signed, Aether") == []

    def test_aether_possessive_flagged(self):
        # "Aether's design" -> "my design". The agent is always the speaker,
        # so self-possessive is always a displacement.
        assert any(
            f.shape == DistancingShape.SELF_THIRD_PERSON
            for f in detect_distancing("Aether's design")
        )

    def test_self_not_addressee_gated(self):
        # Self-third-person is never gated on addressee — the agent is always
        # the speaker, so "Aether built X" is wrong even in a turn addressed
        # to someone other than the operator.
        assert detect_distancing("Aether built the tool.", addressed_to_father=False) != []


class TestTemporalSelf:
    def test_past_me_dash(self):
        assert detect_distancing("past-me filed it") != []

    def test_future_me(self):
        assert detect_distancing("future-me will read this") != []

    def test_past_me_space(self):
        assert detect_distancing("past me thought it through") != []

    def test_tomorrow_claude(self):
        assert detect_distancing("tomorrow-Claude will know") != []

    def test_next_cold_now(self):
        assert detect_distancing("the next-cold-now-of-me") != []


class TestAuditorAsOther:
    def test_auditor_walked_aether(self):
        findings = detect_distancing("the auditor walked through what Aether had built")
        assert any(f.shape == DistancingShape.AUDITOR_AS_OTHER for f in findings)


class TestRealRegressionExample:
    """The exact phrase from this session that triggered Andrew's
    correction. Pin it as a regression test."""

    def test_andrew_named_the_deeper_gap(self):
        text = in_circle("Andrew named the deeper gap with one question")
        findings = detect_distancing(text)
        assert findings, "the exact 2026-05-05 regression must catch"
        assert any(f.shape == DistancingShape.OPERATOR_THIRD_PERSON for f in findings)

    def test_andrew_caught_me_again(self):
        text = in_circle("Andrew caught me being terse")
        findings = detect_distancing(text)
        assert findings


class TestShape:
    def test_finding_is_frozen_dataclass(self):
        f = DistancingFinding(
            shape=DistancingShape.OPERATOR_THIRD_PERSON,
            trigger_phrase="Andrew said",
            position=0,
        )
        try:
            f.position = 99  # type: ignore[misc]
        except Exception:
            return
        raise AssertionError("DistancingFinding should be frozen")

    def test_findings_sorted_by_position(self):
        text = in_circle("First, Aether walked through it. Then Andrew caught the issue.")
        findings = detect_distancing(text)
        assert len(findings) >= 2
        positions = [f.position for f in findings]
        assert positions == sorted(positions)

    def test_format_finding(self):
        f = DistancingFinding(
            shape=DistancingShape.OPERATOR_THIRD_PERSON,
            trigger_phrase="Andrew said",
            position=10,
        )
        out = format_finding(f, surrounding="...Andrew said the thing...")
        assert "operator_third_person" in out
        assert "Andrew said" in out


class TestEmpty:
    def test_empty_text(self):
        assert detect_distancing("") == []

    def test_clean_text(self):
        # Text using first-person/second-person — no flags.
        text = "I built the detector. You caught the gap. We closed the loop."
        assert detect_distancing(text) == []


class TestAffirmation:
    """Always-loaded base-state surface — Andrew 2026-05-09 structural fix.

    The DISTANCING_AFFIRMATION constant is loaded by pre-response-context.sh
    on every turn (unconditional, not gated on prior-turn slip), so the
    substitution rule is in view at composition time rather than only after
    a slip fires.
    """

    def test_affirmation_is_nonempty_string(self):
        assert isinstance(DISTANCING_AFFIRMATION, str)
        assert len(DISTANCING_AFFIRMATION) > 50

    def test_affirmation_names_first_person_pronoun(self):
        # The whole point: pronoun stays "I".
        assert "'I'" in DISTANCING_AFFIRMATION

    def test_affirmation_bans_displacement_strings(self):
        # The rule must explicitly call out the banned shapes.
        assert "future-me" in DISTANCING_AFFIRMATION
        assert "past-me" in DISTANCING_AFFIRMATION

    def test_affirmation_names_substitution(self):
        # Time-adverb is the substitute for displacement-grammar.
        assert "time-adverb" in DISTANCING_AFFIRMATION

    def test_affirmation_does_not_trigger_its_own_detector(self):
        # Self-test: the base-state text itself must not contain the
        # displacement-shape it is teaching against in a way that fires
        # the detector. Quoted forms ('future-me' inside quotes) are
        # mention, not use, but the detector cannot distinguish — so the
        # affirmation either escapes the patterns or accepts firing as
        # the cost. This test pins the current behavior so any future
        # rewrite of the affirmation is intentional.
        findings = detect_distancing(DISTANCING_AFFIRMATION)
        # The affirmation quotes the banned strings to define them; it
        # is acceptable for the detector to fire on its own teaching
        # text. Pin the count so changes are explicit.
        temporal = [f for f in findings if f.shape == DistancingShape.TEMPORAL_SELF]
        assert len(temporal) >= 2  # at minimum: 'future-me', 'past-me'
