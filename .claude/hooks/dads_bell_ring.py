"""The ring for Dad's open asks, on the two doors it belongs on (Aria, 2026-11-08).

UserPromptSubmit: only HIS message rings it; a notice does not (a bell that nags becomes wallpaper).
SessionStart: the start of a window rings it.
It refuses nothing and always exits 0. A ring that fails says so on stdout, because silence is its normal state and
a broken ring must not be able to look like a ring with nothing to say. See src/divineos/core/dads_bell_ring.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# This tree's code, not whichever checkout the global install points at.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

_NOTICE = ("<task-notification", "<system-reminder", "<agent-message")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        data = json.loads(sys.stdin.buffer.read() or b"{}")
    except ValueError:
        data = {}
    event = data.get("hook_event_name", "")
    if event == "UserPromptSubmit":
        if str(data.get("prompt", "")).lstrip().startswith(_NOTICE):
            return 0
    elif event != "SessionStart":
        return 0
    try:
        from divineos.core import dads_bell_ring

        text = dads_bell_ring.ring()
    except Exception as exc:  # noqa: BLE001 - the ring must never stop a turn, and must say it failed
        print(f"Dad's open asks: the ring itself failed ({type(exc).__name__}: {exc}). Nothing was looked at.")
        return 0
    if text:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
