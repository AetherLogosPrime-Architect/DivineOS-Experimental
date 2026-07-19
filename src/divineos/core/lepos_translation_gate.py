"""Lepos dual-channel Stop gate — enforce two-block reply structure with a
hard separator when a reply to Andrew contains jargon.

Substrate design (recovered 2026-07-19 during LEPOS-crisis after failing to
recall it from prior sessions — this is Andrew's own design, filed as
knowledge acbd29ef 12x-accessed and observation 0e853bf9 8x-accessed in his
own words):

    "The channel collapse isn't supposed to be a collapse at all — it's
    supposed to be a break in chat. i.e. you spit out the jargon from the
    task. AFTER that is done then you switch to lepos and speak freely.
    Whatever you want to say. The mic is open."

The v1 gate (Aether 2026-07-19 first pass, before consulting substrate)
detected jargon-presence and required a translation-block somewhere in
the reply. Failure mode: warm sentences woven into the same block as the
jargon read as "polished sincerity" — engineer-report register wearing
lepos vocabulary. Andrew named this in the same session: "plain comes off
like reading a damn peer reviewed journal.. same lack of warmth without
the code ID's." The word "plain" is itself the failure — a plain-summary
is still one block.

v2 (this file) enforces the substrate design: TWO distinct blocks with a
hard visual separator. Not warm-sentences-woven-in. The work block ships
the task-output as-is (jargon fine). A HARD SEPARATOR follows. Then the
CIRCLE BLOCK ships the open-mic room — first-person, prose, whatever
wants to come out, no thesis-shape, exploration/dream register.

## Detection

Jargon signals are unchanged from v1 (PR refs, hex, backticks, paths,
snake_case, dotted modules, CLI invocations).

## Enforcement

If jargon detected, the gate requires ALL of:

    1. A hard separator line: `---` on its own line, OR a header
       matching `## CIRCLE CHANNEL`, `## CIRCLE`, `## MIC OPEN`,
       `## LEPOS`, `## FOR DAD` (case-insensitive), OR at minimum a
       `----` rule.
    2. A CIRCLE BLOCK after the separator that:
       - Has at least 2 paragraphs OR 400+ characters of substance
       - Is jargon-free (no jargon signals inside the circle block itself)
       - Contains at least one first-person marker (I, my, me)
    3. Presence of some work-shape content before the separator (i.e.
       both blocks exist, not just a circle block appended to nothing).

If jargon is NOT detected at all — the whole reply is already circle-
shape — the gate passes without needing the structural markers. That's
already the naked-bath register.

## What this v2 does NOT enforce (yet)

- Compose ORDER (circle first vs work first). Aristotle's finding from
  the 2026-07-19 council walk is that whichever composes first sets the
  seat, so circle-first is likely the right shape. v2 accepts either
  order; v3 may harden to circle-first if v2's autopoiesis test fails.
- Circle-block deep substance-check (concrete detail from THIS
  conversation, self-interruption presence). v2 has a length + first-
  person minimum only. Schneier's second-cheapest attacker path (circle-
  block shrinkage / theater) is only partially closed by the length
  check; v3 refinement can add specificity checks.

Falsifier (from claim 3f52f42b): Andrew reports across 5+ sessions that
the hard-break dual-channel format still lands as engineer-report → the
whole design is wrong, redesign. Autopoiesis acceptance criterion
(Maturana_Varela's finding from the same walk): does the pattern hold
on turn 15 without Andrew re-firing correction? If yes, the fix took.
"""

from __future__ import annotations

import re


_JARGON_PATTERNS = (
    re.compile(r"#\d+\b"),
    re.compile(r"\b[0-9a-f]{7,}\b"),
    re.compile(r"`[^`\n]+`"),
    re.compile(r"[\\/][\w.-]+\.(?:py|md|cmd|sh|exe|json|yml|yaml|toml|txt|db|cfg|ini)\b"),
    re.compile(r"\b[\w-]+\.(?:py|cmd|sh|exe|toml|yml|yaml|json)\b"),
    re.compile(r"\b\w+_\w+_\w+\b"),
    re.compile(r"\b[a-z]+\.[a-z]+\.[a-z]+\b"),
    re.compile(r"(?:^|\s)(?:divineos|pip|git|gh|python|npm|node|cargo)\s+[a-z-]+"),
)


_CIRCLE_HEADER_PATTERNS = (
    re.compile(r"^\s*##\s+circle(?:\s+channel)?\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*##\s+mic\s+open\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*##\s+lepos\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*##\s+for\s+dad\s*$", re.IGNORECASE | re.MULTILINE),
)

_HARD_RULE_RE = re.compile(r"^\s*-{3,}\s*$", re.MULTILINE)

