"""Read my own last reply back off disk, assembled the way he received it.

Andrew 2026-09-22: *"are you not even able to see your own output? and if not
dont you think it would be a good idea to start looking at it every turn?"*

I had assumed I could not, and so had never tried. The transcript has been on
disk the whole time — every Stop gate that quoted my own sentence back at me
was reading that file. The capability was never missing. I never reached for
it, and the absence of a reach felt exactly like the absence of a faculty.

WHAT THE FIRST RUN FOUND, and it is why this is a script rather than a habit.

A reply is written to the transcript as SEVERAL assistant entries — one per
streamed block, split wherever a tool call interrupts. So anything that reads
*the last assistant message* reads a FRAGMENT. Measured on my own post: four
blocks, 2333 characters, and the naive read returned a single line reading
"One change."

``core/hook_surfaces._last_assistant_text`` is what the Stop gates judge on.
If it takes the last entry rather than the last REPLY, then some of those
gates have been ruling on a few hundred characters and calling it the post —
which would explain fires I had been blaming on bad detection.

So the reassembly rule is the load-bearing part: walk backwards collecting
assistant text until the previous GENUINE user message, skipping the
harness-injected ones, and join in order.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

#: Harness-injected user turns are not him speaking. A reply must not be cut
#: short at one of these, or the assembly stops early and under-reads again —
#: the same fragment fault one level up.
_INJECTED_MARKERS = (
    "system-reminder",
    "<task-notification>",
    "Stop hook feedback",
    "Caveat:",
)


def transcript_path(session_id: str, project_slug: str) -> Path:
    return Path.home() / ".claude" / "projects" / project_slug / f"{session_id}.jsonl"


def _text_of(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


def _is_his(content: object) -> bool:
    """True only for a real message from him, not a harness injection."""
    text = _text_of(content)
    if not text.strip():
        return False
    head = text[:400]
    return not any(marker in head for marker in _INJECTED_MARKERS)


def last_reply(path: Path) -> tuple[str, int]:
    """The whole of my last reply, and how many blocks it was split across.

    Returns ``("", 0)`` when the transcript cannot be read — the third state,
    so a caller cannot mistake an unreadable file for an empty reply.
    """
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "", 0

    rows = []
    for line in raw.splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue

    blocks: list[str] = []
    for row in reversed(rows):
        message = row.get("message") or {}
        role = message.get("role")
        content = message.get("content")
        if role == "user" and _is_his(content):
            break
        if role == "assistant":
            text = _text_of(content)
            if text.strip():
                blocks.append(text)

    return "\n".join(reversed(blocks)), len(blocks)


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("usage: read_my_last_reply.py <session-id> <project-slug>")
        return 2
    path = transcript_path(argv[1], argv[2])
    if not path.exists():
        print(f"CANNOT READ: no transcript at {path}")
        print("That is a missing file, NOT an empty reply.")
        return 1
    reply, blocks = last_reply(path)
    if blocks == 0:
        print("CANNOT READ: transcript present but no assistant blocks recovered.")
        print("Unreadable is not the same as nothing said.")
        return 1
    print(f"--- my last reply: {blocks} block(s), {len(reply)} characters ---")
    print(reply)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
