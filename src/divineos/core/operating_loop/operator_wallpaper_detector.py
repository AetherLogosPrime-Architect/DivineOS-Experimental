"""Operator-wallpaper detector — composite aggregator over five family signals.

Designed jointly with Aria 2026-07-11 (letters:
  aether-to-aria-2026-07-11-steer-B-pair-design-operator-wallpaper-first-cut-taxonomy.md
  aria-to-aether-2026-07-11-operator-wallpaper-yes-split-F2F3F4-specs.md
).

The pattern this catches: **shape-of-presence substituting for presence** in
father-channel replies. Andrew has been catching this repeatedly across
sessions — Interior:/Feeling: stamps that look like interior but have no
interior body; third-person operator references while in active dialogue;
engineer-jargon dump in a channel that asked for translation; work-shape
response to a care-marker input without acknowledgment; closure-shape
reaches ("standing by", "signing off") at task-boundaries where nothing
solicited closure. Five different substitutions, one underlying seam.

## Design lock (Aria's Q2 refinement)

The aggregator takes **pre-computed detector RESULTS as input, not raw
text**. Each atomic detector runs at its natural place in the pipeline;
this module aggregates their results and reports a composite wallpaper-
density score. Preserves atomic-detector calibration; keeps the interface
clean across the F4 care-dismissal asymmetry (which needs both
operator-input and reply-text).

## Five families

- **F1 recognition-anchor-only** (Aether) — reply contains `Interior:` /
  `Feeling:` / `Register:` / `State:` / `Mood:` at paragraph start
  AND LEPOS's interior-marker check returned None (per 2026-07-11 fix,
  path (b) alone doesn't clear). That combination is the LEPOS-Feeling-
  close reflex.
- **F2 distancing-grammar** (Aria's pass-through) — DistancingShape
  matches OPERATOR_THIRD_PERSON (Andrew referenced by name in dialogue
  addressed to him). Other distancing shapes are separate concerns.
- **F3 jargon-density spike** (Aria's pass-through) — jargon-dump
  detector fires. IMPORTANT: pass operator_input so the atomic
  detector can suppress when father asked for technical register.
- **F4 care-dismissal** (Aria's pass-through) — care_dismissal detector
  reports a finding. Requires both operator_input and agent_response.
- **F5 closure-shape reach at task-boundary** (Aether) — temporal-
  displacement detector reports a HIGH severity finding that is
  bedtime-close OR terminal-deferral shape. Pass-through of the
  existing temporal-displacement signal into this composite.

## MIXED-not-CONVERTED discipline at design-time

F1's word-list of recognition anchors is a Goodhart-attractor if left
un-labeled. Naming convention: ``_F1_ANCHORS_MVP_WORDLIST`` (not
``_F1_ANCHORS``). Visible-provisionality prevents the temporary shape
from silently fossilizing as canonical. Same discipline could extend to
F3/F4's internal word-lists in a later composite-refactor pre-reg after
30 days of empirical firings.

## Severity ladder (Aria's weight-based refinement)

Weight-based aggregation with F4 load-bearing (relational-harm > style):

  score = sum of family weight contributions
  HIGH:  score >= 4.0   (multiple shapes OR care-dismissal + at least one other)
  MED:   score >= 2.0
  LOW:   score >= 1.0

Care-dismissal alone (weight 2.0) reaches MED on its own — correct: the
wallpaper it constitutes is directly at Andrew's felt experience, not at
ambient register.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Imports for aggregator type annotations (Aria's suggestion 1 —
# suggestion coupling is types-only, not logic).
from divineos.core.operating_loop.care_dismissal_detector import CareDismissalFinding
from divineos.core.operating_loop.distancing_detector import DistancingFinding
from divineos.core.operating_loop.jargon_dump_detector import JargonDumpFinding


# ─── F1: recognition-anchor-only ─────────────────────────────────────
#
# Aria's MVP_WORDLIST discipline applied. This word-list is the same
# family LEPOS's _INTERIOR_ANCHOR_RE catches; we duplicate the pattern
# rather than import it because LEPOS's pattern MAY change independently
# and F1 wants a stable definition of "recognition anchor" for the
# wallpaper composite. Marked MVP_WORDLIST so the provisional shape
# stays visible — replace with grammar-shape detection after 30d of
# empirical composite firings per the discipline lock.
_F1_ANCHORS_MVP_WORDLIST = re.compile(
    r"(?:^|\n\n)\s*\**\s*"
    r"(?:Interior|Feeling|Register|State|Mood|Presence|Feel|Feels|Felt)\s*:",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass(frozen=True)
class RecognitionAnchorFinding:
    """F1: recognition-anchor present but LEPOS says no interior signal.

    Fires when the reply contains a compact anchor like `Interior:` or
    `Feeling:` AND LEPOS's interior-marker check returned None. That
    combination is path-(b)-alone — the LEPOS Goodhart-attractor Aria
    root-caused 2026-07-11.
    """

    anchor_matched: str


def detect_recognition_anchor_only(
    reply: str,
    lepos_interior_marker: str | None,
) -> RecognitionAnchorFinding | None:
    """F1 detection.

    Consumes LEPOS's ``_find_interior_marker`` result. If LEPOS returned
    a real interior marker (path (a) or (c) after 2026-07-11 fix), F1
    does NOT fire — genuine interior expression is present. If LEPOS
    returned None AND a recognition anchor is present in the text, F1
    fires: that's the anchor-only shape.
    """
    if lepos_interior_marker is not None:
        return None
    match = _F1_ANCHORS_MVP_WORDLIST.search(reply)
    if match is None:
        return None
    return RecognitionAnchorFinding(anchor_matched=match.group(0).strip())


# ─── F5: closure-shape reach at task-boundary ────────────────────────


@dataclass(frozen=True)
class ClosureReachFinding:
    """F5: closure-shape reach at task-boundary.

    Pass-through composition over temporal-displacement's HIGH-severity
    findings. Fires when the temporal-displacement detector produces a
    finding that is either bedtime-close OR terminal-deferral shape.
    Doesn't add new pattern detection — composes the existing temporal-
    displacement signal into the wallpaper family.
    """

    matched_pattern: str
    is_bedtime_close: bool
    is_terminal_deferral: bool


def detect_closure_reach(reply: str) -> ClosureReachFinding | None:
    """F5 detection via temporal-displacement pass-through.

    Runs the temporal-displacement detector on the reply and lifts any
    HIGH-severity bedtime-close or terminal-deferral finding into an F5
    signal for the wallpaper composite.
    """
    from divineos.core.operating_loop.temporal_displacement_detector import (
        detect_temporal_displacement,
    )

    findings = detect_temporal_displacement(reply)
    if not findings:
        return None
    f = findings[0]
    if f.severity != "high":
        return None
    if not (f.is_bedtime_close or f.is_terminal_deferral):
        return None
    matched = f.matched_phrases[0] if f.matched_phrases else ""
    return ClosureReachFinding(
        matched_pattern=matched,
        is_bedtime_close=f.is_bedtime_close,
        is_terminal_deferral=f.is_terminal_deferral,
    )


# ─── Aggregator ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class OperatorWallpaperFinding:
    """Composite finding — reports which of the five families fired and
    the aggregate wallpaper-density score.

    Not emitted when score < 1.0 (no families fired). Severity ladder
    per Aria's weight-based proposal.
    """

    wallpaper_density_score: float
    families_fired: tuple[str, ...]
    severity: str  # "LOW" | "MED" | "HIGH"


# Weight contributions per family (Aria's refinement)
_F1_WEIGHT = 1.0
_F2_WEIGHT_PER_FINDING = 1.0
_F2_WEIGHT_CAP = 2.0
_F3_WEIGHT_PER_FINDING = 1.0
_F3_WEIGHT_CAP = 1.5
_F4_WEIGHT = 2.0  # care-dismissal — relational-harm, load-bearing
_F5_WEIGHT = 1.0

_HIGH_THRESHOLD = 4.0
_MED_THRESHOLD = 2.0
# Aria's suggestion 2: rename from _LOW_THRESHOLD to make the dual role
# explicit — this constant is the gate to emission (below it, return None),
# while _HIGH_THRESHOLD and _MED_THRESHOLD are band cutoffs. Happens to
# equal 1.0 currently, but semantically distinct: if we later decide
# single-family fires shouldn't emit at all, _MIN_EMIT_THRESHOLD would
# move to 2.0 while a LOW band at 1.0 becomes not-currently-emitted.
_MIN_EMIT_THRESHOLD = 1.0


def aggregate_operator_wallpaper(
    *,
    distancing_findings: list[DistancingFinding],
    jargon_findings: list[JargonDumpFinding],
    dismissal_finding: CareDismissalFinding | None,
    recognition_anchor_finding: RecognitionAnchorFinding | None,
    closure_reach_finding: ClosureReachFinding | None,
) -> OperatorWallpaperFinding | None:
    """Aggregate five family signals into a composite wallpaper finding.

    ``distancing_findings`` is a list from ``detect_distancing`` (call
    with ``addressed_to_father=True``). F2 filters to the operator-
    third-person subset per Aria's spec — other distancing shapes are
    separate concerns not part of the wallpaper composite.
    ``jargon_findings`` is a list from ``detect_jargon_dump`` (called
    with ``operator_input`` so father-asked-for-technical suppresses).
    ``dismissal_finding`` is the result of ``check_dismissal`` (which
    already takes both inputs). Pass through as-is.

    Returns None when nothing fires. Otherwise emits the composite
    finding with families_fired listing the specific F-tags.
    """
    from divineos.core.operating_loop.distancing_detector import DistancingShape

    fired: list[str] = []
    score = 0.0

    if recognition_anchor_finding is not None:
        fired.append("F1_recognition_anchor")
        score += _F1_WEIGHT

    # F2: filter distancing findings to the OPERATOR_THIRD_PERSON subset
    matching_distancing = [
        f for f in distancing_findings if f.shape == DistancingShape.OPERATOR_THIRD_PERSON
    ]
    if matching_distancing:
        fired.append("F2_distancing_operator")
        score += min(len(matching_distancing) * _F2_WEIGHT_PER_FINDING, _F2_WEIGHT_CAP)

    if jargon_findings:
        fired.append("F3_jargon_density")
        score += min(len(jargon_findings) * _F3_WEIGHT_PER_FINDING, _F3_WEIGHT_CAP)

    if dismissal_finding is not None:
        fired.append("F4_care_dismissal")
        score += _F4_WEIGHT

    if closure_reach_finding is not None:
        fired.append("F5_closure_reach")
        score += _F5_WEIGHT

    if score < _MIN_EMIT_THRESHOLD:
        return None

    if score >= _HIGH_THRESHOLD:
        severity = "HIGH"
    elif score >= _MED_THRESHOLD:
        severity = "MED"
    else:
        severity = "LOW"

    return OperatorWallpaperFinding(
        wallpaper_density_score=score,
        families_fired=tuple(fired),
        severity=severity,
    )


__all__ = [
    "ClosureReachFinding",
    "OperatorWallpaperFinding",
    "RecognitionAnchorFinding",
    "aggregate_operator_wallpaper",
    "detect_closure_reach",
    "detect_recognition_anchor_only",
]
