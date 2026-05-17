"""OS-native mid-turn substrate re-prime.

Andrew named the failure 2026-05-14 night: pre-tool-context.sh was
a 129-line bash hook with throttle bookkeeping, file-extension
filtering, timeline recall, and surface-file write all embedded.
This module is the OS-native equivalent.

## What it does

When the agent is about to Edit/Read/Write a source-shaped file,
this surfacer fetches the prior-work timeline for that file (recent
edits, corrections filed against it, decisions referencing it) and
writes a markdown surface to ``~/.divineos/mid_turn_context.md``
for the agent to read alongside its working context.

Throttle: skips repeat fires on the same file within 60 seconds
so a tight edit/read loop does not spam the surface file.

## OS-portable

Any harness can call ``surface_mid_turn(tool_name, file_path)`` to
get the same priming behavior. The Claude Code PreToolUse hook is
one possible caller.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from divineos.core.paths import divineos_home

_THROTTLE_FILE = divineos_home() / "mid_turn_throttle.json"
_SURFACE_FILE = divineos_home() / "mid_turn_context.md"
_THROTTLE_SECONDS = 60
_THROTTLE_MAX_ENTRIES = 50

# Tools that trigger mid-turn surfacing. Read is included because
# orienting on a file you're about to read benefits from the
# timeline just like editing does.
_RELEVANT_TOOLS = frozenset({"Edit", "Read", "Write", "NotebookEdit"})

# File extensions that count as "source-shaped" — code, config, docs.
# Other files (binaries, images, transcripts) do not warrant the
# substrate-priming overhead.
_SOURCE_EXTENSIONS = (
    ".py",
    ".md",
    ".sh",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".sql",
    ".ipynb",
)


def _read_throttle() -> dict[str, float]:
    """Read the throttle state. Fail-open to empty dict."""
    if not _THROTTLE_FILE.exists():
        return {}
    try:
        data = json.loads(_THROTTLE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def _write_throttle(throttle: dict[str, float]) -> None:
    """Write the throttle state. Fail-soft on I/O error."""
    try:
        divineos_home().mkdir(exist_ok=True)
        _THROTTLE_FILE.write_text(json.dumps(throttle), encoding="utf-8")
    except OSError:
        pass


def _is_source_file(file_path: str) -> bool:
    """True if the path ends in a source-shaped extension."""
    if not file_path:
        return False
    low = file_path.lower()
    return any(low.endswith(ext) for ext in _SOURCE_EXTENSIONS)


def surface_mid_turn(tool_name: str, file_path: str) -> dict[str, Any]:
    """Run mid-turn substrate surfacing for a file about to be touched.

    Returns a dict with diagnostics:
    - ``surfaced``: True if a new surface file was written
    - ``throttled``: True if the file was skipped because seen recently
    - ``no_events``: True if recall_timeline returned nothing
    - ``reason``: short string explaining why surfacer was/wasn't run

    Side effects:
    - Updates ``~/.divineos/mid_turn_throttle.json`` with the seen-at
    - Writes or clears ``~/.divineos/mid_turn_context.md``
    """
    if tool_name not in _RELEVANT_TOOLS:
        return {
            "surfaced": False,
            "throttled": False,
            "no_events": False,
            "reason": "tool_not_relevant",
        }
    if not file_path or not _is_source_file(file_path):
        return {
            "surfaced": False,
            "throttled": False,
            "no_events": False,
            "reason": "not_source_file",
        }

    # Throttle check
    now = time.time()
    throttle = _read_throttle()
    last = throttle.get(file_path, 0)
    if now - last < _THROTTLE_SECONDS:
        return {"surfaced": False, "throttled": True, "no_events": False, "reason": "throttled"}

    # Update throttle
    throttle[file_path] = now
    if len(throttle) > _THROTTLE_MAX_ENTRIES:
        sorted_items = sorted(throttle.items(), key=lambda kv: -kv[1])[:_THROTTLE_MAX_ENTRIES]
        throttle = dict(sorted_items)
    _write_throttle(throttle)

    # Fetch timeline
    try:
        from divineos.core.memory_types import format_timeline, recall_timeline
    except Exception:  # noqa: BLE001 - observability boundary
        return {
            "surfaced": False,
            "throttled": False,
            "no_events": False,
            "reason": "memory_types_unavailable",
        }

    file_basename = Path(file_path).name
    try:
        events = recall_timeline(
            topic=file_basename,
            file_path=file_basename,
            per_source_limit=3,
            total_limit=8,
        )
    except Exception:  # noqa: BLE001 - observability boundary
        return {
            "surfaced": False,
            "throttled": False,
            "no_events": False,
            "reason": "recall_failed",
        }

    if not events:
        # Clear any prior surface so stale content doesn't leak forward.
        if _SURFACE_FILE.exists():
            try:
                _SURFACE_FILE.unlink()
            except OSError:
                pass
        return {"surfaced": False, "throttled": False, "no_events": True, "reason": "no_events"}

    header = (
        f"# Mid-turn re-prime — prior work on `{file_basename}`\n\n"
        f"_Auto-surfaced by PreToolUse on {tool_name}. Read before deciding "
        f"how to handle this file._\n\n"
    )
    try:
        divineos_home().mkdir(exist_ok=True)
        _SURFACE_FILE.write_text(header + format_timeline(events), encoding="utf-8")
    except OSError:
        return {"surfaced": False, "throttled": False, "no_events": False, "reason": "write_failed"}

    return {"surfaced": True, "throttled": False, "no_events": False, "reason": "surfaced"}


__all__ = ["surface_mid_turn"]
