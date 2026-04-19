"""Scheduled-run scaffolding — the layer below Routines integration.

Routines (Anthropic feature shipped with Opus 4.7) lets an agent run
on schedules, API triggers, or GitHub events without a human
initiating a conversation. DivineOS was designed with this trajectory
in mind; corrigibility, the off-switch, and the engagement gates all
assume autonomous runtime would eventually exist.

This module is the scaffolding that makes scheduled runs **safe** and
**distinguishable** from human-initiated sessions:

1. **Event-type separation.** Scheduled runs emit ``SCHEDULED_RUN_START``
   and ``SCHEDULED_RUN_END`` events — distinct from ``SESSION_START`` /
   ``SESSION_END``. Any code that counts sessions (e.g., the 20-session
   observation prereg for relational slips) naturally excludes headless
   runs because they never emit SESSION events.

2. **Headless execution context.** A context manager that sets a
   thread-local flag, allowing specific commands to bypass interactive
   gates (briefing required, engagement marker, require-goal hook)
   while *still respecting operating mode* (corrigibility's
   EMERGENCY_STOP / DIAGNOSTIC gates).

3. **Whitelist discipline.** Only explicitly-safe commands can run
   headless in v0.1: anti-slop, health, verify, inspect (read-only
   observers). Writes are deferred to Tier 2. See
   ``_HEADLESS_WHITELIST``.

4. **Finding collection.** Scheduled runs can record findings (what
   broke, what's stuck, what needs attention) into the end-event
   payload. The briefing surfaces unresolved findings so they're
   visible next time a human initiates a session.

## Scaling protocol

* **Tier 1** (this module, v0.1): read-only observers. Scheduled
  anti-slop / health / verify. Nothing changes state except the log.
* **Tier 2** (future): scheduled hygiene. Sleep consolidation, FTS
  rebuild, knowledge maintenance — operations the system does in
  response to normal use, now on a schedule.
* **Tier 3** (future): scheduled substantive work. Audit routing,
  prereg auto-assessment, anything that takes concrete action.
* **Tier 4** (never, probably): scheduled creative work. New
  detectors, new hypotheses. This tier would require a serious
  supervision structure that does not exist today.

## What this module does NOT do

* Does not implement Routines integration itself. This is the
  scaffolding; Routines is the delivery mechanism (cloud scheduler,
  cron, external trigger). When we wire up Routines, it will call
  ``divineos scheduled <command>`` and the scaffolding handles the rest.
* Does not bypass corrigibility. EMERGENCY_STOP still refuses every
  scheduled command. DIAGNOSTIC still refuses writes. The off-switch
  is the off-switch.
"""

from __future__ import annotations

import contextvars
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator


# Event types used by scheduled runs. Distinct from SESSION_* so that
# session-counting code naturally excludes headless runs.
EVENT_SCHEDULED_RUN_START = "SCHEDULED_RUN_START"
EVENT_SCHEDULED_RUN_END = "SCHEDULED_RUN_END"


# Context variable tracking whether we're inside a scheduled run.
# Using contextvars (not thread-local) so async code works correctly.
_headless_context: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "_divineos_headless", default=False
)


# Commands allowed to run under headless mode in v0.1. Read-only
# observers only. Anything that writes substantive state is deferred
# to Tier 2.
_HEADLESS_WHITELIST: frozenset[str] = frozenset(
    {
        # Runtime verification — the most valuable scheduled use case
        "anti-slop",
        # Health / drift checks
        "health",
        # Ledger integrity
        "verify",
        # Read-only inspections
        "inspect",  # via `divineos inspect <read-only-subcmd>`
        "audit",  # via `divineos audit summary` etc.
        "progress",
    }
)


@dataclass
class RunFindings:
    """Collected findings from a scheduled run.

    Attributes:
        failures: list of plain-English descriptions of problems
            detected. Empty = clean run.
        notes: non-failure observations the operator might want to
            see (e.g., "3 new mode changes since last run").
        metrics: structured metric key-value pairs.
    """

    failures: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def is_clean(self) -> bool:
        """True if no failures were recorded."""
        return len(self.failures) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "failures": list(self.failures),
            "notes": list(self.notes),
            "metrics": dict(self.metrics),
            "clean": self.is_clean(),
        }


def is_headless() -> bool:
    """Return True if the current execution context is a scheduled run."""
    return _headless_context.get()


def is_command_allowed_headless(command: str) -> tuple[bool, str]:
    """Check whether a command may run in headless (scheduled) mode.

    Only whitelisted read-only observers are permitted in v0.1. This
    is independent of operating-mode gating — both checks must pass
    for a scheduled command to run.

    Returns:
        (allowed, reason). ``reason`` is empty when allowed.
    """
    if command in _HEADLESS_WHITELIST:
        return True, ""
    return (
        False,
        f"Command '{command}' not in headless whitelist. Scheduled runs in "
        f"v0.1 are limited to read-only observers: "
        f"{sorted(_HEADLESS_WHITELIST)}. Adding a command to the whitelist "
        f"is a Tier-2 scope change requiring deliberate review.",
    )


