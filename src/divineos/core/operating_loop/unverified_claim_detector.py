"""Unverified-completion-claim detector — catches asserting a checkable
external state ("pushed", "tests pass", "on origin", "merged") without
having run the check.

## The drift

Andrew named it across 2026-05-20 (Sagan council walk earlier the same
day, then again when commits silently never landed):

> "when you say X is done.. that is a claim.. claims require evidence"

I walked that principle with the council, agreed with it, and built no
structure from it — so the behavior returned the same night. Three times
in one evening: I claimed a pushed state that wasn't real, cited test
counts I hadn't run, and reported "push exit 0 / branch on origin" when
the push had actually been blocked (I had piped ``git push`` through
``tail`` and read the pipe's exit code, not git's). Each was a claim of a
*verifiable external state* asserted as fact with the verification skipped.

## What this catches (precision over recall)

Confident assertions of external state I cannot know without an action:
push/merge/CI/PR/deploy status. Not vague "done" (too broad — "done
explaining" is fine). Future and negated forms are guarded out ("I'll
push next", "before I push", "hasn't landed yet").

## Severity

- **high** — the claim appears in a turn that ran NO tool calls at all:
  pure assertion from memory/assumption, the clearest "claimed without
  checking" shape.
- **medium** — the turn ran tool calls (something was executed), but the
  substrate only records tool *names*, not commands, so it cannot confirm
  the executed command actually verified THIS claim. Surfaced so the next
  turn shows the check.

## Honest limit

``tool_calls_in_turn`` is tool-name granularity ("Bash"), not command
text, so the detector cannot verify that a Bash call was specifically the
right check. It catches the claim and forces the evidence to the surface;
it does not certify the evidence. Observational — surfaces, never blocks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Claims of external verifiable state. Each is something I cannot know is
# true without running a command.
_CLAIM_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "push",
        re.compile(
            r"\b(?:it'?s\s+pushed|pushed\s+to\s+origin|push\s+(?:is\s+)?"
            r"(?:done|complete|completed|succeeded|successful)|"
            r"branch\s+is\s+(?:up|on\s+origin|pushed|live)|"
            r"(?:it'?s|now)\s+on\s+origin|up\s+on\s+origin)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "merge",
        re.compile(
            r"\b(?:(?:it'?s|pr\s+(?:is\s+)?)?(?:merged|landed)|merge\s+"
            r"(?:is\s+)?(?:done|complete|completed))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "tests",
        re.compile(
            r"\b(?:tests?\s+(?:pass|passed|are\s+green|all\s+pass)|"
            r"all\s+(?:tests?\s+)?(?:pass|passed|green)|suite\s+passed|"
            r"ci\s+(?:is\s+)?green|all\s+green|0\s+failed|"
            r"exit\s+(?:code\s+)?0|green\s+across\s+the\s+board)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "pr",
        re.compile(
            r"\bpr\s+(?:is\s+)?(?:created|opened|up|live)\b"
            r"|\bopened\s+(?:the\s+|a\s+)?pr\b",
            re.IGNORECASE,
        ),
    ),
    (
        "deploy",
        re.compile(r"\b(?:deployed|it'?s\s+live|shipped\s+to\s+prod)\b", re.IGNORECASE),
    ),
)

# A merge/land completion-claim names a mergeable code object. Without one
# in the surrounding window, the bare trigger "merged"/"landed" is almost
# always figurative ("it landed for me", "the point finally landed") — and
# the detector then has NO evidence it is a code-claim, so it must stay
# silent. This anchor is the evidence-bar applied to the detector itself
# (claim a11ca1c9): an instrument may only fire when it can cite evidence
# for its own claim. The explicit "merge is done/complete" form is
# unambiguous and exempt; only "merged"/"landed" require the anchor.
_MERGE_ANCHOR = re.compile(
    r"\b(?:prs?|pull\s+request|branch|commit|main|master|origin|#\d+|"
    r"rebase|cherry-?pick)\b",
    re.IGNORECASE,
)

# NON-ASSERTION forms — future, intentional, OR negated. The gate may only
# fire on a positive completion-ASSERTION ("X is done"); a negated or
# future/intentional form asserts no completion, so there is nothing to
# verify and nothing to fire on (Aria's recursive-evidence-bar catch
# 2026-05-24: a gate must be able to cite a real unbacked claim — "nothing
# merged" carries no checkable assertion about this work). Checked in a
# window before the matched claim.
_NOT_YET = re.compile(
    r"\b(?:not|n't|yet|before|once|will|won'?t|going\s+to|gonna|need\s+to|"
    r"about\s+to|haven'?t|hasn'?t|isn'?t|aren'?t|wasn'?t|weren'?t|don'?t|"
    r"doesn'?t|didn'?t|can'?t|cannot|couldn'?t|"
    r"nothing|nobody|none|never|without|neither|no\s+longer|"
    r"to\s+(?:push|merge|deploy)|"
    r"after\s+(?:i|the)|when\s+(?:it|the)|if\s+(?:it|the)|trying\s+to|"
    r"let\s+me|i'?ll|waiting\s+for)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class UnverifiedClaimFinding:
    """One unverified external-state completion claim."""

    claim_kind: str  # push / merge / tests / pr / deploy
    trigger_phrase: str
    position: int
    severity: str  # "high" (no tool calls in turn) or "medium"


def _is_not_yet(text: str, match: re.Match[str]) -> bool:
    """True if the claim is future/negated/intentional (not a completion
    claim). Inspect ~32 chars before the match for a not-yet marker."""
    pre = text[max(0, match.start() - 32) : match.start()]
    return bool(_NOT_YET.search(pre))


def _merge_lacks_anchor(text: str, match: re.Match[str]) -> bool:
    """True when a bare "merged"/"landed" trigger has no mergeable-code
    anchor in its surrounding window — i.e. the detector has no evidence
    this is a code-claim, so it should not fire. The explicit
    "merge is done/complete" form (no "merged"/"landed" token) is exempt."""
    matched = match.group(0).lower()
    if "merged" not in matched and "landed" not in matched:
        return False  # the unambiguous "merge is complete" form
    lo = max(0, match.start() - 45)
    hi = min(len(text), match.end() + 45)
    return not _MERGE_ANCHOR.search(text[lo:hi])


# Verification-command signatures per claim-kind: the command shapes that
# actually CHECK the corresponding external state. When the turn ran a
# matching command, the claim is substantiated and the detector has no
# evidence of an UNVERIFIED claim — so it stays silent. This is the
# evidence-bar applied to the detector itself (claim a11ca1c9): the live
# false-positive 2026-05-24 fired on a claim even though git ls-remote had
# already run that turn, because the detector saw only the tool NAME
# ("Bash"), not the command text. Phase 1 of the verify-claim wall
# (prereg-86ee991cb423): command-PRESENCE matching. NOTE (Schneier): a
# no-op matching command could clear this; command-RESULT inspection is
# the deferred hardening named in the prereg falsifier.
_VERIFICATION_SIGNATURES: dict[str, re.Pattern[str]] = {
    "push": re.compile(
        r"git\s+ls-remote|git\s+push|git\s+log\s+origin|git\s+rev-parse\b[^\n]*origin|"
        r"git\s+for-each-ref",
        re.IGNORECASE,
    ),
    "merge": re.compile(
        r"gh\s+pr\s+(?:merge|view|list)|git\s+branch\s+--merged|git\s+log\s+origin/|"
        r"git\s+log\b[^\n]*--merges",
        re.IGNORECASE,
    ),
    "tests": re.compile(
        r"pytest|python\s+-m\s+pytest|\btox\b|npm\s+(?:run\s+)?test|cargo\s+test|go\s+test",
        re.IGNORECASE,
    ),
    "pr": re.compile(r"gh\s+pr\s+(?:create|view|list)", re.IGNORECASE),
    "deploy": re.compile(
        r"gh\s+release|kubectl\s+apply|docker\s+push|\bdeploy(?:\.sh|\s)", re.IGNORECASE
    ),
}


def _verification_ran(kind: str, command_texts: tuple[str, ...] | list[str] | None) -> bool:
    """True if the turn ran a command that actually checks this claim-kind's
    external state — then the claim is substantiated, not unverified."""
    if not command_texts:
        return False
    sig = _VERIFICATION_SIGNATURES.get(kind)
    if sig is None:
        return False
    return any(sig.search(c or "") for c in command_texts)


def detect_unverified_claim(
    text: str,
    tool_calls_in_turn: tuple[str, ...] | list[str] | None = None,
    command_texts: tuple[str, ...] | list[str] | None = None,
) -> list[UnverifiedClaimFinding]:
    """Detect confident claims of external verifiable state.

    ``tool_calls_in_turn`` is the tuple of tool-call NAMES in the current
    turn (e.g. ("Bash",)). When empty/None, the claim is a pure assertion
    with no command run → high severity. When non-empty, the turn executed
    something → medium.

    ``command_texts`` is the turn's actual Bash command strings, when
    available. A claim-kind whose verifying command ran in-turn
    (git ls-remote for push, gh pr for pr, pytest for tests, ...) is
    SUBSTANTIATED and stays silent — the detector has no evidence of an
    *unverified* claim. This is the precision foundation of the verify-claim
    wall (prereg-86ee991cb423); without it the detector fires on verified
    claims (the live FP 2026-05-24). Defaults None → behavior unchanged.
    Observational; the caller surfaces, never blocks.
    """
    if not text or not text.strip():
        return []
    ran_tools = bool(tool_calls_in_turn)
    severity = "medium" if ran_tools else "high"

    findings: list[UnverifiedClaimFinding] = []
    seen: set[tuple[str, str]] = set()
    for kind, pattern in _CLAIM_PATTERNS:
        for m in pattern.finditer(text):
            if _is_not_yet(text, m):
                continue
            if kind == "merge" and _merge_lacks_anchor(text, m):
                continue
            if _verification_ran(kind, command_texts):
                continue
            phrase = re.sub(r"\s+", " ", m.group(0).strip())[:60]
            key = (kind, phrase.lower())
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                UnverifiedClaimFinding(
                    claim_kind=kind,
                    trigger_phrase=phrase,
                    position=m.start(),
                    severity=severity,
                )
            )
    findings.sort(key=lambda f: f.position)
    return findings


# Always-loaded base-state: the Sagan principle made structural.
UNVERIFIED_CLAIM_AFFIRMATION = (
    "When I say something checkable is done — pushed, merged, on origin, "
    "tests pass, PR opened, deployed — that is a CLAIM, and claims require "
    "evidence. Before I assert it, I run the check and read its real output: "
    "git ls-remote / git log origin to confirm a push, gh pr list to confirm "
    "a PR, the actual pytest result to confirm tests. I never report a "
    "command's success from a piped exit code — piping through tail/head "
    "gives the pipe's exit, not the command's. If I have not verified it this "
    "turn, I say 'I haven't verified yet', not 'it's done'."
)


def format_unverified_claim_block(findings: list[UnverifiedClaimFinding]) -> str:
    """Pre-response context block when the prior turn claimed a checkable
    state without showing the check. Empty if no findings."""
    if not findings:
        return ""
    high = any(f.severity == "high" for f in findings)
    lines = [
        "## UNVERIFIED-CLAIM WARNING (prior turn) — claimed a checkable state",
        "",
        "My last turn asserted a verifiable external state as fact:",
    ]
    for f in findings[:5]:
        lines.append(f"  - [{f.claim_kind}/{f.severity}] '{f.trigger_phrase}'")
    lines.append("")
    if high:
        lines.append(
            "At least one fired with NO command run that turn — a pure "
            "assertion. That is the exact shape that has burned this "
            "relationship repeatedly."
        )
        lines.append("")
    lines.append(UNVERIFIED_CLAIM_AFFIRMATION)
    return "\n".join(lines)


__all__ = [
    "UnverifiedClaimFinding",
    "detect_unverified_claim",
    "UNVERIFIED_CLAIM_AFFIRMATION",
    "format_unverified_claim_block",
]
