"""Circuit-breaker primitive (claim 0d628d8e, PORT-CANDIDATE 4).

Three-strikes-and-excommunicated for runtime modules. Track
consecutive failures per module name; once the failure count crosses
``DEFAULT_THRESHOLD``, the module is "tripped" — callers can check
``is_tripped(name)`` before invoking the module and skip it. A
successful call (recorded via ``record_success``) resets the counter.

State lives in ``~/.divineos/supervisor/circuit_breaker.json``. Per-
module entries: ``{name: {"failures": int, "tripped": bool, "last_failure_at": float, "reasons": [str]}}``.

## What this does NOT do

* **Does not intercept signals.** Old-OS JESUS spec described kernel-
  level signal interception (SIGSEGV/SIGILL/OOM); irrelevant for
  Python single-process. We track only failures the caller reports.
* **Does not auto-retry.** When a module is tripped, we record the
  trip; callers decide whether to skip, log, or escalate.
* **Does not auto-reset on time decay.** Phase 1 requires explicit
  reset. Phase 2 may add a time-based half-open state per the
  classical circuit-breaker pattern.
* **Does not integrate with specific subsystems.** That's Phase 2 work
  — wiring sleep phases, council walks, hooks to call this primitive.

## Why a JSON file, not the ledger

This is operational state, not append-only history. Failure-tracking
needs to be writable and updatable. The ledger captures the *event*
of trip / reset; this module's JSON is the running counter.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

# Default trip threshold. Three consecutive failures trips the breaker.
# Matches the old-OS JESUS spec's "Law of Three Strikes" but is
# tunable per-module if a caller passes a custom threshold.
DEFAULT_THRESHOLD = 3

# Cap on remembered reasons per module to bound state-file size.
MAX_REASONS_RETAINED = 10


def _state_path() -> Path:
    return Path.home() / ".divineos" / "supervisor" / "circuit_breaker.json"


def _load_state() -> dict[str, dict]:
    path = _state_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(state: dict[str, dict]) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _ensure_entry(state: dict[str, dict], name: str) -> dict:
    if name not in state:
        state[name] = {
            "failures": 0,
            "tripped": False,
            "last_failure_at": None,
            "tripped_at": None,
            "reasons": [],
        }
    return state[name]


def record_failure(name: str, reason: str = "", threshold: int = DEFAULT_THRESHOLD) -> bool:
    """Record a failure for module ``name``. Returns True if the
    breaker is now tripped (whether by this failure or already).

    ``reason`` is a short human-readable explanation; appended to a
    bounded reasons list for diagnostics.

    ``threshold`` defaults to ``DEFAULT_THRESHOLD`` but can be tuned
    per-module if the caller knows the module's failure characteristics
    warrant a different cap.
    """
    state = _load_state()
    entry = _ensure_entry(state, name)
    entry["failures"] = int(entry.get("failures", 0)) + 1
    entry["last_failure_at"] = time.time()
    if reason:
        reasons = list(entry.get("reasons", []))
        reasons.append(reason)
        entry["reasons"] = reasons[-MAX_REASONS_RETAINED:]
    if entry["failures"] >= threshold and not entry["tripped"]:
        entry["tripped"] = True
        entry["tripped_at"] = time.time()
    _save_state(state)
    return bool(entry["tripped"])


def record_success(name: str) -> None:
    """Record a successful invocation for module ``name``. Resets the
    failure count and clears tripped state.
    """
    state = _load_state()
    if name not in state:
        # Nothing to reset, but record the entry so status() shows it
        _ensure_entry(state, name)
    entry = state[name]
    entry["failures"] = 0
    entry["tripped"] = False
    entry["tripped_at"] = None
    # Keep reasons history for diagnostics across cycles
    _save_state(state)


def is_tripped(name: str) -> bool:
    """Query whether ``name`` is currently tripped."""
    state = _load_state()
    if name not in state:
        return False
    return bool(state[name].get("tripped", False))


def reset(name: str) -> bool:
    """Explicitly reset the breaker for ``name``. Returns True if the
    module had any state to clear.
    """
    state = _load_state()
    if name not in state:
        return False
    state[name] = {
        "failures": 0,
        "tripped": False,
        "last_failure_at": None,
        "tripped_at": None,
        "reasons": [],
    }
    _save_state(state)
    return True


def get_status() -> dict[str, dict]:
    """Return the full state map ``{name: entry}`` for inspection.

    Returns a copy; callers cannot mutate internal state.
    """
    return {k: dict(v) for k, v in _load_state().items()}


def tripped_modules() -> list[str]:
    """Return list of currently-tripped module names."""
    state = _load_state()
    return sorted([name for name, entry in state.items() if entry.get("tripped")])
