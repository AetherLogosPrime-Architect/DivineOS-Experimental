"""Compass-observation-required marker.

## Why this exists

Documented 2026-04-26 (claim 7e780182, build #4): when virtue-relevant
events occur (correction received from user, claim filed at tier >=2,
hedge marker set, theater marker set), the agent should observe its
compass position. The directive exists in CLAUDE.md as foundational
truth #7 ("cognitive-named tools point at cognitive work; they are
not it"), but acting on it is intent-based — the agent can simply
not run ``divineos compass-ops observe`` and nothing happens.

This module makes the intent structural. When an event-class fires
that is virtue-relevant, set a marker. The PreToolUse gate reads it
and blocks non-bypass tools until ``divineos compass-ops observe``
is run, which clears the marker as a side effect.

Same architectural pattern as ``hedge_marker``, ``correction_marker``,
``theater_marker``: marker set by detection point, gate reads, CLI
clears. Filings without follow-through are decoration; the gate
converts intent into can-not-without.

## What sets the marker

* ``divineos correction``: a user correction has been logged. Compass
  observation is the calibration step.
* ``divineos claim --tier 2`` or higher: a substantive claim has been
  filed. Position relevant to what the claim asserts is virtue-
  relevant.
* The hedge or theater marker has been set: the conditions that put
  those there are virtue-relevant by definition.

## Falsifier

The marker should NOT block when:
* The triggering event was self-trivial (low-tier claim, no-op
  correction, etc.) — caller should not call ``set_marker`` for those.
* ``divineos compass-ops observe`` has been run since the marker was
  set (clears as side effect).
"""

from __future__ import annotations

import json
import time
from pathlib import Path


def marker_path() -> Path:
    return Path.home() / ".divineos" / "compass_required.json"


def _under_pytest() -> bool:
    """True if running inside a pytest test.

    Used so the cascade triggers in this module (called from other
    markers' set_marker functions) don't leak real markers into the
    user's home dir during tests that patch the source marker's
    path but cannot reasonably patch every cascade target.
    """
    import os

    return "PYTEST_CURRENT_TEST" in os.environ


def set_marker(trigger_kind: str, trigger_summary: str) -> None:
    """Write the marker. Called from event-detection points.

    ``trigger_kind`` is a short tag like "correction", "claim_t2",
    "hedge", "theater". ``trigger_summary`` is a short human-readable
    description shown in the gate message.

    No-op when running under pytest unless the test explicitly opts in
    via ``DIVINEOS_TEST_ALLOW_COMPASS_CASCADE`` env var.
    """
    if _under_pytest():
        import os

        if not os.environ.get("DIVINEOS_TEST_ALLOW_COMPASS_CASCADE"):
            return
    path = marker_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "ts": time.time(),
            "kind": trigger_kind,
            "summary": (trigger_summary or "")[:200],
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
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
    kind = marker.get("kind", "event")
    summary = (marker.get("summary") or "").replace("\n", " ")[:120]
    return (
        f"BLOCKED: virtue-relevant {kind} event occurred ({summary!r}). "
        f"Compass position must be observed before further tool use. "
        f'Run: divineos compass-ops observe <spectrum> -p <position> -e "<evidence>". '
        f"Architecture is will, enforcement is promise (claim 7e780182)."
    )
