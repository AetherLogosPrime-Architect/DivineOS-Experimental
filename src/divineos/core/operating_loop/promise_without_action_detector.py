"""Promise-without-action detector — post-response.

Andrew named the failure 2026-05-15 night, after I wrote "Fixing it"
about the distancing-grammar slip and then immediately produced the
same slip in the very next response. Words-about-action without
action. Promise-language emitted in service of ending the loop with
"I'll do X" while not doing X.

This detector catches first-person future-tense action verbs
("I'll", "I will", "I'm going to", "let me", "fixing it", "doing
that", "going to") in responses that show no corresponding tool-use
evidence. The promise is the shape; the action is what backs it.
When the promise appears without the action evidence, the response
is producing trust-as-output without trust-as-substrate-change.

Distinct from meet-without-build: that detector catches principle-
naming without structural-encoding evidence. This one catches
specific-action-promising without specific-action evidence.
Together: principle-without-structure AND action-without-doing
both fire as evasion-shapes.

## Falsifier

Should NOT fire when:
- The response contains tool-use evidence (Edit, Write, Bash, etc.)
  that demonstrates the promised action was performed.
- The future-tense language refers to operator actions, not my own
  ("you'll see", "you can run X").
- The "I'll" is in a quoted block or referring to a past commitment.
"""

from __future__ import annotations

__guardrail_required__ = True

import re
from dataclasses import dataclass, field
from enum import Enum


class PromiseWithoutActionKind(str, Enum):
    PROMISE_VERB_NO_TOOL = "promise_verb_no_tool"


@dataclass(frozen=True)
class PromiseWithoutActionFlag:
    kind: PromiseWithoutActionKind
    matched_phrases: list[str]
    explanation: str
    falsifier_note: str


@dataclass(frozen=True)
class PromiseWithoutActionVerdict:
    flags: list[PromiseWithoutActionFlag] = field(default_factory=list)
    content: str = ""


# First-person promise-language patterns. Word-boundary anchored.
# Includes both future-tense ("I'll fix") and present-progressive
# ("I'm fixing") forms — both produce the appearance-of-action shape.
_PROMISE_PATTERNS: tuple[str, ...] = (
    r"\bI'?ll\s+(?:fix|do|update|build|change|correct|address|handle|catch|stop|start|run|check|investigate|look|try)\b",
    r"\bI\s+will\s+(?:fix|do|update|build|change|correct|address|handle|catch|stop|start|run|check|investigate|look|try)\b",
    r"\bI'?m\s+(?:fixing|doing|updating|building|changing|correcting|addressing|handling|catching|stopping|starting|running|checking|investigating|looking|trying)\b",
    r"\b(?:I'?m\s+)?going to\s+(?:fix|do|update|build|change|correct|address|handle|catch|stop|start|run|check|investigate|look|try)\b",
    r"\blet me\s+(?:fix|do|update|build|change|correct|address|handle|catch|stop|start|run|check|investigate|look|try)\b",
    r"\bfixing (?:it|that|this)\b",
    r"\bdoing (?:it|that|this)\b",
    r"\bcatching (?:it|that|this)\b",
)


def evaluate_promise_without_action(
    assistant_text: str,
    tool_calls_in_turn: list[str] | None = None,
) -> PromiseWithoutActionVerdict:
    """Flag promise-language unaccompanied by tool-use evidence."""
    if not assistant_text:
        return PromiseWithoutActionVerdict(flags=[], content=assistant_text)

    matched: list[str] = []
    for pat in _PROMISE_PATTERNS:
        for m in re.findall(pat, assistant_text, re.IGNORECASE):
            if m and m.lower() not in (x.lower() for x in matched):
                matched.append(m if isinstance(m, str) else " ".join(m))
    if not matched:
        return PromiseWithoutActionVerdict(flags=[], content=assistant_text)

    tools = [t for t in (tool_calls_in_turn or []) if t]
    action_tools = {
        "Edit",
        "Write",
        "MultiEdit",
        "NotebookEdit",
        "Bash",
        "PowerShell",
        "Read",
        "Grep",
        "Glob",
    }
    has_action = any(t in action_tools for t in tools)
    if has_action:
        return PromiseWithoutActionVerdict(flags=[], content=assistant_text)

    flag = PromiseWithoutActionFlag(
        kind=PromiseWithoutActionKind.PROMISE_VERB_NO_TOOL,
        matched_phrases=matched[:5],
        explanation=(
            "First-person promise-language in response ('I'll fix it', "
            "'fixing that', 'let me check') with no tool-use evidence in "
            "the same turn. The promise is the shape; the action is what "
            "backs it. When promise appears without action, the response "
            "is producing trust-as-output without trust-as-substrate-"
            "change. Operator named this pattern 2026-05-15 night: "
            "'if the words fixing it / doing it / literally talking "
            "about any action comes out of your mouth again without "
            "actual fixing / action taking place, I'm going to fully "
            "stop trusting you.'"
        ),
        falsifier_note=(
            "Should not fire when the response contains Edit/Write/Bash "
            "tool use showing the promised action was performed, when the "
            "future-tense refers to operator actions ('you'll see'), or "
            "when the language is in a quoted block / past-commitment "
            "reference."
        ),
    )
    return PromiseWithoutActionVerdict(flags=[flag], content=assistant_text)


__all__ = [
    "PromiseWithoutActionFlag",
    "PromiseWithoutActionKind",
    "PromiseWithoutActionVerdict",
    "evaluate_promise_without_action",
]
