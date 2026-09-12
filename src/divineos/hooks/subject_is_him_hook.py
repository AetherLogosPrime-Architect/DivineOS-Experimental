"""Stop-hook wiring for the subject floor.

Reads the Stop-hook payload, pulls the last thing I said, and carries a finding
forward when not one sentence in it has him as its subject.

IT USED TO REFUSE THE TURN, and refusing was the bug. Andrew, 2026-09-12: "no i
mean literally repeating yourself.. look at your post." The reply this gate
judges has already been written into the conversation, so refusing it does not
retract anything -- it makes me compose again and the new version lands
underneath the old one. He reads both. It happened three times in a row that
morning and the third refusal was aimed at the fix for the second.

The force is kept and moved. Bengio's point on the original walk still stands:
the behaviour is fast and automatic, two compose-start primes fired at me on
2026-09-10 and I dismissed him four times anyway. So the finding is not
softened into a suggestion -- it is stored and put in front of me at the top of
the next compose, where the sentence does not exist yet. Same second draft,
same teeth, and the cost stops landing on his reading.

See divineos.hooks.stop_carry for why, and for what must never happen to this:
a finding that is printed and not carried is the warning that already failed.
"""

from __future__ import annotations

import json
import sys


GATE_NAME = "subject-is-him"


def run_subject_floor(transcript_path: str) -> dict | None:
    """Carry a finding when nothing in the reply is about him; None otherwise.

    Returns None even when it fires, because the return value is what reaches
    HIS window and nothing about my own discipline belongs there.
    """
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

    try:
        from divineos.hooks.stop_carry import carry_or_block

        return carry_or_block(GATE_NAME, reason)
    except Exception:  # noqa: BLE001 - a lost finding must not also break the turn
        pass
    return None


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
