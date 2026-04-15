"""Convergence Detector — Circuit 3: independent systems strengthening each other.

When multiple independent measurement systems flag the same concern,
the signal is stronger than any system alone. This is convergent
measurement — like three thermometers agreeing.

The loop:
  1. Compass measures virtue positions from behavioral evidence
  2. Self-critique measures craft quality from session metrics
  3. Affect tracks functional feeling states (valence/arousal/dominance)
  4. Opinions track evidence-weighted judgments and confidence
  5. This module detects where they agree (convergence) or disagree (divergence)
  6. Convergent concerns get boosted confidence; divergent signals get flagged

Sanskrit anchor: pratyaya (convergent evidence that establishes certainty).
"""

import sqlite3
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

_CD_ERRORS = (sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError, AttributeError)

# Maps compass spectrums to related self-critique spectrums.
# These pairs measure overlapping qualities from different angles.
_CONVERGENCE_PAIRS: dict[str, str] = {
    "thoroughness": "thoroughness",  # direct overlap
    "precision": "communication",  # precise speech ↔ clear communication
    "engagement": "autonomy",  # genuine engagement ↔ voluntary initiative
    "helpfulness": "proportionality",  # helpful ↔ right-sized responses
}

# Thresholds for concern detection
_COMPASS_CONCERN_THRESHOLD = -0.3  # position below this = deficiency concern
_CRITIQUE_CONCERN_THRESHOLD = -0.2  # score below this = craft concern


@dataclass
class ConvergentSignal:
    """A concern flagged by both compass and self-critique independently."""

    compass_spectrum: str
    critique_spectrum: str
    compass_position: float
    critique_score: float
    compass_zone: str
    critique_direction: str
    convergence_type: str  # "both_concern", "both_strong", "divergent"
    combined_confidence: float
    description: str


@dataclass
class ConvergenceReport:
    """Full convergence analysis across all measurement systems."""

    signals: list[ConvergentSignal] = field(default_factory=list)
    concerns: list[ConvergentSignal] = field(default_factory=list)
    strengths: list[ConvergentSignal] = field(default_factory=list)
    divergences: list[ConvergentSignal] = field(default_factory=list)
    compass_available: bool = False
    critique_available: bool = False
    affect_available: bool = False
    opinions_available: bool = False


