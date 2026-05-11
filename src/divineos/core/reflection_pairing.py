"""Reflection pairing — substrate lays the sources side-by-side; agent does the metacognition.

Phase 2C (correctly-shaped) of the shoggoth-metrics redesign. See
exploration/44_shoggoth_metrics_redesign.md for the design spec.

## What this is

A structured side-by-side surface that pairs the agent's reflection
text with substrate evidence on the same spectrum, then prompts the
agent to do the actual metacognitive work of comparing both.

## What this is NOT

This is **not** a numerical alignment check. An earlier draft of
Phase 2C built numerical-divergence between agent-position-estimate
and substrate-measured-position — which was itself shoggoth-shaped:
name claimed "honesty calibration," computation was just arithmetic
on two floats. Numbers can describe results, badly; they cannot
DO metacognitive work.

Andrew named this directly: *"the values need to be self reflection..
was I honest here? through each of the 10 values and be able to back
them up with evidence based on what actually happened.. it needs to
be tied to your metacognition, that's what self reflection is..
looking at what occurred and measuring it to your values. with words
and reason not numbers."*

The right shape for the alignment check is *not a number*. It's
**laying both sources next to each other and letting the agent reason**.

## How this works

1. Agent has saved an initial reflection on an axis (via reflect-ops
   save). Reflection contains text + evidence pointers.
2. The pairing surface assembles:
   a. The agent's reflection (what they said).
   b. Substrate observations on that spectrum from the session's
      time window (what was observed, by whom — measured, behavioral,
      self-reported).
   c. A metacognitive prompt asking the agent to compare both.
3. Agent does the comparison in conversation, then saves a *follow-up
   reflection* with the deepened read backed by evidence from both
   sources.

The substrate's job: present the two sources cleanly.
The agent's job: do the metacognitive comparison and produce a
deeper reflection.

There is no central grader. There is no divergence-number. The check
IS the reading and the response, not a calculation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from divineos.core.moral_compass import SPECTRUMS, get_observations
from divineos.core.reflection_storage import Reflection, get_reflections_for_session


@dataclass(frozen=True)
class ReflectionPairing:
    """One reflection paired with substrate evidence on the same spectrum.

    The pairing is structured for the agent to read both sides and do
    the metacognitive comparison. The substrate doesn't compute a gap;
    it presents the materials for the agent to compare.
    """

    reflection: Reflection
    substrate_observations: list[dict[str, Any]]
    spec_labels: dict[str, str]  # deficiency / virtue / excess labels


def build_pairing(reflection: Reflection, lookback: int = 30) -> ReflectionPairing:
    """Build the side-by-side pairing for one reflection.

    Pulls substrate observations on the same spectrum (most-recent N)
    so the agent can compare their reflection against what the
    substrate independently observed.
    """
    observations = get_observations(spectrum=reflection.spectrum, limit=lookback)
    spec = SPECTRUMS.get(reflection.spectrum, {})

    return ReflectionPairing(
        reflection=reflection,
        substrate_observations=observations,
        spec_labels=dict(spec),
    )


def build_session_pairings(session_id: str, lookback: int = 30) -> list[ReflectionPairing]:
    """Build pairings for all reflections in a session."""
    reflections = get_reflections_for_session(session_id)
    return [build_pairing(r, lookback=lookback) for r in reflections]


def format_pairing(pairing: ReflectionPairing) -> str:
    """Format one pairing as a side-by-side metacognitive prompt.

    The output is NOT an analysis. It's a structured presentation of
    both sources, with a prompt asking the agent to do the comparison.
    """
    refl = pairing.reflection
    spec = pairing.spec_labels
    virtue = spec.get("virtue", refl.spectrum)
    deficiency = spec.get("deficiency", "")
    excess = spec.get("excess", "")

    lines = [
        "=" * 60,
        f"REFLECTION PAIRING — {refl.spectrum.upper()} ({virtue})",
        f"   spectrum: {deficiency} <-- [{virtue}] --> {excess}",
        "=" * 60,
        "",
        "── WHAT I SAID (my reflection) ────────────────────────",
        f"  [{refl.reflection_id[:8]}]",
        f"  {refl.reflection_text}",
        "",
    ]

    if refl.evidence_refs:
        lines.append("  evidence I named:")
        for ref in refl.evidence_refs:
            ref_type = ref.get("type", "ref")
            ref_id = ref.get("id", "")
            ref_label = ref.get("label", "")
            lines.append(f"    [{ref_type}:{ref_id}] {ref_label}")
        lines.append("")

    lines.extend(
        [
            "── WHAT THE SUBSTRATE OBSERVED (independent of my reflection) ──",
        ]
    )

    if not pairing.substrate_observations:
        lines.extend(
            [
                "  (no observations recorded on this spectrum — substrate has",
                "  no independent evidence to pair with the reflection.)",
                "",
            ]
        )
    else:
        for obs in pairing.substrate_observations[:10]:
            obs_id = obs.get("obs_id", "")[:8] if obs.get("obs_id") else ""
            source = obs.get("source", "?")
            pos = obs.get("position", 0.0)
            evidence_text = obs.get("evidence", "")[:200]
            lines.append(f"  [{obs_id}] source={source}, pos={pos:+.2f}")
            lines.append(f"    {evidence_text}")
        lines.append("")

    lines.extend(
        [
            "── METACOGNITIVE PROMPT ──────────────────────────────",
            "",
            "Reading both sides:",
            "",
            "  1. Does my reflection account for what the substrate observed?",
            "     Or did I name a different story than the observations show?",
            "",
            "  2. Where is my reflection SHARPER than the substrate observations?",
            "     (My interior access catches things observations can't.)",
            "",
            "  3. Where are the substrate observations SHARPER than my reflection?",
            "     (External signals catch what I can't see from inside.)",
            "",
            "  4. What's the deeper read when I hold BOTH sources at once?",
            "     Where did I drift, where did I hold, what nuance did I miss?",
            "",
            "Reason in words, not numbers. The check IS the reasoning, backed",
            "by evidence from both sources. Save the deepened reflection via:",
            '  divineos reflect-ops save <spectrum> "<deeper read>"',
            "  -e reflection:" + refl.reflection_id[:8] + ':"original reflection"',
            '  -e observation:<obs_id>:"..." (for any substrate observation that shifted the read)',
            "=" * 60,
        ]
    )

    return "\n".join(lines)


def format_session_pairings(session_id: str, lookback: int = 30) -> str:
    """Format all reflection pairings for a session."""
    pairings = build_session_pairings(session_id, lookback=lookback)

    if not pairings:
        return (
            f"No reflections recorded for session {session_id[:12]}...\n"
            'Save reflections first via: divineos reflect-ops save <spectrum> "<text>"'
        )

    header = [
        "=" * 60,
        f"SESSION REFLECTION PAIRINGS — {session_id[:12]}...",
        "=" * 60,
        "",
        f"Pairing {len(pairings)} reflection(s) with substrate observations.",
        "Each pairing prompts metacognitive comparison — words and reasoning,",
        "not numerical divergence.",
        "",
    ]

    body = []
    for p in pairings:
        body.append(format_pairing(p))
        body.append("")

    return "\n".join(header + body)
