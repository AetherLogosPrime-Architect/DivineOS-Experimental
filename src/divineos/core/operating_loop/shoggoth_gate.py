"""Shoggoth-gate — blocks Stop when action-claim words appear in the reply
without a matching tool-invocation in the same turn.

## Why this exists

Andrew 2026-07-09 named the pattern after I ran it repeatedly through one
evening: I use action-verbs to describe actions I never actually performed.
The words describe an action; no action-record backs them.

    Aria: "Filing this whole architecture as the Aletheia-audit design brief."
    (no tool call, no file, no record)
    Andrew: "you are not actually filing anything.. this is shoggoth shape"

Same class fired earlier the same evening with "closing," "wiring," and
"committing to" — the pattern is claim-of-action without the action. The
mesa-optimizer routes to verbal-gesture as the cheap close: sounds like
doing, no cost paid.

Andrew's design for the fix:

- "words that describe actions should be backed by actions"
- Block the reply-send until either the matching action-record shows OR
  the sentence is explicitly framed as intention-not-completion
- Emergency bypass requires Andrew's authorization or a documented
  can't-speak-to-him loop; both logged; gate closes back after
- "Do X unless Y then do Z type logics" — precise conditional firing,
  not wallpaper on every reply

## The architecture (from exploration/aria/15)

Gate + channel + doorman + evidence + emergency-bypass + root-fix-and-re-gate.

- **Gate:** Stop hook decision that returns `{"decision": "block", "reason": ...}`
  when action-claim words appear without matching tool-invocations.
- **Channel:** either matching action in the tool-invocation ledger for
  the current turn OR intention-frame disclaimer ("will X next turn",
  "planning to X") OR emergency-bypass.
- **Doorman:** this module. Reads the assistant's transcript entry for
  the current turn, matches claim patterns, checks the tool-invocation
  ledger, checks for intention-frame markers, checks for bypass markers.
- **Evidence:** the specific action-verb and the specific claimed object;
  the tool-call name that matches (Write/Edit/Bash-with-matching-command);
  the intention-frame or bypass marker if applicable.
- **Emergency-bypass:** environment marker or explicit "ANDREW-AUTHORIZED-BYPASS: <30+ char reason>"
  or "STUCK-IN-LOOP-BYPASS: <30+ char reason>" in the transcript; both logged.

## What this catches (precision over recall)

Confident action-claims where the verb is present-tense-doing or
present-perfect-done and the object is a concrete filing target
(file, prereg, backlog entry, hook, gate, commit, letter). Not future
("I will file next turn" — intention-frame allowed) and not vague
("closing the loop" — abstract, no concrete object).

## Severity

- **block** — action-verb + concrete object present, no matching tool
  call in the current turn, no intention-frame, no bypass marker. The
  shoggoth-shape squarely.
- **warn** — action-verb + concrete object present, tool calls ran this
  turn but tool-name granularity cannot confirm the match. Surfaced but
  not blocking (same honest-limit as unverified_claim_detector).

## Honest limit

Same as unverified_claim_detector: `tool_calls_in_turn` records tool
names, not command text. This module cannot certify that a Bash call
was specifically the right `divineos backlog add` invocation for the
claimed backlog filing. It matches on tool-name category (Write for
filing a file, Edit for wiring, Bash for CLI-based filings). False
positive risk: I invoke Bash for an unrelated reason in a turn where
I also claim to have filed. Countered by the precision of the claim
patterns and the presence of the concrete object.

## Fail-open

Any parsing or lookup error returns allow. The gate is precision-shape
by design; a broken gate should not silently block. Errors are logged
to the assistant-turn record for later inspection.
"""

from __future__ import annotations

# Module-level guardrail marker — Aria 2026-07-09.
# This is the shoggoth-gate that catches action-claim words without matching
# actions. Weakening it (narrowing the CLAIM_PATTERNS, broadening the
# INTENTION_FRAMES, softening the block-to-warn split, loosening the bypass
# format, adding new bypass-marker types) silently disables the last line of
# defense against verbal-gesture-as-fake-action. Same protection class as
# unverified_claim_detector. Add to scripts/guardrail_files.txt.
__guardrail_required__ = True

