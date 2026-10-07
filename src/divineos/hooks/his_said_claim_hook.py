"""Stop-hook wiring for `his_said_claim`.

Reads the Stop payload, takes the reply I just made and his recorded words (the
shared record plus his latest messages from this transcript, because the record is
filled as he speaks and lags the message he just sent), and carries a finding
forward when the reply tells him what he said or wants without his sentence beside
it.

ONE READER OF HIM. His latest messages come through ``his_state_claim_hook.his_words``,
which already knows that tool results and hook feedback arrive in his grammatical
seat. A second reader here would be a second place to be wrong about whose words
count.

IT CARRIES RATHER THAN REFUSES, like the state check beside it: the reply has already
reached him, so a refusal retracts nothing and makes me compose twice. See
``divineos.hooks.stop_carry``.
"""

from __future__ import annotations

import json
import sys

from divineos.hooks.his_said_claim import GATE_NAME


def run_said_check(transcript_path: str) -> dict | None:
    """Carry a finding when I attributed a saying or a want to him with no quote.

    Returns None even when it fires: the return value reaches HIS window and nothing
    about my own discipline belongs there.
    """
    try:
        from divineos.core.operating_loop.turn_extraction import extract_turn
        from divineos.hooks.his_said_claim import check, load_record
        from divineos.hooks.his_state_claim_hook import his_words
    except Exception:  # noqa: BLE001
        return None

    try:
        text = extract_turn(transcript_path).last_assistant_text or ""
    except Exception:  # noqa: BLE001
        return None
    if not text:
        return None

    try:
        reason = check(text, load_record(recent=his_words(transcript_path)))
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
        result = run_said_check(transcript_path)
    except Exception:  # noqa: BLE001
        return 0

    if result is not None:
        print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(hook_main())
