"""F39 abstention telemetry — Aletheia review-note followup (2026-07-18).

F39's edit-token-overlap check has a legitimate fail-open path: when the
gate can't extract content tokens from the edit's target file (bash-
anchored fingerprint, unreadable file, relative-path test scaffold), it
returns ``None`` and the overlap check abstains. Aletheia flagged this
as the same disease F41 just cured: a check that abstains silently is
a check that can go dark without telling anyone.

The cure is her F41 pattern reapplied: instrument the abstention path.
Count how often the check ran with real tokens vs how often it
abstained. If the abstention ratio in production is high, the check is
effectively dark and the F39 gap has quietly reopened. If the ratio is
low, the check is live and the fix is doing its job.

This is telemetry only — no runtime gate change. The counter is stored
in a small JSON file under the marker directory; a HUD slot reads it
and surfaces a warning when the abstention ratio crosses a threshold.

Same shape as F41's heartbeat: fail-loud on liveness while fail-open
on output, so a fail-open path can't hide as absence-of-flags.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

_TELEMETRY_FILE = "f39_abstention_telemetry.json"
# Statistical floor — don't surface a warning until we have at least
# this many samples. Prevents a startup-noise reading of "100% abstention
# on 1 sample" from firing.
_MIN_SAMPLES_FOR_WARNING = 20
# Warning fires when abstention ratio exceeds this on the recent window.
_ABSTENTION_WARNING_THRESHOLD = 0.5


def _marker_path() -> Any:
    """Resolve the telemetry file path via the shared marker directory."""
    from divineos.core.operating_loop_audit import marker_path

    return marker_path(_TELEMETRY_FILE)


@dataclass(frozen=True)
class AbstentionStats:
    """Snapshot of the F39 abstention telemetry.

    - total_samples: total (abstain + live) recorded.
    - abstain_count: how many calls returned None edit_content_tokens.
    - live_count: how many calls returned a real token set (possibly empty).
    - abstention_ratio: abstain_count / total_samples (0.0 if no samples).
    - last_recorded_ts: epoch seconds of the most recent record; 0 if never.
    """

    total_samples: int = 0
    abstain_count: int = 0
    live_count: int = 0
    abstention_ratio: float = 0.0
    last_recorded_ts: float = 0.0


def record_edit_tokens_result(is_none: bool, now: float | None = None) -> None:
    """Record one gate call's edit-token-extraction result.

    ``is_none=True`` means the F39 overlap check abstained (fail-open
    path); ``is_none=False`` means real tokens were extracted and the
    check evaluated. Fail-soft on IO errors so the substance-binding
    gate never crashes because of telemetry.
    """
    resolved_now = now if now is not None else time.time()
    try:
        path = _marker_path()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                data = {}
        except (OSError, ValueError):
            data = {}
        abstain = int(data.get("abstain_count", 0))
        live = int(data.get("live_count", 0))
        if is_none:
            abstain += 1
        else:
            live += 1
        data = {
            "abstain_count": abstain,
            "live_count": live,
            "last_recorded_ts": float(resolved_now),
        }
        path.write_text(json.dumps(data), encoding="utf-8")
    except (OSError, ValueError):
        # Telemetry failure must not break the gate — fail-soft.
        return


def read_abstention_stats() -> AbstentionStats:
    """Return the current abstention telemetry snapshot.

    Empty snapshot (all zeros) when the file doesn't exist yet or can't
    be read; downstream consumers should treat that as 'no data,' not
    'no abstentions.'
    """
    try:
        path = _marker_path()
        if not path.exists():
            return AbstentionStats()
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return AbstentionStats()
    except (OSError, ValueError):
        return AbstentionStats()
    abstain = int(data.get("abstain_count", 0))
    live = int(data.get("live_count", 0))
    total = abstain + live
    ratio = (abstain / total) if total else 0.0
    return AbstentionStats(
        total_samples=total,
        abstain_count=abstain,
        live_count=live,
        abstention_ratio=ratio,
        last_recorded_ts=float(data.get("last_recorded_ts", 0.0)),
    )


def abstention_warning_should_fire(stats: AbstentionStats | None = None) -> bool:
    """True if the F39 check is effectively dark and a warning should surface.

    Requires: at least ``_MIN_SAMPLES_FOR_WARNING`` samples AND abstention
    ratio above ``_ABSTENTION_WARNING_THRESHOLD``. Both conditions guard
    against startup noise.
    """
    stats = stats if stats is not None else read_abstention_stats()
    return (
        stats.total_samples >= _MIN_SAMPLES_FOR_WARNING
        and stats.abstention_ratio > _ABSTENTION_WARNING_THRESHOLD
    )


__all__ = [
    "AbstentionStats",
    "record_edit_tokens_result",
    "read_abstention_stats",
    "abstention_warning_should_fire",
]
