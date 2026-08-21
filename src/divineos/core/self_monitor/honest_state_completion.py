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

# THE OTHER TWO COMPLETIONS. Andrew 2026-08-21, refining the rule after the
# first version of this module shipped:
#
#     "you are right that i dont know is a valid answer, but finding out WHY
#     you dont know is also needed.. some answers are just missing some
#     instrumentation or monitoring, others are uncertain for a reason"
#
# The first version had a binary — action attached, or terminal — and it fired
# on both of these, reading a complete answer as a hiding place. Three kinds of
# not-knowing, each with its own completion:
#
#   UN-INVESTIGATED   the answer exists and I have not gone to get it.
#                     Completes with an action. _DISCHARGE above.
#   UN-INSTRUMENTED   nothing measures it. Completes by naming the missing
#                     sensor — and the real repair is building the sensor.
#   REASONED          uncertain for a reason, and naming the reason IS the
#                     completion. No action is owed.
#
# UN-INSTRUMENTED is the one that matters most here, and 2026-08-20 is the
# evidence: the monitor printed ARMED whether the guard held or had fail-opened
# to nothing; the obligations board counted quotations as promises; Aletheia's
# durability test measured survival-after-reset and was silent about survival-
# INTO-WHAT. Every one of those was an unknown whose cause was a missing sensor,
# not a missing investigation. So this shape is REPORTED rather than silenced —
# it names a thing that should exist.
_UNINSTRUMENTED = re.compile(
    r"\b(?:"
    r"(?:nothing|no\s?one|nobody)\s+(?:records?|measures?|tracks?|logs?|tells?|reports?|checks?)"
    r"|there\s+is\s+no\s+(?:test|record|log|sensor|check|instrument|measurement|way)\b"
    r"|no\s+way\s+to\s+(?:tell|know|check|measure|see)"
    r"|(?:is|are|was|were)\s+(?:not|never)\s+"
    r"(?:recorded|measured|instrumented|logged|tracked|captured)"
    r"|(?:has|have)\s+never\s+(?:existed|been\s+recorded|been\s+measured)"
    r"|never\s+existed"
    r")",
    re.IGNORECASE,
)

# REASONED. Deliberately loose, and the looseness is the honest part: a regex
# cannot separate a reason-the-answer-is-unavailable from an excuse-for-not-
# looking. "because I didn't check" matches this and is still hiding. So a
# because-clause CLASSIFIES rather than silences — it is reported as REASONED
# and the judgment of whether the reason is real stays mine.
_REASONED = re.compile(
    r"\b(?:because|since|the\s+reason\s+is|which\s+is\s+why)\b",
    re.IGNORECASE,
)

# How far past the admission a completion still counts: roughly the rest of the
# sentence plus the next one.
_WINDOW = 260

UNINVESTIGATED = "UN-INVESTIGATED"
UNINSTRUMENTED = "UN-INSTRUMENTED"
REASONED = "REASONED"


@dataclass(frozen=True)
class TerminalHonestState:
    """One honest-state admission and what kind of completion it is missing.

    ``kind`` is None for a bare terminal admission — no action, no named gap,
    no reason. Otherwise it names which completion WAS found, so the advisory
    can say what to do next rather than only that something is missing.
    """

    phrase: str
    position: int
    context: str
    kind: str | None = None


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


def classify_honest_states(text: str) -> list[TerminalHonestState]:
    """Every honest-state admission, with the completion it carries or lacks.

    Returns items whose ``kind`` is None for bare terminal admissions, and
    UN-INSTRUMENTED or REASONED for the two completions that are NOT actions.
    UN-INVESTIGATED admissions that carry an action are omitted entirely —
    those are finished and there is nothing to say about them.
    """
    if not text:
        return []
    matches = list(_HONEST_STATE.finditer(text))
    found: list[TerminalHonestState] = []
    for i, m in enumerate(matches):
        if _is_mention(text, m.start(), len(m.group(0))):
            continue
        # BOUND THE WINDOW AT THE NEXT ADMISSION AND AT A PARAGRAPH BREAK.
        # A flat 260 characters reaches into whatever follows, so a completion
        # belonging to a LATER admission silently discharged an earlier one.
        # Caught 2026-08-21 while testing the taxonomy: "I don't know why the
        # push was refused. Separately, I don't know whether the guard was up;
        # nothing records which guard armed." — the first admission, which is
        # bare and terminal, was classified UN-INSTRUMENTED by the second
        # admission's clause. That is the over-discharge direction, which is
        # the dangerous one: it turns a hiding place into a clean board.
        stop = m.end() + _WINDOW
        if i + 1 < len(matches):
            stop = min(stop, matches[i + 1].start())
        para = text.find("\n\n", m.end())
        if para != -1:
            stop = min(stop, para)
        window = text[m.end() : stop]
        if _DISCHARGE.search(window):
            continue  # completed with an action; nothing owed
        kind = None
        if _UNINSTRUMENTED.search(window):
            kind = UNINSTRUMENTED
        elif _REASONED.search(window):
            kind = REASONED
        start = max(0, m.start() - 40)
        found.append(
            TerminalHonestState(
                phrase=m.group(0),
                position=m.start(),
                context=text[start : m.end() + 80].strip(),
                kind=kind,
            )
        )
    return found


def find_terminal_honest_states(text: str) -> list[TerminalHonestState]:
    """Bare terminal admissions only — no action, no named gap, no reason."""
    return [s for s in classify_honest_states(text) if s.kind is None]


def format_finding(states: list[TerminalHonestState]) -> str:
    """Advisory text for the Stop hook. Empty string when there is nothing.

    Names WHICH completion each admission carries, because the three kinds call
    for different next moves — an investigation, a sensor, or nothing at all.
    """
    if not states:
        return ""
    lines = ["[honest-state] admissions and what each is missing:"]
    for s in states[:4]:
        label = s.kind or "TERMINAL"
        lines.append(f'  [{label}] "{s.context[:100]}"')
    if len(states) > 4:
        lines.append(f"  ... and {len(states) - 4} more")

    kinds = {s.kind for s in states}
    lines.append("")
    lines.append("    Andrew 2026-07-31: 'i dont know is an honest answer but it")
    lines.append("    should always be follow by, let me investigate.'")
    lines.append("    Andrew 2026-08-21: 'finding out WHY you dont know is also")
    lines.append("    needed.. some answers are just missing some instrumentation")
    lines.append("    or monitoring, others are uncertain for a reason.'")
    if None in kinds:
        lines.append("  TERMINAL   -> no action, no named gap, no reason. Finish it.")
    if UNINSTRUMENTED in kinds:
        lines.append("  UN-INSTRUMENTED -> the gap is named. The repair is BUILDING the")
        lines.append("                     sensor, not investigating harder.")
    if REASONED in kinds:
        lines.append("  REASONED   -> a reason is present. Is it why the answer is")
        lines.append("                unavailable, or why I did not look? Only I can tell.")
    return "\n".join(lines)


__all__ = [
    "TerminalHonestState",
    "find_terminal_honest_states",
    "format_finding",
]