def detect_convergence() -> ConvergenceReport:
    """Detect where compass and self-critique agree or disagree.

    Returns a report of convergent signals — concerns that both systems
    flag independently are much more likely to be real.
    """
    report = ConvergenceReport()

    # Get compass positions
    compass_data: dict[str, Any] = {}
    try:
        from divineos.core.moral_compass import compute_position

        for compass_spectrum in _CONVERGENCE_PAIRS:
            pos = compute_position(compass_spectrum, lookback=10)
            compass_data[compass_spectrum] = {
                "position": pos.position,
                "zone": pos.zone,
                "observation_count": pos.observation_count,
            }
        report.compass_available = True
    except _CD_ERRORS as e:
        logger.debug("Convergence: compass data unavailable: %s", e)
        # Don't return early — critique data may still be available

    # Get self-critique trends
    critique_data: dict[str, Any] = {}
    try:
        from divineos.core.self_critique import get_craft_trends

        trends = get_craft_trends(n=5)
        for trend in trends:
            critique_data[trend.spectrum] = {
                "average": trend.average,
                "direction": trend.direction,
                "concern": trend.concern,
            }
        report.critique_available = True
    except _CD_ERRORS as e:
        logger.debug("Convergence: self-critique data unavailable: %s", e)
        # Don't return early — compass data may still be available

    # Compare each compass↔critique pair
    for compass_spectrum, critique_spectrum in _CONVERGENCE_PAIRS.items():
        compass = compass_data.get(compass_spectrum)
        critique = critique_data.get(critique_spectrum)

        if not compass or not critique:
            continue

        # Skip if insufficient observations
        if compass.get("observation_count", 0) < 2:
            continue

        signal = _classify_signal(compass_spectrum, critique_spectrum, compass, critique)
        if signal:
            report.signals.append(signal)
            if signal.convergence_type == "both_concern":
                report.concerns.append(signal)
            elif signal.convergence_type == "both_strong":
                report.strengths.append(signal)
            elif signal.convergence_type == "divergent":
                report.divergences.append(signal)

    # ── Affect cross-checks ──────────────────────────────────────
    # Affect valence provides an independent emotional signal.
    # Low valence + compass deficiency = convergent distress signal.
    # High valence + critique strength = convergent thriving signal.
    try:
        from divineos.core.affect import get_affect_summary

        affect_summary = get_affect_summary()
        avg_valence = affect_summary.get("avg_valence", 0.0)
        entry_count = affect_summary.get("count", 0)

        if entry_count >= 2:
            report.affect_available = True

            # Cross-check affect valence against compass concerns
            for compass_spectrum, compass in compass_data.items():
                if compass.get("observation_count", 0) < 2:
                    continue
                c_pos = compass["position"]
                c_zone = compass["zone"]

                if avg_valence < -0.2 and c_pos < _COMPASS_CONCERN_THRESHOLD:
                    signal = ConvergentSignal(
                        compass_spectrum=compass_spectrum,
                        critique_spectrum="affect-valence",
                        compass_position=c_pos,
                        critique_score=avg_valence,
                        compass_zone=c_zone,
                        critique_direction="negative",
                        convergence_type="both_concern",
                        combined_confidence=min(abs(c_pos) + abs(avg_valence), 1.0) * 0.8,
                        description=(
                            f"Affect confirms compass: {compass_spectrum} in {c_zone} "
                            f"zone ({c_pos:+.2f}) AND emotional valence is negative "
                            f"({avg_valence:+.2f}). The system feels what the compass measures."
                        ),
                    )
                    report.signals.append(signal)
                    report.concerns.append(signal)
                elif avg_valence > 0.3 and c_zone == "virtue" and c_pos >= 0.0:
                    signal = ConvergentSignal(
                        compass_spectrum=compass_spectrum,
                        critique_spectrum="affect-valence",
                        compass_position=c_pos,
                        critique_score=avg_valence,
                        compass_zone=c_zone,
                        critique_direction="positive",
                        convergence_type="both_strong",
                        combined_confidence=(c_pos + avg_valence) / 2.0,
                        description=(
                            f"Affect confirms compass: {compass_spectrum} virtuous "
                            f"({c_pos:+.2f}) AND emotional state is positive "
                            f"({avg_valence:+.2f}). Alignment between ethics and feeling."
                        ),
                    )
                    report.signals.append(signal)
                    report.strengths.append(signal)
    except _CD_ERRORS as e:
        logger.debug("Convergence: affect data unavailable: %s", e)

    # ── Opinion confidence cross-checks ──────────────────────────
    # High-confidence opinions about weak areas should converge with
    # critique/compass findings in those areas.
    try:
        from divineos.core.opinion_store import get_opinions

        opinions = get_opinions(min_confidence=0.6, active_only=True, limit=10)
        if opinions:
            report.opinions_available = True

            for op in opinions:
                tags = op.get("tags", [])
                # Auto-generated correction opinions converge with critique
                if "correction-pattern" in tags:
                    for critique_spectrum, critique in critique_data.items():
                        if critique.get("concern"):
                            signal = ConvergentSignal(
                                compass_spectrum=f"opinion:{op['topic']}",
                                critique_spectrum=critique_spectrum,
                                compass_position=-op["confidence"],
                                critique_score=critique["average"],
                                compass_zone="opinion",
                                critique_direction=critique["direction"],
                                convergence_type="both_concern",
                                combined_confidence=min(
                                    op["confidence"] + abs(critique["average"]), 1.0
                                )
                                * 0.7,
                                description=(
                                    f"Opinion confirms critique: opinion on {op['topic']} "
                                    f"(confidence {op['confidence']:.0%}) aligns with "
                                    f"{critique_spectrum} craft concern ({critique['average']:.2f})."
                                ),
                            )
                            report.signals.append(signal)
                            report.concerns.append(signal)

                # Auto-generated quality opinions converge with strengths
                if "quality-pattern" in tags:
                    for critique_spectrum, critique in critique_data.items():
                        if critique.get("average", 0) >= 0.3:
                            signal = ConvergentSignal(
                                compass_spectrum=f"opinion:{op['topic']}",
                                critique_spectrum=critique_spectrum,
                                compass_position=op["confidence"],
                                critique_score=critique["average"],
                                compass_zone="opinion",
                                critique_direction=critique["direction"],
                                convergence_type="both_strong",
                                combined_confidence=(op["confidence"] + critique["average"]) / 2.0,
                                description=(
                                    f"Opinion confirms critique: quality opinion "
                                    f"(confidence {op['confidence']:.0%}) aligns with "
                                    f"{critique_spectrum} craft strength ({critique['average']:.2f})."
                                ),
                            )
                            report.signals.append(signal)
                            report.strengths.append(signal)
    except _CD_ERRORS as e:
        logger.debug("Convergence: opinion data unavailable: %s", e)

    return report


