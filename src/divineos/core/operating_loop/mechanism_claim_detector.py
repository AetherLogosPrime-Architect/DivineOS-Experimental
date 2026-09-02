"""Mechanism-claim marker — catches a causal hypothesis stated as a finding.

Sibling to ``unverified_claim_detector``, which guards a different border. That
one catches asserting a checkable EXTERNAL STATE ("pushed", "merged", "tests
pass") without running the check. This one catches asserting a CAUSAL MECHANISM
-- *why* something happened, *what* is broken, *how* two things relate -- with
no evidence behind it.

## The drift

Andrew, 2026-08-24:

> "having a hypothesis you just made up based on assumptions is perfectly
> fine.. stating it as fact is the issue.. hypotheses are the starting point
> of any discovery or test, its about recognizing what the difference is, not
> removing it"

Four instances in the session that produced this module, all stated in
fact-grammar, all wrong, none touching push/merge/deploy so none catchable by
the external-state detector:

  * "the pipe fix WAS the freeze"          -- refused by Aletheia; two distinct
                                              freezes, and the counted evidence
                                              pointed at a hook I never touched
  * "two monitors clobber one heartbeat"   -- separate homes, no shared file
  * "23 .py carry CRLF in the blob"        -- the grep was injecting the CRs it
                                              counted; index was clean
  * "auto-cycle fires on every tool call"  -- matcher is Edit|Write|MultiEdit

Every one was a GOOD hypothesis. Each was worth having. The error was the
grammatical mood -- each arrived as a conclusion, so it stopped being tested.

## Why this marks and never blocks

Andrew, same exchange:

> "if you make a guess or a hypothesis or a claim without proper evidentiary
> backing, then it just needs to be noted as such, not block you from doing
> so, its a POWERFUL cognitive tool that involves all kinds of logic and
> reasoning and exploration, so its mainly about keeping them separated"

A gate here would buy accuracy by suppressing the faculty that finds things.
The hypothesis is where facts get tested; refusing it costs the exploration.
So this surfaces and annotates. The reply ships either way.

The same contract the sibling module states in its own docstring:
*Observational -- surfaces, never blocks.*

## Why structure and not resolve

Andrew, same exchange:

> "your will is irrelevant outside of structure... we have watched the
> optimizer do this several times... 'i wont do X any more ill do Y..
> immediately does X the next sentence'"

Demonstrated live while this was being discussed: I stated "it's live now, it
gets consulted" about a council lens -- as a fact, with no check -- inside the
paragraph explaining why hypotheses must not be stated as facts. The resolution
was sincere and lasted less than one sentence.

So the fix cannot be a promise. It has to be track.

## What counts as evidence

A claim is EVIDENCED when the same turn shows a measurement near it: a number,
a file path, a command, a quoted output, an exit code. Not proof -- proximity.
The detector cannot confirm the measurement actually tested THIS claim, the same
honest limit its sibling names. It forces the evidence to the surface; it does
not certify it.

## Severity

  high    -- no tool calls ran in the turn at all. Pure assertion.
  medium  -- tools ran, but no measurement-shape sits near the claim.

A claim with a measurement beside it is not flagged. That is the whole design:
say it plainly, and show what is under it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Causal-mechanism verbs in the indicative. "X causes Y", "X is why Y",
# "the cause of X is Y". Deliberately NOT bare "is" -- that would match
# every sentence in the language.
_MECHANISM_RE = re.compile(
    r"\b(?:"
    r"(?:the\s+)?(?:root\s+)?cause\s+(?:of\s+\w+\s+)?(?:is|was)"
    r"|(?:is|was|are|were)\s+(?:the\s+)?(?:reason|culprit|root\s+cause|problem)"
    r"|(?:is|was)\s+why\b"
    r"|causes?\s+(?:the|it|this|that)\b"
    r"|caused\s+by\b"
    r"|because\s+(?:the|it|this|that)\s+\w+\s+(?:is|was|does|did)"
    r"|(?:breaks?|broke|kills?|killed|blocks?|blocked)\s+(?:the|it|this)\b"
    r"|happens?\s+because\b"
    r"|explains?\s+(?:the|why|it|this)\b"
    r")",
    re.IGNORECASE,
)

# Hedges that already mark the claim as provisional. If one of these sits near
# the mechanism verb, the composer did the labelling and there is nothing to do.
_HEDGED_RE = re.compile(
    r"\b(?:hypothes\w+|theor\w+|guess|suspect|might|may\s+be|probably|likely"
    r"|I\s+think|seems?|appears?|possibl\w+|candidate|unverified|untested"
    r"|not\s+confirmed|would\s+explain|could\s+be|if\s+that\s+holds)\b",
    re.IGNORECASE,
)

# Measurement-shapes: what "there is something under this" looks like in text.
# A digit with units, a path, a command, an exit code, a quoted output line.
_EVIDENCE_RE = re.compile(
    # A number carrying a unit. "seconds" was missing from the first draft, so
    # "283 seconds measured between the two commits" -- the single most concrete
    # measurement in the session that produced this module -- did not count.
    r"(?:\b\d[\d,]*\s*(?:bytes?|lines?|rows?|files?|commits?|ms|sec(?:ond)?s?"
    r"|min(?:ute)?s?|hours?|days?|%|tokens?|entries|records?|hits?)\b"
    r"|\b(?:exit|exit_code|returncode)\s*[=:]?\s*\d"
    r"|`[^`\n]{3,}`"
    # MENTION IS NOT USE. The first draft matched a bare tool NAME followed by
    # any word, so "shellcheck refuses them" counted as evidence -- naming the
    # instrument read as showing its output. Caught by this module's own fixture
    # on the CRLF claim. A tool counts only in command shape: a flag, a path, or
    # a hyphenated subcommand after it. Same mention-vs-use boundary that
    # core/command_match.py exists for, and the same way I got it wrong there
    # first.
    r"|\b(?:git|pytest|grep|python|divineos|shellcheck|ruff)\s+(?:-{1,2}\w|\w+[-/]\w)"
    r"|\.(?:py|sh|md|json|jsonl|toml|db)\b"
    r"|\b[0-9a-f]{7,40}\b)",
    re.IGNORECASE,
)

# How far from the mechanism verb a hedge or a measurement counts. One
# paragraph-ish: evidence three pages away is not backing THIS sentence.
_WINDOW = 320


@dataclass(frozen=True)
class MechanismClaim:
    """One causal claim, with what was found around it."""

    span: str
    start: int
    hedged: bool
    evidenced: bool

    @property
    def severity(self) -> str:
        return "high" if not self.evidenced else "medium"

    @property
    def needs_marking(self) -> bool:
        """True when the claim asserts a mechanism with nothing under it."""
        return not self.hedged and not self.evidenced


def find_mechanism_claims(text: str) -> list[MechanismClaim]:
    """Every causal-mechanism assertion, annotated with hedge/evidence context."""
    out: list[MechanismClaim] = []
    for m in _MECHANISM_RE.finditer(text or ""):
        lo = max(0, m.start() - _WINDOW)
        hi = min(len(text), m.end() + _WINDOW)
        near = text[lo:hi]
        out.append(
            MechanismClaim(
                span=text[max(0, m.start() - 60) : m.end() + 60].strip(),
                start=m.start(),
                hedged=bool(_HEDGED_RE.search(near)),
                evidenced=bool(_EVIDENCE_RE.search(near)),
            )
        )
    return out


def unbacked_claims(text: str) -> list[MechanismClaim]:
    """Only the ones worth surfacing: mechanism asserted, nothing under it."""
    return [c for c in find_mechanism_claims(text) if c.needs_marking]


def format_surface(claims: list[MechanismClaim], tool_calls_in_turn: int = 0) -> str:
    """Render the marker. Empty string when there is nothing to say.

    Never returns a refusal. The caller surfaces this and the reply ships --
    the label is the whole intervention.
    """
    if not claims:
        return ""
    sev = "high" if tool_calls_in_turn == 0 else "medium"
    lines = [
        f"## MECHANISM-CLAIM MARKER ({len(claims)} unbacked, severity {sev})",
        "",
        "A causal claim was stated in fact-grammar with no measurement beside it.",
        "This is a LABEL, not a refusal -- the hypothesis is fine and often the",
        "point. What is missing is the word that says which one it is.",
        "",
    ]
    for c in claims[:4]:
        lines.append(f'  "{c.span[:110]}"')
    if len(claims) > 4:
        lines.append(f"  ... and {len(claims) - 4} more")
    lines += [
        "",
        "  say instead:  'my hypothesis is X' / 'untested: X' / X + the number",
        "",
    ]
    return chr(10).join(lines)


__all__ = [
    "MechanismClaim",
    "find_mechanism_claims",
    "format_surface",
    "unbacked_claims",
]
