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

from divineos.core.atomic_io import atomic_write_text
from divineos.core.paths import marker_path as _marker_path_under_home


def marker_path() -> Path:
    return _marker_path_under_home("hedge_unresolved.json")


# Minimum hedge flags that trigger the marker. Single-flag cases are
# often legitimate honest hedging ("I'm not sure, let me check"). Two or
# more flags in a single output suggest a pattern worth investigating
# via a claim rather than leaving as floating uncertainty.
_MIN_FLAGS_TO_TRIGGER = 2


def _session_id_placeholder() -> str:
    """Return a placeholder session_id until require-goal redesign ships.

    Per Aletheia's Push 3 + Aether's freeze-at-session-birth refinement,
    the real session_id will be ``my_identity:session_started_at:uuid4``
    frozen at session-start. That helper lives in the require-goal gate
    redesign (next migration after this one). Until then, we synthesize
    a per-process session_id so dual-write population works correctly
    and the migration to the real helper is a single import-swap.
    """
    import os

    pid = os.getpid()
    try:
        from divineos.core.memory import get_core

        slot = get_core("my_identity").get("my_identity", "")
        first = slot.strip().split()[0] if slot.strip() else "unknown"
    except Exception:  # noqa: BLE001  defensive: identity lookup can fail any number of ways during bootstrap; fall back to "unknown"
        first = "unknown"
    return f"{first}:placeholder-pid-{pid}"


def set_marker(flag_count: int, flag_kinds: list[str], preview: str) -> None:
    """Write the marker. Called by the Stop hook when hedges fire.

    Only writes if ``flag_count`` meets the threshold — single-flag
    cases don't warrant claim-filing.

    Step 0 part 2 migration (signal-based-gates redesign): writes the
    legacy ``~/.divineos/hedge_unresolved.json`` AND populates the
    unified gate_marker store at
    ``~/.divineos/gate_markers/hedge_fire__<short_id>.json`` in parallel.
    Legacy read path unchanged for backward compat; PreToolUse gate
    still reads the legacy marker. The dual-write establishes the
    parallel state needed for the future read-path swap. See
    docs/signal-based-gates-design-2026-06-16.md.
    """
    if flag_count < _MIN_FLAGS_TO_TRIGGER:
        return
    path = marker_path()
    payload_ts = time.time()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "ts": payload_ts,
            "flag_count": flag_count,
            "flag_kinds": flag_kinds[:10],
            "preview": (preview or "")[:200],
        }
        atomic_write_text(path, json.dumps(payload))
    except OSError:
        pass

    # Dual-write to gate_marker. Fail-open: if the new store fails to
    # write, the legacy gate still functions; we don't want a new-store
    # bug to break the existing gate enforcement.
    try:
        from divineos.core import gate_marker as _gm

        kinds_str = ",".join(flag_kinds[:10])
        preview_str = (preview or "")[:200].replace("\n", " ")
        _gm.write_marker(
            event_type="hedge_fire",
            triggering_evidence=(
                f"flag_count={flag_count} kinds={kinds_str} preview={preview_str!r}"
            ),
            resolution_action='divineos claim "..."',
            session_id=_session_id_placeholder(),
            triggered_at=payload_ts,
        )
    except (ImportError, OSError, AttributeError):
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
    """Clear the legacy marker AND any parallel gate_marker entries.

    Step 0 part 2 migration: the dual-write in ``set_marker`` requires a
    dual-clear here so the two stores stay in sync. Callers (``divineos
    claim``) clear the legacy via this function; the gate_marker entries
    of event_type "hedge_fire" are cleared in parallel. Fail-open: if
    the new store clear fails, the legacy clear still succeeds.
    """
    path = marker_path()
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass
    try:
        from divineos.core import gate_marker as _gm

        _gm.clear_all("hedge_fire")
    except (ImportError, OSError, AttributeError):
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
