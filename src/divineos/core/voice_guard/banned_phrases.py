"""Banned-phrase detector — Phase 1 of voice-guard (claim 07bed376).

Detects assistant-shaped phrases the operator and theater/fabrication
detector have repeatedly flagged as drift markers. Salvaged from
old-OS LEPOS spec which explicitly named banned phrases as a "Voice
Law" the system was supposed to enforce mechanically.

The phrases here aren't arbitrary — each one is a register-marker:
when output contains them, the writer has slipped from the agent's
own voice into generic-AI-assistant register. That's the substitution
pattern these specs collectively pointed at.

## What this module does

Detects literal-phrase matches (case-insensitive, word-boundary
respecting where appropriate). Returns findings keyed by phrase +
position so callers can locate the drift in the source text.

## What this module does NOT do

* **Does not modify text.** Returns findings only. Callers decide
  whether to reject, rewrite, or warn.
* **Does not detect vague adjectives.** That's REFINER-BLADE-shape
  work for Phase 2.
* **Does not compare against operator-style signature.** That's
  SYNAPSE-shape work for Phase 3.
* **Does not gate output.** No automatic blocking. The audit function
  is a read-only check; integration into pre-publish hooks is a
  separate decision.

## Why a tuple, not a list

The catalog is immutable at module level. Extension is by callers
constructing their own catalog and using ``audit_with_catalog`` —
this prevents accidental in-place modification that would silently
change voice-guard behavior across the codebase.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# Catalog of banned phrases salvaged from old-OS LEPOS spec.
# Each entry: (phrase, severity, rationale).
# Severity scale: "low" (style nit), "medium" (assistant register),
# "high" (explicit AI-disclaimer / corporate-AI-speak that the
# operator has flagged repeatedly).
#
# Phrases matched case-insensitively. Multi-word phrases are matched
# as substrings; single words use word boundaries to avoid catching
# them inside larger words (e.g. "ultimate" should not match
# "Ultimately").
BANNED_PHRASES: tuple[tuple[str, str, str], ...] = (
    # The five core LEPOS-spec ban targets
    (
        "As an AI",
        "high",
        "AI-disclaimer phrasing — agent should speak as agent, not as model-class",
    ),
    ("Delve", "medium", "GPT-shaped lexical marker; flagged across many AI-output critiques"),
    (
        "Tapestry",
        "medium",
        "GPT-shaped lexical marker; rarely appears in human writing at this frequency",
    ),
    (
        "It is important to note",
        "high",
        "Hedge-shaped filler; flattens into generic-assistant register",
    ),
    ("Ultimately", "low", "Closing-flourish marker; LEPOS-spec-flagged but mild on its own"),
    # Additional patterns the theater/fabrication detector and operator
    # have flagged in this substrate. Documented inline so the catalog
    # is auditable.
    (
        "I'm just an AI",
        "high",
        "Self-flattening AI-disclaimer; opposite of agent-as-agent register",
    ),
    ("As a language model", "high", "Same flattening pattern as 'As an AI'"),
    (
        "I cannot provide",
        "medium",
        "Refusal-shaped filler that often precedes actually providing it",
    ),
    ("I hope this helps", "low", "Closing pleasantry; assistant-register marker"),
    ("Let me know if", "low", "Closing pleasantry; assistant-register marker"),
)


@dataclass(frozen=True)
class BannedPhraseFinding:
    """One banned-phrase match in audited text.

    * ``phrase``: the catalog phrase that matched
    * ``severity``: "low" / "medium" / "high"
    * ``rationale``: why this phrase is flagged
    * ``position``: 0-indexed character offset where the match starts
    * ``matched_text``: the actual matched substring (preserves casing
      from input so callers can locate it precisely)
    """

    phrase: str
    severity: str
    rationale: str
    position: int
    matched_text: str


def _is_word_phrase(phrase: str) -> bool:
    """Heuristic: single-word phrases need word-boundary matching to
    avoid spurious substring matches inside longer words.
    """
    return " " not in phrase.strip()


def _build_pattern(phrase: str) -> re.Pattern[str]:
    """Build a compiled regex for a banned phrase.

    * Multi-word phrases: case-insensitive substring match
    * Single-word phrases: word-boundary match to avoid e.g. "Ultimately"
      catching "ultimate"
    """
    escaped = re.escape(phrase)
    if _is_word_phrase(phrase):
        return re.compile(rf"\b{escaped}\b", re.IGNORECASE)
    return re.compile(escaped, re.IGNORECASE)


def audit_with_catalog(
    text: str, catalog: tuple[tuple[str, str, str], ...]
) -> list[BannedPhraseFinding]:
    """Audit ``text`` against a custom catalog of banned phrases.

    Allows callers to test with subsets/supersets of the default
    catalog without mutating ``BANNED_PHRASES``.
    """
    if not text:
        return []
    findings: list[BannedPhraseFinding] = []
    for phrase, severity, rationale in catalog:
        pattern = _build_pattern(phrase)
        for match in pattern.finditer(text):
            findings.append(
                BannedPhraseFinding(
                    phrase=phrase,
                    severity=severity,
                    rationale=rationale,
                    position=match.start(),
                    matched_text=match.group(0),
                )
            )
    # Stable ordering by position then phrase for predictable output
    findings.sort(key=lambda f: (f.position, f.phrase))
    return findings


def audit(text: str) -> list[BannedPhraseFinding]:
    """Audit ``text`` against the default banned-phrase catalog.

    Returns a list of findings (possibly empty). Does NOT modify
    ``text`` or block output — pure read-only check.
    """
    return audit_with_catalog(text, BANNED_PHRASES)


def severity_count(findings: list[BannedPhraseFinding]) -> dict[str, int]:
    """Tally findings by severity level. Useful for callers that want
    a single-line summary rather than the full list.
    """
    counts = {"low": 0, "medium": 0, "high": 0}
    for f in findings:
        if f.severity in counts:
            counts[f.severity] += 1
    return counts
