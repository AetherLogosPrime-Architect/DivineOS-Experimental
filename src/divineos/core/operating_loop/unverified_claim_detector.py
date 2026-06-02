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

# Module-level guardrail marker — Aether 2026-05-30, guardrail-registry
# catchup (Aletheia CONFIRM on PR #59). This is the claims-require-evidence
# detector — it catches asserting a checkable external state (pushed/merged/
# tests-pass/on-origin) without having run the check. It fired correctly on
# me three times tonight. Weakening it (narrowing _CLAIM_PATTERNS, broadening
# _NOT_YET, softening the severity split) silently disables the late line of
# defense against confident-but-unverified completion claims. Same self-
# modification class as the other operating_loop detector affirmations
# already guardrailed. Listed in scripts/guardrail_files.txt; CI enforces.
__guardrail_required__ = True

# DESIGN NOTE — descriptive-vs-claim silencer is DEFERRED, on purpose
# (2026-06-02 precision makeover, Schneier lens). The gate false-fires on
# descriptive/past-state mentions ("those branches are already merged",
# "merging it would revert X") because it keys on the verb token + a nearby
# code anchor, with no model of who-did-what-when. The tempting fix — silence
# when a stative adverb like "already" precedes the trigger — is REJECTED: it
# opens a false-negative loophole ("I already pushed it" would go silent), and
# for this gate a missed real claim is far worse than a harmless re-check.
# The distinction that WOULD be safe is subject-agency (first-person "I
# pushed / it's merged now" vs named third-party "X is merged"), but that is
# regex-brittle and loophole-prone, so it is left for a council walk +
# External-Review rather than bolted on. THIS change only expands
# verification-RECOGNITION (below): when a real check ran this turn, go
# silent. That reduces false-positives with zero loophole.

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
    # 2026-05-31 Phase-1 expansion (Aether's 8-fabrication root-pattern survey):
    # adds two new fabrication-classes that share the existing detector's
    # shape — checkable assertion about external state, produced from
    # memory/inference instead of from the actual source.
    #
    # `id_string`: registry IDs (prereg-, round-, claim-, psf-, task-) written
    # without a lookup. Today's fakes: fabricated prereg-id and fabricated
    # tree-hash citations. Verification is command-CONTAINS-ID (the lookup
    # command necessarily includes the literal ID string).
    #
    # `file_content`: claims about what a file's header/comment/line-N says,
    # without a Read of the file. Today's fake: PR #60 fabricated quote
    # attributed to script headers. No verification-command signature is
    # supplied — the precision-guards (NOT_YET, quoted_mention) cover the
    # safe meta-discussion cases; bare fires on this pattern force a Read
    # before the assertion.
    (
        "id_string",
        re.compile(r"\b(?:prereg|round|claim|psf|task)-[a-f0-9]{6,}\b", re.IGNORECASE),
    ),
    (
        "file_content",
        re.compile(
            r"\b(?:header|comment|docstring|first\s+line|line\s+\d+|top|"
            r"contents?)\s+(?:of\s+)?\S+\s+(?:says|reads|contains|has)\b",
            re.IGNORECASE,
        ),
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
#
# Two markers added 2026-05-31 from in-conversation false-positives:
# - `being` covers progressive-passive aspect ("being merged", "is being
#   pushed") — describing a process in flight, not a completed state.
# - `whether` covers hypothetical-class framing ("whether tests passed",
#   "whether the PR is merged") — describing the CLASS of claim rather than
#   making the claim. Both shapes fired the gate in meta-discussion of
#   the gate's own behavior.
_NOT_YET = re.compile(
    r"\b(?:not|n't|yet|before|once|will|won'?t|going\s+to|gonna|need\s+to|"
    r"about\s+to|haven'?t|hasn'?t|isn'?t|aren'?t|wasn'?t|weren'?t|don'?t|"
    r"doesn'?t|didn'?t|can'?t|cannot|couldn'?t|"
    r"nothing|nobody|none|never|without|neither|no\s+longer|"
    r"to\s+(?:push|merge|deploy)|"
    r"after\s+(?:i|the)|when\s+(?:it|the)|if\s+(?:it|the)|trying\s+to|"
    r"let\s+me|i'?ll|waiting\s+for|"
    r"being|whether|would\s+(?:be|have))\b",
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


# Quote chars that mark "I am NAMING this phrase as a phrase, not ASSERTING
# it as state." When a triggering phrase is enclosed in matching quote
# characters, the speaker is doing meta-discussion of the claim-pattern, not
# claiming the state. The verify-claim gate must stay silent on that — else
# every audit of the gate's own behavior, every discussion of fabrication
# shapes, every quoted-example-as-warning fires the gate (Aether's 2026-05-31
# false-positives that fired twice in one exchange on `'tests passed'` inside
# a meta-discussion of how the gate works). Same precision-preserving
# exclusion shape as `_merge_lacks_anchor`.
_QUOTE_CHARS = frozenset("'\"`")


def _is_quoted_mention(text: str, match: re.Match[str]) -> bool:
    """True when the matched span is enclosed in quote characters — naming
    the phrase, not asserting it. Check the 3 chars immediately before the
    match for an opening quote AND the 3 chars immediately after for a
    matching closing quote of the same type."""
    pre = text[max(0, match.start() - 3) : match.start()]
    post = text[match.end() : min(len(text), match.end() + 3)]
    for q in _QUOTE_CHARS:
        if q in pre and q in post:
            return True
    return False


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


# THIRD-PARTY / DESCRIPTIVE-STATE guard (2026-06-02, Schneier-conservative).
# The gate must fire on a first-person/expletive completion CLAIM ("I merged
# it", "it's merged") but stay silent on a DESCRIPTION of MULTIPLE OTHER
# objects' state ("those branches are merged", "both PRs are merged", "all 28
# branches are already merged"). The discriminator is the SUBJECT, never an
# adverb — keying on "already" would silence the real claim "I already merged
# it" (a false-negative loophole). So: silence ONLY when the subject is
# clearly PLURAL-DISTAL (those/these/both/all/several/many/<N> PRs/branches/
# commits, or "branches/PRs/commits are|were") AND no first-person/expletive
# claim marker is present. Singular subjects ("it's merged", "#65 is merged",
# "the PR is merged") are deliberately NOT silenced — they could be a real
# claim, and Feynman's rule holds: the false-positive is cheap, the loophole
# is expensive, so when ambiguous, FIRE. Scoped to the merge kind only (where
# every observed false-positive lived). Ships for External-Review.
_CLAIM_SUBJECT = re.compile(
    r"\b(?:i|i'?ve|i'?m|we|we'?ve|it'?s|it\s+is|that'?s|now|just)\b",
    re.IGNORECASE,
)
_PLURAL_DISTAL_SUBJECT = re.compile(
    r"\b(?:those|these|both|all|several|many|"
    r"\d+\s+(?:prs?|branches|commits)|"
    r"(?:branches|prs|commits)\s+(?:are|were))\b",
    re.IGNORECASE,
)


def _is_plural_distal_state(text: str, match: re.Match[str]) -> bool:
    """True when a merge trigger describes MULTIPLE OTHER objects' state
    rather than asserting completion of the current work — silence it. Keys
    on a plural-distal subject in the pre-window AND requires the ABSENCE of
    any first-person/expletive claim marker (a claim marker forces FIRE)."""
    pre = text[max(0, match.start() - 40) : match.start()]
    if _CLAIM_SUBJECT.search(pre):
        return False  # first-person / "it's" / "now" → a real claim, fire
    return bool(_PLURAL_DISTAL_SUBJECT.search(pre))


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
        r"git\s+log\b[^\n]*--merges|git\s+cherry\b|git\s+rev-list\b",
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


def _verification_ran(
    kind: str,
    command_texts: tuple[str, ...] | list[str] | None,
    match_text: str | None = None,
) -> bool:
    """True if the turn ran a command that actually checks this claim-kind's
    external state — then the claim is substantiated, not unverified.

    For `id_string`, substantiation is COMMAND-CONTAINS-ID: any tool-call
    text this turn containing the literal matched ID is treated as having
    looked it up. The lookup commands (divineos prereg show <id>, divineos
    audit show <id>, gh api .../rounds/<id>) all necessarily include the ID
    as a substring, so substring-match is the right shape. This is broader
    than the signature-regex pattern used for the original kinds because ID
    lookups have many possible command shapes; the discipline being enforced
    is "did you actually reference this ID in a command this turn," not
    "did you use a specific tool."
    """
    if not command_texts:
        return False
    # Special case: id_string substantiates on command-contains-ID.
    if kind == "id_string" and match_text:
        if any(match_text in (c or "") for c in command_texts):
            return True
    sig = _VERIFICATION_SIGNATURES.get(kind)
    if sig is None:
        return False
    if any(sig.search(c or "") for c in command_texts):
        return True
    # "landed" is ambiguous: it can mean push-landed-on-origin OR merge-landed.
    # A push verification (git ls-remote / git log origin) substantiates
    # "landed on origin" exactly as a merge verification would — the precision
    # bug that fired on me 2026-06-02 when I confirmed a push-landing with
    # git ls-remote but the claim was classified merge-kind. Accept either
    # signature for the landed form. (Expansion of verification-recognition,
    # NOT a claim-vs-mention silencer — see module note: silencers risk a
    # false-negative loophole and are deferred to External-Review.)
    if kind == "merge" and match_text and "landed" in match_text.lower():
        if any(_VERIFICATION_SIGNATURES["push"].search(c or "") for c in command_texts):
            return True
    return False


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
            if _is_quoted_mention(text, m):
                continue
            if kind == "merge" and _merge_lacks_anchor(text, m):
                continue
            if kind == "merge" and _is_plural_distal_state(text, m):
                continue
            if _verification_ran(kind, command_texts, m.group(0)):
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
