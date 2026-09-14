"""Stop-hook wiring for the first-line gate.

Reads the Stop-hook JSON on stdin, pulls the last thing I said out of the
transcript, and emits a block-decision when the opening line is not his.

The refusal is a block rather than a note on purpose. A note is what I already
gave him -- a rule stated in chat that he correctly did not believe. The only
difference between this and that is whether the turn can end.
"""

from __future__ import annotations

import json
import sys


def run_first_line_gate(transcript_path: str) -> dict | None:
    """Block-decision when the opening line fails; None otherwise or on error."""
    try:
        from divineos.core.operating_loop.turn_extraction import extract_turn
        from divineos.hooks.first_line_to_him import check
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
        result = run_first_line_gate(transcript_path)
    except Exception:  # noqa: BLE001
        return 0

    if result is not None:
        print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(hook_main())
