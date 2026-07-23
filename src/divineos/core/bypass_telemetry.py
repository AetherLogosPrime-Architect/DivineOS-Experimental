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
    # 2026-07-22 (task #18, prereg-30485a180429, council-411666e581dd):
    # every bypass event auto-files a pending investigation obligation
    # via structural_fix_tracker. The obligation surfaces in the
    # briefing dashboard and blocks the extract pipeline (via
    # enforce_bypass_investigation_gate) until resolved. Andrew
    # directive 93164891: "A bypass or escape hatch is last resort so
    # any use of them gets logged and needs to automatically launch a
    # root cause investigation." Truth #10: feed the optimizer cost
    # data in its own currency — every bypass costs a real followup
    # task. Council walk file-ALL decision per Yudkowsky + Schneier:
    # authorization-filter is the attack surface; better to file all
    # and require corroborator on resolution. Corroborator-resolution
    # enforcement is task #24 followup. This filing wire is
    # best-effort: if structural_fix_tracker is unavailable, the
    # telemetry event still lands and the bypass is not lost.
    try:
        from divineos.core.structural_fix_tracker import record_pending_fix

        record_pending_fix(
            content=(
                f"Root-cause investigation owed: bypass of gate "
                f"'{gate_name}' via env var '{env_var}' on "
                f"{time.strftime('%Y-%m-%d')}. Reason given: "
                f"{(reason or '(none)').strip()[:200]}. Investigate "
                f"whether this gate is wrong-shape (frequent legitimate "
                f"bypass = gate discipline is off) or the bypass-use "
                f"is wrong (frequent bypass without operator "
                f"authorization = my discipline is off). Resolve by "
                f"either landing a structural fix to the gate OR "
                f"citing an operator-authorization corroborator."
            ),
            trigger=f"bypass:{env_var}",
            source_kind="bypass_use",
        )
    except Exception:  # noqa: BLE001 - fail-open on tracker import
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


def full_history_stats() -> dict:
    """Return full-history bypass stats — since first-recorded event.

    Fixes the subset-is-not-the-whole violation (Andrew 2026-05-20,
    council-8faadb872d0b): the windowed ``bypass_rate()`` presents a
    14-day sample and misreads as-if-total when the surface names only
    the window. This function reports the invariant that lets the
    observer compare the sample to the whole.

    Returns:
        total_events_all_time: int — every distinct (env, session, day)
            row on record, no window filter
        first_recorded_date: str — YYYY-MM-DD of earliest event, or ""
            if log is empty
        unique_days_all_time: int — distinct days with any bypass
            across the whole history
        days_since_first: float — wall-clock days from first-event to
            now (0.0 if log is empty)
        events_per_day_avg: float — total_events_all_time / max(1.0,
            days_since_first), or 0.0 if empty

    Boundary behavior (Knuth walk council-8faadb872d0b): empty log
    returns all zeros with first_recorded_date="". Corrupted lines
    skipped (fail-open on record-level, same as bypass_rate). Missing
    timestamp fields skipped from the earliest-event calculation.
    Future timestamps (clock-drift or manual edits) are clamped so
    days_since_first is never negative.
    """
    log = _event_log()
    empty_result = {
        "total_events_all_time": 0,
        "first_recorded_date": "",
        "unique_days_all_time": 0,
        "days_since_first": 0.0,
        "events_per_day_avg": 0.0,
    }
    if not log.exists():
        return empty_result
    total = 0
    days: set[str] = set()
    earliest_ts: float | None = None
    try:
        for line in log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except (ValueError, TypeError):
                continue
            total += 1
            days.add(rec.get("day", ""))
            ts = rec.get("timestamp")
            if isinstance(ts, (int, float)) and ts > 0:
                if earliest_ts is None or ts < earliest_ts:
                    earliest_ts = ts
    except OSError:
        return empty_result
    if total == 0 or earliest_ts is None:
        return empty_result
    now = time.time()
    days_since_first = max(0.0, (now - earliest_ts) / 86400.0)
    events_per_day_avg = total / max(1.0, days_since_first)
    first_date = time.strftime("%Y-%m-%d", time.gmtime(earliest_ts))
    return {
        "total_events_all_time": total,
        "first_recorded_date": first_date,
        "unique_days_all_time": len(days),
        "days_since_first": round(days_since_first, 1),
        "events_per_day_avg": round(events_per_day_avg, 2),
    }


def briefing_block() -> str:
    """Briefing surface — empty unless bypasses fired recently.

    Post-fix (council-8faadb872d0b, 2026-07-21): surface shows BOTH
    the windowed sample AND the full-history counts so the observer
    can compare — closing the subset-is-not-the-whole violation.
    Every number is labeled with its scope (Norman gulf-of-evaluation)
    so the reader cannot conflate windowed with full-history.
    """
    stats = bypass_rate()
    full = full_history_stats()
    if stats["total_events"] == 0 and full["total_events_all_time"] == 0:
        return ""
    lines = [
        "## GATE BYPASS TELEMETRY",
        "",
        "### Windowed (recent sample)",
        f"{stats['total_events']} bypass event(s) across "
        f"{stats['unique_days']} distinct day(s), "
        f"within the last {stats['window_days']} days.",
    ]
    if stats["by_env_var"]:
        lines.append("By gate-bypass env var (windowed):")
        for env, count in sorted(stats["by_env_var"].items(), key=lambda x: -x[1]):
            lines.append(f"  - {env}: {count}")
    if full["total_events_all_time"]:
        lines.append("")
        lines.append("### Full history (since first recorded event)")
        lines.append(
            f"{full['total_events_all_time']} total event(s) since "
            f"{full['first_recorded_date']} "
            f"({full['days_since_first']} days elapsed, "
            f"{full['unique_days_all_time']} distinct active day(s), "
            f"avg {full['events_per_day_avg']} events/day)."
        )
    # Elevated-rate call-to-action recomputed against BOTH scales
    # (Norman walk). Windowed threshold: 5-in-14-days ≈ 0.36/day.
    # Full-history threshold: sustained avg >= 0.5 events/day OR
    # more than 20 total events (indicates habituation across time).
    windowed_elevated = stats["total_events"] >= 5
    full_history_elevated = full["events_per_day_avg"] >= 0.5 or full["total_events_all_time"] >= 20
    if windowed_elevated or full_history_elevated:
        lines.append("")
        which = []
        if windowed_elevated:
            which.append("windowed sample")
        if full_history_elevated:
            which.append("full-history rate")
        lines.append(
            f"Elevated bypass rate ({' + '.join(which)}) -- gates are being "
            "routed-around. Per psf-ac523181: bypass habituation degrades the "
            "gate to warning. Investigate whether the gates are wrong-shape "
            "or the bypass-discipline is."
        )
    return "\n".join(lines)


__all__ = ["record_bypass", "bypass_rate", "full_history_stats", "briefing_block"]
