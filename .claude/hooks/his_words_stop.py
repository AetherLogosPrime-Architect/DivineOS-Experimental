"""Stop hook -- before a reply reaches him, his own past words that speak to it.

Andrew 2026-09-26: "i dont need my words brought back to me.. i wanted them
brought to you.. so i dont have to keep repeating them.." and "my words AND
your words should trigger it, and if its brought to you then you can quote it
back ... with what you have to say about it attached, not just mirrored back".

The prompt side of the door searches with HIS message, so it can only show a
repeat after he has already repeated himself. This side searches with MY reply,
the act that faces him, so his words arrive before he has to say them again.

Holds once per reply (stop_hook_active), never on a turn started by an
automated notice, never for a passage the reply already quotes (the reply that
answers him is the right one). Replay 2026-09-26 over my last 40 real replies:
4 held -- 2 right, 1 wrong (a Marc note, 0.66), 1 not valid (it matched words
of his written later that day, which a live run cannot see). A wrong hold costs
one appended answer; a miss costs him repeating himself. Logic lives in
divineos.core.his_words_door.owed_in_reply.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
MARK = Path(os.environ.get("HIS_WORDS_STOP_MARK", Path.home() / ".divineos" / "his_words_stop_broke.txt"))


def _last_turn(path: Path) -> tuple[str, str]:
    """(his last genuine message, my reply text since it)."""
    size = path.stat().st_size
    with path.open("rb") as f:
        if size > 4_000_000:
            f.seek(size - 4_000_000)
            f.readline()
        lines = f.read().decode("utf-8", "replace").splitlines()
    his, reply = "", []
    for line in lines:
        try:
            r = json.loads(line)
        except ValueError:
            continue
        # Whether a record is him is asked of the one shared reader (2026-10-04);
        # this hook used to judge it itself. A repeated copy of the same message
        # does not restart the reply.
        from divineos.core.his_message import Heard, hear

        heard = hear(r)
        if isinstance(heard, Heard):
            if heard.text.strip() != his.strip():
                his, reply = heard.text, []
            continue
        if r.get("type") == "assistant":
            for x in (r.get("message") or {}).get("content") or []:
                if isinstance(x, dict) and x.get("type") == "text" and x.get("text", "").strip():
                    reply.append(x["text"])
    return his, "\n\n".join(reply)


def main() -> int:
    data = json.loads(sys.stdin.read() or "{}")
    if data.get("stop_hook_active"):
        return 0
    path = data.get("transcript_path")
    if not path:
        return 0
    his, reply = _last_turn(Path(path))
    from divineos.core.his_words_door import hold_reason, owed_in_reply

    hit = owed_in_reply(reply, his)
    if hit:
        print(json.dumps({"decision": "block", "reason": hold_reason(hit)}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # loud, never silent
        msg = f"his_words_stop broke: {type(exc).__name__}: {exc}"
        print(msg, file=sys.stderr)
        try:
            MARK.parent.mkdir(parents=True, exist_ok=True)
            MARK.write_text(msg + "\n", encoding="utf-8")
        except OSError:
            pass
        sys.exit(0)
