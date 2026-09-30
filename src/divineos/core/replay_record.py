"""Replay a change against the real record of his turns, before building it.

Station (d) of docs/drafts/his_builds_get_the_full_workshop_draft_2026-09-30.md.
On 2026-09-30 the replay was the only thing that stopped a bad build for him
before it reached him: Aria's script overturned the self-answered rule (3 of
112 replies changed, 2 of them wrong), and a replay of 155 real writes killed
the words-at-the-write door in both windows before a line of it existed. She
had written the same script three times that night. This is that script once.

It takes a rule as two functions, before and after, runs both over every turn
of his in a real transcript, and returns the turns where they disagree, each
with what he said NEXT, because his next message is the only verdict on
whether the change mattered.

WHAT THE RESULT MUST SAY ABOUT ITSELF (Hawking, walk-730523fa0265): which file
was read, how many of his turns, and the earliest one actually read. An author
who picks the window can pick one that misses the failures, so the window is
reported, never implied.

An empty result is only honest with its search attached. ``Replay.searched``
is always filled, so "no turn differs" can be re-run and checked.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from divineos.core.his_message import Heard, hear


@dataclass(frozen=True)
class Turn:
    """One message of his, what I did in answer, and what he said next."""

    when: str
    his: str
    reply: str
    tools: tuple[str, ...]
    next_his: str = ""


@dataclass(frozen=True)
class Differs:
    turn: Turn
    before: object
    after: object


@dataclass
class Replay:
    searched: str
    turns_read: int
    earliest: str
    differs: list[Differs] = field(default_factory=list)


def read_records(path: Path) -> list[dict]:
    """Every JSON line of a transcript. A line that will not parse is skipped:
    the harness writes partial lines when a session is killed mid-write."""
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def turns_in(records: list[dict], since: str = "") -> list[Turn]:
    """His dated messages in order, each paired with my answer to it.

    A turn runs from one message of his to the next. Bookmark copies are
    skipped (they carry no date and repeat a dated record). Timestamps are
    compared as ISO strings, which sort correctly within one zone.
    """
    open_turns: list[dict] = []
    for rec in records:
        got = hear(rec)
        if isinstance(got, Heard) and not got.bookmark:
            if since and got.when and got.when < since:
                open_turns.append({"skip": True})
                continue
            open_turns.append({"when": got.when, "his": got.text, "reply": [], "tools": []})
            continue
        if not open_turns or open_turns[-1].get("skip") or rec.get("type") != "assistant":
            continue
        for c in (rec.get("message") or {}).get("content") or []:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "text" and c.get("text"):
                open_turns[-1]["reply"].append(c["text"])
            elif c.get("type") == "tool_use":
                open_turns[-1]["tools"].append(str(c.get("name") or ""))

    kept = [t for t in open_turns if not t.get("skip")]
    turns = []
    for i, t in enumerate(kept):
        nxt = kept[i + 1]["his"] if i + 1 < len(kept) else ""
        turns.append(
            Turn(
                when=t["when"],
                his=t["his"],
                reply="\n".join(t["reply"]),
                tools=tuple(t["tools"]),
                next_his=nxt,
            )
        )
    return turns


def replay(
    path: Path,
    before: Callable[[Turn], object],
    after: Callable[[Turn], object],
    since: str = "",
) -> Replay:
    """Run both rules over every turn of his in ``path``; keep where they differ."""
    turns = turns_in(read_records(path), since=since)
    result = Replay(
        searched=f"{path} since {since or 'the start'}",
        turns_read=len(turns),
        earliest=turns[0].when if turns else "",
    )
    for t in turns:
        b, a = before(t), after(t)
        if b != a:
            result.differs.append(Differs(t, b, a))
    return result


def render(result: Replay, width: int = 110) -> str:
    """Plain text: the window first, then each differing turn with his next words."""
    lines = [
        f"searched: {result.searched}",
        f"his turns read: {result.turns_read}, earliest: {result.earliest or 'none'}",
        f"turns where the rule changes: {len(result.differs)}",
    ]
    for d in result.differs:
        t = d.turn
        lines.append("")
        lines.append(f"{t.when}  before={d.before!r}  after={d.after!r}")
        lines.append(f"  he said:   {t.his[:width]!r}")
        lines.append(f"  he said next: {t.next_his[:width]!r}")
    return "\n".join(lines)