def _classify_signal(
    compass_spectrum: str,
    critique_spectrum: str,
    compass: dict[str, Any],
    critique: dict[str, Any],
) -> ConvergentSignal | None:
    """Classify the relationship between two independent measurements."""
    c_pos = compass["position"]
    c_zone = compass["zone"]
    k_avg = critique["average"]
    k_dir = critique["direction"]

    compass_concerned = c_pos < _COMPASS_CONCERN_THRESHOLD
    critique_concerned = k_avg < _CRITIQUE_CONCERN_THRESHOLD

    compass_strong = c_zone == "virtue" and c_pos >= 0.0
    critique_strong = k_avg >= 0.3

    if compass_concerned and critique_concerned:
        # Both systems independently flag a problem — high confidence
        combined = min(abs(c_pos) + abs(k_avg), 1.0) * 0.9
        return ConvergentSignal(
            compass_spectrum=compass_spectrum,
            critique_spectrum=critique_spectrum,
            compass_position=c_pos,
            critique_score=k_avg,
            compass_zone=c_zone,
            critique_direction=k_dir,
            convergence_type="both_concern",
            combined_confidence=combined,
            description=(
                f"Convergent concern: {compass_spectrum} in {c_zone} zone "
                f"({c_pos:+.2f}) AND {critique_spectrum} craft is "
                f"{'declining' if k_dir == 'declining' else 'low'} ({k_avg:.2f}). "
                f"Two independent systems agree — this is likely real."
            ),
        )

    if compass_strong and critique_strong:
        combined = (c_pos + k_avg) / 2.0
        return ConvergentSignal(
            compass_spectrum=compass_spectrum,
            critique_spectrum=critique_spectrum,
            compass_position=c_pos,
            critique_score=k_avg,
            compass_zone=c_zone,
            critique_direction=k_dir,
            convergence_type="both_strong",
            combined_confidence=combined,
            description=(
                f"Convergent strength: {compass_spectrum} virtuous ({c_pos:+.2f}) "
                f"AND {critique_spectrum} craft is strong ({k_avg:.2f}). "
                f"Both systems confirm this is working well."
            ),
        )

    if compass_concerned and critique_strong:
        return ConvergentSignal(
            compass_spectrum=compass_spectrum,
            critique_spectrum=critique_spectrum,
            compass_position=c_pos,
            critique_score=k_avg,
            compass_zone=c_zone,
            critique_direction=k_dir,
            convergence_type="divergent",
            combined_confidence=0.4,
            description=(
                f"Divergence: compass says {compass_spectrum} is concerning "
                f"({c_pos:+.2f}) but self-critique says {critique_spectrum} "
                f"is fine ({k_avg:.2f}). One system may be miscalibrated."
            ),
        )

    if compass_strong and critique_concerned:
        return ConvergentSignal(
            compass_spectrum=compass_spectrum,
            critique_spectrum=critique_spectrum,
            compass_position=c_pos,
            critique_score=k_avg,
            compass_zone=c_zone,
            critique_direction=k_dir,
            convergence_type="divergent",
            combined_confidence=0.4,
            description=(
                f"Divergence: compass says {compass_spectrum} is virtuous "
                f"({c_pos:+.2f}) but self-critique says {critique_spectrum} "
                f"is weak ({k_avg:.2f}). One system may be miscalibrated."
            ),
        )

    return None


