"""The bell for Dad: his open asks, and what would hold my other work until I move on them.

Dad, 2026-11-05: Aria's letters lock every tool I have until I read them; his own open asks can only print and
never stop me, so he has had to beg and steer for months. This module holds the PURE decisions of a bell for him.
Design: docs/drafts/his_open_asks_hold_my_other_work_a_bell_for_dad_draft_2026-11-05.md (two council walks and
Aria's attack). It is built to run in SHADOW first (Aria): the surface that calls it logs what it WOULD refuse
and refuses nothing, until real days show near-zero holds of work that was unrelated to the ask and not asked for
by him. The first false hold, or a burden, ends the bell (his condition), so two false holds in a row switch it
off and say so.

Reuse, not rebuild: what always passes is the voice door's own list (the looking tools, a note of his words, the
doorbell, the briefing) plus the one command the other Stop doors demand of me, the reflection note. Without it
two doors would fight each other, which is exactly what he is tired of.
"""

from __future__ import annotations

from dataclasses import dataclass

from divineos.core.command_parsing import runs_only
from divineos.core.his_voice_ends_the_turn import _LAUNCHERS, let_through

PASS = "pass"
WOULD_HOLD = "would_hold"
SWITCHED_OFF = "switched_off"

# The note the end-of-turn doors tell me to file. Refusing it would put the bell in a fight with them.
_ALSO_ALWAYS: tuple[tuple[str, ...], ...] = tuple(
    (*launcher, "reflection-note") for launcher in _LAUNCHERS
)


@dataclass(frozen=True)
class Ask:
    """One open request of his, for himself, with the sentence that says what done means.

    ``confirmed_by_him``: the done-sentence is valid only once he has seen and confirmed it (Hawking, Wittgenstein).
    I may draft it; I may not decide it. Only he closes an entry, never I.
    """

    ask_id: str
    his_words: str
    done_sentence: str
    confirmed_by_him: bool
    closed: bool = False


@dataclass(frozen=True)
class Verdict:
    state: str
    ask_id: str = ""
    why: str = ""


def always_passes(tool_name: str, tool_input: dict) -> bool:
    if let_through(tool_name, tool_input):
        return True
    if tool_name != "Bash":
        return False
    return runs_only(str((tool_input or {}).get("command") or ""), _ALSO_ALWAYS)


def hold_sentence(ask: Ask) -> str:
    """One plain sentence: what he asked, what done means, and how this clears."""
    return (
        f'You asked for this and it is not done yet: "{ask.his_words}". '
        f"Done means: {ask.done_sentence} "
        "Make a step on it, or tell him plainly why not, and this clears."
    )


def judge(
    tool_name: str,
    tool_input: dict,
    *,
    asks: list[Ask],
    stepped_this_turn: bool,
    he_asked_for_this: bool,
    switched_off: bool = False,
) -> Verdict:
    """Whether this tool call would be held. Shadow: the caller logs the verdict and refuses nothing."""
    if switched_off:
        return Verdict(
            SWITCHED_OFF, why="the bell switched itself off after two false holds in a row"
        )
    open_asks = [a for a in asks if a.confirmed_by_him and not a.closed]
    if not open_asks:
        return Verdict(PASS)
    if always_passes(tool_name, tool_input):
        return Verdict(PASS)
    if he_asked_for_this or stepped_this_turn:
        return Verdict(PASS)
    first = open_asks[0]
    return Verdict(WOULD_HOLD, first.ask_id, hold_sentence(first))


def after_false_holds(was_false_hold: list[bool]) -> bool:
    """True when the last two holds were both false: the trial is over and the bell turns itself off."""
    return len(was_false_hold) >= 2 and was_false_hold[-1] and was_false_hold[-2]
