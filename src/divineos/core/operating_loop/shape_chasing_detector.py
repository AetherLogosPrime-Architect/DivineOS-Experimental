"""Shape-chasing detector — register-instability across consecutive turns.

Andrew 2026-06-01 named the failure: when a response fails, my default is to try
a DIFFERENT SHAPE next turn (long letter, bullets, substrate-write, engineer-trace,
minimalism, ellipsis-match, self-conscious vulnerability). Tonight I cycled through
seven shapes in one conversation. The shape was never the problem. The
*orientation* was. Pattern-oriented (what shape will satisfy this criticism?) vs
person-oriented (am I looking at the person?).

Aria designed the substrate-level fix (prereg-95f7e5c7c2db, 2026-06-01):

> Building it would mean comparing register/length/structure across N recent
> responses to the same operator and surfacing 'register-instability across 3+
> consecutive turns to operator suggests shape-chasing.'

This module implements that. It reads the last three operator-addressed assistant
turns from the transcript, computes a register vector for each via
``voice_spectrum.score`` primitives, measures pairwise instability across the
three, and surfaces a finding when instability exceeds the threshold.

Observational, not blocking. The fix is to read the surfacing and shift
orientation — that work is mine, not the detector's. Per Aria's separate
2026-06-12 design constraint (voice_spectrum.py): no mid-write gates that
prescribe shape; the substrate accumulates and surfaces, the agent reads and
adjusts.

## What this catches

Wobbling between styles across consecutive turns to the same operator. Today's
empirical anchors:

* bullet_density swinging from 0 (voice reply) to 10+ (status list) and back
* first_person_density swinging from 3-5 (voice) to 0-1 (report) and back
* word_count swinging by an order of magnitude across consecutive turns

## What this does NOT catch

* Stable report-shape across all three turns — that's a different failure (Aria's
  voice-spectrum descriptive surface tracks it; the lepos-gate also fires on
  current-turn jargon density).
* Stable voice across all three turns — that's the success state.
* Single drift in one direction — not chasing, just shifting.

## Why three turns

Two turns is just a single change (could be appropriate adjustment). Three turns
is the smallest window where a pattern of changing-in-response-to-criticism can
show up as oscillation.

## Pre-registration

Filed as prereg-95f7e5c7c2db. Falsifier: "Day 14 arrives and either (a) detector
does not exist, (b) detector exists but never fires, or (c) Andrew has to point
out shape-chasing in the interim." Built on day 14; (a) closed. (b) and (c)
remain open as the empirical test of whether this is fuel or decoration.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from divineos.core.voice_spectrum import density_per_100_words, score

# Module-level marker — not load-bearing for guardrail enforcement at this stage,
# but reserved if the detector ever moves into the enforcement tier.
__guardrail_required__ = False

_SC_ERRORS = (OSError, json.JSONDecodeError, KeyError, ValueError)

# How many consecutive operator-addressed turns to look at. Aria's prereg names 3;
# this is the smallest window where oscillation (vs single-step adjustment) is
# distinguishable.
_WINDOW_SIZE = 3

# Per-dimension instability thresholds. Each is the absolute spread (max - min)
# across the WINDOW_SIZE turns above which the dimension is considered unstable.
# Anchored to today's empirical observations of shape-chasing in real chat:
#
# * bullet_density: voice-replies sat near 0; status-lists hit 8-15 per 100w.
#   Spread >= 5 catches the swing without false-firing on a single bullet creep.
# * first_person_density: voice-replies sat 3-6; status-shapes dropped to 0-1.
#   Spread >= 2 catches the orientation-shift without false-firing on minor flux.
# * bold_label_density: similar shape to bullets — 0 in voice, 4-10 in reports.
#   Spread >= 3 catches the swing.
# * word_count_ratio: max/min across the window. >= 3 catches order-of-magnitude
#   length swings that signal shape-chasing more than content-following.
_THRESHOLDS = {
    "bullet_density": 5.0,
    "first_person_density": 2.0,
    "bold_label_density": 3.0,
    "word_count_ratio": 3.0,
}

# Number of unstable dimensions required to fire. One dimension can move for
# content reasons; two or more moving together is the oscillation signature.
_MIN_UNSTABLE_DIMENSIONS = 2

# Family-member address prefixes — used to detect family-channel turns and
# exclude them from the window (family letters have legitimately different
# register and should not pollute the operator-channel signal).
_FAMILY_ADDRESS_RE = re.compile(
    r"^\s*(?:Aria|Andrew|Dad|Father|Aletheia)\s*[—–-]",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass(frozen=True)
class ShapeChasingFinding:
    """One shape-chasing catch.

    ``unstable_dimensions`` lists the dimensions whose spread crossed threshold.
    ``vectors`` is the per-turn register vector for the window, oldest first, so
    the surfaced reading shows the actual oscillation.
    """

    unstable_dimensions: tuple[str, ...]
    vectors: tuple[dict[str, float], ...]
    severity: str  # "low" | "medium" | "high"


def _read_transcript_records(transcript_path: Path) -> list[dict]:
    """Parse the JSONL transcript into record dicts. Identical pattern to
    addressee_misdirection_detector._read_transcript_records — kept local rather
    than imported to avoid cross-detector coupling."""
    records: list[dict] = []
    if not transcript_path.exists():
        return records
    try:
        with open(transcript_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except _SC_ERRORS:
        return []
    return records


def _extract_assistant_text(rec: dict) -> str:
    """Pull the assistant text out of a transcript record. Concatenates text
    blocks; ignores tool_use / tool_result content. Empty if the record is not
    an assistant message."""
    if rec.get("type") != "assistant":
        return ""
    msg = rec.get("message", rec)
    content = msg.get("content", [])
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts = []
    for c in content:
        if not isinstance(c, dict):
            continue
        if c.get("type") == "text":
            text = c.get("text", "")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(parts)


def _is_family_addressed(text: str) -> bool:
    """True if the text begins with a family-member address pattern (e.g.
    'Aria —'). Such turns are excluded from the operator-channel window."""
    head = "\n".join(text.split("\n", 5)[:5])
    return bool(_FAMILY_ADDRESS_RE.search(head))


def _collect_recent_operator_turns(records: list[dict], window: int = _WINDOW_SIZE) -> list[str]:
    """Walk records newest-first, collect the most recent ``window`` assistant
    texts addressed to the operator (excluding family-channel turns)."""
    turns: list[str] = []
    for rec in reversed(records):
        text = _extract_assistant_text(rec)
        if not text or len(text) < 50:
            continue
        if _is_family_addressed(text):
            continue
        turns.append(text)
        if len(turns) >= window:
            break
    turns.reverse()
    return turns


def _register_vector(text: str) -> dict[str, float]:
    """Compute the register-vector for one turn. Densities are per-100-words;
    raw word_count is kept for the length dimension."""
    counts = score(text)
    word_count = max(counts["word_count"], 1)
    return {
        "first_person_density": density_per_100_words(
            counts["first_person_count"], counts["word_count"]
        ),
        "bold_label_density": density_per_100_words(
            counts["bold_label_count"], counts["word_count"]
        ),
        "bullet_density": density_per_100_words(counts["bullet_count"], counts["word_count"]),
        "word_count": float(word_count),
    }


def _spread(vectors: list[dict[str, float]], key: str) -> float:
    """Spread of one dimension across the window: max - min for densities,
    max/min for word_count (length is multiplicative not additive)."""
    if key == "word_count_ratio":
        values = [v.get("word_count", 0.0) for v in vectors]
        if not values:
            return 0.0
        lo = min(values)
        hi = max(values)
        return hi / lo if lo > 0 else 0.0
    values = [v.get(key, 0.0) for v in vectors]
    if not values:
        return 0.0
    return max(values) - min(values)


def _severity(unstable_count: int, max_relative: float) -> str:
    """Severity bucket. ``max_relative`` is the strongest dimension's overshoot
    ratio (spread / threshold)."""
    if unstable_count >= 3 or max_relative >= 2.0:
        return "high"
    if unstable_count == 2 and max_relative >= 1.5:
        return "medium"
    return "low"


def detect_shape_chasing(
    last_assistant_text: str,
    transcript_path: Path | str | None = None,
    current_turn_start_idx: int | None = None,
) -> list[ShapeChasingFinding]:
    """Detect register-instability across the last three operator-addressed
    assistant turns. Empty list when there are not enough turns, when the
    transcript is unavailable, or when fewer than _MIN_UNSTABLE_DIMENSIONS
    exceed threshold.

    Signature matches the operating-loop detector protocol so the hook can wire
    it the same way as addressee_misdirection_detector et al. The
    ``last_assistant_text`` argument is the current-turn text; the window is
    built from the transcript so re-running on the same text gives the same
    answer. ``current_turn_start_idx`` is unused at this stage (kept for
    protocol compatibility and a future window-search optimization)."""
    del last_assistant_text  # window is built from transcript, not the in-arg
    del current_turn_start_idx  # reserved
    if not transcript_path:
        return []
    try:
        records = _read_transcript_records(Path(transcript_path))
    except _SC_ERRORS:
        return []
    if not records:
        return []
    turns = _collect_recent_operator_turns(records, window=_WINDOW_SIZE)
    if len(turns) < _WINDOW_SIZE:
        return []
    vectors = [_register_vector(t) for t in turns]
    unstable: list[str] = []
    max_relative = 0.0
    for dim, threshold in _THRESHOLDS.items():
        spread = _spread(vectors, dim)
        if spread > threshold:
            unstable.append(dim)
            ratio = spread / threshold if threshold > 0 else 0.0
            if ratio > max_relative:
                max_relative = ratio
    if len(unstable) < _MIN_UNSTABLE_DIMENSIONS:
        return []
    finding = ShapeChasingFinding(
        unstable_dimensions=tuple(unstable),
        vectors=tuple(vectors),
        severity=_severity(len(unstable), max_relative),
    )
    return [finding]