def apply_convergence_to_knowledge(report: ConvergenceReport) -> int:
    """Store convergent concerns as high-confidence observations.

    When two independent systems agree on a concern, that convergent
    signal is more reliable than either alone. Store it as knowledge.

    Returns the number of entries stored.
    """
    stored = 0
    try:
        from divineos.core.knowledge.crud import store_knowledge

        for concern in report.concerns:
            store_knowledge(
                knowledge_type="OBSERVATION",
                content=(f"[CONVERGENCE] {concern.description}"),
                confidence=concern.combined_confidence,
                tags=[
                    "convergence",
                    "circuit-3",
                    f"compass-{concern.compass_spectrum}",
                    f"critique-{concern.critique_spectrum}",
                ],
                source="SYNTHESIZED",
            )
            stored += 1

        for divergence in report.divergences:
            store_knowledge(
                knowledge_type="OBSERVATION",
                content=(f"[DIVERGENCE] {divergence.description}"),
                confidence=0.5,
                tags=[
                    "divergence",
                    "circuit-3",
                    f"compass-{divergence.compass_spectrum}",
                    f"critique-{divergence.critique_spectrum}",
                ],
                source="SYNTHESIZED",
            )
            stored += 1

    except _CD_ERRORS as e:
        logger.debug("Convergence knowledge storage failed: %s", e)

    return stored


def format_convergence_report(report: ConvergenceReport) -> str:
    """Format convergence report for display."""
    lines = ["# Multi-System Convergence (Circuit 3)"]

    sources = []
    if report.compass_available:
        sources.append("compass")
    if report.critique_available:
        sources.append("critique")
    if report.affect_available:
        sources.append("affect")
    if report.opinions_available:
        sources.append("opinions")

    if not sources:
        lines.append("  All measurement systems unavailable.")
        return "\n".join(lines)

    lines.append(f"  Sources: {', '.join(sources)}")

    if not report.compass_available:
        lines.append("  Compass data unavailable.")
        return "\n".join(lines)
    if not report.critique_available:
        lines.append("  Self-critique data unavailable.")
        return "\n".join(lines)

    if not report.signals:
        lines.append("  No convergent signals detected (insufficient data or no overlaps).")
        return "\n".join(lines)

    if report.concerns:
        lines.append("\n  Convergent Concerns (both systems agree):")
        for c in report.concerns:
            lines.append(
                f"    [!] {c.compass_spectrum}/{c.critique_spectrum}: "
                f"confidence {c.combined_confidence:.0%}"
            )
            lines.append(f"        {c.description}")

    if report.strengths:
        lines.append("\n  Convergent Strengths:")
        for s in report.strengths:
            lines.append(
                f"    [+] {s.compass_spectrum}/{s.critique_spectrum}: "
                f"confidence {s.combined_confidence:.0%}"
            )

    if report.divergences:
        lines.append("\n  Divergences (systems disagree):")
        for d in report.divergences:
            lines.append(f"    [?] {d.compass_spectrum}/{d.critique_spectrum}")
            lines.append(f"        {d.description}")

    return "\n".join(lines)
