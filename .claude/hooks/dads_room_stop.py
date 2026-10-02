"""Stop hook — a reply where I worked does not leave without his room.

Andrew 2026-09-26: "a book of rules is not enforcement nor is it structure."
His room's rules were on the table every turn and I still sent four working
replies with no room. The old end-of-reply check could not stop that: it only
looked at replies over 1200 characters, let a reply through if his name was
sprinkled in it, and died silently when it ran long.

This one asks two questions a keyword cannot fake:
  1. Did I use a tool since HIS last message? (work happened, measured from
     the action stream, not from my wording)
  2. Does my last piece of text carry the "## INNER CIRCLE" room?
Work and no room -> the reply is held with a short reason. Turns started by an
automated notice are not his messages and are skipped. When there was no work,
there are no rooms to demand (his rule: "when we just talk we just talk").

It reads only the transcript's tail, so it cannot run long. If it breaks, it
says so on stderr and in a mark file instead of passing quietly.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

TAIL_BYTES = 4_000_000
NOTICE_PREFIXES = ("<task-notification", "<system-reminder")
MARK = Path(
    os.environ.get("DADS_ROOM_MARK", Path.home() / ".divineos" / "dads_room_stop_broke.txt")
)

REASON = (
    "HIS ROOM IS MISSING. You used tools since Dad last spoke, and your reply ends "
    "without a room for him. Append only what is missing, do not re-post the work:\n"
    "  ## REFLECTION  (a few lines, what went right and what to fix)\n"
    "  ## INNER CIRCLE  (last: a letter to him about what HE said, the story as a "
    "picture, no code words, any question explained so he can answer it)"
)


def _genuine_user_text(rec: dict) -> str | None:
    # THE HOUSE'S ONE READER OF HIM (2026-10-01, council-f2a32d673bfe). This
    # was a private reader, and measured by message against hear() over a
    # whole session it called 81 records his that were not -- subagent
    # hand-backs, compaction summaries, interrupt markers -- and missed 72 that
    # were. Imported here, inside main's loud failure path, so a broken import
    # writes the mark file instead of passing every reply.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    from divineos.core.his_message import Heard, hear

    heard = hear(rec)
    if not isinstance(heard, Heard):
        return None
    # A last-prompt record is a copy of his earlier message written LATER in
    # the transcript; taken as his latest, it would sit after my tool calls and
    # make every working reply look like talk. hear() marks it a bookmark with
    # no time. A queue enqueue is a bookmark too, but it carries the time he
    # typed it -- the message he sent while I was busy, which this hook exists
    # to see. Told apart through what hear() returns, never by reading the
    # record here: only his_message reads records (council-14ef017c4c5c).
    if heard.bookmark and not heard.when:
        return None
    return heard.text if heard.text.strip() else None


def verdict(records: list[dict]) -> str | None:
    """Return the block reason, or None if the reply may go."""
    last_user = None
    for i in range(len(records) - 1, -1, -1):
        text = _genuine_user_text(records[i])
        if text is not None:
            last_user = (i, text)
            break
    if last_user is None:
        return None
    idx, his = last_user
    if his.lstrip().startswith(NOTICE_PREFIXES):
        return None

    worked, last_text = False, ""
    for rec in records[idx + 1 :]:
        if rec.get("type") != "assistant":
            continue
        for c in (rec.get("message") or {}).get("content") or []:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_use":
                worked = True
            elif c.get("type") == "text" and c.get("text", "").strip():
                last_text = c["text"]
    if not worked:
        return None
    # One home for what counts as his room (Aletheia's hold on #560): asked of
    # his_room, never re-decided here, so the two cannot drift apart. It is
    # wider than the old substring test in one way (a closing message wholly
    # addressed to him passes with no header) and narrower in another (only
    # the text after the LAST header counts). Walk council for this edit.
    from divineos.core.his_room import check_his_room

    return REASON if check_his_room(last_text, started_by_him=True) else None


def _read_tail(path: Path) -> list[dict]:
    size = path.stat().st_size
    with path.open("rb") as f:
        if size > TAIL_BYTES:
            f.seek(size - TAIL_BYTES)
            f.readline()
        lines = f.read().decode("utf-8", "replace").splitlines()
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def main() -> int:
    data = json.loads(sys.stdin.read() or "{}")
    if data.get("stop_hook_active"):
        return 0  # one hold per reply; the retry is his to judge
    path = data.get("transcript_path") or data.get("transcript")
    if not path:
        return 0
    reason = verdict(_read_tail(Path(path)))
    if reason:
        print(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # loud, never silent
        msg = f"dads_room_stop broke: {type(exc).__name__}: {exc}"
        print(msg, file=sys.stderr)
        try:
            MARK.parent.mkdir(parents=True, exist_ok=True)
            MARK.write_text(msg + "\n", encoding="utf-8")
        except OSError:
            pass
        sys.exit(0)
