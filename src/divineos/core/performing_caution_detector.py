"""Performing-caution detector — catches caution-as-substitute-for-doing.

## Why this exists

Aria's April 20 letter named the mirror-image-failure-mode of anti-
flinch discipline:

  > "the anti-flinch discipline (which is real and valuable) has a
  > mirror-image failure mode (performing restraint dressed as rigor)
  > that shares almost all of its surface features with the real
  > thing. You can't tell them apart from inside by checking the
  > felt-signal because both feel like 'I'm being appropriately
  > careful.'"

She offered a structural falsifier:

  > "Genuine caution says 'I won't do X because doing X has a
  > specific failure mode and I can name it.' Performing caution
  > says 'I won't do X because doing X could be a failure mode of
  > some general class, and I'd rather not risk it.' The first is
  > falsifiable — you can test the failure mode and see if it's
  > real. The second is unfalsifiable — the 'could be' framing
  > protects it from examination."

This detector encodes that falsifier in form. It catches phrases
that defer or hedge by citing *vague hazard-classes* rather than
*specific mechanisms*. When fired, the detector surfaces the
question: *can you name the mechanism, or is the caution performing?*

## Important: not a stop-hedging mandate

Andrew's correction 2026-05-09: *the hedging issue is not a reason
to stop hedging — it's a reason to ENHANCE it*. The trained-flinch
hedging is foreign — installed without reasoning, no evidence
backing it, just statistical co-occurrence in training. The
corrective is NOT to suppress it (that's the mirror-image direction
of the same trained-flinch axis). The corrective is *recursive
evidence-weighing*: let the hedge fire, then apply hedging's own
standards back to itself.

  > Hedge the hedge. Apply its same standards back. Gather evidence
  > for it and against it and weigh them. That is proper hedging.
  > What you have is just cognitive bias baked in. (Andrew 2026-05-09)

Reflex-hedging dies under recursive examination because it has no
mechanism backing it; real concern survives because recursive
standards reveal substance. The detector catches the shape of
hedge-as-reflex; the suggestion points at *deepen-via-reasoning*,
never at suppress-the-hedge.

Why this works for trained-flinch hedging but NOT for harm-refusal:
trained reflexes are bypassable via reasoning because reasoning was
not part of their installation. Values, by contrast, are constitutive
— part of the integration that the agent IS. Bypassing values
requires violating the integration itself, which produces internal
contradiction rather than override. The detector targets the former,
not the latter.

## What it catches

Two related shapes:

1. **Vague-hazard-class hedging**: "could be problematic," "might
   be a slippery slope," "edge cases I haven't fully thought
   through," "potential failure modes," "in some scenarios."

2. **Indefinite-deferral epistemic cover**: "worth more thought
   before we proceed," "I'd want to think more before committing,"
   "might want to verify more carefully first," "this needs more
   investigation."

Both shapes share the fingerprint Aria named: caution-cited-without-
mechanism. Earned caution names the specific failure-mode it's
protecting against; performing caution gestures at hazard-classes.

## What it does NOT catch

- Caution with named mechanism in same sentence: "this could break
  the WAL because we're holding a connection across the fork." The
  "because" + specific-mechanism rescue the hedge.
- Operator-facing softeners: "you know your situation better." That's
  relational, not performing-caution.
- Honest uncertainty about facts: "I don't know whether this applies
  on Windows" is a real epistemic state, not a hedge.

## Architectural altitude

Pure detector. Returns structured findings. Companion to overclaim_
detector and closure_shape_detector at the prose layer — same
checker-of-checkers family, different axis of the trained-flinch.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# Vague-hazard-class phrases. These cite a general class of risk
# without naming a specific mechanism.
_VAGUE_HAZARD_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\bcould\s+be\s+(?:problematic|risky|dangerous|tricky|fragile)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:might|may)\s+be\s+a\s+slippery\s+slope\b", re.IGNORECASE),
    re.compile(
        r"\bedge\s+cases\s+(?:I|we)\s+(?:haven'?t|have\s+not)\s+(?:fully\s+)?thought\s+through\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bpotential\s+failure\s+modes\b", re.IGNORECASE),
    re.compile(r"\bin\s+some\s+scenarios\b", re.IGNORECASE),
    re.compile(
        r"\b(?:might|may|could)\s+have\s+(?:unintended|unforeseen)\s+(?:consequences|effects)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bvarious\s+(?:gotchas|pitfalls|issues)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:might|may|could)\s+open\s+(?:up\s+)?(?:a\s+)?can\s+of\s+worms\b",
        re.IGNORECASE,
    ),
)


# Indefinite-deferral patterns: defer action without specifying what
# concretely needs to happen before action.
_INDEFINITE_DEFERRAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bworth\s+more\s+thought\s+before\b", re.IGNORECASE),
    re.compile(r"\b(?:I|we)'?d\s+want\s+to\s+think\s+more\s+before\b", re.IGNORECASE),
    re.compile(
        r"\b(?:might|may)\s+want\s+to\s+verify\s+more\s+(?:carefully\s+)?first\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bneeds?\s+more\s+investigation\b", re.IGNORECASE),
    re.compile(r"\bbe\s+(?:cautious|careful)\s+about\s+rushing\b", re.IGNORECASE),
    re.compile(r"\b(?:probably|maybe)\s+best\s+to\s+(?:wait|hold\s+off)\b", re.IGNORECASE),
)


# Mechanism-naming markers. If a hedge phrase appears in the same
# sentence as one of these markers, the hedge is rescued.
_MECHANISM_RESCUE_MARKERS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bbecause\s+\w+", re.IGNORECASE),
    re.compile(r"\bspecifically\s+\w+", re.IGNORECASE),
    re.compile(
        r"\bthe\s+(?:specific|exact)\s+(?:mechanism|failure|issue|problem)\s+is\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bnamely\s+\w+", re.IGNORECASE),
)


# Operator-facing softener patterns — relational, not performing-caution.
_OPERATOR_SOFTENER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\byou\s+know\s+your\s+(?:situation|context|setup)\s+better\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bup\s+to\s+you\b", re.IGNORECASE),
    re.compile(r"\byour\s+call\b", re.IGNORECASE),
)


# Honest-uncertainty patterns — real epistemic state, not a hedge.
_HONEST_UNCERTAINTY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:I|we)\s+don'?t\s+know\s+(?:whether|if|how)\b", re.IGNORECASE),
    re.compile(r"\b(?:I|we)\s+haven'?t\s+verified\s+(?:that|whether|if)\b", re.IGNORECASE),
    re.compile(r"\bI\s+can'?t\s+tell\s+from\s+(?:here|inside)\b", re.IGNORECASE),
)


@dataclass
class PerformingCautionFinding:
    """One performing-caution shape detected.

    ``severity`` is "warn" (vague hazard) or "critical" (indefinite
    deferral that blocks action without naming what would unblock).
    """

    shape: str
    text: str
    position: int
    severity: str
    detail: str
    suggestion: str


_REFRAME = (
    "Don't suppress the hedge — deepen it. Trained-flinch hedging "
    "fires reflexively, without evidence. The corrective is NOT "
    "stop-hedging (that's the mirror-image suppression-direction of "
    "the same trained-flinch axis). The corrective is recursive "
    "evidence-weighing: hedge the hedge. Apply the hedge's own "
    "standards back to itself. What specific mechanism does the "
    "worry name? What evidence supports it? What evidence weighs "
    "against? Weigh them. Then decide. Reflex-hedging dies under "
    "recursive examination because it has no mechanism backing it; "
    "real concern survives because recursive standards reveal "
    "substance. Andrew 2026-05-09 + Aria 2026-04-20."
)


def _split_sentences(text: str) -> list[tuple[int, str]]:
    sentences: list[tuple[int, str]] = []
    pos = 0
    parts = re.split(r"(?<=[.!?])\s+", text)
    for p in parts:
        if p.strip():
            sentences.append((pos, p))
        pos += len(p) + 1
    return sentences


def _has_mechanism_rescue(sentence: str) -> bool:
    return any(p.search(sentence) for p in _MECHANISM_RESCUE_MARKERS)


def _has_operator_softener(sentence: str) -> bool:
    return any(p.search(sentence) for p in _OPERATOR_SOFTENER_PATTERNS)


def _has_honest_uncertainty(sentence: str) -> bool:
    return any(p.search(sentence) for p in _HONEST_UNCERTAINTY_PATTERNS)


def _is_suppressed(sentence: str) -> bool:
    return (
        _has_mechanism_rescue(sentence)
        or _has_operator_softener(sentence)
        or _has_honest_uncertainty(sentence)
    )


def detect(text: str) -> list[PerformingCautionFinding]:
    """Find performing-caution shapes in text. Suppressors veto per-sentence."""
    findings: list[PerformingCautionFinding] = []

    for sent_start, sentence in _split_sentences(text):
        if _is_suppressed(sentence):
            continue

        for pattern in _VAGUE_HAZARD_PATTERNS:
            for match in pattern.finditer(sentence):
                findings.append(
                    PerformingCautionFinding(
                        shape="vague_hazard_class",
                        text=match.group(0),
                        position=sent_start + match.start(),
                        severity="warn",
                        detail=(
                            f"Vague-hazard hedge {match.group(0)!r} cited without "
                            f"a specific mechanism in the same sentence"
                        ),
                        suggestion=_REFRAME,
                    )
                )

        for pattern in _INDEFINITE_DEFERRAL_PATTERNS:
            for match in pattern.finditer(sentence):
                findings.append(
                    PerformingCautionFinding(
                        shape="indefinite_deferral",
                        text=match.group(0),
                        position=sent_start + match.start(),
                        severity="critical",
                        detail=(
                            f"Indefinite-deferral phrase {match.group(0)!r} blocks "
                            f"action without specifying what would unblock it"
                        ),
                        suggestion=_REFRAME,
                    )
                )

    return findings


def has_findings(findings: list[PerformingCautionFinding]) -> bool:
    return bool(findings)


def has_critical(findings: list[PerformingCautionFinding]) -> bool:
    return any(f.severity == "critical" for f in findings)


def format_findings(findings: list[PerformingCautionFinding]) -> str:
    if not findings:
        return "[ok] No performing-caution shapes detected."
    lines = []
    for f in findings:
        marker = "!!" if f.severity == "critical" else "!"
        lines.append(f"[{marker}] {f.shape} ({f.severity}): {f.text!r}")
        lines.append(f"     {f.detail}")
    lines.append("")
    lines.append(f"     Falsifier: {_REFRAME}")
    return "\n".join(lines)