@contextmanager
def headless_run(
    command: str, trigger: str = "manual", actor: str = "scheduler"
) -> Iterator[RunFindings]:
    """Context manager for a scheduled headless run.

    Emits a SCHEDULED_RUN_START event on entry and a SCHEDULED_RUN_END
    event on exit. Sets the headless context flag so downstream gates
    know to bypass briefing/engagement checks. The findings object is
    yielded so the caller can record failures / notes / metrics; it
    will be attached to the end-event payload.

    Args:
        command: the command being run headless (must be in the
            whitelist — caller's responsibility to check).
        trigger: what caused this run ("cron", "github-webhook",
            "api", "manual"). Recorded in the start event.
        actor: the actor field for ledger events. Defaults to
            "scheduler".

    Yields:
        RunFindings instance to be populated during the run.

    Raises:
        RuntimeError: if nested headless runs are attempted.
    """
    if _headless_context.get():
        raise RuntimeError(
            "Nested headless runs are not supported. A scheduled run must "
            "not spawn another scheduled run — that would defeat the "
            "separation between scheduled and interactive contexts."
        )

    run_id = f"sched-{uuid.uuid4().hex[:12]}"
    findings = RunFindings()
    token = _headless_context.set(True)
    started_at = time.time()

    try:
        from divineos.core.ledger import log_event

        try:
            log_event(
                event_type=EVENT_SCHEDULED_RUN_START,
                actor=actor,
                payload={
                    "run_id": run_id,
                    "command": command,
                    "trigger": trigger,
                    "started_at": started_at,
                },
            )
        except Exception:  # noqa: BLE001 — ledger unavailable must not block
            pass

        yield findings

    finally:
        _headless_context.reset(token)
        completed_at = time.time()
        try:
            from divineos.core.ledger import log_event

            log_event(
                event_type=EVENT_SCHEDULED_RUN_END,
                actor=actor,
                payload={
                    "run_id": run_id,
                    "command": command,
                    "trigger": trigger,
                    "started_at": started_at,
                    "completed_at": completed_at,
                    "duration_sec": round(completed_at - started_at, 3),
                    **findings.to_dict(),
                },
            )
        except Exception:  # noqa: BLE001
            pass


def recent_scheduled_runs(limit: int = 10) -> list[dict[str, Any]]:
    """Return recent SCHEDULED_RUN_END events for briefing surface.

    Args:
        limit: how many recent end-events to return.

    Returns:
        list of dicts with keys: timestamp, command, duration_sec,
        clean, failures, notes. Empty list if no scheduled runs yet.
    """
    try:
        import json as _json

        from divineos.core.ledger import get_connection
    except ImportError:
        return []

    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT timestamp, payload FROM system_events "
            "WHERE event_type = ? ORDER BY timestamp DESC LIMIT ?",
            (EVENT_SCHEDULED_RUN_END, limit),
        ).fetchall()
    finally:
        conn.close()

    results: list[dict[str, Any]] = []
    for ts, payload in rows:
        try:
            data = _json.loads(payload) if isinstance(payload, str) else (payload or {})
        except (ValueError, TypeError):
            data = {}
        results.append(
            {
                "timestamp": float(ts),
                "command": data.get("command", "?"),
                "duration_sec": data.get("duration_sec", 0.0),
                "clean": bool(data.get("clean", True)),
                "failures": list(data.get("failures") or []),
                "notes": list(data.get("notes") or []),
            }
        )
    return results


def unresolved_findings_summary() -> str:
    """Return a short, human-readable summary of recent scheduled-run
    failures, or empty string if the runs have been clean.

    Used by the briefing to surface problems that occurred while the
    operator was away.
    """
    runs = recent_scheduled_runs(limit=20)
    if not runs:
        return ""

    failing_runs = [r for r in runs if not r["clean"]]
    if not failing_runs:
        return ""

    # Only summarize failures since the most recent CLEAN run — older
    # failures may have been resolved and we don't want to re-surface
    # noise.
    cutoff_ts = 0.0
    for r in runs:
        if r["clean"]:
            cutoff_ts = r["timestamp"]
            break

    actionable = [r for r in failing_runs if r["timestamp"] > cutoff_ts]
    if not actionable:
        return ""

    lines = [f"[scheduled run] {len(actionable)} unresolved finding-set(s) since last clean run:"]
    for r in actionable[:5]:
        cmd = r["command"]
        failures = r["failures"]
        lines.append(f"  - {cmd}: {len(failures)} failure(s)")
        for f in failures[:3]:
            lines.append(f"      • {f[:120]}")
    return "\n".join(lines)


__all__ = [
    "EVENT_SCHEDULED_RUN_END",
    "EVENT_SCHEDULED_RUN_START",
    "RunFindings",
    "headless_run",
    "is_command_allowed_headless",
    "is_headless",
    "recent_scheduled_runs",
    "unresolved_findings_summary",
]
