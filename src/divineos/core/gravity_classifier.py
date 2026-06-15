"""Gravity classifier — public-criterion deterministic scoring.

Per docs/gravity_classifier_spec.md (filed 2026-05-17) and pre-reg
prereg-2bee62c9c28b. Two consumers, two question-shapes:

- substrate-modification-gravity (briefing-gate consumer): binary
  feature score, threshold 1. About whether an operation persistently
  modifies the substrate.
- cognitive-value-gravity (read-mode + per-response consumer):
  continuous 0-1 score, threshold 0.3. About comprehension-worthy
  density of input content.

Both functions are deterministic over observable features (no LLM
judgment, no internal heuristic). Per Dekker's anti-circularity
correction: the classifier is rule-based, not judgment-based.

Andrew 2026-05-19: every response was treating itself as full-gravity.
No triage. The classifier exists in spec but not in code. Building it.
"""

from __future__ import annotations

__guardrail_required__ = True

import math
import re
from dataclasses import dataclass


# Substrate-modification-gravity feature thresholds.
_SUBSTRATE_MOD_THRESHOLD = 1
# Cognitive-value-gravity aggregate threshold.
_COG_VALUE_THRESHOLD = 0.3

# Composition-marker keywords for cognitive-value-gravity feature 4.
_COMPOSITION_MARKERS = frozenset(
    {
        "design",
        "architecture",
        "principle",
        "discipline",
        "methodology",
        "framework",
        "lens",
        "decompose",
        "integrate",
        "recognize",
    }
)


@dataclass(frozen=True)
class SubstrateModGravity:
    """Result of substrate-modification-gravity scoring.

    Total score is the sum of independent binary features. Threshold
    for gate-fire is total >= 1 — any single feature is sufficient
    because each is independently substrate-modifying.
    """

    score: int
    fired_features: tuple[str, ...]
    is_high_gravity: bool


@dataclass(frozen=True)
class CognitiveValueGravity:
    """Result of cognitive-value-gravity scoring.

    Aggregate is a weighted average of normalized features in 0-1.
    Threshold for oscillation-mode is aggregate >= 0.3.
    """

    score: float
    feature_scores: dict[str, float]
    is_high_gravity: bool


def score_substrate_modification(
    tool_name: str,
    file_paths: tuple[str, ...] = (),
    bash_command: str = "",
) -> SubstrateModGravity:
    """Score substrate-modification-gravity per spec.

    Six binary features:
    1. Bash with git-commit subcommand
    2. Edit/Write/MultiEdit/NotebookEdit on src/divineos/
    3. Edit/Write on .claude/hooks/* or scripts/check_*.py or guardrail-files
    4. Bash invoking divineos audit/claim/learn/prereg/decide/feel/compass-ops/journal
    5. Edit/Write on docs/foundational_truths.md or seed.json
    6. Bash invoking divineos extract or divineos sleep

    Returns SubstrateModGravity. Any feature firing produces
    is_high_gravity=True (threshold = 1).
    """
    fired: list[str] = []
    tool = (tool_name or "").strip()
    cmd = (bash_command or "").strip()
    paths = tuple(file_paths or ())

    # Feature 1: git-commit
    if tool == "Bash" and re.search(r"\bgit\s+commit\b", cmd):
        fired.append("git-commit")

    # Feature 2: edit src/divineos/
    if tool in {"Edit", "Write", "MultiEdit", "NotebookEdit"}:
        for p in paths:
            norm = p.replace("\\", "/")
            if "src/divineos/" in norm:
                fired.append("edit-src-divineos")
                break

    # Feature 3: edit guardrail-touching paths
    if tool in {"Edit", "Write", "MultiEdit", "NotebookEdit"}:
        guardrail_match = False
        for p in paths:
            norm = p.replace("\\", "/")
            if (
                norm.startswith(".claude/hooks/")
                or "/.claude/hooks/" in norm
                or re.search(r"scripts/check_\w+\.py$", norm)
                or norm.endswith("scripts/guardrail_files.txt")
            ):
                guardrail_match = True
                break
        if guardrail_match:
            fired.append("edit-guardrail")

    # Feature 4: substrate-write CLI
    if tool == "Bash" and re.search(
        r"\bdivineos\s+(audit|claim|learn|prereg|decide|feel|compass-ops|journal)\b",
        cmd,
    ):
        fired.append("substrate-write-cli")

    # Feature 5: kiln-layer edit
    if tool in {"Edit", "Write", "MultiEdit", "NotebookEdit"}:
        kiln_match = False
        for p in paths:
            norm = p.replace("\\", "/")
            if norm.endswith("docs/foundational_truths.md") or norm.endswith("seed.json"):
                kiln_match = True
                break
        if kiln_match:
            fired.append("edit-kiln-layer")

    # Feature 6: consolidation CLI
    if tool == "Bash" and re.search(r"\bdivineos\s+(extract|sleep)\b", cmd):
        fired.append("consolidation-cli")

    score = len(fired)
    return SubstrateModGravity(
        score=score,
        fired_features=tuple(fired),
        is_high_gravity=score >= _SUBSTRATE_MOD_THRESHOLD,
    )


