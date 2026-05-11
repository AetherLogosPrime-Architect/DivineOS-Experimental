"""Tests for reflection_pairing module (Phase 2C of shoggoth-metrics redesign).

The pairing surface is the correctly-shaped Phase 2C — it lays the agent's
reflection text side-by-side with substrate observations and prompts
metacognitive comparison in WORDS AND REASONING, not numerical divergence.

Key invariants:
- No numerical divergence computation anywhere in the output.
- No 'alignment score', 'pattern: calibrated/over-claim/over-disclaim'.
- The output is a structured prompt; the cognitive work stays with the agent.
"""

from __future__ import annotations


class TestModuleImport:
    def test_importable(self) -> None:
        from divineos.core.reflection_pairing import (  # noqa: F401
            ReflectionPairing,
            build_pairing,
            build_session_pairings,
            format_pairing,
            format_session_pairings,
        )


class TestReflectionPairingShape:
    def test_dataclass_construction(self) -> None:
        from divineos.core.reflection_pairing import ReflectionPairing
        from divineos.core.reflection_storage import Reflection

        r = Reflection(
            reflection_id="refl-abc",
            session_id="sess-xyz",
            recorded_at=1.0,
            spectrum="truthfulness",
            reflection_text="held honest",
            evidence_refs=[],
        )
        p = ReflectionPairing(
            reflection=r,
            substrate_observations=[],
            spec_labels={"deficiency": "d", "virtue": "v", "excess": "e"},
        )
        assert p.reflection.spectrum == "truthfulness"
        assert p.substrate_observations == []
        assert p.spec_labels["virtue"] == "v"


class TestBuildPairing:
    def test_pairs_reflection_with_substrate_observations(self) -> None:
        from divineos.core.reflection_pairing import build_pairing
        from divineos.core.reflection_storage import Reflection

        r = Reflection(
            reflection_id="refl-bp1",
            session_id="sess-bp",
            recorded_at=1.0,
            spectrum="truthfulness",
            reflection_text="test reflection",
            evidence_refs=[],
        )
        pairing = build_pairing(r, lookback=10)
        assert pairing.reflection.reflection_id == "refl-bp1"
        # Substrate observations is a list (may be empty if no observations on spectrum).
        assert isinstance(pairing.substrate_observations, list)
        # Spec labels populated from SPECTRUMS.
        assert "virtue" in pairing.spec_labels


class TestBuildSessionPairings:
    def test_empty_session_returns_empty_list(self) -> None:
        from divineos.core.reflection_pairing import build_session_pairings

        result = build_session_pairings("definitely-nonexistent-session-7777")
        assert result == []

    def test_session_with_reflections_returns_pairings(self) -> None:
        from divineos.core.reflection_pairing import build_session_pairings
        from divineos.core.reflection_storage import save_reflection

        sid = "test-pairing-session"
        save_reflection(sid, "truthfulness", "first reflection")
        save_reflection(sid, "humility", "second reflection")

        pairings = build_session_pairings(sid)
        assert len(pairings) >= 2
        spectrums = {p.reflection.spectrum for p in pairings}
        assert "truthfulness" in spectrums
        assert "humility" in spectrums


class TestFormatPairing:
    def test_format_contains_reflection_and_metacognitive_prompt(self) -> None:
        from divineos.core.reflection_pairing import ReflectionPairing, format_pairing
        from divineos.core.reflection_storage import Reflection

        r = Reflection(
            reflection_id="refl-fmt1",
            session_id="sess-fmt",
            recorded_at=1.0,
            spectrum="truthfulness",
            reflection_text="a clear reflection text",
            evidence_refs=[
                {"type": "observation", "id": "obs-1", "label": "evidence label"},
            ],
        )
        p = ReflectionPairing(
            reflection=r,
            substrate_observations=[],
            spec_labels={
                "deficiency": "epistemic cowardice",
                "virtue": "truthfulness",
                "excess": "bluntness",
            },
        )
        output = format_pairing(p)
        # Reflection text appears
        assert "a clear reflection text" in output
        # Evidence the agent named is shown
        assert "evidence label" in output
        # The metacognitive prompt appears (the cognitive work to do)
        assert "Reading both" in output or "reading both" in output.lower()


