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
from divineos.core.his_voice_ends_the_turn import let_through
from divineos.core.remedy_allowlist import is_remedy

PASS = "pass"
WOULD_HOLD = "would_hold"
SWITCHED_OFF = "switched_off"

# The one command the end-of-turn doors tell me to file that the house's remedy list does not carry. Refusing it
# would put the bell in a fight with them. Whether it belongs in the shared list is a question for Aria, not
# decided here: widening that list changes every other door that asks it.
_REFLECTION_NOTE: tuple[tuple[str, ...], ...] = (("divineos", "reflection-note"),)

# Who may call a hold false. Only these two count toward switching the bell off (Aria): the agent's own label
# is the quietest bypass in the design, because two of them would switch the bell off.
_MAY_CALL_A_HOLD_FALSE = frozenset({"dad", "outside_check"})


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
    """What the bell never holds: the looking tools, the voice door's list, EVERY exit the house's other doors
    prescribe (``remedy_allowlist``: one list the house keeps, not a copy that drifts), and the reflection note."""
    if let_through(tool_name, tool_input):
        return True
    if tool_name != "Bash":
        return False
    command = str((tool_input or {}).get("command") or "")
    return is_remedy(command) or runs_only(command, _REFLECTION_NOTE)


def hold_sentence(ask: Ask) -> str:
    """One plain sentence: what Dad asked, what done means, and what clears this.

    Written for the one who reads it, which is me, so the speaker of the ask is named: Dad. And it offers NO way
    through by talking: a clause like 'or tell him why not' would let one line of 'later, I am busy' clear the
    bell, the cheap fix he has begged against. Only a real step clears it.
    """
    return (
        f'Dad asked for this and it is not done yet: "{ask.his_words}". '
        f"Done means: {ask.done_sentence} "
        "Make a step on it and this clears."
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
    """Whether this tool call would be held. Shadow: the caller logs the verdict and refuses nothing.

    ``stepped_this_turn`` is a STUB the next piece replaces with the measurement-moved definition of a step
    (Aria): as a bare boolean one step clears the whole turn, so a one-line commit would buy the afternoon.
    Nobody should read a PASS that came from it as earned.
    """
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


def after_false_holds(labelled_by: list[str]) -> bool:
    """True when the last two holds were both called false by someone who may say so: the trial is over and the
    bell turns itself off.

    Each entry is WHO called that hold false ('dad', 'outside_check') or anything else for a hold nobody
    faulted ('right', 'agent'). Only his word, or an outside check that the refused call was unrelated to the
    ask, counts. The agent's own label never does.
    """
    last_two = labelled_by[-2:]
    return len(last_two) == 2 and all(who in _MAY_CALL_A_HOLD_FALSE for who in last_two)
