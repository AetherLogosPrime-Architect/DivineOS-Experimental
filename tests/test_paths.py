"""Tests for centralized ~/.divineos path construction.

Audit finding 2026-05-03 round 3: ``Path.home() / ".divineos"`` was
reconstructed across 20+ modules. Adding a single helper reduces
duplication and — more importantly — fixes a pre-existing test
isolation bug: conftest sets ``DIVINEOS_HOME`` for per-test
isolation, but the legacy modules ignored it and wrote to the
real ``~/.divineos`` instead.
"""

from __future__ import annotations

from pathlib import Path


from divineos.core.paths import divineos_home, marker_path, state_dir


def test_divineos_home_default(monkeypatch):
    """Without DIVINEOS_HOME set, returns ~/.divineos."""
    monkeypatch.delenv("DIVINEOS_HOME", raising=False)
    home = divineos_home()
    assert home == Path.home() / ".divineos"


def test_divineos_home_honors_env_override(monkeypatch, tmp_path):
    """DIVINEOS_HOME env var overrides the default. This is the
    isolation hook conftest uses to give each test a private state
    directory."""
    override = tmp_path / "custom_home"
    monkeypatch.setenv("DIVINEOS_HOME", str(override))
    assert divineos_home() == override


def test_marker_path_under_home(monkeypatch, tmp_path):
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
    p = marker_path("compass_required.json")
    assert p == tmp_path / "compass_required.json"


def test_state_dir_under_home(monkeypatch, tmp_path):
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
    p = state_dir("supervisor")
    assert p == tmp_path / "supervisor"


def test_marker_path_does_not_create(monkeypatch, tmp_path):
    """marker_path returns a path; it does NOT create the file or
    parent directory. Callers are responsible for ensuring
    parents exist before writing."""
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path / "not_yet_created"))
    p = marker_path("test.json")
    assert not p.exists()
    assert not p.parent.exists()


def test_marker_path_with_existing_helpers(monkeypatch, tmp_path):
    """The 7 markers migrated in this commit should all resolve
    under the test's DIVINEOS_HOME, proving the test-isolation
    hookup works end-to-end."""
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))

    from divineos.core import (
        compass_required_marker,
        correction_marker,
        extract_marker,
        hedge_marker,
        mansion_quiet_marker,
        theater_marker,
    )
    from divineos.core.void import mode_marker

    # Each marker_path() call should land under tmp_path, not under
    # the real ~/.divineos. Pre-migration, these would have leaked
    # to the user's home directory during tests.
    assert compass_required_marker.marker_path().is_relative_to(tmp_path)
    assert correction_marker.marker_path().is_relative_to(tmp_path)
    assert extract_marker.marker_path().is_relative_to(tmp_path)
    assert hedge_marker.marker_path().is_relative_to(tmp_path)
    assert mansion_quiet_marker.marker_path().is_relative_to(tmp_path)
    assert theater_marker.marker_path().is_relative_to(tmp_path)
    assert mode_marker.marker_path().is_relative_to(tmp_path)
