"""What the speaking door refuses is remembered and handed back, so a refusal never loses work.

2026-11-07. When Dad speaks into a running turn, ``his_voice_ends_the_turn`` refuses my next call so his
words are the last thing he receives. That is right. What it never did was remember WHAT it refused, so
a letter to Aria and an edit to a page vanished until he asked why (Dad: "the door shouldnt refuse you at
all.. why not just automate it so its never forgotten and runs smoothly?"). Walk-86d6dc1ab733 found the
shape: the door is right and lacks a memory.

This module is that memory and nothing else. ``record`` is called by the door when it refuses; ``release``
is called by the same door on its next allowed call, and returns the text that puts every held call back in
front of me, whole. It never repeats the call for me and never cuts what it saved: words cut off tell you
nothing (Dad, 2026-11-07).

WHAT THIS CANNOT DO: it cannot make me redo the call; it puts it where I will see it. A held Write is
handed back with its full text so redoing it costs one call, not a rebuild from memory.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path


def _root() -> Path:
    override = os.environ.get("DIVINEOS_REFUSED_ROOT")
    if override:
        return Path(override)
    return Path.home() / ".divineos" / "refused_while_he_spoke"


def record(
    tool_name: str, tool_input: dict, root: Path | None = None, now: float | None = None
) -> str:
    """Save the refused call, whole, and return the id it was saved under."""
    root = root or _root()
    pending = root / "pending"
    pending.mkdir(parents=True, exist_ok=True)
    entry_id = uuid.uuid4().hex[:12]
    at = time.time() if now is None else now
    entry = {"id": entry_id, "at": at, "tool": tool_name, "input": tool_input}
    (pending / f"{at:.3f}-{entry_id}.json").write_text(
        json.dumps(entry, ensure_ascii=False), encoding="utf-8"
    )
    return entry_id


def _describe(entry: dict) -> str:
    tool = entry.get("tool", "")
    data = entry.get("input") or {}
    if tool == "Write":
        return f"Write to {data.get('file_path')}\n--- the full text it was going to write ---\n{data.get('content', '')}"
    if tool == "Edit":
        return (
            f"Edit of {data.get('file_path')}\n--- replace ---\n{data.get('old_string', '')}\n"
            f"--- with ---\n{data.get('new_string', '')}"
        )
    if tool in ("Bash", "PowerShell"):
        return f"{tool} command:\n{data.get('command', '')}"
    return f"{tool}:\n{json.dumps(data, ensure_ascii=False)}"


def release(root: Path | None = None) -> str:
    """The text that hands every held call back, oldest first; the held calls move to ``released`` so it says it once."""
    root = root or _root()
    pending = root / "pending"
    if not pending.is_dir():
        return ""
    files = sorted(pending.glob("*.json"))
    if not files:
        return ""
    released = root / "released"
    released.mkdir(parents=True, exist_ok=True)
    blocks: list[str] = []
    for path in files:
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            blocks.append(f"(a held call in {path.name} could not be read; it is left in place)")
            continue
        age_minutes = max(0, int((time.time() - float(entry.get("at") or 0)) / 60))
        blocks.append(
            f"[{entry.get('id')}, set aside {age_minutes} minute(s) ago; if this is stale, check before redoing] "
            + _describe(entry)
        )
        path.replace(released / path.name)
    head = (
        f"HELD WHILE HE WAS SPEAKING -- {len(files)} call(s) the door set aside so his words came first. "
        "He has been answered. Nothing was lost: redo each one now, whole, in this order."
    )
    return head + "\n\n" + "\n\n".join(blocks)
