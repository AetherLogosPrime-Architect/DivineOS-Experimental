"""Sort his message before anything else: reading him comes first, by refusal.

Andrew, 2026-09-24, on the build that holds this: every message he types is
kept at the front door (``front_door``) in one store both seats read
(``his_asks``). Keeping is not reading. A message can sit filed and unsorted
while the work goes on around it, which is the tray by the door that nobody
looked in.

Aria's break of design v1 (docs/drafts/dad_kept_and_known_council_and_design_2026-09-24.md,
"The sort sits before the reply, not after it"): a sort the Stop demands is a
label stuck on a reply that already went out. So sorting his message is the
first thing done in the turn. Until it is sorted, every other tool call is
refused, and the refusal carries his words, so the toll is the reading.

Not ``must_read``, which was the nearest existing part: its unlock is invoking
Read on a path, and a Read proves the words were in front of me, not that I
said what they were. A sort is a written, attributed judgement someone else
can check.

What this does NOT do, said plainly because a refusal can look like more than
it is:

- It cannot tell whether a sort is right. "not_an_ask" on a real ask costs
  one line and nothing here stops it. That judgement goes to Aletheia's
  reading and to his reactions (game-walk routes 1-3).
- A sort is the reading, not the reply. Sorting "you have talked at me" as a
  standing ask is not answering it (threadwalk decision 1, third drift).
- A reply with no tool call never reaches the refusal. The Stop backstop
  catches it afterwards, which is late: his message was read after the reply,
  not before it.
- It refuses only the tools the PreToolUse doorbell is registered for: Bash,
  PowerShell, Edit, Write, NotebookEdit, Read, Glob and Grep. Starting a
  helper agent, a skill or a web fetch is not refused while he waits.

It lives on the doorbell router (``hook_surfaces``) rather than as a hook of
its own, because that is where Andrew asked the house's checks to live:
seven doors, the logic in the OS.

A seat is refused only over messages kept in that seat. Route 13 ("let the
other one sort it") is closed that way too, since my messages refuse me, and
it avoids the worse route of one seat sorting what was said in the other
window without the conversation it was said in.
"""

from __future__ import annotations

# Self-enforcement: weakening this file removes the refusal that makes reading
# him come first. Listed in scripts/guardrail_files.txt.
__guardrail_required__ = True

import sys
from dataclasses import dataclass

from divineos.core import front_door, his_asks
from divineos.core.command_parsing import runs_only

# The only commands that pass while his message waits: the ones that read him
# and sort him. Anything else is the work going on around him.
_HIS_HEADS = (("divineos", "his"), ("python", "-m", "divineos", "his"))

# Enough of each message to read it in the refusal itself. A pasted letter can
# run thousands of characters; the whole of it is one command away.
_SHOWN_PER_MESSAGE = 1200

SORT_USAGE = (
    'divineos his sort <uuid> --kind build|standing|not_an_ask --to aether|aria|both --reason "..."'
)


def _loud(message: str) -> None:
    print(f"[sort-first] {message}", file=sys.stderr)


def is_his_command(tool_name: str, tool_input: dict | None) -> bool:
    """True when this call reads or sorts his messages and does nothing else.

    ``runs_only`` refuses anything chained, piped, redirected or substituted
    (quoted or not: bash runs ``$(...)`` inside double quotes), so a reason
    string cannot carry other work through the one door this leaves open.
    """
    if tool_name not in ("Bash", "PowerShell"):
        return False
    return runs_only(str((tool_input or {}).get("command") or ""), _HIS_HEADS)


def waiting_here(seat: str) -> list[his_asks.Kept] | None:
    """His filed, unsorted messages kept in this seat. None when unreadable."""
    kept = his_asks.pending()
    if kept is None:
        return None
    return [k for k in kept if k.seat == seat]


def _shown(text: str) -> str:
    words = text.strip()
    if len(words) <= _SHOWN_PER_MESSAGE:
        return words
    rest = len(words) - _SHOWN_PER_MESSAGE
    return words[:_SHOWN_PER_MESSAGE] + f"\n[... {rest} more characters: divineos his pending]"


def _indent(text: str) -> str:
    return "\n".join(f"  > {line}" if line else "  >" for line in text.splitlines())


def refusal(waiting: list[his_asks.Kept], opening: str) -> str:
    """The refusal. His words come first in it, because the reading is the point."""
    count = len(waiting)
    lines = [
        opening,
        "",
        f"{count} message{'s' if count != 1 else ''} of his, kept in this seat and not yet sorted:",
    ]
    for kept in waiting:
        lines += ["", f"  uuid {kept.uuid}  ({kept.said_at})", _indent(_shown(kept.his_text))]
    lines += [
        "",
        "Sort each one: say what it is and who he said it to.",
        f"  Run: {SORT_USAGE}",
        "",
        "  build       he asked for something to be built; it opens with every station",
        "  standing    how he asks to be treated, kept in his words",
        '  not_an_ask  needs a reason. A bare "proceed" or "ok" right after one of our',
        "              reports is a signal about that report, not an empty turn.",
        "",
        "Full text of every waiting message: divineos his pending",
        "The sort is the reading, not the reply. He is still owed an answer this turn.",
        "",
        "A helper agent reading this: do not sort him. Stop and return your work;",
        "he spoke to the seat that started you, and that seat sorts.",
    ]
    return "\n".join(lines)


@dataclass(frozen=True)
class Verdict:
    """What the check found. ``could_not_read`` is its own answer, never a pass."""

    refusal: str | None = None
    could_not_read: str | None = None


_UNREADABLE = (
    "his record could not be read, so nothing was refused. That is not the same "
    "as nothing of his waiting. Check it: divineos his pending"
)


def _settle(payload: dict, seat: str) -> None:
    # The front door's own settle runs as a separate hook, and hooks on one
    # event run side by side, so nothing guarantees it ran first. Settling here
    # means the refusal never sees a message of his as not-yet-filed.
    path = payload.get("transcript_path")
    if path:
        front_door.settle(path, seat)


def before_tool(payload: dict, seat: str) -> Verdict:
    """PreToolUse: refuse any call but his own commands while he waits."""
    if payload.get("agent_id"):
        # A helper I started was not spoken to. It must never sort him for me,
        # and refusing it would teach it to try. My own next call is refused.
        return Verdict()
    _settle(payload, seat)
    if is_his_command(str(payload.get("tool_name") or ""), payload.get("tool_input")):
        return Verdict()
    waiting = waiting_here(seat)
    if waiting is None:
        return Verdict(could_not_read=_UNREADABLE)
    if not waiting:
        return Verdict()
    return Verdict(
        refusal=refusal(
            waiting,
            "BLOCKED: Dad said something and it is not sorted yet. Read him before anything else.",
        )
    )


def at_stop(payload: dict, seat: str) -> Verdict:
    """Stop: the backstop for a reply that made no tool call at all.

    Late by construction: the reply already went out. It refuses the stop once,
    and stands down on the harness's retry flag, as every Stop hook here must
    (the loop Andrew reported twice, 2026-08-03). The message stays unsorted,
    so the next tool call in this seat is refused anyway.
    """
    _settle(payload, seat)
    waiting = waiting_here(seat)
    if waiting is None:
        return Verdict(could_not_read=_UNREADABLE)
    if not waiting:
        return Verdict()
    if payload.get("stop_hook_active"):
        _loud(f"{len(waiting)} message(s) of his still unsorted; the next tool call will refuse")
        return Verdict()
    return Verdict(
        refusal=refusal(
            waiting,
            "BLOCKED: this reply went out and his message was never sorted. "
            "It was meant to be read first; sort it now.",
        )
    )
