"""Corrections notebook — the user's exact words, raw, no framing.

When the user corrects something, the architectural fix is to capture their
exact words verbatim with a timestamp and nothing else — no severity, no
category, no interpretation field. The reflex this is meant to replace is
the one that turns 'they said X' into 'I got Y wrong about X.' Distortion
rides on truth. The fix is to keep the truth uncoated.

Design layer: the analysis-as-substitute pattern fires pre-analytically;
only a different reflex can intercept it, and reflexes come from reps under
live conditions. This is the rep-tool. Structural layer: the rep alone dies
when the session dies — so it must be carved into structure to survive.

Both layers in one file: write raw, store persistent, surface in briefing
so the next session reads the actual words before forming any frame.
"""

from __future__ import annotations

import json
import time
from typing import Any

from divineos.core._hud_io import _ensure_hud_dir

_CORRECTIONS_FILE = "corrections.jsonl"

_CORR_ERRORS = (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError)


def _path() -> Any:
    return _ensure_hud_dir() / _CORRECTIONS_FILE


def log_correction(text: str, session_id: str | None = None) -> dict[str, Any]:
    """Capture a correction verbatim. No framing. No interpretation.

    Append-only JSONL — never edits, never reframes. The whole point is
    that what gets stored is exactly what was said, not my reading of it.
    """
    entry: dict[str, Any] = {
        "text": text,
        "timestamp": time.time(),
        "session_id": session_id or "",
    }
    line = json.dumps(entry, ensure_ascii=False)
    with _path().open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    return entry


def load_corrections() -> list[dict[str, Any]]:
    """Read all corrections in chronological order."""
    p = _path()
    if not p.exists():
        return []
    out: list[dict[str, Any]] = []
    try:
        with p.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except _CORR_ERRORS:
        return []
    return out


def recent_corrections(limit: int = 5) -> list[dict[str, Any]]:
    """Return the most recent N corrections, newest first."""
    all_c = load_corrections()
    return list(reversed(all_c[-limit:]))


def format_for_briefing(limit: int = 5) -> str:
    """Render recent corrections for the briefing surface.

    Read these BEFORE forming any frame about what's going on. The whole
    purpose is to put the user's actual words in front of next-me before
    any interpretation layer engages.
    """
    recents = recent_corrections(limit=limit)
    if not recents:
        return ""

    lines = ["", "# Recent Corrections (read raw — the user's exact words)", ""]
    for c in recents:
        ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(c.get("timestamp", 0)))
        text = (c.get("text") or "").strip()
        # Don't truncate. The whole point is the full uncoated text.
        lines.append(f"  [{ts}]")
        for ln in text.splitlines() or [text]:
            lines.append(f"    {ln}")
        lines.append("")
    return "\n".join(lines)
