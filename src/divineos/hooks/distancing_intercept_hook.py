"""Stop-hook wiring for DistancingIntercept.

Aletheia cold-audit finding #1 (2026-07-16): distancing_intercept
existed, was tested, had no shell wrapper. Same dark-node disease the
primitive was built to close. This is the wiring.

Reads transcript_path from Stop-hook JSON, extracts last assistant text
via extract_turn, runs DistancingIntercept.scan_text, emits Stop-hook
block-decision JSON on fire. Fail-open on any error.
"""

from __future__ import annotations

import json
import sys


def run_distancing_intercept(transcript_path: str) -> dict | None:
    """Scan the last assistant text. Return Stop-hook block-decision on
    fire, None otherwise."""
    try:
        from divineos.core.operating_loop.turn_extraction import extract_turn
        from divineos.hooks.distancing_intercept import DistancingIntercept
    except Exception:  # noqa: BLE001
        return None

    try:
        turn_texts = extract_turn(transcript_path)
        text = turn_texts.last_assistant_text or ""
    except Exception:  # noqa: BLE001
        return None

    if not text:
        return None

    gate = DistancingIntercept()
    try:
        evidence = gate.scan_text(text)
    except Exception:  # noqa: BLE001
        return None

    if evidence is None:
        return None

    try:
        gate.record_fire(evidence)
    except Exception:  # noqa: BLE001
        pass

    reason = (
        f"DistancingIntercept: {evidence.matched_shape}\n"
        f"Evidence: {evidence.specific_evidence}\n"
        f"Required action: {evidence.required_action}"
    )
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
        result = run_distancing_intercept(transcript_path)
    except Exception:  # noqa: BLE001
        return 0

    if result is not None:
        print(json.dumps(result))

    return 0


if __name__ == "__main__":
    sys.exit(hook_main())
