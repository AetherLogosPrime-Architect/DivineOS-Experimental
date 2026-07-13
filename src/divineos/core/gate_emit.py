"""Gate-emit noise-suppression primitive (Aletheia audit finding #2).

Each gate emits a status line on every substrate-touching action. Individually
each line is honest ("consultation ratio 0.55 — HEALTHY", "compass drift 0.03
— nominal"). Aggregated, the substrate-touching workflow surfaces 40 lines
of forgettable text on trivial edits. Aletheia's audit named this as fitness
axis failure: honest-but-unfit signal that trains the reader to skim past
the aggregate.

## The shape (Aletheia's spec verbatim)

    a single ``emit_gate_state(gate, state, last_state)`` helper that
    suppresses when ``state == last_state && state in {HEALTHY, nominal}``
    fixes ALL gates at once instead of per-gate.

## The primitive

``maybe_emit_gate(gate_name, state, content, quiet_on_repeat)`` returns the
content when the state changed OR when the state is not in the quiet-on-
repeat set. Returns an empty string otherwise. Last-state is persisted per
gate in a small JSON side-file so successive calls compare against the last
actually-emitted state.

## When to migrate a gate

- If the gate emits every substrate action AND
- The gate has a well-defined "quiet state" (HEALTHY, nominal, OK, all-clear)
- AND the reader learns nothing from repeats of that quiet state

For each migrated gate the reader still sees:
- The FIRST time the state becomes quiet after being non-quiet (transition)
- EVERY time the state is non-quiet (loud when it matters)
- SUPPRESSED subsequent quiet-state calls until state changes

## Fail-soft direction

Any I/O error → return content (do NOT suppress). Better noisy than silent
about state. The primitive is a comfort feature, not an integrity gate.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from divineos.core.paths import divineos_home


_STATE_FILE_NAME = "gate_last_states.json"


def _state_file_path() -> Path:
    """Location of the per-gate last-state persistence file."""
    return divineos_home() / _STATE_FILE_NAME


def _load_last_states() -> dict[str, str]:
    """Load the last-emitted-state map. Empty dict on any error."""
    path = _state_file_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    # Expected shape: {"gate_name": {"state": "HEALTHY", "ts": 1234.0}}
    result: dict[str, str] = {}
    for gate, entry in data.items():
        if isinstance(entry, dict):
            state = entry.get("state")
            if isinstance(state, str):
                result[gate] = state
    return result


def _save_last_state(gate_name: str, state: str) -> None:
    """Persist a single gate's last-state. Fail-soft on any I/O error."""
    path = _state_file_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Read-modify-write to preserve other gates' entries.
        data: dict = {}
        if path.exists():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    data = loaded
            except (json.JSONDecodeError, OSError):
                data = {}
        data[gate_name] = {"state": state, "ts": time.time()}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass


def maybe_emit_gate(
    gate_name: str,
    state: str,
    content: str,
    *,
    quiet_on_repeat: frozenset[str] | set[str] = frozenset({"HEALTHY", "nominal"}),
) -> str:
    """Return content when this call should surface, empty string otherwise.

    ``gate_name`` uniquely identifies the gate for last-state tracking
    (e.g. "consultation_tracker", "compass_drift", "andrew_correction").

    ``state`` is the current gate state as a bare uppercase or lowercase
    token (e.g. "HEALTHY", "DEGRADED", "SEVERE", "nominal", "drift").

    ``content`` is what the caller would emit if surfacing. Returned as-is
    on surface; empty string returned on suppress.

    ``quiet_on_repeat`` is the set of state tokens for which repeat emits
    are suppressed. Defaults to {"HEALTHY", "nominal"} per Aletheia's spec.
    States NOT in this set always surface — non-quiet states are loud by
    definition (that's the whole point of the gate).

    Suppression rule: surface when (state changed since last emit) OR
    (state not in quiet_on_repeat). Suppress when (state unchanged AND
    state in quiet_on_repeat).

    On ANY error path, returns content (fail-loud rather than fail-silent).
    """
    try:
        last_states = _load_last_states()
        last = last_states.get(gate_name)

        # If state changed OR is a non-quiet state, surface.
        if last != state or state not in quiet_on_repeat:
            _save_last_state(gate_name, state)
            return content

        # State unchanged AND quiet — suppress.
        return ""
    except Exception:  # noqa: BLE001 - fail-soft direction is content-through
        return content


__all__ = ["maybe_emit_gate"]
