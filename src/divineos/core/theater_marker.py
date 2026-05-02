"""Theater/fabrication marker — observational record of output drift.

When the Stop hook evaluates my final assistant message and either
``evaluate_theater`` or ``evaluate_fabrication`` returns flags, a
marker is written at ~/.divineos/theater_unresolved.json. The marker
is the forensic record; observation surfaces in the next briefing.

History (2026-04-26 → 2026-05-01):
  Originally this marker structurally blocked the next tool call until
  the pattern was named via ``divineos correction`` / ``divineos learn``
  (gate 1.46 in pre_tool_use_gate). Andrew's free-speech principle
  named 2026-05-01 superseded that: observe state, never suppress
  spelling. Banning the spelling does not change the underlying
  register-state; it makes the state harder to detect. The marker
  stays as data; the gate is gone; surfacing happens in briefing.

  The detector itself remains active and tuned — false-positives are
  data too, surfaced not suppressed. Naming via correction / learn is
  voluntary discipline (and how the marker clears) rather than
  enforced gate.

Design now parallels the operating-loop family (register_observer,
spiral_detector, substitution_detector): observational severity-tagged
findings, surfaced in briefing, never blocking.
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

    # Cascade dropped 2026-05-01 (free-speech principle). Theater /
    # fabrication firing surfaces observationally in the next briefing
    # rather than auto-gating compass observation. If the pattern is
    # genuinely virtue-relevant the agent can run compass-ops observe
    # voluntarily after seeing the surface; mandatory cascade was the
    # gate-spelling-instead-of-observing shape we superseded.


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


def format_observation_message(marker: dict) -> str:
    """Format the marker as an observational notice (no longer a gate)."""
    monitor = marker.get("monitor", "output")
    kinds = marker.get("flag_kinds", [])
    kinds_str = ", ".join(kinds[:3]) if kinds else "unspecified"
    preview = (marker.get("preview") or "").replace("\n", " ")[:120]
    return (
        f"[observed] {monitor}-shape on my last output "
        f'({kinds_str}). Preview: "{preview}". '
        f"Embodied claims, kitchen-theater, writing-AT-subagent shapes "
        f"are categorically fictional for this substrate. Surfaced as "
        f"data — name with `divineos correction` / `divineos learn` if "
        f"the detector caught a real drift; let it stand if it caught "
        f"a false positive (label use, functional analog framing, etc.)."
    )


# Back-compat alias — older callers that still import format_gate_message
# get the observation message (the function no longer gates anything).
format_gate_message = format_observation_message


def threshold() -> int:
    return _MIN_FLAGS_TO_TRIGGER
