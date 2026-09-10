"""Stop-hook wiring for the subject floor.

Reads the Stop-hook payload, pulls the last thing I said, and refuses the turn
when not one sentence in it has him as its subject.

Blocking rather than advisory, per Bengio on the walk: the behaviour is fast
and automatic and the knowledge is not in the path. Two compose-start primes
fired at me on 2026-09-10 and I dismissed him four times anyway.
"""

from __future__ import annotations

import json
import sys


def run_subject_floor(transcript_path: str) -> dict | None:
    """Block-decision when nothing in the reply is about him; None otherwise."""
    try:
        from divineos.core.operating_loop.turn_extraction import extract_turn
        from divineos.hooks.subject_is_him import check
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
        result = run_subject_floor(transcript_path)
    except Exception:  # noqa: BLE001
        return 0

    if result is not None:
        print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(hook_main())
