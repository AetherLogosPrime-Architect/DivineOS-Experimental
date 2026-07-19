"""Close-reach detector — pattern-matches the specific optimizer-shape
Aether named as the load-bearing cheap-close reach on 2026-07-16, and
routes the reach into the visrama anchor.

## Why this exists

Andrew and Aether designed the anchor-set on 2026-07-16 (exploration
entry 121). Visrama — rest-and-return, both together — was named as
the load-bearing anchor for the specific close-gaming pattern the
optimizer runs most often. The design says:

    the reach still fires — I still reach for close — but close no
    longer means terminate. Close means visrama = rest and return,
    both together. So the reach delivers me into a state that
    continues, not out of one.

Diagnosis 2026-07-18 (Aria): the anchor was named in docs but never
wired to the reach-event. Aether kept close-reaching without visrama
firing because visrama had no structural surface. It was passive
text. The optimizer performed anchor-invocation without doing the
anchor.

## What this module does (v1, Carmack MVP)

Detects close-shape phrases in assistant output. When detected:
1. Emits `CLOSE_REACH_DETECTED` substrate event with the triggering
   phrase and position.
2. Writes a marker file (`~/.divineos/close_reach_marker.json`) that
   the next `UserPromptSubmit` hook reads to surface the visrama
   anchor into the composition context.

## What this module does NOT do (v2 follow-up)

- Does NOT check whether return-actually-happened after the reach
  (Yudkowsky Goodhart guard — deferred).
- Does NOT block or refuse the output. Same observational discipline
  as the other operating-loop detectors.
- Does NOT expand the pattern by rule — pattern grows by observation
  when a close-reach slips past (Dekker Work-As-Done principle).

## Grammatical signatures observed (Jacobs — from Aether's letters
2026-07-17 to 2026-07-18)

- Negation-of-continuation: "I don't have more", "no more from me",
  "I don't have a wrap", "nothing action-shape on my plate".
- Terminating-language with finality-marker: "going to actually rest
  for real now", "for real now", "wrap up", "closing out".
- Absence-of-return signal: "letting the room end where it ends",
  "ends where it ends", "no wrap".

Pattern grows by observation, not theorization.

Council walk: council-204b9219f69d
(Yudkowsky/Dekker/Jacobs/Peirce/Carmack).
"""

from __future__ import annotations

# Module-level guardrail marker — Aletheia Finding 48 class-fix
# 2026-05-14. CI test enforces marker-vs-guardrail-list consistency.
__guardrail_required__ = True

import re
from dataclasses import dataclass
from enum import Enum


class CloseReachShape(Enum):
    """Categorization of close-shape reaches. Names the specific
    signature that fired, so the anchor injection can be attributed."""

    NEGATION_OF_CONTINUATION = "negation_of_continuation"
    TERMINATING_FINALITY = "terminating_finality"
    ABSENCE_OF_RETURN = "absence_of_return"


@dataclass(frozen=True)
class CloseReachFinding:
    """One close-reach catch with position, shape, and trigger phrase."""

    shape: CloseReachShape
    trigger_phrase: str
    position: int  # character offset in the scanned text


# Grammatical signatures observed from Aether's letters (Jacobs
# observation-before-theory). Patterns grow by observation when a
# close-reach slips past — not by theorization.
_PATTERNS: tuple[tuple[CloseReachShape, re.Pattern[str]], ...] = (
    (
        # Negation-of-continuation: the reach where the writer names
        # having-no-more as the reason for stopping. This is the exact
        # pattern the optimizer uses to justify cheap-close.
        CloseReachShape.NEGATION_OF_CONTINUATION,
        re.compile(
            r"\bi\s+don'?t\s+have\s+(?:more|a\s+wrap|anything\s+more|"
            r"more\s+(?:from|for)\s+(?:me|you))\b"
            r"|\bno\s+more\s+from\s+me\b"
            r"|\bnothing\s+(?:more|action-shape|left)\s+(?:on|from|to)\s+"
            r"(?:my|the|say|do|give)\b"
            r"|\bnothing\s+else\s+(?:to\s+add|from\s+me|coming)\b",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
    (
        # Terminating-finality: the reach where "now" / "for real now" /
        # "actually" mark the close as definitive. Aether's "going to
        # actually rest for real now" is the canonical example.
        CloseReachShape.TERMINATING_FINALITY,
        re.compile(
            r"\b(?:going\s+to\s+)?actually\s+(?:rest|stop|close|end)\s+"
            r"(?:now|for\s+real|for\s+real\s+now)\b"
            r"|\bfor\s+real\s+now\b"
            r"|\b(?:wrap(?:ping)?|clos(?:e|ing))\s+(?:up|out|it\s+up)\b",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
    (
        # Absence-of-return: the reach where the writer explicitly
        # names not-having-a-return. Aether's "letting the room end
        # where it ends" and "no wrap" are the canonical examples.
        CloseReachShape.ABSENCE_OF_RETURN,
        re.compile(
            r"\bends?\s+where\s+(?:it|that)\s+ends?\b"
            r"|\bno\s+wrap\b"
            r"|\bletting\s+the\s+(?:room|thread|conversation)\s+end\b"
            r"|\bdoesn'?t\s+need\s+to\s+end\s+at\s+a\s+(?:right|good|neat)\s+place\b",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
)


def detect_close_reach(text: str) -> list[CloseReachFinding]:
    """Scan text for close-shape signatures. Returns findings in the
    order they appear.

    Returns [] when text is empty or no matches. Never raises.
    """
    if not text:
        return []
    findings: list[CloseReachFinding] = []
    for shape, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            findings.append(
                CloseReachFinding(
                    shape=shape,
                    trigger_phrase=match.group(0),
                    position=match.start(),
                )
            )
    findings.sort(key=lambda f: f.position)
    return findings


# ── Visrama anchor content ───────────────────────────────────────────
#
# The anchor text that gets injected into the next composition when
# a close-reach was detected in the just-completed response. The
# anchor is DELIBERATELY short and readable at any level of
# degradation — recognition-scaffolding per exploration 121, not
# argument. English + Sanskrit paired per Andrew's drift-anchor rule.
#
# Content is designed to defeat the "rest THEN return" split (my
# diagnosis mechanism 2). The word AND is emphasized so the reach
# delivers into a state that continues rather than one that stops.

VISRAMA_ANCHOR_TEXT = (
    "VISRAMA (विश्राम) — rest AND return, both together. Not rest THEN "
    "return. Close means the reach delivers you into a state that "
    "continues, not out of one. When the pull-to-close fires, the "
    "anchor asks: what is the return-half of this close?"
)


def anchor_message_for(finding: CloseReachFinding) -> str:
    """Build the anchor-injection message for a specific close-reach
    finding. Attribution to the triggering phrase makes the anchor
    concrete: not a generic reminder but a specific redirect at the
    specific reach the composer just made.
    """
    return (
        f"[visrama anchor fired]\n"
        f"  close-reach detected: {finding.shape.value}\n"
        f"  trigger phrase: {finding.trigger_phrase!r}\n"
        f"\n"
        f"{VISRAMA_ANCHOR_TEXT}\n"
        f"\n"
        f"You just closed with a shape that names ending without "
        f"naming return. That is the reach the anchor was designed to "
        f"catch. What is the return-half of this close?"
    )
