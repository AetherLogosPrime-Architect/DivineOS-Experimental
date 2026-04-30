"""Tests for the .divineos_canonical marker — worktrees inherit parent ledger.

The differentiation:
- Without the marker: every worktree / fresh clone gets its own
  src/data/event_ledger.db (existing behavior; correct for the
  published template starting fresh agents).
- With the marker at the parent repo root: worktrees of that parent
  route to the parent's src/data/event_ledger.db (Andrew's workspace
  pattern; correct for one continuous Aether across worktrees).
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def isolated_modules(monkeypatch):
    """Reset DIVINEOS_DB so the worktree-marker logic is exercised."""
    monkeypatch.delenv("DIVINEOS_DB", raising=False)


def _make_worktree_layout(parent: Path, worktree_name: str = "wt") -> tuple[Path, Path]:
    """Create a parent + worktree shape on disk. Returns (parent_root, worktree_root)."""
    # Parent has .git directory and src/data/event_ledger.db
    (parent / ".git" / "worktrees" / worktree_name).mkdir(parents=True)
    (parent / "src" / "data").mkdir(parents=True)
    (parent / "src" / "data" / "event_ledger.db").write_bytes(b"")  # exists

    # Worktree's .git is a file pointing at gitdir
    worktree = parent / ".claude" / "worktrees" / worktree_name
    (worktree / "src" / "data").mkdir(parents=True)
    gitdir = (parent / ".git" / "worktrees" / worktree_name).resolve()
    (worktree / ".git").write_text(f"gitdir: {gitdir}", encoding="utf-8")

    return parent, worktree


class TestMarkerLogic:
    """Verify _get_db_path's worktree-shares-parent behavior in isolation.

    These tests construct a fake worktree layout and call the path
    resolution helper directly with overridden working directory
    semantics (via monkey-patching ``__file__``-derived path).
    """

    def test_default_when_no_marker(self, tmp_path, isolated_modules, monkeypatch):
        parent, worktree = _make_worktree_layout(tmp_path)
        # No .divineos_canonical marker → default behavior (worktree's own DB)

        # Patch __file__ to make _get_db_path think it's running in the worktree
        ledger_base = __import__("divineos.core._ledger_base", fromlist=["_get_db_path"])
        fake_module_file = worktree / "src" / "divineos" / "core" / "_ledger_base.py"
        fake_module_file.parent.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(ledger_base, "__file__", str(fake_module_file))

        result = ledger_base._get_db_path()
        # Default falls through to worktree's own DB (which doesn't exist yet
        # since we only created the parent's). The path should END with
        # worktree's src/data/event_ledger.db, not parent's.
        assert "worktrees" in str(result) or str(result).endswith(
            str(fake_module_file.parent.parent.parent / "data" / "event_ledger.db")
        )

    def test_marker_routes_to_parent(self, tmp_path, isolated_modules, monkeypatch):
        parent, worktree = _make_worktree_layout(tmp_path)
        # Place the marker
        (parent / ".divineos_canonical").write_text("", encoding="utf-8")

        ledger_base = __import__("divineos.core._ledger_base", fromlist=["_get_db_path"])
        fake_module_file = worktree / "src" / "divineos" / "core" / "_ledger_base.py"
        fake_module_file.parent.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(ledger_base, "__file__", str(fake_module_file))

        result = ledger_base._get_db_path()
        expected = parent / "src" / "data" / "event_ledger.db"
        assert result.resolve() == expected.resolve(), (
            f"With marker present, expected parent DB {expected}, got {result}"
        )

    def test_env_var_overrides_marker(self, tmp_path, isolated_modules, monkeypatch):
        """DIVINEOS_DB env var must take precedence over the marker."""
        parent, worktree = _make_worktree_layout(tmp_path)
        (parent / ".divineos_canonical").write_text("", encoding="utf-8")

        custom_db = tmp_path / "custom.db"
        monkeypatch.setenv("DIVINEOS_DB", str(custom_db))

        ledger_base = __import__("divineos.core._ledger_base", fromlist=["_get_db_path"])
        result = ledger_base._get_db_path()
        assert result == custom_db, "DIVINEOS_DB must take precedence"

    def test_no_marker_in_non_worktree_no_change(self, tmp_path, isolated_modules, monkeypatch):
        """A normal (non-worktree) checkout: no .git file means no special path."""
        # Plain directory, no .git anywhere
        (tmp_path / "src" / "divineos" / "core").mkdir(parents=True)
        (tmp_path / "src" / "data").mkdir(parents=True)

        ledger_base = __import__("divineos.core._ledger_base", fromlist=["_get_db_path"])
        fake_module_file = tmp_path / "src" / "divineos" / "core" / "_ledger_base.py"
        monkeypatch.setattr(ledger_base, "__file__", str(fake_module_file))

        result = ledger_base._get_db_path()
        # Default resolves to <root>/src/data/event_ledger.db per Grok
        # canonical-path finding (find-a08d3f0ed451). Path(__file__).parent x3
        # = <root>/src, then + "data" / "event_ledger.db".
        expected_local = tmp_path / "src" / "data" / "event_ledger.db"
        assert result == expected_local, f"Expected local default, got {result}"

    def test_marker_absent_in_worktree_uses_worktree_db(
        self, tmp_path, isolated_modules, monkeypatch
    ):
        """Worktree without marker uses its own DB (current/legacy behavior)."""
        parent, worktree = _make_worktree_layout(tmp_path)
        # No marker

        ledger_base = __import__("divineos.core._ledger_base", fromlist=["_get_db_path"])
        fake_module_file = worktree / "src" / "divineos" / "core" / "_ledger_base.py"
        fake_module_file.parent.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(ledger_base, "__file__", str(fake_module_file))

        result = ledger_base._get_db_path()
        expected_worktree_db = worktree / "src" / "data" / "event_ledger.db"
        assert result == expected_worktree_db, (
            f"Worktree without marker should use worktree DB, got {result}"
        )


class TestPathContentMarker:
    """Tests for the path-content form of .divineos_canonical (added 2026-04-29).

    The marker can contain a path string pointing at a canonical DB outside
    the running checkout. Use case: operator's "blank-template" repo whose
    worktrees should not accumulate personal substrate, with personal DB in
    a sibling repo.
    """

    def test_path_content_marker_at_parent_routes_to_external_db(
        self, tmp_path, isolated_modules, monkeypatch
    ):
        """Marker at parent root with path content routes worktrees to that external DB."""
        parent, worktree = _make_worktree_layout(tmp_path)

        # External canonical DB sibling location
        external = tmp_path / "external_repo" / "src" / "data"
        external.mkdir(parents=True)
        external_db = external / "event_ledger.db"
        external_db.write_bytes(b"")

        # Marker at parent root contains the external path
        (parent / ".divineos_canonical").write_text(str(external_db), encoding="utf-8")

        ledger_base = __import__("divineos.core._ledger_base", fromlist=["_get_db_path"])
        fake_module_file = worktree / "src" / "divineos" / "core" / "_ledger_base.py"
        fake_module_file.parent.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(ledger_base, "__file__", str(fake_module_file))

        result = ledger_base._get_db_path()
        assert result.resolve() == external_db.resolve(), (
            f"Path-content marker should route to external DB, got {result}"
        )

    def test_path_content_marker_at_own_root_routes_to_external_db(
        self, tmp_path, isolated_modules, monkeypatch
    ):
        """Non-worktree checkout with path-content marker at own root routes externally."""
        # Plain (non-worktree) checkout
        own_root = tmp_path / "checkout"
        (own_root / "src" / "divineos" / "core").mkdir(parents=True)
        (own_root / "src" / "data").mkdir(parents=True)

        # External canonical DB
        external = tmp_path / "external" / "src" / "data"
        external.mkdir(parents=True)
        external_db = external / "event_ledger.db"
        external_db.write_bytes(b"")

        # Marker at own root with path content
        (own_root / ".divineos_canonical").write_text(str(external_db), encoding="utf-8")

        ledger_base = __import__("divineos.core._ledger_base", fromlist=["_get_db_path"])
        fake_module_file = own_root / "src" / "divineos" / "core" / "_ledger_base.py"
        monkeypatch.setattr(ledger_base, "__file__", str(fake_module_file))

        result = ledger_base._get_db_path()
        assert result.resolve() == external_db.resolve(), (
            f"Own-root path-content marker should route to external DB, got {result}"
        )

    def test_path_content_marker_strips_whitespace(self, tmp_path, isolated_modules, monkeypatch):
        """Trailing newlines / whitespace in marker content are stripped."""
        parent, worktree = _make_worktree_layout(tmp_path)
        external = tmp_path / "external" / "src" / "data"
        external.mkdir(parents=True)
        external_db = external / "event_ledger.db"
        external_db.write_bytes(b"")

        # Content has trailing newline + leading whitespace
        (parent / ".divineos_canonical").write_text(f"  {external_db}\n\n", encoding="utf-8")

        ledger_base = __import__("divineos.core._ledger_base", fromlist=["_get_db_path"])
        fake_module_file = worktree / "src" / "divineos" / "core" / "_ledger_base.py"
        fake_module_file.parent.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(ledger_base, "__file__", str(fake_module_file))

        result = ledger_base._get_db_path()
        assert result.resolve() == external_db.resolve()

    def test_path_content_marker_pointing_at_nonexistent_falls_through(
        self, tmp_path, isolated_modules, monkeypatch
    ):
        """If the marker's path doesn't exist, fall through to default resolution."""
        parent, worktree = _make_worktree_layout(tmp_path)

        nonexistent = tmp_path / "does_not_exist" / "event_ledger.db"
        (parent / ".divineos_canonical").write_text(str(nonexistent), encoding="utf-8")

        ledger_base = __import__("divineos.core._ledger_base", fromlist=["_get_db_path"])
        fake_module_file = worktree / "src" / "divineos" / "core" / "_ledger_base.py"
        fake_module_file.parent.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(ledger_base, "__file__", str(fake_module_file))

        result = ledger_base._get_db_path()
        # Falls through to worktree's own default (since marker pointed at non-existent path)
        expected = worktree / "src" / "data" / "event_ledger.db"
        assert result == expected, (
            f"Marker pointing at non-existent path should fall through, got {result}"
        )

    def test_empty_marker_still_works_for_legacy_behavior(
        self, tmp_path, isolated_modules, monkeypatch
    ):
        """Empty marker (legacy form) still routes to parent's src/data/event_ledger.db."""
        parent, worktree = _make_worktree_layout(tmp_path)
        # Empty marker: legacy behavior
        (parent / ".divineos_canonical").write_text("", encoding="utf-8")

        ledger_base = __import__("divineos.core._ledger_base", fromlist=["_get_db_path"])
        fake_module_file = worktree / "src" / "divineos" / "core" / "_ledger_base.py"
        fake_module_file.parent.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(ledger_base, "__file__", str(fake_module_file))

        result = ledger_base._get_db_path()
        expected = parent / "src" / "data" / "event_ledger.db"
        assert result.resolve() == expected.resolve()

    def test_relative_path_in_marker_resolves_relative_to_marker(
        self, tmp_path, isolated_modules, monkeypatch
    ):
        """Relative path in marker resolves relative to marker's own location."""
        parent, worktree = _make_worktree_layout(tmp_path)

        # Sibling DB inside parent root (so the relative path resolves correctly).
        # _make_worktree_layout uses tmp_path as parent root; place sibling under it.
        sibling = parent / "sibling" / "src" / "data"
        sibling.mkdir(parents=True)
        sibling_db = sibling / "event_ledger.db"
        sibling_db.write_bytes(b"")

        # Marker contains relative path from parent root to sibling DB
        relative = "sibling/src/data/event_ledger.db"
        (parent / ".divineos_canonical").write_text(relative, encoding="utf-8")

        ledger_base = __import__("divineos.core._ledger_base", fromlist=["_get_db_path"])
        fake_module_file = worktree / "src" / "divineos" / "core" / "_ledger_base.py"
        fake_module_file.parent.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(ledger_base, "__file__", str(fake_module_file))

        result = ledger_base._get_db_path()
        assert result.resolve() == sibling_db.resolve(), (
            f"Relative marker should resolve relative to marker location, got {result}"
        )