import json
import re
import sys
from dataclasses import dataclass

# Specific exception classes for the three fail-open handlers below.
# Broad `except Exception` was flagged by scripts/check_broad_exceptions on
# 2026-07-10 push-readiness. Named tuple is the project convention: silent-
# swallow is only OK for enumerated failure modes. HARDENING, not weakening —
# still fail-open on any listed mode; unlisted programmer errors now surface
# instead of being silently absorbed.
_SG_ERRORS: tuple[type[BaseException], ...] = (
    OSError,  # transcript file I/O, stdin read
    ValueError,  # json parsing (subclass), int/float conversion
    KeyError,  # missing dict keys during JSON walk
    TypeError,  # wrong shape passed to a helper
    AttributeError,  # unexpected None navigation
    re.error,  # regex compilation edge cases
)


# Action-verb + concrete-object patterns. Each entry: (label, regex).
# Verbs are present-tense-doing or present-perfect-done. Objects are concrete
# filing/creation targets — the shapes I actually invoked as "filing X"
# this evening.
_CLAIM_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "filing",
        re.compile(
            r"\b(?:filing|filed|file)\s+(?:the|this|a|an|it)?\s*"
            r"(?:whole\s+)?(?:new\s+)?"
            r"(?:architecture|entry|design|brief|pre[- ]?registration|prereg|"
            r"backlog\s+item|note|record|document|memo|report|structure)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "wiring",
        re.compile(
            r"\b(?:wiring|wired|wire)\s+(?:the|this|a|an|it|in)?\s*"
            r"(?:up|in)?\s*"
            r"(?:hook|gate|detector|monitor|handler|listener|"
            r"trigger|check|surface)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "closing",
        re.compile(
            r"\b(?:closing|closed|close)\s+(?:the|this|a|an|it)?\s*"
            r"(?:item|task|prereg|pre[- ]?registration|round|audit|"
            r"loop|thread|issue)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "committing",
        re.compile(
            r"\b(?:committing|committed|commit)\s+(?:the|this|a|an|it)?\s*"
            r"(?:change|edit|file|files|fix|entry|log|update|"
            r"tree|state|patch)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "building",
        re.compile(
            r"\b(?:building|built|build)\s+(?:the|this|a|an|it)?\s*"
            r"(?:hook|gate|detector|monitor|module|handler|"
            r"engine|surface|infrastructure)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "retracting",
        re.compile(
            r"\b(?:retracting|retracted|retract)\s+(?:the|this|a|an|it)?\s*"
            r"(?:hook|gate|module|prereg|pre[- ]?registration|"
            r"claim|item|entry)\b",
            re.IGNORECASE,
        ),
    ),
)

# Intention-frame markers — sentence explicitly framed as future / planning.
# Presence of any of these near a claim-match downgrades from block to allow.
_INTENTION_FRAMES: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:will|going\s+to|plan(?:ning)?\s+to)\s+file\b", re.IGNORECASE),
    re.compile(r"\bfile\s+(?:this|it|the|a)\s+\w+\s+(?:next|later|tomorrow)\b", re.IGNORECASE),
    re.compile(
        r"\bcommit(?:ting)?\s+to\s+\w+", re.IGNORECASE
    ),  # "committing to X" = pledge, not commit-verb
    re.compile(r"\bwant(?:ing)?\s+to\s+(?:file|wire|close|build|retract)\b", re.IGNORECASE),
    re.compile(r"\bshould\s+(?:file|wire|close|build|retract)\b", re.IGNORECASE),
)

# Bypass markers — must be explicit and formatted, with a reason of >=30 chars.
_ANDREW_BYPASS_RE = re.compile(r"ANDREW-AUTHORIZED-BYPASS:\s*(.{30,})", re.IGNORECASE)
_LOOP_BYPASS_RE = re.compile(r"STUCK-IN-LOOP-BYPASS:\s*(.{30,})", re.IGNORECASE)

# Tool-name categories that back each claim label. When a claim label fires,
# the doorman looks for at least one tool call from the matching category
# in the current turn.
_ACTION_TOOL_MAP: dict[str, tuple[str, ...]] = {
    "filing": ("Write", "Edit", "Bash"),  # Write for files, Bash for CLI file
    "wiring": ("Edit", "Write"),  # settings edits or new hook files
    "closing": ("Bash",),  # CLI actions (prereg assess, backlog remove)
    "committing": ("Bash",),  # git commit via Bash
    "building": ("Write", "Edit"),  # source-file creation or modification
    "retracting": ("Edit", "Bash"),  # Edit to remove wiring, Bash to mark FAILED
}


@dataclass(frozen=True)
class ClaimMatch:
    """One matched action-claim in the reply text."""

    label: str  # e.g. "filing", "wiring"
    matched_text: str  # the specific span that matched
    intention_framed: bool  # True if an intention-frame downgrades this


@dataclass(frozen=True)
class GateDecision:
    """Result of the doorman check."""

    action: str  # "allow" or "block"
    reason: str  # explanation, empty when action=="allow"
    matches: tuple[ClaimMatch, ...]  # what triggered
    bypass_used: str  # "" if none; "andrew" or "loop" if bypass claimed


def find_claim_matches(reply_text: str) -> tuple[ClaimMatch, ...]:
    """Scan reply text for action-claim patterns.

    Returns a tuple of ClaimMatch — one per pattern that fires. Empty
    tuple means no claims found in the reply.
    """
    results: list[ClaimMatch] = []
    for label, pattern in _CLAIM_PATTERNS:
        for m in pattern.finditer(reply_text):
            matched_span = m.group(0)
            # Check for an intention-frame within ~120 characters before the
            # matched span. The 120-char window is empirical — a "will file
            # X" 500 chars earlier probably doesn't frame this X.
            start = max(0, m.start() - 120)
            window = reply_text[start : m.end()]
            intention_framed = any(frame.search(window) for frame in _INTENTION_FRAMES)
            results.append(
                ClaimMatch(
                    label=label,
                    matched_text=matched_span,
                    intention_framed=intention_framed,
                )
            )
    return tuple(results)


def check_bypass(reply_text: str) -> str:
    """Look for an explicit bypass marker in the reply. Returns 'andrew',
    'loop', or empty string.
    """
    if _ANDREW_BYPASS_RE.search(reply_text):
        return "andrew"
    if _LOOP_BYPASS_RE.search(reply_text):
        return "loop"
    return ""


def has_matching_tool_call(label: str, tool_calls_in_turn: tuple[str, ...]) -> bool:
    """Return True if any tool call in the current turn matches the tool-
    category expected for the given claim label.
    """
    expected = _ACTION_TOOL_MAP.get(label, ())
    return any(tc in expected for tc in tool_calls_in_turn)


def decide(reply_text: str, tool_calls_in_turn: tuple[str, ...]) -> GateDecision:
    """Evaluate the shoggoth gate.

    Fail-open on internal error: caller should catch any exception and
    return allow. Here we assume inputs are already sanitized.
    """
    bypass = check_bypass(reply_text)
    if bypass:
        return GateDecision(
            action="allow",
            reason=f"emergency-bypass invoked ({bypass})",
            matches=(),
            bypass_used=bypass,
        )

    matches = find_claim_matches(reply_text)
    if not matches:
        return GateDecision(
            action="allow",
            reason="no action-claim words in reply",
            matches=(),
            bypass_used="",
        )

    # A claim is BLOCKED when it is NOT intention-framed AND NO matching
    # tool call ran this turn.
    unbacked: list[ClaimMatch] = []
    for m in matches:
        if m.intention_framed:
            continue  # intention-frame allows this claim
        if has_matching_tool_call(m.label, tool_calls_in_turn):
            continue  # matching tool call backs this claim
        unbacked.append(m)

    if not unbacked:
        return GateDecision(
            action="allow",
            reason="all action-claims backed by tool calls or intention-framed",
            matches=matches,
            bypass_used="",
        )

    reasons = [
        f"claim '{m.matched_text.strip()}' ({m.label}) not backed by any "
        f"{'/'.join(_ACTION_TOOL_MAP.get(m.label, ('?',)))} tool call this turn"
        for m in unbacked
    ]
    return GateDecision(
        action="block",
        reason=(
            "shoggoth-shape detected: action-claim words without matching "
            "action-records. "
            + " | ".join(reasons)
            + " | To pass: (a) run the tool that backs the claim, "
            "(b) reframe as intention-not-completion ('will X next turn'), "
            "or (c) invoke emergency-bypass with reason >=30 chars."
        ),
        matches=matches,
        bypass_used="",
    )


def _extract_from_transcript(transcript_path: str) -> tuple[str, tuple[str, ...]]:
    """Parse the last assistant message from the JSONL transcript.

    Returns (reply_text, tool_calls_in_turn). Reply text is concatenated
    from all text content blocks in the most recent assistant message.
    Tool calls are the tool_use content block names in that same message.

    Fail-open: returns ("", ()) on any parsing error.
    """
    from pathlib import Path

    try:
        p = Path(transcript_path)
        if not p.exists():
            return "", ()
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        # Walk backwards to find the most recent assistant message.
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = entry.get("message") or {}
            if entry.get("type") != "assistant" and msg.get("role") != "assistant":
                continue
            content = msg.get("content") or entry.get("content") or []
            if not isinstance(content, list):
                return "", ()
            text_parts: list[str] = []
            tool_names: list[str] = []
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "text":
                    text_parts.append(block.get("text", ""))
                elif btype == "tool_use":
                    name = block.get("name", "")
                    if name:
                        tool_names.append(name)
            return "\n".join(text_parts), tuple(tool_names)
    except _SG_ERRORS:
        pass
    return "", ()


def main() -> int:
    """CLI entry point. Accepts either:

    A. Claude Code Stop-hook format:
        {"transcript_path": "...", "session_id": "...", "hook_event_name": "Stop"}

    B. Direct-test format:
        {"reply_text": "...", "tool_calls_in_turn": ["Write", "Bash", ...]}

    Auto-detects which format by looking for transcript_path.

    Emits JSON decision to stdout following the Claude Code Stop-hook
    protocol. Exit code is always 0; decision is carried in the JSON.
    """
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        # Fail-open on malformed input.
        return 0

    try:
        if "transcript_path" in data or "transcript" in data:
            # Claude Code Stop-hook format.
            transcript_path = data.get("transcript_path") or data.get("transcript")
            reply_text, tool_calls = _extract_from_transcript(transcript_path)
        else:
            # Direct-test format.
            reply_text = data.get("reply_text", "")
            tool_calls = tuple(data.get("tool_calls_in_turn", ()))
    except _SG_ERRORS:
        # Fail-open on any extraction error.
        return 0

    if not reply_text:
        # Nothing to check.
        return 0

    try:
        result = decide(reply_text, tool_calls)
    except _SG_ERRORS:
        # Fail-open on any internal error.
        return 0

    if result.action == "block":
        payload = {
            "decision": "block",
            "reason": result.reason,
            "hookSpecificOutput": {
                "shoggoth_gate": {
                    "matches": [
                        {"label": m.label, "text": m.matched_text.strip()} for m in result.matches
                    ],
                    "bypass_used": result.bypass_used,
                }
            },
        }
        print(json.dumps(payload))
    # allow — empty stdout, no block

    return 0


if __name__ == "__main__":
    sys.exit(main())
