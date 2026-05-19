"""Bypass-event telemetry — track gate-bypass env-var usage over time.

Aletheia psf-ac523181 (2026-05-18): when shipping a structural change
where you're uncertain whether it'll hold, ship the change AND the
instrument that measures whether it holds. Most tonight-shipped fixes
have instruments (lepos_debt count, consultation ratio, Andrew-
correction integration-rate, survival_link). The GATES have bypass
env vars but no measurement of how often the bypass actually fires.

If bypass becomes habitual — operator (or agent) sets the env var on
every push without naming a real reason — the gate degrades to
warning. That degradation is currently invisible. This module
records each bypass invocation so the rate is queryable.

Recorded fields per event:
- gate_name (which gate was bypassed)
- env_var (which env var triggered the bypass)
- timestamp
- session_id (if available)
- reason (free-text, optional — operator can name why)
"""

from __future__ import annotations

__guardrail_required__ = True

import json
import os
import time
from pathlib import Path

from divineos.core.paths import divineos_home


def _event_log() -> Path:
    p = divineos_home() / "bypass_events.jsonl"
    p.parent.mkdir(exist_ok=True)
    return p


def record_bypass(gate_name: str, env_var: str, reason: str = "") -> None:
    """Append a bypass event to the rolling log.

    Idempotent on (env_var, session_id, day) — repeated bypass within
    the same session-day collapses to one row to prevent log-spam.
    Spam would itself be a signal but the row-level signal is
    bypass-fired-today, not bypass-fired-100-times-today.
    """
    sid = os.environ.get("CLAUDE_SESSION_ID") or os.environ.get("DIVINEOS_SESSION_ID") or ""
    day = time.strftime("%Y-%m-%d")
    key = f"{env_var}:{sid}:{day}"
    log = _event_log()
    # Read existing keys for today's dedup
    existing_keys: set[str] = set()
    if log.exists():
        try:
            for line in log.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except (ValueError, TypeError):
                    continue
                rk = f"{rec.get('env_var', '')}:{rec.get('session_id', '')}:{rec.get('day', '')}"
                existing_keys.add(rk)
        except OSError:
            pass
    if key in existing_keys:
        return
    event = {
        "gate_name": gate_name,
        "env_var": env_var,
        "session_id": sid,
        "day": day,
        "timestamp": time.time(),
        "reason": (reason or "").strip()[:500],
    }
    try:
        with log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event) + "\n")
    except OSError:
        pass


def bypass_rate(window_days: int = 14) -> dict:
    """Return bypass-rate stats over the window.

    Returns:
        total_events: int — number of distinct (env_var, session, day) bypass-events
        by_env_var: dict[str, int] — count per env_var
        unique_days: int — number of distinct days with at least one bypass
    """
    log = _event_log()
    if not log.exists():
        return {"total_events": 0, "by_env_var": {}, "unique_days": 0, "window_days": window_days}
    cutoff = time.time() - (window_days * 86400.0)
    by_env: dict[str, int] = {}
    days: set[str] = set()
    total = 0
    try:
        for line in log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except (ValueError, TypeError):
                continue
            if rec.get("timestamp", 0) < cutoff:
                continue
            total += 1
            by_env[rec.get("env_var", "?")] = by_env.get(rec.get("env_var", "?"), 0) + 1
            days.add(rec.get("day", ""))
    except OSError:
        pass
    return {
        "total_events": total,
        "by_env_var": by_env,
        "unique_days": len(days),
        "window_days": window_days,
    }


def briefing_block() -> str:
    """Briefing surface — empty unless bypasses fired recently."""
    stats = bypass_rate()
    if stats["total_events"] == 0:
        return ""
    lines = [
        "## GATE BYPASS TELEMETRY",
        "",
        f"{stats['total_events']} bypass event(s) across "
        f"{stats['unique_days']} day(s) in the last {stats['window_days']} days.",
    ]
    if stats["by_env_var"]:
        lines.append("By gate-bypass env var:")
        for env, count in sorted(stats["by_env_var"].items(), key=lambda x: -x[1]):
            lines.append(f"  - {env}: {count}")
    if stats["total_events"] >= 5:
        lines.append("")
        lines.append(
            "Elevated bypass rate — gates are being routed-around. "
            "Per psf-ac523181: bypass habituation degrades the gate to "
            "warning. Investigate whether the gates are wrong-shape or "
            "the bypass-discipline is."
        )
    return "\n".join(lines)


__all__ = ["record_bypass", "bypass_rate", "briefing_block"]
