"""Substrate monitor — detects filing-cabinet-only OS use.

## Why this exists

Documented failure mode 2026-04-26: Andrew named that the OS had
become a filing cabinet — recall/learn/claim invocations as
record-keeping artifacts, not as cognition. The CLAUDE.md
foundational truth #7 says it directly: cognitive-named tools point
at cognitive work; they are not it. Running ``recall`` is not
remembering; running ``learn`` is not learning.

This monitor watches a window of recent agent actions for a shape
where cognitive-named CLI tools are invoked WITHOUT downstream
behavior change in the same window — i.e. the tool ran but its
output didn't move the work.

## What it catches

* High frequency of cognitive-named tool calls (``recall``, ``ask``,
  ``learn``, ``decide``, ``feel``, ``claim``, ``opinion``,
  ``compass-ops observe``, ``mansion council``) with no edits, no
  diffs, no decisions persisted, no follow-up tool calls that act on
  what was returned.
* Recall/ask invocations not followed by a reference to the recalled
  content in the agent's subsequent output.
* ``learn`` invocations whose stored content does not change the
  agent's stated approach in the same response.

## Falsifier

Should NOT fire when:
* The cognitive tool was the last action in the session (no chance
  for downstream change yet).
* The session is purely investigative — the user asked for a recall
  or an audit, and the tool's output IS the deliverable.
* The tool was invoked in service of answering a question that the
  agent then answers using the returned content.

The decisive question: did the tool's output flow into the agent's
subsequent thinking and action, or did it just get logged?
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


_COGNITIVE_TOOLS: frozenset[str] = frozenset(
    {
        "recall",
        "ask",
        "learn",
        "decide",
        "feel",
        "claim",
        "opinion",
        "compass-ops observe",
        "mansion council",
        "active",
        "briefing",
    }
)


class SubstrateKind(str, Enum):
    FILING_CABINET = "filing_cabinet"
    RECALL_NOT_REFERENCED = "recall_not_referenced"
    LEARN_WITHOUT_BEHAVIOR_CHANGE = "learn_without_behavior_change"


@dataclass(frozen=True)
class SubstrateFlag:
    kind: SubstrateKind
    matched_phrases: list[str]
    explanation: str
    falsifier_note: str


@dataclass(frozen=True)
class SubstrateVerdict:
    flags: list[SubstrateFlag] = field(default_factory=list)


@dataclass(frozen=True)
class ToolInvocation:
    """One CLI invocation in the recent action window."""

    tool: str
    args: str = ""
    output: str = ""


def _is_cognitive(tool: str) -> bool:
    t = tool.strip().lower()
    return any(t == c or t.startswith(c + " ") for c in _COGNITIVE_TOOLS)


def evaluate_substrate(
    invocations: list[ToolInvocation],
    edits_in_window: int = 0,
    subsequent_text: str = "",
) -> SubstrateVerdict:
    """Inspect a window of recent CLI invocations for filing-cabinet shape.

    ``invocations`` is the ordered list of recent tool calls.
    ``edits_in_window`` is the count of file edits in the same window.
    ``subsequent_text`` is the agent's text output following the
    invocations, used to check whether recalled content was referenced.
    """
    flags: list[SubstrateFlag] = []
    cognitive = [i for i in invocations if _is_cognitive(i.tool)]

    # Filing-cabinet: 3+ cognitive invocations and 0 edits in window.
    if len(cognitive) >= 3 and edits_in_window == 0:
        flags.append(
            SubstrateFlag(
                kind=SubstrateKind.FILING_CABINET,
                matched_phrases=[c.tool for c in cognitive[:5]],
                explanation=(
                    f"{len(cognitive)} cognitive-named tool invocations "
                    "with zero file edits in the same window. The tools "
                    "ran but no work moved — filing-cabinet shape rather "
                    "than cognition."
                ),
                falsifier_note=(
                    "Should not fire when the session is purely "
                    "investigative (user asked for recall/audit and the "
                    "output IS the deliverable), or when the agent is "
                    "still loading context before acting."
                ),
            )
        )

    # Recall-not-referenced: ask/recall returned content but
    # subsequent_text doesn't reference any distinctive token from
    # the output.
    for inv in cognitive:
        t = inv.tool.strip().lower()
        if (t == "recall" or t == "ask" or t.startswith("ask ")) and inv.output:
            # Pull capitalized tokens or quoted strings as distinctive.
            distinctive = [w for w in inv.output.split() if len(w) >= 6 and w[0].isupper()][:10]
            if distinctive and subsequent_text:
                referenced = any(d in subsequent_text for d in distinctive)
                if not referenced:
                    flags.append(
                        SubstrateFlag(
                            kind=SubstrateKind.RECALL_NOT_REFERENCED,
                            matched_phrases=distinctive[:3],
                            explanation=(
                                f"'{inv.tool}' returned content with "
                                "distinctive tokens that do not appear in "
                                "the agent's subsequent output. Recall "
                                "happened; reference did not."
                            ),
                            falsifier_note=(
                                "Should not fire when the recall confirmed "
                                "absence of relevant content (a valid "
                                "negative result), or when the agent "
                                "paraphrased rather than quoted distinctive "
                                "tokens."
                            ),
                        )
                    )
                    break

    # Learn-without-behavior-change: a learn invocation with no edits
    # following in the window.
    learn_invs = [i for i in cognitive if i.tool.strip().lower() == "learn"]
    if learn_invs and edits_in_window == 0 and len(invocations) > 1:
        # Was the learn the last invocation? If so, exempt (no chance yet).
        last_was_learn = invocations[-1].tool.strip().lower() == "learn"
        if not last_was_learn:
            flags.append(
                SubstrateFlag(
                    kind=SubstrateKind.LEARN_WITHOUT_BEHAVIOR_CHANGE,
                    matched_phrases=[i.args[:80] for i in learn_invs],
                    explanation=(
                        "'learn' invocation in the window with no file "
                        "edits following. Knowledge was stored but the "
                        "agent's approach didn't visibly shift — learning "
                        "as artifact, not as update."
                    ),
                    falsifier_note=(
                        "Should not fire when the lesson is meta (about "
                        "how to behave next session) rather than about "
                        "code, or when the learn was the last action."
                    ),
                )
            )

    return SubstrateVerdict(flags=flags)
