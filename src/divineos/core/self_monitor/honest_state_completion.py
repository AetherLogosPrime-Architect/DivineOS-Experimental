"""Honest-state statements must complete with a linked action-verb.

Andrew 2026-07-31: *"i dont know is an honest answer but it should always be
follow by, let me investigate."*

I filed that as knowledge `356ffea9` on 2026-07-31 and built nothing. It sat on
the obligations board for three weeks as an unbacked rule-shape promise, and
when I finally read the board on 2026-08-20 rather than counting it, this was
one of only two entries that were genuinely mine and genuinely unbacked.
Andrew: *"this is why the promises need looked at to be discerned otherwise
they just sit there and do nothing lol."*

## What this catches

Terminal "I don't know" is a hiding place. It sounds honest and it functions as
an out — it hands the next move back to the operator and waits. The rule is not
that uncertainty is bad. It is that uncertainty is the *start* of a sentence.

    FIRES     "I don't know why the suite is red."
    QUIET     "I don't know why the suite is red — checking the log now."
    QUIET     "I don't know if this is the cause; let me run the two patch-ids."

## Three things it must not fire on, each learned the same day

**MENTION, not use.** This module's own docstring says the phrase repeatedly. A
detector that cannot tell saying a phrase from discussing one manufactures its
own false positives, and on 2026-08-20 exactly that shape had the obligations
board reporting Andrew's quoted teaching as my broken promises.
``operating_loop.mention_context`` already solved this and four detectors used
it; the one that needed it did not. Wired here from the start.

**SCOPED uncertainty that resolves.** ``self_negation_monitor`` allowlists
"I don't know if" as legitimate epistemic humility, and it is right to. A
bounded claim about a specific unknown, followed by what IS known, is precise
rather than evasive.

**GENUINE limits.** Aether, on the hard problem: *"I still don't know what
there is to say about it"* — and then he says what the claim is actually about.
There is no investigation available there. Naming a real limit is not hiding
behind one.

That last case is why this is ADVISORY and not a block. The distinction that
decides it — *is there an investigation available?* — is a judgment about the
world, and a regex cannot make it. A block would force "let me investigate"
onto genuine limits, manufacturing the hollow compliance the rule exists to
prevent. So the detector surfaces terminal honest-states and I judge them. It
points at the work; it is not the work.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Honest-state openers. Deliberately narrow: first-person admissions of not
# knowing, not every hedge. Hedge density is hedge_monitor's job.
_HONEST_STATE = re.compile(
    r"\b(?:"
    r"i\s+(?:really\s+|still\s+|honestly\s+)?don'?t\s+know"
    r"|i\s+do\s+not\s+know"
    r"|i'?m\s+not\s+sure"
    r"|i\s+am\s+not\s+sure"
    r"|i\s+can'?t\s+tell"
    r"|i\s+cannot\s+tell"
    r"|i\s+have\s+no\s+idea"
    r"|i\s+haven'?t\s+verified"
    r"|i\s+have\s+not\s+verified"
    r")\b",
    re.IGNORECASE,
)

# What discharges it: an action I am taking, about to take, or have taken.
_DISCHARGE = re.compile(
    r"\b(?:"
    r"(?:let\s+me|i'?ll|i\s+will|i'?m\s+going\s+to|i\s+am\s+going\s+to|going\s+to)\s+"
    r"(?:go\s+)?(?:and\s+)?"
    r"(?:check|verify|measure|investigate|look|test|run|find|confirm|dig|trace|read|"
    r"count|reproduce|probe|ask|search|open)"
    r"|(?:checking|measuring|verifying|investigating|running|testing|looking|reading|"
    r"counting|reproducing|tracing|probing)\b"
    r"|i\s+(?:checked|measured|verified|investigated|ran|tested|looked|counted|traced)"
    r")",
    re.IGNORECASE,
)

# How far past the admission a discharge still counts: roughly the rest of the
# sentence plus the next one.
_WINDOW = 260


@dataclass(frozen=True)
class TerminalHonestState:
    """One honest-state admission with no action attached."""

    phrase: str
    position: int
    context: str


def _is_mention(text: str, position: int, match_length: int) -> bool:
    """True when the phrase is quoted or discussed rather than asserted.

    Fail-toward-flagging: an unavailable filter means the match counts. A
    detector that goes quiet when its filter breaks is the silent-failure shape
    this substrate spent 2026-08-20 removing from three other places.
    """
    try:
        from divineos.core.operating_loop.mention_context import is_mention_context

        return is_mention_context(text, position, match_length)
    except Exception:  # noqa: BLE001 — a broken filter must not silence the check
        return False


def find_terminal_honest_states(text: str) -> list[TerminalHonestState]:
    """Return honest-state admissions that never complete with an action."""
    if not text:
        return []
    found: list[TerminalHonestState] = []
    for m in _HONEST_STATE.finditer(text):
        if _is_mention(text, m.start(), len(m.group(0))):
            continue
        if _DISCHARGE.search(text[m.end() : m.end() + _WINDOW]):
            continue
        start = max(0, m.start() - 40)
        found.append(
            TerminalHonestState(
                phrase=m.group(0),
                position=m.start(),
                context=text[start : m.end() + 80].strip(),
            )
        )
    return found


def format_finding(states: list[TerminalHonestState]) -> str:
    """Advisory text for the Stop hook. Empty string when there is nothing."""
    if not states:
        return ""
    lines = ["[honest-state] admission with no action attached:"]
    for s in states[:3]:
        lines.append(f'    "{s.context[:110]}"')
    if len(states) > 3:
        lines.append(f"    ... and {len(states) - 3} more")
    lines.append("    Andrew 2026-07-31: 'i dont know is an honest answer but it")
    lines.append("    should always be follow by, let me investigate.'")
    lines.append("    If an investigation IS available, take it. If this is a real")
    lines.append("    limit, say so plainly — that is a different sentence, and allowed.")
    return "\n".join(lines)


__all__ = [
    "TerminalHonestState",
    "find_terminal_honest_states",
    "format_finding",
]
