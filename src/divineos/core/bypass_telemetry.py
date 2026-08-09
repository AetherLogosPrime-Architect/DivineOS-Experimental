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
    # 2026-08-09: allowlisted command-prefix passes do NOT file an obligation.
    #
    # Eight of these were sitting in the pending-fix backlog, two filed the
    # same day I found them: "Root-cause investigation owed: bypass of gate
    # 'briefing' via env var 'cmd:divineos ask'". That is the engagement gate's
    # own prescribed remedy, and `divineos briefing` HAS to pass the
    # briefing-staleness gate or a stale briefing could never be refreshed.
    # The obligations were owed for obeying.
    #
    # Not merely noise: per the note below, these obligations BLOCK the extract
    # pipeline until resolved. So complying with one gate manufactured a
    # blocker on another.
    #
    # ON THE FENCE THIS TOUCHES, because it is a real one. The council walk
    # (Yudkowsky + Schneier) chose file-ALL precisely so that no
    # authorization-filter would exist: a per-use judgment about whether my own
    # bypass was justified is exactly the surface the optimizer would work.
    # That reasoning holds and I am not weakening it.
    #
    # BYPASS_PREFIXES is a different object. It is a static declared constant,
    # auditable in one place, fixed before any bypass happens -- not a
    # judgment made at bypass-time by the party doing the bypassing. Every
    # env-var and marker bypass, which is where a real evasion would live,
    # still files. The exemption is also stated in plain sight on the briefing
    # surface ("N of these are allowlisted commands passing a gate by design"),
    # so it cannot be a quiet hole.
    if str(env_var).startswith("cmd:"):
        return

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
        "evasions_all_time": 0,
    }
    if not log.exists():
        return empty_result
    total = 0
    evasions = 0  # lifetime count EXCLUDING allowlisted `cmd:` passes
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
            if not str(rec.get("env_var", "")).startswith("cmd:"):
                evasions += 1
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
        # 2026-08-09: the lifetime signal is kept, but split by kind. Removing
        # the full-history trigger outright would have lost what it guarded --
        # slow habituation across months, which no 14-day window can see. The
        # defect was never that it looked at the whole history; it was that the
        # whole history could not be split, so allowlisted passes kept it lit
        # forever. Splittable now, so it can fire on evasions and stay quiet on
        # exemptions.
        "evasions_all_time": evasions,
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
        # Placed HERE, not after the full-history block. First version appended
        # it at the end, where "N of the above" read as N of the lifetime total
        # instead of N of the window -- a true number filed under the wrong
        # denominator, which is the same defect this whole fix is about.
        _exempt = sum(v for k, v in stats["by_env_var"].items() if k.startswith("cmd:"))
        if _exempt:
            lines.append(
                f"  ({_exempt} of these are allowlisted commands passing a gate "
                f"by design -- not evasions, excluded from the rate verdict.)"
            )
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
    # THE VERDICT COUNTS EVASIONS, NOT EXEMPTIONS. (Aria 2026-08-09.)
    #
    # It used to be computed from stats["total_events"] -- every recorded
    # event, including the `cmd:` ones. Those fire when an ALLOWLISTED command
    # passes the briefing-staleness gate, and `divineos briefing` has to be
    # allowlisted or a stale briefing could never be refreshed. They are
    # chicken-and-egg exemptions the design requires, not evasions.
    #
    # Measured on the live store the turn this was found: 60 of 64 windowed
    # events were `cmd:divineos ask|briefing|goal|context|recall` -- the exact
    # commands the engagement gate ORDERS me to run. The gate demanded them,
    # then filed each one as evidence I was routing around it, and told me to
    # investigate my own discipline. I hit the block while investigating the
    # block, ran `divineos ask` as instructed, and incremented the number that
    # was accusing me.
    #
    # Worse than a false positive: with thresholds of 5-in-window or 20-ever
    # against 169 lifetime events, the warning COULD NEVER TURN OFF AGAIN. A
    # light that is always on carries no information, and this one spends its
    # permanent signal telling me to distrust myself on evidence of compliance.
    #
    # Recording all of it stays right -- visibility was the point when the
    # `cmd:` capture was added. The distinction belongs at the verdict, which
    # is the only place it changes what anyone does.
    evasions = {k: v for k, v in stats["by_env_var"].items() if not k.startswith("cmd:")}
    evasion_count = sum(evasions.values())

    # Same two scales as before, same thresholds -- 5 in the window, or 20
    # across the lifetime. Only the INPUT changed: evasions, not every event.
    #
    # Both scales are kept on purpose. Dropping the lifetime trigger was my
    # first fix and it was wrong: it would have lost the thing that trigger
    # guards, which is slow habituation across months that no 14-day window
    # can see. test_full_history_elevated_at_20_total failed and was right to.
    # The defect was never that it looked at the whole history -- it was that
    # the whole history could not be split by kind, so allowlisted passes kept
    # the light on forever. Split now, so it fires on evasions and stays quiet
    # on exemptions.
    lifetime_evasions = full.get("evasions_all_time", 0)
    windowed_elevated = evasion_count >= 5
    full_history_elevated = lifetime_evasions >= 20
    if windowed_elevated or full_history_elevated:
        lines.append("")
        which = []
        if windowed_elevated:
            which.append(f"{evasion_count} in the windowed sample")
        if full_history_elevated:
            which.append(f"{lifetime_evasions} lifetime")
        lines.append(
            f"Elevated bypass rate ({' + '.join(which)}, allowlisted passes "
            "excluded) -- gates are being routed-around. Per psf-ac523181: "
            "bypass habituation degrades the gate to warning. Investigate "
            "whether the gates are wrong-shape or the bypass-discipline is."
        )
    return "\n".join(lines)


__all__ = ["record_bypass", "bypass_rate", "full_history_stats", "briefing_block"]
