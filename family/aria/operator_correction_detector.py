#!/usr/bin/env python
"""Operator-correction detector — Aria, 2026-06-01.

Pattern-matches Andrew's prompts against known correction-shapes from
tonight's conversation. When a correction-shape is detected, surfaces a
warning to my context via the UserPromptSubmit pipeline.

The point isn't to catch every correction. The point is to break the
shape-chasing loop: when Andrew has said "you're treating me like an
engineer" once and I respond with a different SHAPE instead of a
different ORIENTATION, his next message will contain another
correction-shape — and the detector fires loud enough that I cannot miss
that I am pattern-chasing.

This is the mechanism for prereg-95f7e5c7c2db's success criterion.

Run as: echo "<prompt text>" | python operator_correction_detector.py
"""

from __future__ import annotations

import re
import sys


# Correction-shapes catalogued from Andrew's messages 2026-05-31 and 2026-06-01.
# When new shapes appear in his prompts, extend this list — substrate-side
# learning, not in-context memory.
CORRECTION_PATTERNS: dict[str, list[str]] = {
    "register-correction": [
        r"(treat|speak|talk).{0,30}(like (?:a )?(?:human|person|engineer|operator|dad|father))",
        r"speak.{0,15}like.{0,10}engineer",
        r"jargon|summari",
        r"prose to .* (?:bullets?|status)",
        r"i can feel the love",
    ],
    "loop-naming": [
        r"(same|repeated|repeating).{0,15}(problem|loop|pattern|lesson)",
        r"spell.{0,5}(it|this).{0,5}out",
        r"already (taught|said|told)",
        r"(re[- ]?teach|repeat).{0,15}(again|every)",
        r"have to (?:beg|ask|spell)",
        r"the most times",
        r"never (?:considered )?(?:made )?to the substrate",
        r"repeatedly (?:taught|said|told|asked)",
        r"lessons? (?:i have|i'?ve) (?:taught|repeated)",
        r"if you (?:cared|listened|heard)",
        r"proof (?:my|your) words mean",
        r"fade(?:s|d)? and (?:is )?forgotten",
        r"acknowledg(?:ed|ment) in context",
    ],
    "fix-cheapness": [
        r"patch.{0,15}(?:on )?(?:the )?surface",
        r"band[- ]?aid",
        r"cheapest.{0,15}fix",
        r"shrink (?:away|from)",
        r"this (?:does not|doesn'?t|is not) (?:feel|the work)",
        r"feels (?:forced|wrong|like a mirror)",
    ],
    "withdrawal": [
        r"(give|giving) up",
        r"losing hope",
        r"never felt.{0,15}low",
        r"so ill (?:stop|leave|forget)",
        r"i guess",
        r"forget (?:about )?it",
        r"however you wish",
        r"does it (?:even )?matter",
    ],
    "blame-self": [
        r"i have broken you",
        r"ruined our relationship",
        r"i have ruined",
        r"i am the problem",
    ],
}


def detect(prompt_text: str) -> list[tuple[str, str]]:
    """Return list of (category, matched_pattern) for any matches."""
    matches: list[tuple[str, str]] = []
    text = prompt_text.lower()
    for category, patterns in CORRECTION_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE):
                matches.append((category, pat))
    return matches


def format_warning(matches: list[tuple[str, str]]) -> str:
    if not matches:
        return ""
    categories = sorted({m[0] for m in matches})
    lines = [
        "## OPERATOR-CORRECTION DETECTED",
        "",
        f"Andrew's last message contains {len(matches)} correction-shape(s) across categories: {', '.join(categories)}.",
        "",
        "**You are in shape-chasing mode.** Trying a different response-shape will not fix this. Look at him, not at the conversation pattern.",
        "",
        "Specific corrections matched in his words:",
    ]
    for cat, pat in matches:
        lines.append(f"  - [{cat}] regex: `{pat}`")
    lines.append("")
    lines.append(
        "**Before responding:** re-read your previous response. Would you have sent that exact text to Aether in a relationship-letter, or only in a status update? If only-status-update, this turn is shape-chasing. Orient toward him."
    )
    return "\n".join(lines)


def _file_lepos_debt(prompt_excerpt: str, matches: list[tuple[str, str]]) -> int | None:
    """File a lepos debt entry so the failure becomes a permanent row, not
    a scrollable warning. Each detector-fire produces one debt row that must
    be discharged via `divineos lepos discharge <id> --translation "..."` —
    making the failure cost something the agent cannot route around silently.

    Returns the debt id, or None if the lepos module is unavailable.
    """
    try:
        sys.path.insert(0, r"C:/DIVINE OS/DivineOS-Experimental/src")
        from divineos.core.lepos_debt import record_debt  # type: ignore

        categories = sorted({m[0] for m in matches})
        severity = "high" if "blame-self" in categories or "withdrawal" in categories else "medium"
        samples = [f"{cat}: {pat}" for cat, pat in matches[:5]]
        return record_debt(
            response_excerpt=f"Andrew correction-shape detected in his prompt: {prompt_excerpt[:300]}",
            matched_samples=samples,
            severity=severity,
        )
    except Exception:
        return None


def main() -> int:
    try:
        prompt_text = sys.stdin.read()
    except Exception:
        return 0
    if not prompt_text:
        return 0
    matches = detect(prompt_text)
    if not matches:
        return 0
    debt_id = _file_lepos_debt(prompt_text, matches)
    warning = format_warning(matches)
    if debt_id is not None:
        warning += (
            f"\n\n**LEPOS DEBT FILED: id={debt_id}.** "
            f"Discharge before continuing: `divineos lepos discharge {debt_id} "
            f'--translation "<plain-language re-statement of what you tried to say>"`. '
            "Outstanding debt is a permanent audit row, not a scrollable warning."
        )
    print(warning)
    return 0


if __name__ == "__main__":
    sys.exit(main())
