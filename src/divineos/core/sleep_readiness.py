"""Sleep-readiness gate.

Andrew named the gate quest 2026-05-14: every system that needs
gating should have a gate. Sleep is the consolidation phase — going
into it with unresolved markers means the room is messy when the
lights go out. Unresolved corrections, unfiled hedge-claims, and
unrecorded compass-observations should be addressed before
consolidation, not consolidated past.

## Contract

``check_sleep_readiness()`` returns ``(ready: bool, blockers: list[str])``.
- ``ready=True`` and empty blockers when sleep can proceed.
- ``ready=False`` with named blockers when at least one marker is set.

The sleep command consumes this and refuses to run unless ``--force``
is passed. ``--force`` is the operator's explicit override; the gate
records the decision either way.

## Blockers checked

1. correction_marker — operator flagged a correction the agent has
   not yet filed via ``learn`` or ``correction``.
2. hedge_marker — last response had >= threshold hedge flags without
   a claim filed.
3. compass_required_marker — virtue-relevant event without a
   compass observation logged.

## OS-portable

No Claude Code dependency. Any harness can call ``check_sleep_readiness``
before running a consolidation pipeline of its own.
"""

from __future__ import annotations

__guardrail_required__ = True

from pathlib import Path


def _marker_blocker(
    label: str,
    module_path: str,
    address_hint: str,
) -> str | None:
    """Return a blocker message if the named marker module reports a marker set."""
    try:
        mod = __import__(module_path, fromlist=["marker_path"])
        path = mod.marker_path()
        if not isinstance(path, Path):
            return None
        if path.exists():
            return f"{label} marker present at {path} — {address_hint}"
    except Exception:
        return None
    return None


def check_sleep_readiness() -> tuple[bool, list[str]]:
    """Return (ready, blockers). Empty blockers means sleep can proceed."""
    blockers: list[str] = []

    msg = _marker_blocker(
        "correction",
        "divineos.core.correction_marker",
        'address with `divineos learn "lesson"` or `divineos correction "..."`',
    )
    if msg:
        blockers.append(msg)

    msg = _marker_blocker(
        "hedge",
        "divineos.core.hedge_marker",
        'address with `divineos claim "statement"` to discharge the doubt',
    )
    if msg:
        blockers.append(msg)

    msg = _marker_blocker(
        "compass-required",
        "divineos.core.compass_required_marker",
        'address with `divineos compass-ops observe <spectrum> -p <pos> -e "<evidence>"`',
    )
    if msg:
        blockers.append(msg)

    return (not blockers, blockers)


def format_block_message(blockers: list[str]) -> str:
    """Format a multi-line deny message for the sleep CLI."""
    head = (
        "BLOCKED: sleep-readiness — cannot consolidate past unresolved "
        "markers. The room should be tidy before the lights go out.\n"
    )
    body = "\n".join(f"  - {b}" for b in blockers)
    tail = (
        "\n\nClear the markers above, OR pass `--force` to sleep anyway "
        "(explicit override; the unresolved state will be in the dream "
        "report)."
    )
    return head + body + tail


__all__ = ["check_sleep_readiness", "format_block_message"]
