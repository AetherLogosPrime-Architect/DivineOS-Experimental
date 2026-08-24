"""Attribution marker for the extract (consolidation checkpoint) pipeline.

EXTRACT RUNS PRE-COMPACTION -- at 920,000 tokens, not once per session.

Corrected 2026-08-24 by Andrew: *"at no point should anything be skipping
extraction"* and *"it should be tied to the actual token count with a heartbeat
monitor to keep it updated every round, that way you know when 920k tokens has
been reached and we run the ritual."*

This module USED to enforce "runs once per session" via an idempotency guard in
event_commands.py. That guard read a marker cleared only by load-briefing.sh at
SessionStart -- so when a dropped connection meant the next session loaded its
briefing by hand, the stale marker survived and every extract for EIGHT HOURS
returned immediately having stored nothing. Measured: zero knowledge rows for
the whole day until --force was run. The guard is gone.

What remains here is ATTRIBUTION, not permission. The marker records what last
triggered a consolidation so a reader can tell manual from sleep from hook. It
no longer gates anything, and nothing reads it to decide whether to skip.

The real trigger lives in auto_cycle.TRIGGER_THRESHOLD (0.92 of a 1M window =
920,000 tokens) and reads its number from core/context_heartbeat.py, which
stamps the count every round and records a blind sensor as UNKNOWN rather than
as zero.

Historically the marker contained the literal string ``"1"`` — a
bare "ran or didn't run" flag. That produced a confusing skip message
when a second caller hit the guard: "Consolidation already ran this
session — skipping" without any hint of *what* triggered the first run.
Sleep's post-sleep auto-extract was the usual culprit, but the user
(or a later session) had no way to know that from the message.

This module lets us write the marker as JSON capturing timestamp and
trigger, and read it back for a humane skip message. Falls back to the
legacy "ran — no trigger info" interpretation when the marker is the
pre-migration literal ``"1"``.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from divineos.core.atomic_io import atomic_write_text
from divineos.core.paths import marker_path as _marker_path_under_home


def marker_path() -> Path:
    """Absolute path to the extract idempotency marker."""
    return _marker_path_under_home("auto_session_end_emitted")


def write_marker(trigger: str = "manual", session_id: str | None = None) -> None:
    """Write the marker with trigger attribution. Best-effort; swallow OSErrors.

    ``trigger`` values currently in use:
      - "manual" — user ran `divineos extract` directly.
      - "sleep" — triggered by the post-sleep auto-extract subprocess.
      - "hook" — triggered by the post-tool-use checkpoint hook.
    """
    path = marker_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"trigger": trigger, "ts": time.time(), "session_id": session_id}
        atomic_write_text(path, json.dumps(payload))
    except OSError:
        pass


def read_marker() -> dict | None:
    """Return the marker payload, or None if the marker is missing.

    Legacy marker content ``"1"`` is normalized to a dict with
    ``trigger="unknown"``. Always returns either None (no marker) or a
    dict with at least the ``trigger`` key.
    """
    path = marker_path()
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return {"trigger": "unknown"}
    if not raw or raw == "1":
        return {"trigger": "unknown"}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"trigger": "unknown"}
    if not isinstance(data, dict) or "trigger" not in data:
        return {"trigger": "unknown"}
    return data


def format_skip_message(marker: dict) -> str:
    """Return a one-line explanation of what set the marker, if known."""
    trigger = marker.get("trigger", "unknown")
    ts = marker.get("ts")
    if not ts:
        return f"(triggered by: {trigger})"
    age_sec = time.time() - ts
    if age_sec < 60:
        age_str = f"{int(age_sec)}s ago"
    elif age_sec < 3600:
        age_str = f"{int(age_sec // 60)}m ago"
    else:
        age_str = f"{age_sec / 3600:.1f}h ago"
    return f"(triggered by: {trigger}, {age_str})"
