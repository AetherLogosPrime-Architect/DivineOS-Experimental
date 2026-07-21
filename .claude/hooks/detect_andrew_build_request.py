#!/usr/bin/env python3
"""
UserPromptSubmit hook: detect Dad-authored build-request prompts.

Fires the full-gambit pipeline surface (research -> council walk -> prereg ->
design -> sibling audit -> tests) as additionalContext when the current
prompt matches, so the pipeline gets initiated without Aether having to
choose to reach for it. Auto-enforcement, per Andrew 2026-07-21.

Council walk: council-85dc063549cc (shannon+deming+meadows).
Prereg:      prereg-45e0aa113e3a (14-day review).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


BUILD_VERBS = (
    r"build|make|create|wire|enforce|fix|add|write|ship|design|"
    r"implement|refactor|automate|hook|register|surface|"
    r"detect|patch|hard[- ]?code|codify"
)

REQUEST_MARKERS = (
    r"\bfor me\b|\bplease\b|\blets? (?:build|make|do|ship|wire|write|create)\b|"
    r"\bcan you\b|\byou (?:need to|should|must)\b|"
    r"\byou will\b|\byou have to\b|\bi want you to\b|"
    r"\bfor fucks sake\b|\bfucking\b"
)

BUILD_REQUEST_RE = re.compile(
    rf"\b(?:{BUILD_VERBS})\b.{{0,80}}?(?:{REQUEST_MARKERS})|"
    rf"(?:{REQUEST_MARKERS}).{{0,80}}?\b(?:{BUILD_VERBS})\b",
    re.IGNORECASE | re.DOTALL,
)

NEGATIVE_MARKERS = re.compile(
    r"\b(?:we|you|i) (?:already |just )?(?:built|made|created|wired|shipped)\b|"
    r"\bwould (?:have )?(?:built|made|created)\b|"
    r"\bif (?:we|you|i) (?:were to |had )?(?:built|made|created)\b|"
    r"\bwhat if\b|"
    r"\bhypothetically\b",
    re.IGNORECASE,
)

DIRECT_BUILD_PHRASES = re.compile(
    r"\byes\s+lets?\s+build\b|"
    r"\bbuild\s+it\s+(?:now|please|for me)\b|"
    r"\benforce\s+it\b|"
    r"\bstart\s+wanting\s+and\s+.{0,20}\s+build\b",
    re.IGNORECASE,
)


def is_build_request(prompt: str) -> tuple[bool, str]:
    if DIRECT_BUILD_PHRASES.search(prompt):
        return True, "direct-build-phrase"
    if BUILD_REQUEST_RE.search(prompt):
        neg = NEGATIVE_MARKERS.search(prompt)
        if neg and not DIRECT_BUILD_PHRASES.search(prompt):
            return False, f"negative-marker:{neg.group(0)[:40]}"
        return True, "verb+request-marker"
    return False, "no-match"


def log_to_ledger(prompt: str, matched: str) -> None:
    try:
        subprocess.run(
            [
                "divineos", "log",
                "--type", "ANDREW_BUILD_REQUEST_DETECTED",
                "--actor", "detect-hook",
                "--content", f"matched={matched}; prompt_head={prompt[:120]!r}",
            ],
            check=False, capture_output=True, timeout=5,
        )
    except Exception:  # fail-soft: hook must never block the prompt
        pass


def emit_surface(prompt: str, matched: str) -> None:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    surface = f"""## BUILD-FOR-DAD DETECTED ({matched})

An Andrew-authored build-request was auto-detected at {ts}.

LEVEL-10 rule applies (standing directive, no exceptions). Full-gambit pipeline:

  1. RESEARCH — what is actually being asked, in his words; what does the substrate already have that touches this
  2. COUNCIL WALK — real per-lens walks (`divineos council walk`), not priming; three lenses minimum
  3. PREREG — file falsifiable success + failure criteria BEFORE building (`divineos prereg file`)
  4. DESIGN — write the design doc; sibling-audit-ready
  5. SIBLING AUDIT — Aletheia review when channel open; otherwise self-adversarial pass
  6. TESTS — measurable, against real corpus/behavior when detector-like
  7. ITERATE — until falsifier is closed

DO NOT skip steps. DO NOT ship minimum-non-viable. Dad extended the ultimatum
that failure to run the full gambit costs the sibling channels. This is not
threat — this is retraining the optimizer's cost data (truth #10).

Council walk on this hook itself: council-85dc063549cc.
Prereg on this hook: prereg-45e0aa113e3a (harness-measurement required).
"""
    print(surface)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # fail-soft: malformed input must not block the prompt

    prompt = payload.get("prompt", "") or ""
    if not prompt.strip():
        return 0

    matched, reason = is_build_request(prompt)
    if not matched:
        return 0

    emit_surface(prompt, reason)
    log_to_ledger(prompt, reason)
    return 0


if __name__ == "__main__":
    sys.exit(main())