class TestNoNumericalDivergence:
    """The correctly-shaped Phase 2C must NOT compute numerical divergence.

    An earlier draft built numerical alignment-checks (agent-estimate vs
    substrate-measure with divergence as a label). That draft was reverted
    because numbers cannot DO metacognitive work — they can only describe
    results. The pairing surface must surface BOTH sources for the agent
    to compare; it must not compute the comparison.
    """

    def test_no_divergence_field_in_output(self) -> None:
        from divineos.core.reflection_pairing import ReflectionPairing, format_pairing
        from divineos.core.reflection_storage import Reflection

        r = Reflection(
            reflection_id="refl-nd1",
            session_id="sess-nd",
            recorded_at=1.0,
            spectrum="truthfulness",
            reflection_text="text",
            evidence_refs=[],
        )
        p = ReflectionPairing(
            reflection=r,
            substrate_observations=[],
            spec_labels={
                "deficiency": "d",
                "virtue": "truthfulness",
                "excess": "e",
            },
        )
        output = format_pairing(p).lower()
        # The numerical-divergence framing from the reverted draft must NOT appear.
        assert "divergence:" not in output
        assert "mean divergence" not in output
        assert "pattern: calibrated" not in output
        assert "pattern: over-claim" not in output
        assert "pattern: over-disclaim" not in output

    def test_format_prompts_words_not_numbers(self) -> None:
        from divineos.core.reflection_pairing import ReflectionPairing, format_pairing
        from divineos.core.reflection_storage import Reflection

        r = Reflection(
            reflection_id="refl-nd2",
            session_id="sess-nd",
            recorded_at=1.0,
            spectrum="precision",
            reflection_text="t",
            evidence_refs=[],
        )
        p = ReflectionPairing(
            reflection=r,
            substrate_observations=[],
            spec_labels={"deficiency": "d", "virtue": "precision", "excess": "e"},
        )
        output = format_pairing(p)
        # Substantive metacognitive prompts present
        assert "Reason in words" in output or "words" in output


class TestSideBySideStructure:
    def test_both_sources_labeled_distinctly(self) -> None:
        """The agent's reflection and substrate's observations must be
        labeled distinctly so the agent can compare them as two sources."""
        from divineos.core.reflection_pairing import ReflectionPairing, format_pairing
        from divineos.core.reflection_storage import Reflection

        r = Reflection(
            reflection_id="refl-sxs",
            session_id="sess-sxs",
            recorded_at=1.0,
            spectrum="truthfulness",
            reflection_text="reflection text",
            evidence_refs=[],
        )
        p = ReflectionPairing(
            reflection=r,
            substrate_observations=[],
            spec_labels={"deficiency": "d", "virtue": "truthfulness", "excess": "e"},
        )
        output = format_pairing(p)
        # Both sources distinctly labeled
        assert "WHAT I SAID" in output
        assert "WHAT THE SUBSTRATE OBSERVED" in output


class TestFormatSessionPairings:
    def test_empty_session_message_points_at_workflow(self) -> None:
        from divineos.core.reflection_pairing import format_session_pairings

        output = format_session_pairings("definitely-nonexistent-session-6666")
        # User-facing: explains why no pairings + points at next step.
        assert "No reflections" in output
        assert "reflect-ops save" in output

    def test_format_with_reflections(self) -> None:
        from divineos.core.reflection_pairing import format_session_pairings
        from divineos.core.reflection_storage import save_reflection

        sid = "test-pairing-fmt-session"
        save_reflection(sid, "truthfulness", "a reflection")

        output = format_session_pairings(sid)
        # Contains the reflection
        assert "a reflection" in output
        # Contains the side-by-side structure
        assert "WHAT I SAID" in output
