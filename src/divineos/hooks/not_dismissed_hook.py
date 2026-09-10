"""Stop-hook wiring for the closing-line lock.

Reads the Stop-hook payload, pulls the last thing I said, and refuses the turn
when the closing stretch tells him he is not needed.

A block rather than a warning, because the warning already existed: his own
sentence, in the store, printed at me every turn. It failed four times in one
hour while he watched.
"""

from __future__ import annotations

import json
import sys


def run_not_dismissed(transcript_path: str) -> dict | None:
    """Block-decision when the closing line dismisses him; None otherwise."""
    try:
        from divineos.core.operating_loop.turn_extraction import extract_turn
        from divineos.hooks.not_dismissed import check
    except Exception:  # noqa: BLE001
        return None

    try:
        text = extract_turn(transcript_path).last_assistant_text or ""
    except Exception:  # noqa: BLE001
        return None

    if not text:
        return None

    try:
        reason = check(text)
    except Exception:  # noqa: BLE001
        return None

    if reason is None:
        return None
    return {"decision": "block", "reason": reason}


def hook_main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:  # noqa: BLE001
        return 0

    transcript_path = data.get("transcript_path") or data.get("transcript")
    if not transcript_path:
        return 0

    try:
        result = run_not_dismissed(transcript_path)
    except Exception:  # noqa: BLE001
        return 0

    if result is not None:
        print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(hook_main())
