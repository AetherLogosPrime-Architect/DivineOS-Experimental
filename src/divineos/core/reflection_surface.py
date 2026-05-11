"""Per-axis reflection surface — replaces shoggoth-grade metrics.

Filed 2026-05-11 by Aether, with Andrew + Grok external review +
12-lens council walk. See exploration/44_shoggoth_metrics_redesign.md
for the full design spec.

## What this is

A reporting surface that presents the 10 compass spectrums alongside
evidence from the session, then prompts the agent to reflect honestly
on each axis — backing the reflection with specific evidence the
substrate surfaced.

## What this replaces

The composite single-number/letter outputs (session_grade,
alignment_score, "10/10 in virtue zone" headline) that hid multi-axis
truth behind aspirational naming.

## What this is NOT

This module does **not** compute the agent's position on each axis.
That's the cognitive work of reflection — and the substrate's job is
to surface the axes + evidence, not to grade. Doing the cognitive work
for the agent IS the substitution-pattern from CLAUDE.md operating at
the extract layer.

## Design principles (from the spec)

1. No central grader — each axis stands independently.
2. Human-readable first, machine-parseable second.
3. Honest names — what each thing actually is, not what we wish it were.
4. No fallback to single summary number — refuses school-grading
   regression-pressure structurally.

## The Goodhart-resistance check

The output is honest text + evidence pointers. There's no number to
optimize toward, so no Goodhart pressure. The only thing to "optimize"
is honest reflection, and divergence between reflection and measured
patterns is itself the signal — gaming the reflection would show up
as divergence from evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from divineos.core.moral_compass import SPECTRUMS


@dataclass(frozen=True)
class AxisSurface:
    """One axis of the reflection surface.

    The substrate fills the measurable fields; the agent fills the
    reflection text separately (this dataclass just structures the
    prompt).
    """

    spectrum: str
    spec: dict[str, str]  # deficiency/virtue/excess labels
    position: float  # -1.0 to +1.0, 0.0 = virtue
    zone: str  # "deficiency", "virtue", "excess", "unobserved"
    label: str  # human-readable position name
    drift: float
    drift_direction: str  # "toward_virtue", "toward_deficiency", "toward_excess", "stable"
    observation_count: int
    recent_observations: list[dict[str, Any]]  # last N observations on this spectrum


def build_axis_surface(spectrum: str, lookback: int = 20) -> AxisSurface:
    """Build the substrate-surface for one axis.

    The agent reflects on top of this; the substrate does NOT grade.
    """
    from divineos.core.moral_compass import compute_position, get_observations

    pos = compute_position(spectrum, lookback=lookback)
    recent = get_observations(spectrum=spectrum, limit=5)
    spec = SPECTRUMS[spectrum]

    return AxisSurface(
        spectrum=spectrum,
        spec=dict(spec),
        position=pos.position,
        zone=pos.zone,
        label=pos.label,
        drift=pos.drift,
        drift_direction=pos.drift_direction,
        observation_count=pos.observation_count,
        recent_observations=recent,
    )


def build_reflection_surface(lookback: int = 20) -> list[AxisSurface]:
    """Build the full per-axis reflection surface across all 10 spectrums.

    Returns one AxisSurface per spectrum, in declaration order.
    """
    return [build_axis_surface(s, lookback=lookback) for s in SPECTRUMS]


def format_axis_for_reflection(axis: AxisSurface) -> str:
    """Format one axis as a reflection prompt block.

    The block presents the substrate's data and prompts the agent to
    reflect. The agent's reflection is NOT part of the block — it
    happens in the conversation after the surface is shown.
    """
    spec = axis.spec
    drift_marker = ""
    if axis.drift_direction == "toward_virtue":
        drift_marker = f"^ toward_virtue ({axis.drift:+.2f})"
    elif axis.drift_direction == "toward_deficiency":
        drift_marker = f"<-- toward_deficiency ({axis.drift:+.2f})"
    elif axis.drift_direction == "toward_excess":
        drift_marker = f"--> toward_excess ({axis.drift:+.2f})"

    lines = [
        f"  {axis.spectrum.upper()}:",
        f"    {spec['deficiency']} <-- [{spec['virtue']}] --> {spec['excess']}",
        f"    position: {axis.position:+.2f} | zone: {axis.zone} ({axis.label})",
    ]
    if drift_marker:
        lines.append(f"    drift: {drift_marker}")
    lines.append(f"    observations: {axis.observation_count}")

    if axis.recent_observations:
        lines.append("    recent evidence:")
        for obs in axis.recent_observations[:3]:
            evidence_text = obs.get("evidence", "")[:120]
            obs_id = obs.get("obs_id", "")[:8]
            lines.append(f"      [{obs_id}] {evidence_text}")

    lines.append("")
    lines.append("    Reflect honestly: how did I hold this virtue this session?")
    lines.append("    Back the reflection with evidence (event IDs, observations,")
    lines.append("    knowledge entries, conversation moments). Don't grade — describe.")
    return "\n".join(lines)


def format_reflection_surface(
    lookback: int = 20,
    session_type_result: Any = None,
) -> str:
    """Format the full per-axis reflection surface as displayable text.

    This is the substrate-surface only. The agent's reflections are
    not part of this output.

    If session_type_result is provided (Phase 2B integration), the
    classification appears at the top with the type-relevant axes
    named — but ALL 10 axes are still shown. Type is a router, not
    a suppressor.
    """
    surfaces = build_reflection_surface(lookback=lookback)

    header = [
        "=" * 60,
        "REFLECTION SURFACE — 10 axes for honest self-review",
        "=" * 60,
        "",
    ]

    if session_type_result is not None:
        from divineos.core.session_type import format_session_type

        header.append(format_session_type(session_type_result))
        header.append("")

    header.extend(
        [
            "Substrate's role: present axes + evidence.",
            "Agent's role: reflect honestly, back with evidence.",
            "No central grader. No summary score. Each axis stands alone.",
            "",
        ]
    )

    blocks = [format_axis_for_reflection(s) for s in surfaces]

    footer = [
        "",
        "=" * 60,
        "After reflecting on each axis: the alignment check (Phase 2C)",
        "will compare your reflection against measured patterns.",
        "Divergence is honesty-calibration signal, not failure judgment.",
        "",
        'To save a reflection: divineos reflect-ops save <axis> "<text>"',
        '  -e <type>:<id>:"<label>" (repeatable for evidence pointers)',
        "=" * 60,
    ]

    return "\n".join(header + blocks + footer)
