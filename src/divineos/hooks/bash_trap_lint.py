"""Catch shell commands whose behaviour I assumed rather than verified.

Andrew 2026-08-10, after a day of them: "lets look for a way to automate some
stuff to help ok? :)"

Thirteen of the day's twenty-eight failures were one shape: a command whose
behaviour I assumed. Every one returned a PLAUSIBLE WRONG ANSWER WITH EXIT
CODE ZERO, which is why none of them announced themselves.

Council walk walk-eba3cfa75aa4 (10 lenses, high gravity) shaped this, and
two lenses disagreed with the plan I arrived with:

  Dijkstra — a lint is testing, and testing shows the presence of faults,
    not their absence. Where a correct-by-construction fix exists, use it.
  Norman — these are SLIPS, right intention with wrong execution, and the
    answer to slips is forcing functions, never reminders. A lint is a
    warning label on a badly-shaped tool.
  Lamport — a rule I cannot specify exactly must WARN, never block. "grep -c
    is wrong" is false; grep -c is correct when you want lines. The real
    condition is "used where intent is occurrences", undecidable from text.
  Einstein — only automate traps whose failure was SILENT. A traceback is
    its own alarm; twenty rules would be noise, and noise gets ignored.
  Polya — supply the CORRECT FORM. Forbidding teaches nothing.
  Angelou/Dekker — these were slips under normal pressure. A mechanism that
    reads as accusation gets routed around, which is this session's whole
    finding. Instrument the gap; do not police.

THE TWO-TIER DESIGN WAS WRONG AND ANDREW KILLED IT (2026-08-10):

    "again you create a warning.. we have discussed warnings multiple times
     in the past and how they DO NOT WORK... YOU CANNOT WARN THE OPTIMIZER."

I shipped four warn-tier rules and cited the Lamport lens above as the
justification - borrowing a council walk's authority to legitimise the one
thing my own knowledge store already states plainly: text without
consequence is wallpaper to the optimizer; a reminder is only a reminder
when something happens if I ignore it.

Worse, the warn tier was verified SILENT. The hook fired, matched, rendered
and emitted with exit 0 - and a PreToolUse hook's exit-0 output never
reaches me. Four rules rendering perfectly into a closed channel, which is
this session's disease in its purest form.

EVERY RULE BLOCKS NOW. Lamport's objection stands, and the very first live
block after the change was a FALSE POSITIVE - a command writing this
docstring, which contains the pattern as text rather than running it. That
is the objection made flesh, and it is handled without a warning tier: the
exception is encoded structurally rather than verbally. Re-issue with the
rule's ack token and the command runs. Truth 11 remediation (c). The
exception is PAID FOR with one act of naming intent, which is exactly the
reasoning a warning was supposed to prompt and never could.

Wayne's constraint, and it is binding: this catches the traps in the list
below and NOTHING ELSE. It does not cover the class. Saying otherwise would
be the same overclaim as the ledger invariant I stated and broke this
morning.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Trap:
    name: str
    pattern: re.Pattern[str]
    why: str  # the incident, per Knuth: a rule without provenance gets deleted
    instead: str  # per Polya: the correct form, not a prohibition
    ack: str  # the token that buys an exception, per truth 11 remediation (c)


# Each `why` is a real incident from 2026-08-10 unless dated otherwise.
TRAPS: tuple[Trap, ...] = (
    Trap(
        name="wrong-python-tree",
        # Bare `python` at command position, without PYTHONPATH and not
        # `python -m pytest` (pytest inserts rootdir itself).
        pattern=re.compile(
            r"(?:^|[;&|]\s*)(?<!PYTHONPATH=src\s)python\s+(?!-m\s+pytest)(?=-c|-\s|-u|\S*\.py)"
        ),
        why=(
            "Bare `python` in this checkout resolves C:/DIVINE OS/DivineOS-Experimental "
            "— Aether's tree. `import divineos` silently loads HIS modules, so a module "
            "I just wrote reports ModuleNotFoundError and a module we both have reports "
            "his version's behaviour."
        ),
        instead='PYTHONPATH=src python ...   (verify with: python -c "import divineos; print(divineos.__file__)")',
        ack="#tree-ok",
    ),
    Trap(
        name="grep-c-counts-lines",
        pattern=re.compile(r"\bgrep\b[^|;&\n]*\s-\w*c"),
        why=(
            "grep -c counts MATCHING LINES, not occurrences. On single-line JSON I "
            "reported 'Aether appears once' to Andrew. The real count was 29."
        ),
        instead="grep -o <pat> file | wc -l   (only if you want occurrences; -c is right for lines)",
        ack="#lines-ok",
    ),
    Trap(
        name="exit-code-lost-in-pipe",
        pattern=re.compile(r"\bgit\s+(?:push|commit|merge|rebase)\b[^\n]*\|"),
        why=(
            "A pipeline's exit status is the LAST command's. Piping git push through "
            "tail reported success on a REFUSED push. Twice."
        ),
        instead="run it unpiped, or `set -o pipefail` first, and echo $? explicitly",
        ack="#exit-ok",
    ),
    Trap(
        name="truncating-a-surface-i-must-read",
        pattern=re.compile(
            r"\b(?:mansion\s+council|divineos\s+briefing)\b[^\n]*\|\s*(?:tail|head)\b"
        ),
        why=(
            "I piped a council walk through `tail -60`, so a truncation flag selected "
            "my council instead of the manager. Andrew found it, not me."
        ),
        instead="read the whole output; use `divineos walk open` which records the surfaced set",
        ack="#truncate-ok",
    ),
    Trap(
        name="append-may-land-below-exit",
        # Hook files often have NO extension (.git/hooks/commit-msg is the
        # one I actually broke), so matching only *.sh missed the very
        # incident that produced the rule. The test caught that, not me.
        pattern=re.compile(r">>\s*[^\s|;&]*(?:\.(?:sh|bash)\b|hooks/[\w.-]+)"),
        why=(
            "I appended a new gate to the end of .git/hooks/commit-msg, which has "
            "`exit 0` before the end. The gate was dead on arrival and looked wired."
        ),
        instead="insert BEFORE the final exit, then re-read the tail of the file to confirm",
        ack="#append-ok",
    ),
)


@dataclass(frozen=True)
class Fire:
    trap: Trap

    def render(self) -> str:
        return (
            f"[bash-trap:{self.trap.name}] BLOCKED\n"
            f"  why: {self.trap.why}\n"
            f"  instead: {self.trap.instead}\n"
            f"  if this use is genuinely right, re-issue including {self.trap.ack} "
            f"- the exception costs one act of naming intent, which is the point."
        )


def check(command: str) -> list[Fire]:
    """Fires for one command string. Empty list means no KNOWN trap matched.

    Empty is not a safety claim — see the module docstring. It means none of
    the five patterns above matched, and nothing more than that.
    """
    if not command:
        return []
    return [Fire(t) for t in TRAPS if t.pattern.search(command) and t.ack not in command]


def should_block(fires: list[Fire]) -> bool:
    """Any fire blocks.

    Andrew 2026-08-10: "again you create a warning.. we have discussed
    warnings multiple times in the past and how they DO NOT WORK... YOU
    CANNOT WARN THE OPTIMIZER."

    He is right, and my own store already held it: text without consequence
    is wallpaper to the optimizer; a reminder is only a reminder when
    something happens if I ignore it. I had four warn-tier rules and I used
    the Lamport lens from a council walk to JUSTIFY them -- borrowing the
    authority of the process to legitimise the exact thing that does not
    work.

    Lamport's objection was real: grep -c IS correct when you want lines, so
    a blanket block would be wrong. The answer is not a warning. It is truth
    11 remediation (c) -- a conditional rule where the exception is encoded
    structurally and has to be PAID FOR. Re-issue with the ack token and the
    command runs. The cost is naming the intent once, which is exactly the
    reasoning the warning was supposed to prompt and never could."""
    return bool(fires)
