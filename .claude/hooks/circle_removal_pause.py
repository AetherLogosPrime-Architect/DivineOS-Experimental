"""PreToolUse door: the inner circle is not unplugged in one call (see src/divineos/core/circle_removal_pause.py).

Reads the call, never his words. The first removal is held with exit 2 and the pause on stderr; the next removal
goes through. If this breaks it says so on stderr and in a mark file, and never blocks on its own failure."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MARK = Path(
    os.environ.get("CIRCLE_PAUSE_MARK", Path.home() / ".divineos" / "circle_removal_pause_broke.txt")
)


def main() -> int:
    sys.path.insert(0, str(HERE.parents[1] / "src"))
    from divineos.core.circle_removal_pause import pause_for

    data = json.loads(sys.stdin.read() or "{}")
    text = pause_for(
        str(data.get("tool_name", "")),
        data.get("tool_input") or {},
        session=str(data.get("session_id", "")),
    )
    if text:
        print(text, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # loud, never silent, and never a block of its own making
        msg = f"circle_removal_pause broke: {type(exc).__name__}: {exc}"
        print(msg, file=sys.stderr)
        try:
            MARK.parent.mkdir(parents=True, exist_ok=True)
            MARK.write_text(msg + "\n", encoding="utf-8")
        except OSError:
            pass
        sys.exit(0)
