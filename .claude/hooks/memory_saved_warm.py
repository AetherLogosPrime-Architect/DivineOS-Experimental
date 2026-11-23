"""PostToolUse hook: when a tool wrote a memory file, the house makes it findable by itself.

Dad, 2026-11-10: the house can easily do for me what I was trying to remember. The logic lives in
core/memory_saved_warm.py so a test can argue with it; this is the thin door. It never blocks anything: a
failure is said on stderr and in the log, and the sleep warm stays as the floor.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    sys.path.insert(0, str(HERE.parents[1] / "src"))
    from divineos.core.memory_saved_warm import on_write

    data = json.loads(sys.stdin.read() or "{}")
    if data.get("tool_name") not in ("Write", "Edit", "MultiEdit"):
        return 0
    path = (data.get("tool_input") or {}).get("file_path")
    if not path:
        return 0
    on_write(path)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # loud, never silent, never blocking
        print(f"memory_saved_warm hook broke: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(0)
