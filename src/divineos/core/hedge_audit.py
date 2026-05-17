"""OS-native hedge density audit.

Andrew named the failure 2026-05-14 night: detect-hedge.sh was a
97-line bash hook with transcript walking, hedge_monitor invocation,
and marker-setting all embedded. This module is the OS-native
replacement.

## What it does

When called with a transcript path, extracts the last assistant
text via turn_extraction, runs hedge_monitor.evaluate_hedge, and
if the verdict has >= threshold() flags, sets the hedge_marker
so PreToolUse gates can refuse tool use until a claim is filed.

## OS-portable

Any harness can call ``run_hedge_audit(transcript_path)`` to get
the same audit pipeline.
"""

from __future__ import annotations

# Module-level guardrail marker — Aletheia Finding 48 class-fix
# 2026-05-14. CI test (tests/test_guardrail_marker_consistency.py)
# walks src/ and asserts every file with this marker set to True is
# listed in scripts/guardrail_files.txt. Prevents the next refactor
# from silently removing self-enforcement code from multi-party review.
__guardrail_required__ = True

from pathlib import Path
from typing import Any

# Minimum text length below which hedge-density detection is not
# meaningful — too short to have density signal.
_MIN_TEXT_LEN = 200


def run_hedge_audit(transcript_path: str | Path) -> dict[str, Any]:
    """Run hedge density audit on the last assistant turn.

    Returns dict with keys:
    - ``flag_count``: number of hedge flags found
    - ``threshold``: hedge_marker threshold for firing
    - ``marker_set``: True if hedge_marker was set
    - ``kinds``: list of flag kind names (if marker fired)
    """
    try:
        from divineos.core.operating_loop.turn_extraction import extract_turn

        texts = extract_turn(transcript_path)
    except Exception:  # noqa: BLE001 - observability boundary
        return {"flag_count": 0, "threshold": 0, "marker_set": False, "kinds": []}

    last_assistant_text = texts.last_assistant_text
    if not last_assistant_text or len(last_assistant_text) < _MIN_TEXT_LEN:
        return {"flag_count": 0, "threshold": 0, "marker_set": False, "kinds": []}

    try:
        from divineos.core.self_monitor.hedge_monitor import evaluate_hedge
        from divineos.core.hedge_marker import set_marker, threshold
    except Exception:  # noqa: BLE001 - observability boundary
        return {"flag_count": 0, "threshold": 0, "marker_set": False, "kinds": []}

    try:
        verdict = evaluate_hedge(last_assistant_text)
        flags = list(getattr(verdict, "flags", []) or [])
    except Exception:  # noqa: BLE001 - observability boundary
        return {"flag_count": 0, "threshold": 0, "marker_set": False, "kinds": []}

    try:
        thresh = int(threshold())
    except Exception:  # noqa: BLE001 - observability boundary
        thresh = 2  # safe default matching pre-refactor behavior

    if len(flags) < thresh:
        return {
            "flag_count": len(flags),
            "threshold": thresh,
            "marker_set": False,
            "kinds": [],
        }

    # Build kind names from the flag enums/dataclasses.
    kinds: list[str] = []
    for flag in flags:
        kind = getattr(flag, "kind", type(flag).__name__)
        if hasattr(kind, "name"):
            kinds.append(str(kind.name))
        elif "." in str(kind):
            kinds.append(str(kind).split(".")[-1])
        else:
            kinds.append(str(kind))

    marker_set = False
    try:
        set_marker(len(flags), kinds, last_assistant_text[:300])
        marker_set = True
    except Exception:  # noqa: BLE001 - observability boundary
        pass

    return {
        "flag_count": len(flags),
        "threshold": thresh,
        "marker_set": marker_set,
        "kinds": kinds,
    }


__all__ = ["run_hedge_audit"]
