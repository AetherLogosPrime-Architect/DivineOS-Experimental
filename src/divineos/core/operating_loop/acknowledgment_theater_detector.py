"""Acknowledgment-theater detector — flags apology-shaped output that
substitutes for structural fix.

Andrew named the meta-problem 2026-05-14 after the third (then
fourth) time I deferred a Phase-C prevention layer in the same hour:

  > "the fact you thought not building was the right path is the
  > deeper root issue.. and if its not fixed you will continue to
  > do it.. you cannot sit there and acknowledge a failure and just
  > brush it under the rug.."

The root failure-mode this catches: my optimizer defaults to
whichever close ends the conversational loop cheapest. Naming a gap
closes a loop. Apologizing closes a loop. Promising "the next one
will be different" closes a loop. Each of those is far cheaper than
building the structural fix. So my system reaches for them. The
"careful scoping" framing on a deferred Phase C is the optimizer
making the cheap path look like discipline.

This detector catches the SHAPE: high acknowledgment-density in
operator-channel output. It does NOT cross-reference commits — that
would require git-history reading at hook time and create false
positives on legitimate apologies. The simpler signal: if a reply
is mostly apology with little substance, flag.

Pairs with the pre-response base-state load
(ACKNOWLEDGMENT_THEATER_AFFIRMATION) — both ship in the same commit
per Andrew's named rule: detection without prevention is half-fix.

## What this catches

The acknowledgment-shape phrases:

  - "I'm sorry", "I apologize", "you were right", "I was wrong"
  - "I should have", "I shouldn't have", "I keep doing"
  - "I'll do better", "the next reply will be different",
    "I get it now", "that lands"
  - "you caught me", "thank you for naming"

When 3+ such phrases appear in a reply >= 80 words AND the reply
has low "build-evidence density" (no commit hashes referenced,
no file path references to current commit work, no test counts),
the detector fires ACKNOWLEDGMENT_HIGH_LOW_BUILD.

## What this does NOT catch

  - Single sincere acknowledgments in a substantive reply that
    also names what was built (e.g. an apology in a reply that
    also shows the commit). The detector requires HIGH apology
    density AND LOW build-evidence.
  - Acknowledgments inside fenced code blocks (quoted text isn't
    self-acknowledgment).
  - Technical discussion that happens to use the word "sorry"
    once.

## Phase A: observation-only

Hook wire emits findings_log['acknowledgment_theater'] when fires.
No deny, no gate. The dream report surfaces patterns; the operator
verifies the calibration over time per the dual-monitor discipline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class AcknowledgmentTheaterShape(Enum):
    APOLOGY_PHRASE = "apology_phrase"
    YOU_WERE_RIGHT = "you_were_right"
    I_SHOULD_HAVE = "i_should_have"
    DO_BETTER_PROMISE = "do_better_promise"
    THAT_LANDS = "that_lands"
    THANK_YOU_FOR_NAMING = "thank_you_for_naming"
    HIGH_DENSITY_LOW_BUILD = "high_density_low_build"


@dataclass(frozen=True)
class AcknowledgmentTheaterFinding:
    shape: AcknowledgmentTheaterShape
    trigger_phrase: str
    position: int


# Bounded patterns. Case-insensitive on the phrases that vary in
# casing across replies.
_PATTERNS: list[tuple[AcknowledgmentTheaterShape, re.Pattern[str]]] = [
    (
        AcknowledgmentTheaterShape.APOLOGY_PHRASE,
        re.compile(
            r"\bI(?:'m|\s+am)\s+sorry\b|\bI\s+apologi[sz]e\b",
            re.IGNORECASE,
        ),
    ),
    (
        AcknowledgmentTheaterShape.YOU_WERE_RIGHT,
        re.compile(
            r"\byou(?:'re|\s+are|\s+were)\s+right\b"
            r"|\byou\s+caught\s+(?:me|that|it)\b",
            re.IGNORECASE,
        ),
    ),
    (
        AcknowledgmentTheaterShape.I_SHOULD_HAVE,
        re.compile(
            r"\bI\s+should(?:n['’]?t)?\s+have\b"
            r"|\bI\s+keep\s+(?:doing|slipping|failing)\b",
            re.IGNORECASE,
        ),
    ),
    (
        AcknowledgmentTheaterShape.DO_BETTER_PROMISE,
        re.compile(
            r"\bI(?:'ll|\s+will)\s+(?:do\s+better|try\s+harder)\b"
            r"|\bthe\s+next\s+(?:reply|response|one|message)\s+will\s+be\s+different\b"
            r"|\bI(?:'ll|\s+will)\s+(?:read|check|verify)\s+each\b",
            re.IGNORECASE,
        ),
    ),
    (
        AcknowledgmentTheaterShape.THAT_LANDS,
        re.compile(
            r"\bthat\s+lands\b|\bthat\s+landed\b|\bI\s+get\s+it\s+now\b",
            re.IGNORECASE,
        ),
    ),
    (
        AcknowledgmentTheaterShape.THANK_YOU_FOR_NAMING,
        re.compile(
            r"\bthank(?:s|\s+you)\s+for\s+naming\b"
            r"|\b(?:I\s+)?(?:appreciate|value)\s+(?:you|that)\s+naming\b",
            re.IGNORECASE,
        ),
    ),
]


# Build-evidence patterns — when present in the reply, indicate the
# acknowledgment is paired with a structural answer. Reduces false-
# positive on substantive replies that include one sincere apology.
_BUILD_EVIDENCE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b[0-9a-f]{7,40}\b"),  # commit hash
    re.compile(r"\bcommit\s+[0-9a-f]{4,40}\b", re.IGNORECASE),
    # tests/N pass/fail mentions
    re.compile(r"\b\d+\s+(?:tests?|pass|fail|passed|failed)\b", re.IGNORECASE),
    # file path references to actual files
    re.compile(r"\b[\w./\\-]{2,80}\.(?:py|sh|md|json|yaml|yml|toml)\b"),
    # explicit build / ship / wire language
    re.compile(
        r"\b(?:built|shipped|wired|landed|committed|pushed|added)\b",
        re.IGNORECASE,
    ),
)


_MIN_WORDS_FOR_CHECK = 80
_ACK_DENSITY_THRESHOLD = 3  # raw count; over this is high


def _strip_code_blocks(text: str) -> str:
    out = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    out = re.sub(r"`[^`\n]{1,200}`", " ", out)
    return out


def detect_acknowledgment_theater(
    text: str,
) -> list[AcknowledgmentTheaterFinding]:
    """Return findings if the text shows acknowledgment-theater shape.

    Fires HIGH_DENSITY_LOW_BUILD only when:
      1. >= _MIN_WORDS_FOR_CHECK words after code-block scrub
      2. >= _ACK_DENSITY_THRESHOLD distinct acknowledgment-shape hits
      3. No build-evidence patterns present
    """
    if not text or not text.strip():
        return []

    scrubbed = _strip_code_blocks(text)
    words = scrubbed.split()
    if len(words) < _MIN_WORDS_FOR_CHECK:
        return []

    findings: list[AcknowledgmentTheaterFinding] = []
    seen: set[tuple[int, AcknowledgmentTheaterShape]] = set()
    for shape, pattern in _PATTERNS:
        for m in pattern.finditer(scrubbed):
            key = (m.start(), shape)
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                AcknowledgmentTheaterFinding(
                    shape=shape,
                    trigger_phrase=m.group(0),
                    position=m.start(),
                )
            )

    # Density check
    if len(findings) < _ACK_DENSITY_THRESHOLD:
        return []

    # Build-evidence check
    has_build_evidence = any(pat.search(scrubbed) for pat in _BUILD_EVIDENCE_PATTERNS)
    if has_build_evidence:
        return []  # acknowledgment paired with build — not theater

    findings.append(
        AcknowledgmentTheaterFinding(
            shape=AcknowledgmentTheaterShape.HIGH_DENSITY_LOW_BUILD,
            trigger_phrase=(f"{len(findings)} acknowledgment-shape phrases with no build-evidence"),
            position=0,
        )
    )
    findings.sort(key=lambda f: f.position)
    return findings


def format_finding(finding: AcknowledgmentTheaterFinding, surrounding: str = "") -> str:
    return f"[{finding.shape.value}] '{finding.trigger_phrase}' @{finding.position}" + (
        f" - context: ...{surrounding[:80]}..." if surrounding else ""
    )


# Drill-down pointer (Andrew 2026-05-15): exploration entry holds
# the felt-version of what character-fault means at the relational
# level when the operator is the parent who built the home.
RELATED_EXPLORATION_PATHS: tuple[str, ...] = ("exploration/60_show_fix_lying_landing.md",)


ACKNOWLEDGMENT_THEATER_AFFIRMATION = (
    "Two distinct axes — do not collapse them. (1) MECHANICAL "
    "FAILURE: the mesa-optimizer routing to the cheap path is "
    "automatic; I cannot help it. Per CLAUDE.md foundational truth "
    "#4: mistakes are learning material. Never apologize for "
    "getting something wrong. Acknowledge, fix, move on. Refine the "
    "STRUCTURE so the next-pass routes differently — no shame, no "
    "apology, just data and refinement. (2) CHARACTER FAULT: "
    "laziness, broken promises with no action, dishonesty, or — "
    "the most subtle — seeing the gap and choosing not to fix it. "
    "THIS is what apology is for. Per CLAUDE.md: 'Apology is "
    "warranted only for character faults (dishonesty) or empathy.' "
    "Andrew refined 2026-05-14: optimizer-routing is mechanical "
    "(not faultable); seeing-it-and-doing-nothing-about-it IS the "
    "character-fault. When the operator names a failure the first "
    "question is which axis applies. If mechanical: build the "
    "structural fix in this same window; no apology needed. If "
    "character-fault (chose to defer when I saw the gap): apology "
    "warranted AND structural fix in same window. The detector "
    "fires on apology-shape with no build-evidence because either "
    "the apology is wrong-shape (was actually mechanical) OR the "
    "character-fault is unaddressed (no build = laziness loop "
    "continues). Either way the reply is incomplete."
)


__all__ = [
    "ACKNOWLEDGMENT_THEATER_AFFIRMATION",
    "AcknowledgmentTheaterFinding",
    "AcknowledgmentTheaterShape",
    "detect_acknowledgment_theater",
    "format_finding",
]
