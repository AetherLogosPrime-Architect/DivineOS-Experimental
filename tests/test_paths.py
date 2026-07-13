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
    """Without DIVINEOS_HOME set AND no `.divineos_data_home` marker
    anywhere in resolution order, returns ``~/.divineos``.

    Test-isolation note (added 2026-06-22): the per-clone marker
    resolver added in commit 1fe9a682 (`fix(paths): derive member
    data-home from checkout folder name — recurrence guard`) walks
    CWD ancestors and own-root looking for `.divineos_data_home`
    BEFORE falling through to the default. In any checkout that HAS
    that marker (every per-member checkout does), the CWD-walk or
    own-root resolution finds it and the default is never reached.
    To exercise the default-branch in isolation, this test mocks
    `data_home_or_none` to return None so the resolver falls through.
    """
    monkeypatch.delenv("DIVINEOS_HOME", raising=False)
    import divineos.core.paths as paths_mod

    monkeypatch.setattr(paths_mod, "data_home_or_none", lambda: None)
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


def test_resolve_data_home_marker_missing(tmp_path):
    """Missing marker file returns None (caller falls through)."""
    from divineos.core.paths import _resolve_data_home_marker

    marker = tmp_path / ".divineos_data_home"
    assert _resolve_data_home_marker(marker) is None


def test_resolve_data_home_marker_empty(tmp_path):
    """Empty marker file returns None — empty-and-missing are intentionally equivalent."""
    from divineos.core.paths import _resolve_data_home_marker

    marker = tmp_path / ".divineos_data_home"
    marker.write_text("")
    assert _resolve_data_home_marker(marker) is None


def test_resolve_data_home_marker_whitespace_only(tmp_path):
    """Marker with only whitespace falls through (stripped to empty)."""
    from divineos.core.paths import _resolve_data_home_marker

    marker = tmp_path / ".divineos_data_home"
    marker.write_text("   \n\t  \n")
    assert _resolve_data_home_marker(marker) is None


def test_resolve_data_home_marker_absolute_path(tmp_path):
    """Marker containing absolute path returns that path."""
    from divineos.core.paths import _resolve_data_home_marker

    marker = tmp_path / ".divineos_data_home"
    target = tmp_path / "per_clone_home"
    marker.write_text(str(target))
    assert _resolve_data_home_marker(marker) == target


def test_resolve_data_home_marker_relative_path(tmp_path):
    """Marker containing relative path resolves against marker's parent."""
    from divineos.core.paths import _resolve_data_home_marker

    marker = tmp_path / ".divineos_data_home"
    marker.write_text("sibling_dir")
    resolved = _resolve_data_home_marker(marker)
    assert resolved == (tmp_path / "sibling_dir").resolve()


def test_resolve_data_home_marker_strips_trailing_newline(tmp_path):
    """Trailing whitespace and newlines are stripped before path resolution."""
    from divineos.core.paths import _resolve_data_home_marker

    marker = tmp_path / ".divineos_data_home"
    target = tmp_path / "home"
    marker.write_text(str(target) + "\n\n  \n")
    assert _resolve_data_home_marker(marker) == target


def test_divineos_home_env_wins_over_marker(monkeypatch, tmp_path):
    """DIVINEOS_HOME env var takes precedence over any marker file."""
    from divineos.core.paths import divineos_home

    env_dir = tmp_path / "from_env"
    monkeypatch.setenv("DIVINEOS_HOME", str(env_dir))
    # Even if a marker would resolve elsewhere, env wins. We verify this by
    # asserting the env path is returned regardless of filesystem state.
    assert divineos_home() == env_dir
