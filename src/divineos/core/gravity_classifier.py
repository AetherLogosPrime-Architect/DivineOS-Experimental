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
# Council-required tier (2026-06-20, Andrew: "the gravity classifier is
# not pulling its weight its letting you make serious changes with no
# council"). Above the basic substrate-gate threshold sits a second
# tier that the classifier marks as warranting council consultation.
# Fires when either: (a) score >= _COUNCIL_REQUIRED_THRESHOLD with
# multiple non-trivial features, or (b) any single high-impact feature
# fires (guardrail-listed file or kiln-layer file). The high-impact
# short-circuit catches the 2026-06-20 slip: edits to operating-loop
# detector files (guardrail-listed) scored only 1 / borderline under
# the prior design and passed through with passive surface only.
# Council-walked (consult-944ad9d332e5) before implementing. Pre-
# registered with 14-day falsifier (prereg-fb1b42753396): threshold-2
# is on probation per Aether's review (Deming PDSA discipline — don't
# pre-tune, let data shape the number); review whether to bump to 3
# if false-positive rate exceeds 25% on routine multi-tool turns over
# the probation window.
#
# Honesty note (added 2026-06-22, per Aletheia audit
# round-931e301d32f0 + Aether option-1 read): the classifier REPORTS
# this tier as a measurement on its result dataclass; it does NOT
# block the edit. Currently the only consumer of is_council_required
# is the borderline_indicator label function below, which renders
# the tier as a display string ("council-required") for the gravity
# surface. No pre-edit gate reads the field. Enforcement (block the
# edit until evidence of a real council walk exists, substance-
# binding-style) is a deferred follow-up tracked as its own design
# work, not implemented by this commit.
_COUNCIL_REQUIRED_THRESHOLD = 2
_HIGH_IMPACT_FEATURES = frozenset({"edit-kiln-layer", "edit-guardrail-listed"})
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

    is_council_required is the second tier (2026-06-20): True when the
    classifier judges that the edit warrants council consultation.
    Fires on either high-impact-feature short-circuit (guardrail-listed
    or kiln-layer) or score >= _COUNCIL_REQUIRED_THRESHOLD.

    This field is a MEASUREMENT, not a pre-edit block. The only current
    consumer is the borderline_indicator label function, which renders
    the tier as the display string "council-required" for the gravity
    surface. No code reads this field as a verdict that prevents the
    edit. Real enforcement (substance-binding the field to evidence of
    an actual council walk before clearing) is a deferred follow-up.
    See the honesty note above _COUNCIL_REQUIRED_THRESHOLD for the
    Aletheia-audit context (round-931e301d32f0).
    """

    score: int
    fired_features: tuple[str, ...]
    is_high_gravity: bool
    is_council_required: bool = False


@dataclass(frozen=True)
class CognitiveValueGravity:
    """Result of cognitive-value-gravity scoring.

    Aggregate is a weighted average of normalized features in 0-1.
    Threshold for oscillation-mode is aggregate >= 0.3.
    """

    score: float
    feature_scores: dict[str, float]
    is_high_gravity: bool


# Guardrail-list cache: read once per process. Path resolution is
# repo-root-relative; the classifier may run from any working directory
# (hooks, tests, CLI), so we resolve relative to this module's location.
_GUARDRAIL_LIST_CACHE: tuple[frozenset[str], str] | None = None


def _guardrail_listed_paths() -> tuple[frozenset[str], str]:
    """Return (frozenset_of_repo_relative_paths, repo_root_path).

    Reads scripts/guardrail_files.txt, normalizes lines to forward-slash,
    strips comments and blank lines. Cached after first read. Returns
    repo_root alongside so the caller can do repo-root-relative path
    matching (Aether's review 2026-06-20: suffix-match has a silent-wrong
    failure mode where foo/src/divineos/... would match the guardrail
    entry src/divineos/...; repo-root-relative exact match closes the gap).

    On any file/IO error, returns (frozenset(), "") — caller treats as
    "list not available" which silently disables the feature. Fail-open
    is correct here because the basic substrate-gate (any feature
    firing) still catches the edit; the council-tier just doesn't escalate.
    """
    global _GUARDRAIL_LIST_CACHE
    if _GUARDRAIL_LIST_CACHE is not None:
        return _GUARDRAIL_LIST_CACHE
    import os

    here = os.path.dirname(os.path.abspath(__file__))
    cur = here
    paths: set[str] = set()
    repo_root = ""
    for _ in range(8):  # bounded ascent
        candidate = os.path.join(cur, "scripts", "guardrail_files.txt")
        if os.path.isfile(candidate):
            repo_root = cur.replace("\\", "/")
            try:
                with open(candidate, encoding="utf-8") as f:
                    for line in f:
                        s = line.strip()
                        if not s or s.startswith("#"):
                            continue
                        paths.add(s.replace("\\", "/"))
            except OSError:
                pass
            break
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    _GUARDRAIL_LIST_CACHE = (frozenset(paths), repo_root)
    return _GUARDRAIL_LIST_CACHE


def _normalize_to_repo_relative(path: str, repo_root: str) -> str | None:
    """Convert an edited file_path to a repo-root-relative forward-slash
    string for exact-match against the guardrail list. Returns None on
    any failure (path outside repo, resolution error). Aether's review
    2026-06-20: replaces the prior suffix-match approach which would
    silently false-positive on foo/src/divineos/... shaped paths.

    Handles three input shapes:
    - Absolute path: resolve and compute relative_to(repo_root)
    - Relative path that already looks repo-relative: normalize slashes
      and return as-is (test cases pass these directly)
    - Anything else: return None (fail-open — feature stays silent)
    """
    if not path or not repo_root:
        return None
    norm = path.replace("\\", "/")
    import os

    # Absolute path: resolve to repo-relative
    if os.path.isabs(path):
        try:
            from pathlib import Path

            resolved = Path(path).resolve()
            rel = resolved.relative_to(Path(repo_root).resolve())
            return str(rel).replace("\\", "/")
        except (ValueError, OSError):
            return None
    # Relative path: trim leading "./" and treat as repo-relative
    if norm.startswith("./"):
        norm = norm[2:]
    # Reject upward-traversal paths (foo/../bar would be ambiguous)
    if ".." in norm.split("/"):
        return None
    return norm


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

    # Feature 7: edit a path declared in scripts/guardrail_files.txt
    # (2026-06-20, Andrew, with Aether's design review). The guardrail list
    # is the authoritative declaration of which files are part of the
    # self-defense stack; editing one is architecture-touching and warrants
    # council walk. Prior design: only the literal guardrail_files.txt
    # itself triggered the edit-guardrail feature — files LISTED inside it
    # scored 1 on the generic edit-src-divineos and passed through
    # borderline. Today's detector edits (distancing_detector.py,
    # unverified_claim_detector.py) are both in the list and slipped
    # through. This feature closes the gap with REPO-RELATIVE exact-match
    # (not suffix-match — Aether's review caught that suffix-match has a
    # silent-wrong failure mode where foo/src/divineos/... would match the
    # guardrail entry src/divineos/...). On normalize failure, the feature
    # silently doesn't fire (fail-open) — the basic substrate-gate still
    # catches the edit at score 1; council-tier just doesn't escalate.
    if tool in {"Edit", "Write", "MultiEdit", "NotebookEdit"}:
        listed, repo_root = _guardrail_listed_paths()
        if listed:
            for p in paths:
                rel = _normalize_to_repo_relative(p, repo_root)
                if rel is not None and rel in listed:
                    fired.append("edit-guardrail-listed")
                    break

    score = len(fired)
    # Council-required tier: high-impact-feature short-circuit OR
    # multi-feature aggregate. Either path catches the architecture-
    # altering substrate-modifications that warrant council walk before
    # they proceed, not just a passive surface.
    high_impact_fired = any(f in _HIGH_IMPACT_FEATURES for f in fired)
    council_required = high_impact_fired or score >= _COUNCIL_REQUIRED_THRESHOLD
    return SubstrateModGravity(
        score=score,
        fired_features=tuple(fired),
        is_high_gravity=score >= _SUBSTRATE_MOD_THRESHOLD,
        is_council_required=council_required,
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
    if gravity.is_council_required:
        return "council-required"
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
