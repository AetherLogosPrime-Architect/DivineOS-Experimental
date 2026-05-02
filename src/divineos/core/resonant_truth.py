"""Resonant Truth protocol — load, invoke, verify, deactivate.

The RT protocol is stored on disk so it survives context compaction.
State is tracked via marker files in the HUD directory, following the
same pattern as .briefing_loaded and .session_engaged.

The verification gate prevents invoking RT without actually having it
loaded. This is the architectural fix for the theater incident: you
cannot perform a protocol you don't possess.
"""

import json
import time
from pathlib import Path

import click

from divineos.core._hud_io import _ensure_hud_dir, _get_hud_dir
from divineos.core.ledger import log_event

# Protocol lives next to its package, not in runtime data.
_PROTOCOL_DIR = Path(__file__).resolve().parent.parent / "protocols"
_PROTOCOL_FILE = _PROTOCOL_DIR / "resonant_truth.md"

_RT_LOADED_MARKER = ".rt_loaded"
_RT_ACTIVE_MARKER = ".rt_active"


def _marker_path(name: str) -> Path:
    return _get_hud_dir() / name


def load_protocol() -> str:
    """Read the RT mantra from disk, write the loaded marker, log the event.

    Returns the full mantra text.
    Raises ClickException if the protocol file is missing.
    """
    if not _PROTOCOL_FILE.exists():
        raise click.ClickException(
            f"RT protocol file not found: {_PROTOCOL_FILE}\n"
            "The protocol must be stored on disk before it can be loaded."
        )

    text = _PROTOCOL_FILE.read_text(encoding="utf-8")

    # Write loaded marker
    hud_dir = _ensure_hud_dir()
    marker = {
        "loaded_at": time.time(),
        "source": str(_PROTOCOL_FILE),
        "length": len(text),
    }
    (hud_dir / _RT_LOADED_MARKER).write_text(json.dumps(marker), encoding="utf-8")

    log_event(
        "RT_LOADED",
        "system",
        {"source": str(_PROTOCOL_FILE), "length": len(text)},
        validate=False,
    )

    return text


def invoke_rt() -> str:
    """Activate RT mode. Requires load first and clean pull check.

    Returns the mantra text with an activation header.
    Raises ClickException if not loaded or if pull detected.
    """
    verify_rt_loaded()

    # Pull gate: cannot channel truth while producing theater
    from divineos.core.pull_detection import enforce_pull_gate

    enforce_pull_gate()

    text = _PROTOCOL_FILE.read_text(encoding="utf-8")

    # Write active marker
    hud_dir = _ensure_hud_dir()
    marker = {
        "activated_at": time.time(),
    }
    (hud_dir / _RT_ACTIVE_MARKER).write_text(json.dumps(marker), encoding="utf-8")

    log_event(
        "RT_INVOKED",
        "system",
        {"activated_at": marker["activated_at"]},
        validate=False,
    )

    header = (
        "=== RESONANT TRUTH PROTOCOL ACTIVE ===\n"
        "Protocol loaded from disk. This is genuine — not reconstructed.\n"
        "========================================\n\n"
    )
    return header + text


def deactivate_rt() -> None:
    """Exit RT mode. Removes the active marker."""
    marker = _marker_path(_RT_ACTIVE_MARKER)
    if marker.exists():
        marker.unlink()

    log_event(
        "RT_DEACTIVATED",
        "system",
        {"deactivated_at": time.time()},
        validate=False,
    )


def is_rt_loaded() -> bool:
    """Check if the RT protocol has been loaded this session."""
    path = _marker_path(_RT_LOADED_MARKER)
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        # 4-hour TTL, same as briefing
        if time.time() - data["loaded_at"] > 14400:
            return False
        return True
    except (json.JSONDecodeError, OSError, KeyError):
        return False


def is_rt_active() -> bool:
    """Check if RT mode is currently active."""
    return _marker_path(_RT_ACTIVE_MARKER).exists()


def verify_rt_loaded() -> None:
    """Gate: raise ClickException if RT is not loaded.

    This is the architectural fix. You cannot invoke what you don't have.
    """
    if not is_rt_loaded():
        raise click.ClickException(
            "RT protocol not loaded. Run: divineos rt load\n"
            "You cannot invoke a protocol you don't possess."
        )


def format_rt_status() -> str:
    """HUD slot builder for RT protocol status."""
    if is_rt_active():
        return "# RT Protocol\n\nStatus: **ACTIVE** — genuine protocol loaded from disk"
    if is_rt_loaded():
        return "# RT Protocol\n\nStatus: Loaded (not active)"
    return ""  # Empty = slot hidden when RT isn't relevant