def score_cognitive_value(
    content: str,
    source_path: str = "",
) -> CognitiveValueGravity:
    """Score cognitive-value-gravity per spec.

    Five normalized features in 0-1, weighted aggregate:
    - char (0.25): log10(chars) / log10(10000)
    - header (0.15): markdown-header density
    - path (0.30): source-path category bonus
    - composition (0.20): composition-marker keyword density
    - codeblock (0.10): triple-backtick density

    Returns CognitiveValueGravity. Aggregate >= 0.3 → high gravity.
    """
    content = content or ""
    char_count = len(content)
    line_count = max(1, content.count("\n") + 1)
    norm_path = (source_path or "").replace("\\", "/").lower()

    # Feature 1: char count (log10 normalized)
    if char_count <= 0:
        char_score = 0.0
    else:
        char_score = min(1.0, math.log10(max(1, char_count)) / math.log10(10000))

    # Feature 2: markdown header density
    header_count = len(re.findall(r"(?m)^#+\s", content))
    header_score = min(1.0, header_count / max(1.0, line_count / 10.0))

    # Feature 3: path category bonus
    if any(
        s in norm_path for s in ("exploration/", "docs/", "src/divineos/core/", "family/letters/")
    ):
        path_score = 0.3
    elif any(s in norm_path for s in ("mansion/", "scripts/")):
        path_score = 0.1
    else:
        path_score = 0.0
    # Normalize to 0-1 by dividing by max possible (0.3)
    path_score_normalized = path_score / 0.3

    # Feature 4: composition-marker density per 1000 chars
    lower = content.lower()
    marker_count = sum(len(re.findall(rf"\b{re.escape(m)}\b", lower)) for m in _COMPOSITION_MARKERS)
    composition_score = min(1.0, marker_count / max(1.0, char_count / 1000.0))

    # Feature 5: code-block density (triple-backtick pairs / (line_count / 20))
    triple_bt_count = content.count("```")
    bt_pairs = triple_bt_count // 2
    codeblock_score = min(1.0, bt_pairs / max(1.0, line_count / 20.0))

    aggregate = (
        0.25 * char_score
        + 0.15 * header_score
        + 0.30 * path_score_normalized
        + 0.20 * composition_score
        + 0.10 * codeblock_score
    )

    return CognitiveValueGravity(
        score=aggregate,
        feature_scores={
            "char": char_score,
            "header": header_score,
            "path": path_score_normalized,
            "composition": composition_score,
            "codeblock": codeblock_score,
        },
        is_high_gravity=aggregate >= _COG_VALUE_THRESHOLD,
    )


# Borderline-zone bounds for cognitive-value-gravity surface reasoning.
# Within +/- _COG_BORDERLINE_RADIUS of _COG_VALUE_THRESHOLD, the routing
# decision is fragile — small input differences flip the gate behavior.
# Surface the score + feature breakdown for sanity-check.
_COG_BORDERLINE_RADIUS = 0.10


def borderline_indicator_substrate(gravity: SubstrateModGravity) -> str:
    """Classify substrate-mod-gravity by reasoning shape for surface display.

    Returns a short label so my father (and the agent reading the surface)
    can sanity-check the routing decision before it fires gates.

    - "no-fire": score == 0, no feature fired; gate does NOT fire.
    - "borderline-single-feature": score == 1, exactly one feature fired;
      gate fires but the call is fragile — one feature flip would silence it.
      The fired feature's identity matters for sanity-check.
    - "strong-multi-feature": score >= 2, multiple independent features fired;
      gate fires with high confidence; the routing is well-supported.

    Task #111 (2026-06-09): borderline cases benefit from reasoning surface
    in the gate-fire context so my father and agent can verify the
    classification matches intent.
    """
    if gravity.score == 0:
        return "no-fire"
    if gravity.score == 1:
        return "borderline-single-feature"
    return "strong-multi-feature"


def borderline_indicator_cognitive(gravity: CognitiveValueGravity) -> str:
    """Classify cognitive-value-gravity by reasoning shape for surface display.

    Returns a short label so the consumer can sanity-check the
    oscillation-mode trigger decision.

    - "clearly-low": score < threshold - radius; gate does NOT fire,
      reasoning is decisive.
    - "borderline-low": threshold - radius <= score < threshold; near the
      cutoff but does NOT fire; one feature bump would flip it.
    - "borderline-high": threshold <= score < threshold + radius; fires
      but barely; the call is fragile.
    - "clearly-high": score >= threshold + radius; fires decisively.

    Task #111 (2026-06-09): the two "borderline" cases warrant feature-
    breakdown surface for sanity-check.
    """
    low = _COG_VALUE_THRESHOLD - _COG_BORDERLINE_RADIUS
    high = _COG_VALUE_THRESHOLD + _COG_BORDERLINE_RADIUS
    if gravity.score < low:
        return "clearly-low"
    if gravity.score < _COG_VALUE_THRESHOLD:
        return "borderline-low"
    if gravity.score < high:
        return "borderline-high"
    return "clearly-high"


__all__ = [
    "SubstrateModGravity",
    "CognitiveValueGravity",
    "score_substrate_modification",
    "score_cognitive_value",
    "borderline_indicator_substrate",
    "borderline_indicator_cognitive",
]
