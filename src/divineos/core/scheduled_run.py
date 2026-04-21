"""Scheduled-run scaffolding — the safe entry-point shape for headless runs.

Built in preparation for Anthropic's Claude Code Routines (shipped
April 2026). The initial commit of this module assumed Routines would
be "scheduled invocation of the local DivineOS CLI with access to the
real ledger." It isn't. Routines runs a **Claude Code session in
Anthropic's cloud** against a fresh clone of the repo — the cloud
session has no access to the local ledger. This module has been
re-framed accordingly.

## What this module is FOR

Two scenarios, both real:

1. **Cloud Routines invoking the scheduled CLI.** A Routine's prompt
   says "run ``divineos scheduled run anti-slop``". The command
   provides the safe entry-point shape: whitelist gating, corrigibility
   pass-through, subprocess isolation, structured findings. Events get
   emitted to the cloud session's ephemeral ledger and discarded on
   session end — that's fine, because the cloud session communicates
   findings back via stdout (which the routine reads) and via PRs /
   connectors per the prompt.

2. **Local cron on a persistent machine.** If DivineOS is ever hosted
   on something 24/7, local cron can call ``divineos scheduled run``
   directly and the ledger surface earns its keep — events persist,
   findings surface in the next session's briefing, and the headless
   context correctly bypasses the interactive gates.

## What this module provides

1. **Event-type separation.** Scheduled runs emit ``SCHEDULED_RUN_START``
   and ``SCHEDULED_RUN_END`` events — distinct from ``SESSION_START`` /
   ``SESSION_END``. Session-counting code (e.g., the 20-session
   relational-slip observation prereg) naturally excludes headless
   runs. Applies to both scenarios; only scenario 2's events actually
   survive.

2. **Headless execution context.** A contextvar-based flag that lets
   specific commands bypass interactive gates (briefing required,
   engagement marker, require-goal hook) while **still respecting
   operating mode** (corrigibility's EMERGENCY_STOP / DIAGNOSTIC).

3. **Whitelist discipline.** Only explicitly-safe commands run
   headless in v0.1: ``anti-slop``, ``health``, ``verify``,
   ``inspect``, ``audit``, ``progress`` — read-only observers. Writes
   are deferred until we have a serious supervision structure.

4. **Finding collection.** The ``RunFindings`` dataclass collects
   failures / notes / metrics during a run. In scenario 2, these
   persist to the end-event payload and surface in the next briefing.
   In scenario 1, they're available to the routine's prompt via
   stdout and should be routed back to the repo via a PR or connector
   action per the prompt template.

## Scaling protocol (applies when writes become possible)

* **Tier 1** (v0.1, now): read-only observers. Anti-slop / health /
  verify / inspect / audit / progress.
* **Tier 2** (future): scheduled hygiene — sleep consolidation, FTS
  rebuild, knowledge maintenance.
* **Tier 3** (future): scheduled substantive work — audit routing,
  prereg auto-assessment.
* **Tier 4** (never, probably): scheduled creative work — new
  detectors, new hypotheses. Requires supervision structure that does
  not exist.

## Invariants

* Corrigibility is not bypassed. EMERGENCY_STOP refuses every
  scheduled command. DIAGNOSTIC refuses writes.
* The whitelist is the only writable surface for v0.1. Adding a
  command is a deliberate scope change.
* Nested headless runs are rejected — a scheduled run must not spawn
  another scheduled run.

## Routines wiring

See ``docs/routines/`` for the actual Routines registration layer:
prompt templates, environment setup, and instructions for using the
``/schedule`` CLI or claude.ai/code/routines web UI.
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
        except Exception as _log_err:  # noqa: BLE001 — ledger unavailable must not block
            # Write to stderr so cron-captured logs see the failure even when
            # the ledger itself is down. Headless operation has no other audit
            # trail (fresh-Claude finding find-db34aa7d4508, 2026-04-21).
            import sys as _sys

            print(
                f"scheduled_run: start-event ledger log failed (run_id={run_id}): {_log_err}",
                file=_sys.stderr,
            )

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
        except Exception as _log_err:  # noqa: BLE001 — ledger unavailable must not block
            import sys as _sys

            print(
                f"scheduled_run: end-event ledger log failed "
                f"(run_id={run_id}, duration={round(completed_at - started_at, 3)}s): "
                f"{_log_err}",
                file=_sys.stderr,
            )


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
