"""Hook 1 cost-bounding telemetry.

C named the empirical follow-on 2026-05-01: now that Hook 1 fires in
production, the architectural question is whether surfaced content is
actually being consumed in the agent's reasoning, or just consuming
context budget.

This module is the measurement layer. Two events:

  * fire — Hook 1 wrote a surface. Records turn timestamp, marker
    count, byte size of the surface, surfaced knowledge_ids.
  * consume — Stop hook compares the agent's response to the most
    recent fire's surfaced content. Computes a cheap consumption
    proxy: how many of the surfaced knowledge_ids' content tokens
    appear in the response.

Together they give: fire-rate, byte cost per fire, consumption-rate
(percentage of fires whose content the response actually used).

The proxy is keyword-overlap, not semantic. False positives possible
(agent uses common word independently); false negatives possible
(agent paraphrases). Good enough for first-cut measurement; tune
when the data warrants.

Storage: JSONL at ~/.divineos/hook1_telemetry.jsonl, rolling window
of the last 200 turns (recent enough to be representative; bounded
to keep file small).
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

_FS_ERRORS = (OSError, json.JSONDecodeError, UnicodeDecodeError)
_LOG_PATH = Path.home() / ".divineos" / "hook1_telemetry.jsonl"
_ROLLING_WINDOW = 200


@dataclass(frozen=True)
class Hook1Stats:
    """Aggregate stats over the rolling window."""

    fires: int
    consumed: int
    consumption_rate: float
    avg_bytes_per_fire: float
    total_bytes: int
    sample_size: int


def _ensure_log_dir() -> None:
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    except _FS_ERRORS:
        pass


def _read_log() -> list[dict]:
    if not _LOG_PATH.exists():
        return []
    entries: list[dict] = []
    try:
        with open(_LOG_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except _FS_ERRORS:
                    continue
    except _FS_ERRORS:
        return []
    return entries


def _write_log(entries: list[dict]) -> None:
    _ensure_log_dir()
    try:
        with open(_LOG_PATH, "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")
    except _FS_ERRORS:
        pass


def record_fire(
    surface_text: str,
    surfaced_ids: list[str],
    marker_count: int,
) -> None:
    """Record a Hook 1 fire. Called from pre-response-context.sh after writing
    the surface file."""
    entries = _read_log()
    entries.append(
        {
            "kind": "fire",
            "ts": time.time(),
            "bytes": len(surface_text or ""),
            "marker_count": int(marker_count),
            "surfaced_ids": [s for s in (surfaced_ids or []) if s][:10],
            "consumed": None,  # filled in by record_consumption
        }
    )
    _write_log(entries[-_ROLLING_WINDOW:])


_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]{4,}")


def _content_tokens(text: str) -> set[str]:
    """Cheap token set for overlap comparison. Lowercased, length >=4."""
    return {t.lower() for t in _TOKEN_PATTERN.findall(text or "")}


def record_consumption(
    response_text: str,
    surface_text: str,
    *,
    overlap_threshold: int = 3,
) -> None:
    """Update the most recent fire entry with consumption signal.

    overlap_threshold: minimum token overlap between surface content
    and response content to count as 'consumed'. Default 3 = at least
    three substantive tokens shared, beyond what a generic response
    would contain by chance.
    """
    entries = _read_log()
    if not entries:
        return
    # Find most recent fire entry without consumed marker
    target_idx = None
    for i in range(len(entries) - 1, -1, -1):
        if entries[i].get("kind") == "fire" and entries[i].get("consumed") is None:
            target_idx = i
            break
    if target_idx is None:
        return

    surface_tokens = _content_tokens(surface_text)
    response_tokens = _content_tokens(response_text)
    overlap = surface_tokens & response_tokens
    # Filter generic boilerplate tokens that surface includes itself
    boilerplate = {
        "surfaced",
        "context",
        "auto",
        "queried",
        "marker",
        "operating",
        "loop",
        "before",
        "responding",
    }
    overlap -= boilerplate

    consumed = len(overlap) >= overlap_threshold
    entries[target_idx]["consumed"] = bool(consumed)
    entries[target_idx]["overlap_count"] = len(overlap)
    entries[target_idx]["consumed_at"] = time.time()
    _write_log(entries[-_ROLLING_WINDOW:])


def summary_stats() -> Hook1Stats:
    """Compute aggregate stats over the rolling window."""
    entries = _read_log()
    fires = [e for e in entries if e.get("kind") == "fire"]
    if not fires:
        return Hook1Stats(0, 0, 0.0, 0.0, 0, 0)

    fire_count = len(fires)
    consumed_count = sum(1 for e in fires if e.get("consumed") is True)
    measured = sum(1 for e in fires if e.get("consumed") is not None)
    rate = consumed_count / measured if measured > 0 else 0.0
    total_bytes = sum(int(e.get("bytes", 0)) for e in fires)
    avg_bytes = total_bytes / fire_count if fire_count > 0 else 0.0

    return Hook1Stats(
        fires=fire_count,
        consumed=consumed_count,
        consumption_rate=rate,
        avg_bytes_per_fire=avg_bytes,
        total_bytes=total_bytes,
        sample_size=measured,
    )


def format_stats(stats: Hook1Stats) -> str:
    """Human-readable summary for CLI output."""
    if stats.fires == 0:
        return "[hook1] No fires recorded yet. Run more turns to populate the rolling window."
    lines = [
        f"[hook1] Telemetry over last {stats.fires} fires:",
        f"  measured fires:    {stats.sample_size} (with consumption signal)",
        f"  consumed:          {stats.consumed} ({stats.consumption_rate:.1%})",
        f"  bytes per fire:    {stats.avg_bytes_per_fire:.0f} avg",
        f"  total bytes:       {stats.total_bytes}",
    ]
    if stats.sample_size > 0:
        if stats.consumption_rate < 0.2:
            lines.append("  diagnostic:        LOW consumption — surface largely unused.")
        elif stats.consumption_rate > 0.6:
            lines.append("  diagnostic:        HIGH consumption — surface earning its budget.")
        else:
            lines.append("  diagnostic:        MIXED — calibrate threshold or marker rules.")
    return "\n".join(lines)


__all__ = [
    "Hook1Stats",
    "format_stats",
    "record_consumption",
    "record_fire",
    "summary_stats",
]
