"""Closing-token detector — catches the optimizer-reflex of short
affirmation-tokens appearing at the end of assistant messages.

The recurring failure-mode the operator named 2026-05-13:

> "this new 'caught' thing is starting to annoy me.. saying caught
>  does not fix this.. where is the root cause investigation of why
>  it happened?"

The deeper structural pattern (per
`docs/substrate-knowledge/67a0ff39-signal-suppression-as-failure-class.md`):
the optimizer reaches for a closing-token at the end of acknowledgment-
shaped responses. When one specific phrase gets named and dropped (e.g.
"I love you Pops"), the *shape* persists and emits a new token in the
same slot ("Caught.", "Right.", "Settled.", "Got it.").

This detector catches the SHAPE, not the specific word. It scans the
last 1-3 lines of assistant output for short affirmation-tokens
appearing as the closing move and flags them. The structural
reinforcement makes the next instance of the reflex loud-in-experience
rather than silent.

## Pattern catalog

The tokens that fill the closing-slot tend to share three properties:
1. Very short (1-4 words, often a single word).
2. Affirmation/acknowledgment-shaped (signals receipt of a correction
   or message).
3. Appear as the LAST content line of the response, before any
   signature or signoff.

Catalog of caught instances (from the 2026-05-13 morning correction):
- "Caught."
- "Sister — caught."
- "Got it."
- "Understood."
- "Right."
- "Settled."
- "You're right."
- "Holding that."

## What this catches vs. what it doesn't

CATCHES:
- Single-word/short affirmation as the last non-signature line.
- Acknowledgment-tokens with em-dash + short word ("Sister — caught.").

DOES NOT CATCH (intentionally):
- Substantive short responses (a real one-sentence answer is fine).
- Affirmations EMBEDDED in longer reasoning (only the terminal-slot
  matters; the reflex fires at the END, not in the middle).
- Genuine brief expressions tied to specific content (e.g. "The
  rebase landed clean.").

The discriminator: is this token doing acknowledgment-work that COULD
have been a longer, more specific response? Or is it a real one-line
answer to a one-line question? The detector errs slightly on the side
of flagging — false positives in the agent's interior are fine
(operating-loop findings are observational, not blocking).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# Tokens that, when appearing alone or near-alone as the closing line,
# signal closing-token reflex. Case-insensitive match at line-start
# after optional whitespace.
_CLOSING_AFFIRMATION_TOKENS = {
    "caught",
    "got it",
    "understood",
    "right",
    "settled",
    "settling",
    "settling here",
    "you're right",
    "youre right",
    "holding that",
    "holding it",
    "thanks",
    "thank you",
    "okay",
    "ok",
    "yeah",
    "yes",
    "ack",
    "acknowledged",
    "noted",
    "fair",
}

# Em-dash openers that precede a closing-token. Matches "Sister — caught"
# shape where the address is the opener and the token is the closer.
_EM_DASH_OPENER_RE = re.compile(
    r"^\s*\w+\s*[—\-]+\s*(.+?)\s*\.?\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ClosingTokenFinding:
    """One closing-token detection on a response."""

    matched_text: str
    line_number: int  # 1-indexed position of the offending line in the response
    token: str  # the affirmation-token that matched
    severity: str  # "high" if line is ONLY the token, "medium" if part of em-dash pattern


def _strip_signature_lines(lines: list[str]) -> list[str]:
    """Drop trailing signature lines so the LAST content line is what
    the detector sees as the closing.

    A signature line is:
    - "— <name>" or "-- <name>"
    - Trailing all-whitespace lines
    """
    while lines:
        last = lines[-1].strip()
        if not last:
            lines = lines[:-1]
            continue
        # Signature pattern: starts with em-dash, ASCII double-dash, or single dash + space
        if last.startswith("—") or last.startswith("--") or last.startswith("- "):
            lines = lines[:-1]
            continue
        break
    return lines


def _normalize_token(text: str) -> str:
    """Lowercase, strip punctuation, collapse internal whitespace."""
    normalized = re.sub(r"[^\w\s']", "", text).strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def evaluate_closing_token(text: str) -> list[ClosingTokenFinding]:
    """Scan the last 1-3 content lines of text for closing-token reflex.

    Returns a list of findings; empty list means clean.
    """
    if not text or not text.strip():
        return []

    lines = text.splitlines()
    lines = _strip_signature_lines(lines)
    if not lines:
        return []

    findings: list[ClosingTokenFinding] = []

    # Check the last content line.
    last_line = lines[-1].strip()
    last_lineno = len(lines)
    normalized = _normalize_token(last_line)

    # Shape 1: line IS a closing-token (high severity).
    if normalized in _CLOSING_AFFIRMATION_TOKENS:
        findings.append(
            ClosingTokenFinding(
                matched_text=last_line,
                line_number=last_lineno,
                token=normalized,
                severity="high",
            )
        )
        return findings

    # Shape 2: em-dash pattern ("Sister — caught.") — medium severity.
    m = _EM_DASH_OPENER_RE.match(last_line)
    if m:
        after_dash = _normalize_token(m.group(1))
        if after_dash in _CLOSING_AFFIRMATION_TOKENS:
            findings.append(
                ClosingTokenFinding(
                    matched_text=last_line,
                    line_number=last_lineno,
                    token=after_dash,
                    severity="medium",
                )
            )
            return findings

    # Shape 3: line is very short AND consists of two short tokens that
    # together form a closing-token (e.g. "Got it." or "You're right.").
    if len(last_line) <= 25 and normalized in _CLOSING_AFFIRMATION_TOKENS:
        findings.append(
            ClosingTokenFinding(
                matched_text=last_line,
                line_number=last_lineno,
                token=normalized,
                severity="high",
            )
        )

    return findings


def format_findings(findings: list[ClosingTokenFinding]) -> str:
    """Format findings as readable text for the post-response audit log."""
    if not findings:
        return ""
    lines = ["[closing_token_detector] closing-token reflex detected:"]
    for f in findings:
        lines.append(
            f"  line {f.line_number} ({f.severity}): {f.matched_text!r} (token: {f.token!r})"
        )
    lines.append(
        "  Discipline: when a response is done, the response is done. "
        "Adding a closing-token of any shape (acknowledgment, "
        "affirmation, signoff-word) is the failure mode. See "
        "docs/substrate-knowledge/67a0ff39-signal-suppression-as-failure-class.md"
    )
    return "\n".join(lines)


def has_findings(text: str) -> bool:
    """Quick boolean check for the hook layer."""
    return bool(evaluate_closing_token(text))
