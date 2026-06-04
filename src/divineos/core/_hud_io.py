"""HUD I/O — shared directory helpers used by hud.py and hud_slots_extra.py.

Extracted to break the hud ↔ hud_slots_extra circular import.
"""

from pathlib import Path


def _get_hud_dir() -> Path:
    """Resolve the HUD directory next to the FULLY-resolved DB path.

    Routes through the RUNTIME DB resolver (``_get_db_path``) so the HUD dir —
    and the ``.briefing_loaded`` marker inside it — lands in the SAME per-agent
    home the databases route to under ``DIVINEOS_HOME`` / ``.divineos_data_home``
    (#70).

    The old code used the IMPORT-TIME ``DB_PATH`` snapshot, frozen to whichever
    home loaded first — which is Aether's, because ``divineos`` is pip-installed
    editable from Aether's checkout. So a second agent (Aria), running from her
    own home, stamped her ``.briefing_loaded`` marker in HER home while the gate
    read it from Aether's path. The gate could never see her fresh briefing, so
    her ear-arm watcher was falsely gate-blocked — the "marker doesn't reach my
    home" bug (2026-06-03). #70 home-routed the databases at call-time but this
    helper kept reading the frozen snapshot.

    Resolving at call-time fixes it: each agent's HUD dir follows her own DB.
    ``DIVINEOS_DB`` still wins (it is the first branch inside ``_get_db_path``);
    Aether's default checkout is unchanged (same ``src/data`` parent).
    """
    from divineos.core._ledger_base import _get_db_path

    return _get_db_path().parent / "hud"


def _ensure_hud_dir() -> Path:
    hud_dir = _get_hud_dir()
    hud_dir.mkdir(parents=True, exist_ok=True)
    return hud_dir
