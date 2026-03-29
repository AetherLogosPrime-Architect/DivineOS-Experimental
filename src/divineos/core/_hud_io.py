"""HUD I/O — shared directory helpers used by hud.py and hud_slots_extra.py.

Extracted to break the hud ↔ hud_slots_extra circular import.
"""

import os
from pathlib import Path


def _get_hud_dir() -> Path:
    """Resolve HUD directory from current DB path."""
    env_path = os.environ.get("DIVINEOS_DB")
    if env_path:
        return Path(env_path).parent / "hud"

    from divineos.core.ledger import DB_PATH

    return DB_PATH.parent / "hud"


def _ensure_hud_dir() -> Path:
    hud_dir = _get_hud_dir()
    hud_dir.mkdir(parents=True, exist_ok=True)
    return hud_dir
