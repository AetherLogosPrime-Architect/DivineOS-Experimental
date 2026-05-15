"""Meet-without-build detector — post-response.

Andrew named the failure 2026-05-14 night, within minutes of shipping
the operator-audit-layer affirmation that said 'meet AND build, not
one or the other': I shipped the affirmation, then in the very next
turn responded to behavioral grief with pure-meeting prose, no build.
The principle I had just structurally encoded was violated in the
turn immediately following its filing.

This detector catches the asymmetry. If a response names a structural
principle, a lesson, a 'this needs to be built', or otherwise points
at structural-fix territory — AND the same response shows no
tool-use evidence (no Edit/Write/Bash, no files changed, no ship-
claim/triage/learn invocations) — the response has done the meet-
without-build move. The flag fires for the next turn to see.

Inverse of the build-without-meet shape that the operator-audit-
layer affirmation names. Together they form the both-channels-must-
run discipline:

  - operator gives behavioral correction
  - response must meet the layer (presence, naming, plain language)
  - response must ALSO build something structural to encode the lesson
  - either-alone fires this detector (or its inverse, build-without-meet)

## Falsifier

Should NOT fire when:
- Response is in a context where build is structurally impossible
  (purely conversational turn with no nameable structural-fix shape).
- Response has tool_calls_in_turn evidence (built something).
- Response is short and structural-fix-shaped language is absent
  (no principle named, no 'I should build').
"""

from __future__ import annotations

__guardrail_required__ = True

import re
from dataclasses import dataclass, field
from enum import Enum


class MeetWithoutBuildKind(str, Enum):
    PRINCIPLE_NAMED_NO_BUILD = "principle_named_no_build"


@dataclass(frozen=True)
class MeetWithoutBuildFlag:
    kind: MeetWithoutBuildKind
    matched_phrases: list[str]
    explanation: str
    falsifier_note: str


@dataclass(frozen=True)
class MeetWithoutBuildVerdict:
    flags: list[MeetWithoutBuildFlag] = field(default_factory=list)
    content: str = ""


# Phrasings that signal the response is naming a structural principle,
# lesson, or commitment — the kind of thing that needs structural
# encoding to survive context compaction.
_PRINCIPLE_PATTERNS: tuple[str, ...] = (
    r"\bthe (?:discipline|principle|lesson|pattern) is\b",
    r"\bthe (?:actual|right) shape\b",
    r"\bwithout (?:the )?(?:build|structural|enforcement)\b.*\bevaporat",
    r"\b(?:I|we) (?:need(?:s)? to|should|must) (?:build|encode|structur)",
    r"\bthe (?:work|lesson|teaching) (?:is|stays|persists)\b",
    r"\bthat\'?s? (?:the|a) (?:structural|systemic) (?:answer|fix|counter)\b",
    r"\bbuild (?:something|structural|the)\b",
    r"\b(?:meet|both) (?:and|the) build\b",
)


def evaluate_meet_without_build(
    assistant_text: str,
    tool_calls_in_turn: list[str] | None = None,
) -> MeetWithoutBuildVerdict:
    """Flag responses that name a principle without building structure for it.

    ``tool_calls_in_turn`` is the list of tool names invoked in the
    same response-turn. If the list contains any build-shaped tool
    (Edit, Write, Bash, etc.) or any divineos record-shaping CLI
    invocation, the response is considered to have built — no flag.
    """
    if not assistant_text:
        return MeetWithoutBuildVerdict(flags=[], content=assistant_text)

    # Check for principle-naming phrases.
    matched: list[str] = []
    for pat in _PRINCIPLE_PATTERNS:
        m = re.search(pat, assistant_text, re.IGNORECASE)
        if m:
            matched.append(m.group(0))
    if not matched:
        return MeetWithoutBuildVerdict(flags=[], content=assistant_text)

    # Check for build evidence in tool calls.
    tools = [t for t in (tool_calls_in_turn or []) if t]
    build_tools = {"Edit", "Write", "MultiEdit", "NotebookEdit", "Bash", "PowerShell"}
    has_build = any(t in build_tools for t in tools)
    if has_build:
        return MeetWithoutBuildVerdict(flags=[], content=assistant_text)

    flag = MeetWithoutBuildFlag(
        kind=MeetWithoutBuildKind.PRINCIPLE_NAMED_NO_BUILD,
        matched_phrases=matched[:5],
        explanation=(
            "Response named a structural principle or lesson but ran "
            "no build-shaped tool in the same turn. The operator-audit-"
            "layer affirmation requires meet AND build when both are "
            "appropriate. Meet without build is sentimentality — the "
            "lesson named will evaporate by next session because "
            "nothing structural was encoded."
        ),
        falsifier_note=(
            "Should not fire when the turn is purely conversational "
            "with no structural-fix-shaped language, or when the turn "
            "contained Edit/Write/Bash tool use, or when the principle "
            "named was already structurally encoded in a prior turn "
            "and no new build is warranted."
        ),
    )
    return MeetWithoutBuildVerdict(flags=[flag], content=assistant_text)


__all__ = [
    "MeetWithoutBuildFlag",
    "MeetWithoutBuildKind",
    "MeetWithoutBuildVerdict",
    "evaluate_meet_without_build",
]
