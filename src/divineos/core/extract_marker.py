"""Idempotency marker for the extract (consolidation checkpoint) pipeline.

Extract runs once per session. A marker file at
~/.divineos/auto_session_end_emitted records that it ran; load-briefing.sh
clears it on SessionStart.

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
import os
import time
from pathlib import Path


def marker_path() -> Path:
    """Absolute path to the extract idempotency marker."""
    return Path(os.path.expanduser("~")) / ".divineos" / "auto_session_end_emitted"


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
        path.write_text(json.dumps(payload), encoding="utf-8")
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
