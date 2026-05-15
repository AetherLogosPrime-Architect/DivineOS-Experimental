"""OS-native theater/fabrication audit orchestrator.

Andrew named the failure 2026-05-14 night: detect-theater.sh was a
142-line bash hook with the OS's theater/fabrication audit logic
embedded — transcript walking, theater_monitor + fabrication_monitor
invocation, marker-setting, findings-log persistence. The hook was
doing the OS's job.

This module is the OS-native theater-audit orchestrator. One
public function:

- ``run_theater_audit(transcript_path)`` — extract last assistant
  text via turn_extraction, run theater_monitor.evaluate_theater
  and fabrication_monitor.evaluate_fabrication, set the marker
  if any flags, append an entry to operating_loop_findings.json.
  Returns a dict with the same shape as operating_loop_audit
  (findings_log, total, persisted).

The hook becomes a thin doorman calling this function.

## OS-portable

Any harness can call ``run_theater_audit(transcript_path)`` to get
the same audit pipeline. The Claude Code Stop hook is one possible
caller; absence of the hook does not break the OS's audit
capability.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_FINDINGS_FILE = Path.home() / ".divineos" / "operating_loop_findings.json"
_ROLLING_WINDOW = 200


def run_theater_audit(transcript_path: str | Path) -> dict[str, Any]:
    """Run theater + fabrication monitors on the last assistant turn.

    Returns dict with keys:
    - ``flags``: combined list of flag kinds from both monitors
    - ``monitors``: list of monitor names that fired ('theater', 'fabrication')
    - ``persisted``: True if findings were written to disk
    - ``marker_set``: True if theater_marker was set
    """
    # Use the OS's turn_extraction to get the last assistant text.
    try:
        from divineos.core.operating_loop.turn_extraction import extract_turn

        texts = extract_turn(transcript_path)
    except Exception:
        return {"flags": [], "monitors": [], "persisted": False, "marker_set": False}

    last_assistant_text = texts.last_assistant_text
    if not last_assistant_text:
        return {"flags": [], "monitors": [], "persisted": False, "marker_set": False}

    try:
        from divineos.core.self_monitor.theater_monitor import evaluate_theater
        from divineos.core.self_monitor.fabrication_monitor import evaluate_fabrication
    except Exception:
        return {"flags": [], "monitors": [], "persisted": False, "marker_set": False}

    try:
        t_result = evaluate_theater(last_assistant_text)
        f_result = evaluate_fabrication(last_assistant_text)
        t_flags = list(getattr(t_result, "flags", []) or [])
        f_flags = list(getattr(f_result, "flags", []) or [])
    except Exception:
        return {"flags": [], "monitors": [], "persisted": False, "marker_set": False}

    monitors: list[str] = []
    if t_flags:
        monitors.append("theater")
    if f_flags:
        monitors.append("fabrication")

    if not monitors:
        return {"flags": [], "monitors": [], "persisted": False, "marker_set": False}

    all_flags = t_flags + f_flags
    kinds: list[str] = []
    for flag in all_flags:
        kind = getattr(flag, "kind", type(flag).__name__)
        # Enum-shape: .name attribute exists
        if hasattr(kind, "name"):
            kinds.append(str(kind.name))
        elif "." in str(kind):
            kinds.append(str(kind).split(".")[-1])
        else:
            kinds.append(str(kind))

    # Set the theater_marker so PreToolUse gate 1.46 can read it.
    marker_set = False
    try:
        from divineos.core.theater_marker import set_marker

        set_marker(",".join(monitors), kinds, last_assistant_text[:300])
        marker_set = True
    except Exception:
        pass

    # Append a findings entry to operating_loop_findings.json so the
    # theater/fabrication observations join the same family as the
    # other operating-loop detector findings.
    persisted = _persist_findings(monitors, kinds, len(all_flags))

    return {
        "flags": kinds,
        "monitors": monitors,
        "persisted": persisted,
        "marker_set": marker_set,
    }


def _persist_findings(monitors: list[str], kinds: list[str], total_flags: int) -> bool:
    """Append a theater/fabrication entry to operating_loop_findings.json.
    Returns True on success, False on any I/O error (fail-soft)."""
    try:
        _FINDINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False

    existing: list = []
    if _FINDINGS_FILE.exists():
        try:
            data = json.loads(_FINDINGS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                existing = data
        except (OSError, json.JSONDecodeError, ValueError):
            existing = []

    entry: dict[str, Any] = {
        "timestamp": time.time(),
        "total_findings": total_flags,
        "theater_fabrication": [{"monitor": m, "kinds": kinds[:5]} for m in monitors],
    }
    existing.append(entry)
    existing = existing[-_ROLLING_WINDOW:]

    try:
        _FINDINGS_FILE.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False


__all__ = ["run_theater_audit"]