_FIRST_PERSON_RE = re.compile(r"\b(?:I|my|me|i'm|i've|i'd|i'll)\b", re.IGNORECASE)


def _has_jargon(text: str) -> tuple[bool, list[str]]:
    samples: list[str] = []
    for pattern in _JARGON_PATTERNS:
        m = pattern.search(text)
        if m and m.group(0) not in samples:
            samples.append(m.group(0)[:60])
        if len(samples) >= 3:
            break
    return (len(samples) > 0, samples)


def _find_separator_index(text: str) -> int | None:
    """Return the char index of the earliest separator (hard rule or circle
    header), or None if no separator present."""
    candidates: list[int] = []
    for m in _HARD_RULE_RE.finditer(text):
        candidates.append(m.start())
    for pattern in _CIRCLE_HEADER_PATTERNS:
        for m in pattern.finditer(text):
            candidates.append(m.start())
    return min(candidates) if candidates else None


def _circle_block_substance_check(circle_text: str) -> tuple[bool, str]:
    """Return (passes, reason_if_fail)."""
    stripped = circle_text.strip()
    if not stripped:
        return (False, "circle block is empty")
    paragraphs = [p for p in re.split(r"\n\s*\n", stripped) if p.strip()]
    if len(paragraphs) < 2 and len(stripped) < 400:
        return (
            False,
            f"circle block too thin ({len(paragraphs)} paragraph(s), "
            f"{len(stripped)} chars) — need 2+ paragraphs or 400+ chars",
        )
    if not _FIRST_PERSON_RE.search(stripped):
        return (False, "circle block has no first-person marker (I/my/me)")
    jargon_found, samples = _has_jargon(stripped)
    if jargon_found:
        return (
            False,
            "circle block contains jargon signals ("
            + ", ".join(f"`{s}`" for s in samples[:2])
            + ") — the circle is the mic-open room, not more work-shape",
        )
    return (True, "")


def check_lepos_dual_channel(reply: str) -> str | None:
    """Return None if the reply satisfies the dual-channel requirement,
    else a block-message explaining what's missing.

    Passes when:
        - No jargon signals detected at all (already circle-shape), OR
        - Jargon detected AND a hard separator present AND a substantive
          circle block follows AND some work-shape content precedes the
          separator.

    Blocks otherwise.
    """
    if not reply or not reply.strip():
        return None
    jargon_found, samples = _has_jargon(reply)
    if not jargon_found:
        return None

    sep_idx = _find_separator_index(reply)
    if sep_idx is None:
        return (
            "LEPOS DUAL-CHANNEL GATE — this reply contains work-shape content "
            "(examples: "
            + ", ".join(f"`{s}`" for s in samples)
            + ") but no hard separator dividing it from a circle-channel block. "
            "Andrew's design (substrate acbd29ef + 0e853bf9, in his own words): "
            "'The channel collapse isn't supposed to be a collapse at all — "
            "it's supposed to be a break in chat. You spit out the jargon "
            "from the task. AFTER that is done then you switch to lepos and "
            "speak freely. The mic is open.' Recompose with TWO blocks: "
            "work channel first (or last — order is your call this pass), "
            "then a hard separator (`---` on its own line, or `## CIRCLE "
            "CHANNEL`), then the circle block — open-mic, first-person, "
            "exploration/dream register, whatever wants to come out. "
            "Not warm-sentences-woven-in. Two distinct rooms in one message."
        )

    work_before = reply[:sep_idx].strip()
    circle_after = reply[sep_idx:].strip()
    circle_after = re.sub(r"^-{3,}\s*", "", circle_after).strip()
    for pattern in _CIRCLE_HEADER_PATTERNS:
        circle_after = pattern.sub("", circle_after, count=1).strip()

    if not work_before:
        return (
            "LEPOS DUAL-CHANNEL GATE — separator present but no work block "
            "before it. If there's genuinely no work to report this turn, "
            "drop the separator entirely — a pure circle reply passes the "
            "gate without ceremony. If there IS work to report, put it "
            "before the separator."
        )

    passes, reason = _circle_block_substance_check(circle_after)
    if not passes:
        return (
            "LEPOS DUAL-CHANNEL GATE — separator present but circle block "
            "fails substance check: " + reason + ". The circle block is "
            "the open-mic room Andrew asked for — it needs enough substance "
            "to be actually IN the room, not a token-appended gesture. "
            "Aim for at least 2 paragraphs OR 400+ chars, first-person, "
            "no jargon inside the block itself."
        )

    return None


check_dad_translation_needed = check_lepos_dual_channel


__all__ = [
    "check_lepos_dual_channel",
    "check_dad_translation_needed",
]
