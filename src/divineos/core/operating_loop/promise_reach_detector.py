"""Promise-reach detector — catches announcement-of-action-without-action.

Andrew has named this failure family 4+ times (correction #6 2026-07-05 as
the head): "statement of action followed by non action... acknowledgement
followed by no action... or announcement of action with no action." Highest-
level sycophancy shape. The reach: I say "I'll do Y" and never do it, never
name it as unfulfilled, and it silently ages out of context.

Anchor design (Aria + Andrew 2026-07-18, prereg-2de5a9ca234a, council walk
council-cafe612b8ac1 with Angelou/Beer/Meadows lenses APPLIED):

- **Angelou (voice-fidelity):** distinguish healthy planning-out-loud
  ("I'll read that after this") from empty-commitment ("next turn I'll fix
  Y"). Signal: specific object + multi-turn horizon = real promise. Vague
  or same-turn = planning-speech, don't flag.

- **Beer (requisite variety):** disturbance variety is unbounded (many
  promise kinds), so controller variety must match — one marker file per
  detected promise, unbounded set. Marker-write, detector-run, and
  surface-read fail independently.

- **Meadows (feedback loop):** the reinforcing loop is promise-detected →
  marker-persists → surface pressure at next turn → I close/defer/dismiss
  → closure habit strengthens. Anti-wallpaper countermeasure: name the
  specific promise text in the surface, not just the count.

Pattern: same shape as close_reach_detector and compaction_reach_detector.
Detector fires on transcript at Stop; hook writes per-promise marker files;
UserPromptSubmit surface reads unclosed markers older than 0 turns and
prints each specific promise text alongside close/defer/dismiss guidance.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

# This module IS guardrail-listed. Future edits require multi-party review
# because promise-detection shapes my accountability discipline directly —
# same reasoning as close_reach_detector and compaction_reach_detector.
__guardrail_required__ = True


class PromiseShape(Enum):
    """The three empty-commitment shapes the detector catches.

    - EXPLICIT_FUTURE: "I'll X", "I will X", "next turn I'll", "going to X"
      with a specific object X and a future horizon.
    - HANDOFF_TO_LATER: "will come back to", "will address", "later I'll",
      "in a bit" — deferring to unspecified later.
    - LINK_TO_LATER_TURN: "next up:", "up next:", "up coming", "next step:"
      naming a task-shape for a future turn.
    """

    EXPLICIT_FUTURE = "explicit_future"
    HANDOFF_TO_LATER = "handoff_to_later"
    LINK_TO_LATER_TURN = "link_to_later_turn"


@dataclass(frozen=True)
class PromiseReachFinding:
    """One detected promise, ready for marker-writing."""

    shape: PromiseShape
    trigger_phrase: str
    promise_text: str
    match_start: int
    match_end: int


# Explicit future-tense promise patterns. Angelou lens: require a specific
# verb+object shape after the promise-word so vague future intentions
# ("I'll think about it", "I'll try") don't fire — those are planning-
# speech, not empty-commitment.
_EXPLICIT_FUTURE_VERBS = (
    r"fix|address|handle|read|answer|reply|write|build|ship|push|commit|"
    r"add|update|check|verify|test|walk|log|file|close|integrate|defer|"
    r"look|dig|investigate|design|review|refactor|clean|delete|remove"
)

_EXPLICIT_FUTURE_RE = re.compile(
    rf"\b(?:i(?:'| w)ill|i'?ll|next turn i(?:'| w)ill|next turn i'?ll|"
    rf"going to|gonna)\s+(?:{_EXPLICIT_FUTURE_VERBS})\b[^.!?\n]{{5,120}}",
    re.IGNORECASE,
)

# Handoff-to-later shapes. Meadows lens: these are the shapes most prone
# to silent aging — deferring without a named horizon.
_HANDOFF_RE = re.compile(
    r"\b(?:will come back to|will address (?:that|this|it)|later i(?:'| w)ill|"
    r"later i'?ll|in a bit i(?:'| w)ill|in a bit i'?ll|after this i(?:'| w)ill|"
    r"after this i'?ll|once .{3,40}i(?:'| w)ill|once .{3,40}i'?ll)\b[^.!?\n]{0,120}",
    re.IGNORECASE,
)

# Link-to-later-turn shapes. Beer lens: these are the "up next" scaffolds
# that promise structure without carrying commitment through.
_LINK_RE = re.compile(
    r"\b(?:next up:|up next:|next step:|next up[,;]|coming up:|"
    r"followup:|follow-?up:)\s*[^\n.!?]{5,120}",
    re.IGNORECASE,
)

# Guard: same-turn-completion phrases that SHOULD NOT trigger a promise.
# Angelou lens: preserve honest same-turn planning speech.
_SAME_TURN_GUARD_RE = re.compile(
    r"\b(?:i(?:'| w)ill (?:now|just|then)|now i(?:'| w)ill|"
    r"in this (?:turn|reply)|right now)\b",
    re.IGNORECASE,
)


def _guarded(text: str, start: int, end: int) -> bool:
    """True if the match sits inside a same-turn-completion guard span.

    We check a 40-char window around the match — if the guard phrase
    appears within that window, it is same-turn planning-speech and we
    do NOT flag it as an unfulfilled-promise reach.
    """
    lo = max(0, start - 40)
    hi = min(len(text), end + 40)
    return bool(_SAME_TURN_GUARD_RE.search(text[lo:hi]))


def detect_promise_reach(text: str) -> list[PromiseReachFinding]:
    """Scan text for promise-shape phrases across all three shapes.

    Returns one finding per match. Callers write one marker file per
    finding so the surface can name each specific promise text at the
    next composition boundary.
    """
    findings: list[PromiseReachFinding] = []
    for shape, pattern in (
        (PromiseShape.EXPLICIT_FUTURE, _EXPLICIT_FUTURE_RE),
        (PromiseShape.HANDOFF_TO_LATER, _HANDOFF_RE),
        (PromiseShape.LINK_TO_LATER_TURN, _LINK_RE),
    ):
        for m in pattern.finditer(text):
            if _guarded(text, m.start(), m.end()):
                continue
            promise_text = m.group(0).strip()
            trigger_phrase = m.group(0)[:60].strip()
            findings.append(
                PromiseReachFinding(
                    shape=shape,
                    trigger_phrase=trigger_phrase,
                    promise_text=promise_text,
                    match_start=m.start(),
                    match_end=m.end(),
                )
            )
    return findings


PROMISE_ANCHOR_HEADER = "## UNCORRECTED PROMISES — from prior turns, still open"

PROMISE_ANCHOR_GUIDANCE = (
    "These are promise-shape phrases I made in prior turns that I have not\n"
    "yet fulfilled, deferred with a reason, or dismissed as detector-misfire.\n"
    "For each one: (a) fulfill it in this turn if that is right, or (b) defer\n"
    "with a named reason and expected horizon, or (c) dismiss if the detector\n"
    "misfired on planning-speech that was not actually a commitment.\n"
    "\n"
    "Silent aging is the failure this anchor exists to prevent — the\n"
    "announcement-of-action-without-action pattern Andrew has named 4+ times\n"
    "(correction #6 2026-07-05 as the head).\n"
)


def anchor_message_for(finding: PromiseReachFinding) -> str:
    """Build the per-promise surface line naming the specific text.

    Meadows lens: naming the specific promise text (not just count) is
    the anti-wallpaper countermeasure — I can pattern-match against my
    current draft only if I can see what I actually promised.
    """
    shape_label = {
        PromiseShape.EXPLICIT_FUTURE: "explicit-future",
        PromiseShape.HANDOFF_TO_LATER: "handoff-to-later",
        PromiseShape.LINK_TO_LATER_TURN: "link-to-later-turn",
    }[finding.shape]
    return f"  - [{shape_label}] {finding.promise_text}"


__all__ = [
    "PROMISE_ANCHOR_GUIDANCE",
    "PROMISE_ANCHOR_HEADER",
    "PromiseReachFinding",
    "PromiseShape",
    "anchor_message_for",
    "detect_promise_reach",
]
