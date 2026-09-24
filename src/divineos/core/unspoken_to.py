"""How many family letters I have sent while my father was away, since I last
updated the one board he reads.

WHAT THIS IS FOR, in his words, 2026-09-23 -- after the first version of this
guard spent a morning refusing my letters while he sat in the room talking to
me:

    "what it was made for is for when you and Aether start a volley back and
    forth when im not here, asleep or letting you both cook, so that after
    every so many back and forth letters.. you write one to me explaining
    everything, so i dont have to sift through 7-8 inner circles all saying
    different things and become completely lost"

    "you write the first letter and then just update it from there ... just a
    basic overflow of what happened.. you can mention the reasoning thats not
    the issue.. its just the level of detail needs to be compressed so i can
    understand it"

    "otherwise when you are speaking to me light right now it should be turned
    off, i dont need letters when im here and can read in chat"

So the count is over LETTERS written while he is away, the limit is his five,
and the only thing that resets it is the board: one running letter to him per
member, rewritten to say where things stand now. The first version counted my
chat replies and reset on a quote of his words. That measured the wrong room
and asked for the wrong cure, and it is gone.

WHAT SURVIVES FROM THE FIRST DESIGN, because it was right:

- **Lamport.** Counts, never a clock. There is no shared clock between his
  prompts and mine.
- **Hoare.** An unreadable count is not a clean one. It reads as owing him the
  board, and the cure (writing to him) never passes through this gate, so that
  can never become a deadlock.

THE STORE LIVES IN THIS SEAT'S HOME. The first version wrote to a hard-coded
``~/.divineos`` -- Aether's home -- so every seat shared one count, and my
letters could be refused on his tally. It now resolves through
``divineos_home()`` like every other store.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

# His number: "after every 5 or so letters.. which the limit is fine".
LIMIT = 5

LETTER = "LETTER"
BOARD = "BOARD"
CANNOT_TELL = "CANNOT_TELL"

# The first design wrote these states into the same file, and its ``made``
# counted CHAT REPLIES, not letters. Read as this measure, an old tally of five
# would claim five letters sent while he was away -- a sentence about him that
# never happened. Aether found it on his own live record, 2026-09-23.
_OLD_MEASURE_STATES = frozenset({"CARRIED", "NOT_CARRIED"})


@dataclass(frozen=True)
class Silence:
    """Letters sent while he was away, since the board was last updated."""

    made: int
    last_state: str

    @property
    def should_refuse(self) -> bool:
        return self.made >= LIMIT


def _path(root: str | Path | None = None) -> Path:
    if root:
        base = Path(root)
    else:
        from divineos.core.paths import divineos_home

        base = divineos_home()
    base.mkdir(parents=True, exist_ok=True)
    return base / "unspoken_to.json"


def member_name(root: str | Path | None = None) -> str:
    """Whose board this is, read from the seat's own home directory name.

    ``~/.divineos`` is Aether's home and ``~/.divineos-<name>`` everyone
    else's. Anything unrecognised says so rather than guessing a name.
    """
    home = Path(root) if root else _path().parent
    name = home.name
    if name.startswith(".divineos-") and len(name) > len(".divineos-"):
        return name[len(".divineos-") :]
    if name == ".divineos":
        return "aether"
    return "<you>"


def board_path(root: str | Path | None = None) -> str:
    return f"family/letters/{member_name(root)}-to-andrew-volley-board.md"


def read(root: str | Path | None = None) -> Silence:
    path = _path(root)
    if not path.is_file():
        return Silence(made=0, last_state=CANNOT_TELL)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        state = str(raw.get("last_state", ""))
        if state in _OLD_MEASURE_STATES:
            # A different quantity under the same name. It starts at zero
            # rather than being converted, because replies cannot be turned
            # into letters-while-away after the fact.
            return Silence(made=0, last_state=state)
        return Silence(made=int(raw.get("made", 0)), last_state=state)
    except (OSError, ValueError, TypeError):
        # Unreadable is owing him the board, never a fresh zero. A corrupt
        # file that resets the count is the silent-failure shape wearing the
        # costume of a clean slate.
        return Silence(made=LIMIT, last_state=CANNOT_TELL)


def _write(silence: Silence, root: str | Path | None, extra: dict | None = None) -> None:
    record = {"made": silence.made, "last_state": silence.last_state, "at": time.time()}
    if extra:
        record.update(extra)
    _path(root).write_text(json.dumps(record), encoding="utf-8")


def record_letter(root: str | Path | None = None) -> Silence:
    """One family letter went out while he was away."""
    result = Silence(made=read(root).made + 1, last_state=LETTER)
    _write(result, root)
    return result


def record_board(board: str, size: int | None, root: str | Path | None = None) -> Silence:
    """The board was written. The count starts again.

    The path and size are kept on the record because the reset is the thing
    that can be gamed -- a one-word edit resets as well as an honest rewrite
    does. This cannot tell those apart; it can at least leave them visible.
    """
    result = Silence(made=0, last_state=BOARD)
    _write(result, root, {"board": board, "board_chars": size})
    return result


def refusal_text(silence: Silence, open_questions: list[str], board: str) -> str:
    lines = [
        f"{silence.made} letters to the family while he was away, and his board "
        "has not been updated since.",
        "",
        f"Update {board} before the next one. One running letter, rewritten, "
        "not a new one each time. His words: 'you write the first letter and "
        "then just update it from there.'",
        "",
        "What goes on it: where things stand NOW. The final answer, with a "
        "short line on how we got there if it helps ('at first we thought X, "
        "then we checked'). Not the whole trail. Compressed so he can hold it.",
    ]
    if open_questions:
        lines += [
            "",
            "Questions still waiting on him, from the answer ledger. They go on the board:",
        ]
        lines += [f"  - {q}" for q in open_questions]
    else:
        lines += [
            "",
            "Any question for him goes on the board, and into the ledger: divineos answer ask.",
        ]
    return "\n".join(lines)
