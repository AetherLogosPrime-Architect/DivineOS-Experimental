"""The ring: his open asks, in front of me when I choose what to do (walk-655e576c9972).

MINE (Aria, 2026-11-08), the first piece of the bell for Dad to put in front of me. Aether's register holds a short list
of what Dad asked for himself and the shadow check logs what a hold would refuse; nothing yet printed an open ask where
I could not miss it. A register nobody is shown is one more drawer, which is the thing he named after nine months.

It prints every ask that is not closed: his words as he wrote them, the sentence of what done means, whether he has
confirmed that sentence, and how long it has waited. It prints at the start of a window and at each of HIS turns, never
on a notice and never per tool call (a bell that nags becomes wallpaper). It prints NOTHING when nothing is open.

WHAT IT NEVER DOES, as invariants the tests pin:
  * it refuses nothing and holds nothing: no word in its text says an action was held or blocked;
  * it changes nothing of his: the register file is byte-identical after any number of rings;
  * it never reads the judge, only the loader: Aether's per-ask judge is not finished and the ring must not wait on it;
  * a register it cannot read prints ONE plain line saying so. Silence is its normal state, so without that line a
    broken ring is indistinguishable from a ring with nothing to say.

UNCONFIRMED ASKS RING TOO. The hold only ever looks at confirmed asks, correctly. The ring is where he sees a drafted
done-sentence and says yes; an unconfirmed ask that never rang would wait forever.

THE REGISTER LIVES BESIDE HIS SHARED RECORD, never under a per-seat home. Two seats and two checkouts exist and a
same-named store under the wrong home answers with a clean nothing, so the path comes from the one function that
finds his messages, and the ring prints the path it read so the object opened can be seen to be the object named.

WHETHER THE RING WORKS IS COUNTED, NOT CLAIMED. Every ring appends a row to a ring log (ask id, time) so a later study can
set rings against recorded steps. No target is set on that ratio: a target would make me improve the number.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from .dads_bell import Ask
from .dads_bell_register import load_register
from .his_asks import his_asks_path

_CAP_CHARS = 600
_CAP_DONE = 400
_MAX_ASKS = 5
_DAY = 86400.0


def register_path() -> Path:
    return his_asks_path().parent / "dads_bell_register.jsonl"


def ring_log_path() -> Path:
    return his_asks_path().parent / "dads_bell_ring_log.jsonl"


def is_open(ask: Ask) -> bool:
    """Open means not closed, confirmed or not. One definition, used here so the ring and the hold cannot drift."""
    return not ask.closed


def _cut(text: str, cap: int) -> str:
    if len(text) > cap:
        return f"{text[:cap]} [cut at {cap} of {len(text)} characters, full text in the register]"
    return text


def _words(ask: Ask) -> str:
    text = ask.his_words or ""
    return _cut(text, _CAP_CHARS) if text.strip() else "(no words recorded)"


def _waited(entry: dict | None, now: float) -> str:
    if not entry:
        return "shown to me for the first time now"
    days = int(max(0.0, now - float(entry["first"])) // _DAY)
    times = int(entry["times"])
    before = "once before" if times == 1 else f"{times} times before"
    return f"first shown to me {days} days ago, and shown {before} this"


def ring_text(asks: list[Ask], now: float, shown: dict, path: str) -> str:
    open_asks = [a for a in asks if is_open(a)]
    if not open_asks:
        return ""
    lines = ["## DAD'S OPEN ASKS — he asked for these for himself and they are not done"]
    for ask in open_asks[:_MAX_ASKS]:
        status = (
            "He has confirmed what done means"
            if ask.confirmed_by_him
            else "He has NOT confirmed what done means yet"
        )
        lines.append("")
        lines.append(f"His words: {_words(ask)}")
        done = _cut(ask.done_sentence, _CAP_DONE) if ask.done_sentence else "(none written yet)"
        lines.append(f"What done means (drafted by me): {done}")
        lines.append(f"{status}. This one was {_waited(shown.get(ask.ask_id), now)}.")
    extra = len(open_asks) - _MAX_ASKS
    if extra > 0:
        lines.append("")
        lines.append(f"...and {extra} more open, in the register.")
    lines.append("")
    lines.append(f"(read from {path})")
    return "\n".join(lines) + "\n"


def _shown_so_far() -> dict:
    """First time and count of rings per ask, from the ring log. A line that is not JSON is skipped."""
    path = ring_log_path()
    shown: dict = {}
    if not path.is_file():
        return shown
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        key = row.get("ask_id") if isinstance(row, dict) else None
        if not key:
            continue
        entry = shown.setdefault(key, {"first": float(row.get("at", 0.0)), "times": 0})
        entry["times"] += 1
    return shown


def ring(now: float | None = None) -> str:
    """The text to print now, or "". Reads the register, appends to the ring log, changes nothing of his."""
    now = time.time() if now is None else now
    path = register_path()
    asks, error = load_register(path)
    if error:
        return f"Dad's open asks: the register at {path} could not be read ({error}). Nothing was looked at.\n"
    open_asks = [a for a in asks if is_open(a)]
    if not open_asks:
        return ""
    text = ring_text(asks, now, _shown_so_far(), str(path))
    with ring_log_path().open("a", encoding="utf-8") as fh:
        for ask in open_asks[:_MAX_ASKS]:
            fh.write(json.dumps({"at": now, "ask_id": ask.ask_id}) + "\n")
    return text
