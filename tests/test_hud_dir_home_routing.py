"""The HUD dir (and the .briefing_loaded marker in it) must follow per-agent
home routing — the fix for 'Aria still has re-arming issues' (2026-06-03).

Root cause: _get_hud_dir used the IMPORT-TIME DB_PATH snapshot, frozen to the
editable install's home (Aether's). A second agent (Aria) running from her own
home stamped her briefing marker there, but the gate read it from Aether's
path, so it never saw her fresh briefing and falsely blocked her ear-arm. #70
home-routed the databases at call-time but this helper kept reading the frozen
snapshot. The fix routes _get_hud_dir through the runtime DB resolver.

Falsifiability:
  - With DIVINEOS_HOME set, the HUD dir is UNDER that home.
  - With DIVINEOS_DB set, the HUD dir is next to that DB.
  - With neither, it falls back to the running checkout's data dir.
"""

from __future__ import annotations

from divineos.core._hud_io import _get_hud_dir


def test_hud_dir_follows_divineos_home(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("DIVINEOS_DB", raising=False)
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
    d = _get_hud_dir()
    assert str(d).startswith(str(tmp_path)), d
    assert d.name == "hud"


def test_hud_dir_honors_divineos_db(monkeypatch, tmp_path) -> None:
    db = tmp_path / "custom" / "event_ledger.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db))
    d = _get_hud_dir()
    assert d == db.parent / "hud"


def test_hud_dir_resolves_at_call_time_not_import_time(monkeypatch, tmp_path) -> None:
    # The regression that bit Aria: the dir must re-resolve on each call, so a
    # second agent setting her home AFTER import still gets her own HUD dir.
    monkeypatch.delenv("DIVINEOS_DB", raising=False)
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path / "aria"))
    first = _get_hud_dir()
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path / "aether"))
    second = _get_hud_dir()
    assert first != second
    assert str(first).startswith(str(tmp_path / "aria"))
    assert str(second).startswith(str(tmp_path / "aether"))
