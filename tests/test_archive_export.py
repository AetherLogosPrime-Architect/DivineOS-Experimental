"""Regression-pin tests for the archive-export tool.

Andrew named the sync-model gap 2026-05-14: archives drifted because
they were one-shot manual exports. The export tool regenerates the
mirrors from canonical SQLite — runnable on demand or wired into
scheduled-tasks.

These tests pin: the registry has the expected exports, each export
writes the expected file, export_all is fail-soft per-table.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from divineos.core.archive_export import (
    export_all,
    export_one,
    list_exports,
)


def test_list_exports_returns_expected_set() -> None:
    """LOAD-BEARING: the registry has the expected substantive
    tables. If one is missing, the auto-export is incomplete."""
    names = set(list_exports())
    expected = {
        "bio",
        "principles",
        "directives",
        "core_memory",
        "claims",
        "lessons",
        "holding_room",
        "opinions",
        "pre_registrations",
        "decisions",
        "observations",
    }
    missing = expected - names
    assert not missing, f"Missing exports: {missing}"


def test_export_one_unknown_name_raises() -> None:
    """Calling export_one with an unknown name raises ValueError —
    fail-loud on misuse so the operator sees the typo."""
    try:
        export_one("not_a_real_export", dest_dir="/tmp")
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "Unknown export" in str(e)


def test_export_principles_writes_file() -> None:
    """LOAD-BEARING: export_principles writes a file at the expected
    path. Verifies the per-table function executes end-to-end."""
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp)
        n = export_one("principles", dest_dir=dest)
        assert (dest / "principles.md").exists()
        assert n >= 0  # row count, can be 0 if fresh install
        content = (dest / "principles.md").read_text(encoding="utf-8")
        assert "# Principles" in content
        assert "Exported:" in content


def test_export_core_memory_writes_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp)
        n = export_one("core_memory", dest_dir=dest)
        assert (dest / "core_memory.md").exists()
        assert n >= 0


def test_export_all_returns_results_per_name() -> None:
    """LOAD-BEARING: export_all returns a dict with each export's
    row count. Fail-soft per export — one broken table does not
    block others."""
    with tempfile.TemporaryDirectory() as tmp:
        results = export_all(dest_dir=tmp)
    expected_names = set(list_exports())
    for name in expected_names:
        assert name in results, f"export_all missing result for {name}"


def test_export_all_writes_all_files() -> None:
    """Every registered export writes its file under dest_dir."""
    with tempfile.TemporaryDirectory() as tmp:
        export_all(dest_dir=tmp)
        dest = Path(tmp)
        for name in list_exports():
            expected = dest / f"{name}.md"
            assert expected.exists(), f"Missing archive file: {expected.name}"


def test_export_one_dest_dir_created_if_missing() -> None:
    """If the dest directory doesn't exist, export_one creates it
    rather than failing. Makes the tool safe to run in a fresh
    repo where docs/archives/ might not yet exist."""
    with tempfile.TemporaryDirectory() as tmp:
        nested = Path(tmp) / "deeper" / "archives"
        assert not nested.exists()
        export_one("core_memory", dest_dir=nested)
        assert nested.exists()
        assert (nested / "core_memory.md").exists()
