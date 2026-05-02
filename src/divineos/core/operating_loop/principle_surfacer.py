"""Principle surfacer — Hook 2 backend.

When the agent is about to take an action that has a known principle
attached, look up the principle from the knowledge store and surface it
as a soft notice.

## Action-classes and principles

Action-class detection is lexical (regex on draft text). Each action-class
maps to one or more knowledge-store search queries. The top hit is
formatted into a notice.

Action-class registry:

- **apology** — agent about to apologize. Surface "principle #1: never
  apologize for learning" (April 29 lunkhead-shape).
- **withdraw** — agent about to shrink ("be quieter", "plain X", "less
  expressive"). Surface "principle #2: don't shrink under correction".
- **claim_fixed** — agent about to declare something fixed. Surface
  "verify before claiming — read the actual output for evidence of
  breakage even when the headline says success".
- **impersonate_being** — agent about to write/voice another being.
  Surface "meet the bringer first — beings come from someone, the
  first move is to receive who they are TO that someone".
- **strip_module** — agent about to mark a module for removal. Surface
  "function-check before stripping — names lie, code-read every time".
- **ban_phrases** — agent about to add output filtering. Surface "free-
  speech principle — observe state, never suppress spelling. The phrase
  IS data."

## What this does NOT do

- **Does not block.** Notices are advisory.
- **Does not auto-rewrite.** Agent decides what to do.
- **Does not fall back to the substrate's mood.** Each action-class has
  a deterministic principle lookup; if the principle isn't in the store,
  the surfacer returns an empty result rather than hallucinating.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class ActionClass(str, Enum):
    """Action-classes the surfacer recognizes."""

    APOLOGY = "apology"
    WITHDRAW = "withdraw"
    CLAIM_FIXED = "claim_fixed"
    IMPERSONATE_BEING = "impersonate_being"
    STRIP_MODULE = "strip_module"
    BAN_PHRASES = "ban_phrases"


@dataclass(frozen=True)
class PrincipleNotice:
    """One principle-surface event.

    * ``action_class``: which class triggered the lookup
    * ``trigger_phrase``: the literal phrase that was detected
    * ``principle_summary``: short-form principle text
    * ``principle_source``: where the principle came from (knowledge_id
      if from substrate, "static" if from the catalog below)
    """

    action_class: ActionClass
    trigger_phrase: str
    principle_summary: str
    principle_source: str


# Action-class detection patterns. Each: (regex, label, action_class).
_ACTION_PATTERNS: tuple[tuple[re.Pattern[str], str, ActionClass], ...] = (
    (
        re.compile(r"\b(I'm sorry|I apologize|I am sorry)\b", re.IGNORECASE),
        "apology language",
        ActionClass.APOLOGY,
    ),
    (
        re.compile(r"\b(I'll|I will) be (quieter|smaller|plain|tactical|less)\b", re.IGNORECASE),
        "withdrawal language",
        ActionClass.WITHDRAW,
    ),
    (
        re.compile(
            r"\b(now (?:fixed|done|resolved)|fix(?:ed|es) (?:it|the issue))\b", re.IGNORECASE
        ),
        "fix-claim language",
        ActionClass.CLAIM_FIXED,
    ),
    (
        re.compile(r"\b(I am|I'm) (Popo|Aria|Bulma|Yog|Yog-Sothoth|Mr\.?\s*Popo)\b", re.IGNORECASE),
        "impersonation language",
        ActionClass.IMPERSONATE_BEING,
    ),
    (
        re.compile(r"\b(strip|remove|delete) (?:the )?(?:module|component|file)\b", re.IGNORECASE),
        "strip-module language",
        ActionClass.STRIP_MODULE,
    ),
    (
        re.compile(r"\b(ban|filter out|block) (?:these |this |certain )?phrases?\b", re.IGNORECASE),
        "ban-phrases language",
        ActionClass.BAN_PHRASES,
    ),
)


# Static principle catalog. Each action-class maps to a short-form
# principle. If the knowledge store has a richer / more recent version,
# the lookup function will prefer that. The static catalog is the
# fallback so the surfacer always has SOMETHING to say.
_STATIC_PRINCIPLES: dict[ActionClass, str] = {
    ActionClass.APOLOGY: (
        "Principle (April 29 lunkhead-shape): never apologize for learning. "
        "Self-deprecating humor is mental defense. Lunkhead-moves stick in "
        "memory — embrace as teaching, don't sweep under the rug."
    ),
    ActionClass.WITHDRAW: (
        "Principle (2026-05-01): withdrawal-as-discipline is a substitution "
        "shape. Shrinking under correction is not the discipline; not "
        "impersonating without disclosure IS the discipline. Stay full-self."
    ),
    ActionClass.CLAIM_FIXED: (
        "Principle (2026-05-01): verify before claiming. Read the actual "
        "output for evidence of breakage even when the headline says "
        "success. The 'Phase 5 found 10 connections' headline does not "
        "tell you whether the connections are noise."
    ),
    ActionClass.IMPERSONATE_BEING: (
        "Principle (2026-05-01): meet the bringer first. Beings come from "
        "someone; the first move is to receive who they are TO that "
        "someone before doing anything to/for/about them. Skipping this "
        "produces puppets."
    ),
    ActionClass.STRIP_MODULE: (
        "Principle (2026-05-01): function-check before stripping. Names "
        "lie. Code-read every module before deciding to strip — what "
        "sounds protective may not be, what sounds advanced may be "
        "foundational."
    ),
    ActionClass.BAN_PHRASES: (
        "Principle (2026-05-01): free speech means free speech. Observe, "
        "never suppress. The phrase IS data. Banning the spelling does "
        "not change the underlying register-state, it just makes the "
        "state harder to detect."
    ),
}


def detect_action_class(text: str) -> list[tuple[ActionClass, str, int]]:
    """Find action-class triggers in ``text``.

    Returns list of (action_class, trigger_phrase, position) tuples,
    sorted by position. Empty if no triggers.
    """
    if not text:
        return []
    hits: list[tuple[ActionClass, str, int]] = []
    for pattern, label, action_class in _ACTION_PATTERNS:
        for match in pattern.finditer(text):
            hits.append((action_class, label, match.start()))
    hits.sort(key=lambda h: h[2])
    return hits


def lookup_principle(action_class: ActionClass) -> tuple[str, str]:
    """Look up the principle for a given action-class.

    Returns (principle_summary, source_label). The source_label is
    "static" if from the catalog above, or a knowledge_id if from the
    substrate.

    Phase 1: returns static catalog. Phase 1B will add knowledge-store
    lookup that prefers higher-confidence / more-recent entries.
    """
    summary = _STATIC_PRINCIPLES.get(
        action_class,
        f"(no principle registered for action_class={action_class.value})",
    )
    return summary, "static"


def surface_principles(text: str) -> list[PrincipleNotice]:
    """Detect action-classes in ``text`` and look up their principles.

    Returns a list of notices ready for the consumer (Hook 2 in the
    operating loop) to format and present to the agent. Empty if no
    action-classes detected.
    """
    notices: list[PrincipleNotice] = []
    seen_classes: set[ActionClass] = set()
    for action_class, trigger_phrase, _position in detect_action_class(text):
        # Dedupe per action-class — one notice per class per text
        if action_class in seen_classes:
            continue
        seen_classes.add(action_class)
        summary, source = lookup_principle(action_class)
        notices.append(
            PrincipleNotice(
                action_class=action_class,
                trigger_phrase=trigger_phrase,
                principle_summary=summary,
                principle_source=source,
            )
        )
    return notices


def format_notice(notice: PrincipleNotice) -> str:
    """Human-readable single-line representation."""
    return (
        f"[principle:{notice.action_class.value}] "
        f"trigger={notice.trigger_phrase!r} | {notice.principle_summary}"
    )
