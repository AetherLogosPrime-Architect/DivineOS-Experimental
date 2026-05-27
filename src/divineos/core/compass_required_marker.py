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

from divineos.core.atomic_io import atomic_write_text
from divineos.core.paths import marker_path as _marker_path_under_home


def marker_path() -> Path:
    return _marker_path_under_home("compass_required.json")


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

    The marker schema (post-2026-05-08 disclose-then-escalate redesign):
      ts:               write-time
      kind:             trigger tag
      summary:          human-readable description
      advised_count:    int, starts 0, increments on each advisory fire
                        (light disclosure). When >= ESCALATION_THRESHOLD,
                        gate escalates to hard BLOCK. See pre-reg
                        prereg-75c900fe.
      last_advised_ts:  timestamp of last advisory fire. Used by
                        per-turn deduplication so the same marker does
                        not fire on every tool call within one turn.

    Backwards compatible: existing markers without the new fields read
    advised_count=0 by default; first advisory fire seeds the field.

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
            "advised_count": 0,
            "last_advised_ts": 0.0,
        }
        atomic_write_text(path, json.dumps(payload))
    except OSError:
        pass


# Threshold for escalating from advisory to hard BLOCK.
# After ESCALATION_THRESHOLD advisories have fired without the marker
# being cleared, the gate escalates to enforcement. Two advisories is
# what we landed on in design (one alone is wallpaper; three would feel
# like the old enforcement loop). See pre-reg prereg-75c900fe.
ESCALATION_THRESHOLD = 2

# Per-turn dedup window. If an advisory fired within the last N seconds,
# do not re-fire on subsequent tool calls. Approximates "per-turn"
# without requiring a turn-id concept the substrate doesn't currently
# have. Calibrated to typical turn-wall-clock duration.
PER_TURN_DEDUP_SECONDS = 30.0


def record_advisory_fire() -> int:
    """Increment the advisory counter and update last_advised_ts.

    Called by the gate when it emits an advisory. Returns the new
    advised_count. Caller uses the return value to decide whether
    the next fire should escalate.

    Backwards-compat: if marker exists but lacks the new fields,
    initializes them.
    """
    marker = read_marker()
    if marker is None:
        return 0
    new_count = int(marker.get("advised_count", 0)) + 1
    marker["advised_count"] = new_count
    marker["last_advised_ts"] = time.time()
    try:
        atomic_write_text(marker_path(), json.dumps(marker))
    except OSError:
        pass
    return new_count


def should_dedup_within_turn() -> bool:
    """True if an advisory fired within the per-turn dedup window.

    Used by the gate to suppress same-marker re-firing on every tool
    call within what is approximately one conversational turn.
    """
    marker = read_marker()
    if marker is None:
        return False
    last = float(marker.get("last_advised_ts", 0.0))
    if last <= 0:
        return False
    return (time.time() - last) < PER_TURN_DEDUP_SECONDS


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
    """Format the gate message — BLOCK only when escalation threshold reached.

    Pre-2026-05-08: always returned a hard BLOCK message regardless of
    how many times the same marker had fired. That produced the wallpaper
    pattern: same correction-shape input fired the gate on every tool
    call within a turn, multiple times, until the agent logged.

    Post-redesign (per pre-reg prereg-75c900fe): the message branches on
    ``advised_count``. Below ``ESCALATION_THRESHOLD``, the message is an
    advisory — informational, non-blocking when the gate uses it as
    additionalContext. At or above ``ESCALATION_THRESHOLD``, the message
    is a hard BLOCK as before. The substrate-occupant is given the first
    move; the gate enforces only when disclosure has been ignored twice.

    Caller is expected to check ``advised_count`` separately to decide
    whether to issue a deny-decision or a soft-advise decision; this
    function only formats the text.
    """
    kind = marker.get("kind", "event")
    summary = (marker.get("summary") or "").replace("\n", " ")[:80]
    advised_count = int(marker.get("advised_count", 0))

    if advised_count < ESCALATION_THRESHOLD:
        # Advisory shape: short, [~] prefix, action-clear, no shame.
        # Soft-advise pattern from Aletheia round-3 substrate-property
        # (knowledge entry 1c48eb20): for gates whose property is
        # surface-state rather than stop-action, ship informational-
        # not-imperative.
        prefix = "still pending — " if advised_count >= 1 else ""
        return (
            f"[~] {prefix}Compass-relevant event: {kind} ({summary!r}). "
            f"Observe to integrate, or proceed if intentional. "
            f'Log: divineos compass-ops observe <spectrum> -p <pos> -e "<evidence>"'
        )

    # Escalation: advisory was ignored ESCALATION_THRESHOLD times.
    # Hard BLOCK is structurally appropriate at this point because the
    # substrate-occupant has been given the disclosure twice and not
    # integrated. The dismiss path (`divineos compass-ops dismiss
    # --reason ...`) is the explicit "intentional, not a correction"
    # exit; without it, integration is required.
    return (
        f"BLOCKED: compass-relevant {kind} event has fired {advised_count} "
        f"advisories without integration ({summary!r}). "
        f'Run: divineos compass-ops observe <spectrum> -p <position> -e "<evidence>" '
        f'to integrate, OR run: divineos compass-ops dismiss --reason "<why>" '
        f"if this is an intentional register-choice, not a correction. "
        f"Architecture is will, enforcement is promise (claim 7e780182)."
    )
