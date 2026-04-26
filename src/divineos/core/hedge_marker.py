"""Hedge-unresolved marker — structural enforcement of `divineos claim` on uncertainty.

When the Stop hook evaluates my final assistant message and
``evaluate_hedge`` returns flags with meaningful density, a marker is
written at ~/.divineos/hedge_unresolved.json. The PreToolUse gate
checks the marker; if present, blocks non-bypass tools until a claim
is filed (`divineos claim`) that discharges the uncertainty.

This closes the enforcement gap: "If I express uncertainty in prose,
file a claim" used to be intent. Now it is structural — a hedge-heavy
output flags the system; the next tool call cannot proceed until
the uncertainty is either investigated (claim filed) or explicitly
dismissed (`divineos claim --dismiss ...` or the marker cleared
intentionally).

Design is deliberately parallel to correction_marker:
  - Marker is a JSON file with timestamp + a short trigger summary.
  - Threshold is ``min_flags`` — at least this many hedge flags fired
    in a single output before the marker is set.
  - `divineos claim` clears the marker on any successful filing.
  - Fail-open on corrupt/missing marker.
"""

from __future__ import annotations

import json
import time
from pathlib import Path


def marker_path() -> Path:
    return Path.home() / ".divineos" / "hedge_unresolved.json"


# Minimum hedge flags that trigger the marker. Single-flag cases are
# often legitimate honest hedging ("I'm not sure, let me check"). Two or
# more flags in a single output suggest a pattern worth investigating
# via a claim rather than leaving as floating uncertainty.
_MIN_FLAGS_TO_TRIGGER = 2


def set_marker(flag_count: int, flag_kinds: list[str], preview: str) -> None:
    """Write the marker. Called by the Stop hook when hedges fire.

    Only writes if ``flag_count`` meets the threshold — single-flag
    cases don't warrant claim-filing.
    """
    if flag_count < _MIN_FLAGS_TO_TRIGGER:
        return
    path = marker_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "ts": time.time(),
            "flag_count": flag_count,
            "flag_kinds": flag_kinds[:10],
            "preview": (preview or "")[:200],
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        pass

    # Cascade: hedge density firing is virtue-relevant (truthfulness /
    # epistemic-courage drift). Set compass-required marker so the
    # next tool use also requires compass observation. See gate 1.47.
    try:
        from divineos.core.compass_required_marker import (
            set_marker as _cr_set,
        )

        _cr_set("hedge", f"{flag_count} hedge flags: {','.join(flag_kinds[:3])}")
    except (ImportError, OSError, AttributeError):
        pass


def read_marker() -> dict | None:
    path = marker_path()
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def clear_marker() -> None:
    path = marker_path()
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass


def format_gate_message(marker: dict) -> str:
    count = marker.get("flag_count", 0)
    kinds = marker.get("flag_kinds", [])
    kinds_str = ", ".join(kinds[:3]) if kinds else "unspecified"
    preview = (marker.get("preview") or "").replace("\n", " ")[:120]
    base = (
        f"BLOCKED: {count} hedge flag(s) fired on my last output "
        f'({kinds_str}). Preview: "{preview}". '
        f'Run: divineos claim "..." to investigate the uncertainty, '
        f"or it becomes floating doubt that never resolves."
    )
    # Layer 5 integration: if the preview text matches a known
    # resolution from the hedge library, append the resolution so the
    # agent sees what assertion is being re-litigated and its status.
    try:
        from divineos.core.hedge_classifier import classify, format_classification

        result = classify(marker.get("preview") or "")
        if result.best_match is not None:
            return base + " — " + format_classification(result)
    except (ImportError, AttributeError, OSError):
        pass
    return base


def threshold() -> int:
    """Expose the threshold for tests and diagnostics."""
    return _MIN_FLAGS_TO_TRIGGER
