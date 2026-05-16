"""Multiplex context-state persistence.

Stores the current context (set manually for MVP, automated post-MVP)
in a small JSON file in the HUD directory. Per entry 71: MVP version
uses manual setting via CLI; automated detection comes after MVP
passes falsifiers.

Reference: prereg-ebee9082d201, exploration/71_multiplex_rendering_contract.md
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from divineos.core._hud_io import _get_hud_dir
from divineos.core.multiplex_panels import KNOWN_CONTEXTS

_STATE_FILENAME = ".multiplex_context"
_DEFAULT_CONTEXT = "chatting"


def _state_path() -> Path:
    return _get_hud_dir() / _STATE_FILENAME


def get_context() -> str:
    """Return current context. Falls back to default if unset or invalid."""
    path = _state_path()
    if not path.exists():
        return _DEFAULT_CONTEXT
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _DEFAULT_CONTEXT
    if not isinstance(data, dict):
        return _DEFAULT_CONTEXT
    ctx = data.get("context", _DEFAULT_CONTEXT)
    if ctx not in KNOWN_CONTEXTS:
        return _DEFAULT_CONTEXT
    return ctx


def set_context(context: str) -> None:
    """Set current context. Raises ValueError if unknown."""
    if context not in KNOWN_CONTEXTS:
        raise ValueError(
            f"Unknown context: {context}. Known: {list(KNOWN_CONTEXTS)}"
        )
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"context": context, "set_at": int(time.time())}, indent=2),
        encoding="utf-8",
    )


def clear_context() -> None:
    """Reset to default by removing the state file."""
    path = _state_path()
    if path.exists():
        path.unlink()
