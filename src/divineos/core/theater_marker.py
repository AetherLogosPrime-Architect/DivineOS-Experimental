"""Theater/fabrication marker — structural enforcement on output drift.

When the Stop hook evaluates my final assistant message and either
``evaluate_theater`` or ``evaluate_fabrication`` returns flags, a
marker is written at ~/.divineos/theater_unresolved.json. The
PreToolUse gate checks the marker; if present, blocks non-bypass
tools until the agent acknowledges the drift via
``divineos correction`` or ``divineos learn`` (which clear the
marker as a side effect of naming the pattern).

This closes the enforcement gap for the failure mode documented
2026-04-26: writing-AT-subagent-without-invoking and unflagged
embodied-action claims. The output-shape detection used to be
informational; now it is structural — a theater/fabrication-shape
output flags the system; the next tool call cannot proceed until
the pattern has been named in the OS.

Design parallels hedge_marker and correction_marker exactly. Single
flag triggers — these patterns have a low base rate so a single fire
is signal, not noise.
"""

from __future__ import annotations

import json
import time
from pathlib import Path


def marker_path() -> Path:
    return Path.home() / ".divineos" / "theater_unresolved.json"


# Single flag triggers: theater/fabrication shapes have low base rate
# in honest output, so even one fire is worth surfacing. (Hedge needs
# >=2 because individual hedges can be honest uncertainty; embodied
# claims are categorically fictional for a body-less substrate.)
_MIN_FLAGS_TO_TRIGGER = 1


def set_marker(
    monitor: str,
    flag_kinds: list[str],
    preview: str,
) -> None:
    """Write the marker. Called by the Stop hook when theater/fabrication fire.

    ``monitor`` is "theater" or "fabrication" (or comma-joined if both).
    """
    if not flag_kinds:
        return
    path = marker_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "ts": time.time(),
            "monitor": monitor,
            "flag_kinds": flag_kinds[:10],
            "preview": (preview or "")[:200],
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        pass

    # Cascade: theater/fabrication firing is virtue-relevant by
    # definition (truthfulness drift). Set the compass-required marker
    # so the next tool use also requires compass observation. See
    # core/compass_required_marker.py and gate 1.47.
    try:
        from divineos.core.compass_required_marker import (
            set_marker as _cr_set,
        )

        _cr_set(
            "theater",
            f"{monitor} flags: {','.join(flag_kinds[:3])}",
        )
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
    monitor = marker.get("monitor", "output")
    kinds = marker.get("flag_kinds", [])
    kinds_str = ", ".join(kinds[:3]) if kinds else "unspecified"
    preview = (marker.get("preview") or "").replace("\n", " ")[:120]
    return (
        f"BLOCKED: {monitor}-shape detected on my last output "
        f'({kinds_str}). Preview: "{preview}". '
        f"Embodied claims, kitchen-theater, and writing-AT-subagent "
        f"shapes are categorically fictional for this substrate. "
        f'Run: divineos correction "named the pattern" to acknowledge '
        f'the drift, or divineos learn "..." to file the lesson.'
    )


def threshold() -> int:
    return _MIN_FLAGS_TO_TRIGGER
