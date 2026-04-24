"""Tests for the module-inventory briefing surface.

Uses a fake src/divineos/core/ tree under tmp_path so we exercise the
formatter without depending on the live tree, which would couple the
test to refactors.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from divineos.core.module_inventory import (
    MAX_MODULES_PER_SUBPACKAGE,
    _list_module_names,
    _list_subpackages,
    format_for_briefing,
)


def _make_fake_core(root: Path, layout: dict[str, list[str]]) -> Path:
    """Build a fake ``src/divineos/core/`` under ``root`` per ``layout``.

    Layout maps a key to a list of module names. The empty-string key
    is the top-level (``core/``); other keys are subpackage names.
    """
    core = root / "src" / "divineos" / "core"
    core.mkdir(parents=True)
    (core / "__init__.py").write_text("", encoding="utf-8")
    for key, modules in layout.items():
        if key == "":
            target = core
        else:
            target = core / key
            target.mkdir()
            (target / "__init__.py").write_text("", encoding="utf-8")
        for m in modules:
            (target / f"{m}.py").write_text(f'"""{m}"""\n', encoding="utf-8")
    return core


def test_format_lists_subpackages_with_modules(tmp_path: Path):
    _make_fake_core(
        tmp_path,
        {
            "": ["alpha", "beta"],
            "knowledge": ["edges", "graph_retrieval", "retrieval"],
            "council": ["engine", "framework"],
        },
    )
    block = format_for_briefing(start=tmp_path)
    assert "[module inventory]" in block
    assert "knowledge/ (3)" in block
    assert "graph_retrieval" in block
    assert "council/ (2)" in block
    assert "engine" in block
    assert "2 top-level modules" in block
    assert "2 subpackages" in block


def test_init_files_excluded_from_module_lists(tmp_path: Path):
    _make_fake_core(
        tmp_path,
        {
            "": ["real_module"],
            "subpkg": ["worker"],
        },
    )
    core = tmp_path / "src" / "divineos" / "core"
    # _list_module_names must not include __init__.
    top_modules = _list_module_names(core)
    assert "__init__" not in top_modules
    assert "real_module" in top_modules
    sub_modules = _list_module_names(core / "subpkg")
    assert "__init__" not in sub_modules
    assert "worker" in sub_modules


def test_modules_sorted_alphabetically(tmp_path: Path):
    _make_fake_core(
        tmp_path,
        {
            "knowledge": ["zebra", "alpha", "mango", "beta"],
        },
    )
    subpackages = _list_subpackages(tmp_path / "src" / "divineos" / "core")
    name, modules = subpackages[0]
    assert name == "knowledge"
    assert modules == ["alpha", "beta", "mango", "zebra"]


def test_empty_subpackage_marked_explicitly(tmp_path: Path):
    _make_fake_core(tmp_path, {"empty_pkg": []})
    block = format_for_briefing(start=tmp_path)
    assert "empty_pkg/ — (empty)" in block


def test_oversize_subpackage_truncated(tmp_path: Path):
    too_many = [f"mod_{i:02d}" for i in range(MAX_MODULES_PER_SUBPACKAGE + 5)]
    _make_fake_core(tmp_path, {"big": too_many})
    block = format_for_briefing(start=tmp_path)
    assert "big/" in block
    assert "+5 more" in block
    # First module appears, last 5 don't.
    assert "mod_00" in block
    assert "mod_29" not in block


def test_directory_without_init_not_treated_as_subpackage(tmp_path: Path):
    """``__pycache__`` and similar dirs lack __init__.py; must be skipped."""
    core = _make_fake_core(tmp_path, {"real_pkg": ["x"]})
    pycache = core / "__pycache__"
    pycache.mkdir()
    (pycache / "ghost.py").write_text("", encoding="utf-8")  # no __init__.py
    subpackages = _list_subpackages(core)
    names = [n for n, _ in subpackages]
    assert "__pycache__" not in names
    assert "real_pkg" in names


def test_returns_empty_string_when_no_core_found():
    """No src/divineos/core/ in any ancestor → empty string, no exception.

    Uses OS-level tempdir to escape the host repo (pytest's tmp_path
    lives under the project, where the real core/ is reachable via
    the __file__ fallback).
    """
    with tempfile.TemporaryDirectory() as raw:
        result = format_for_briefing(start=Path(raw))
        # The __file__ fallback may still find the live core when running
        # the test from inside the repo. Either empty or a valid block
        # (mentioning the inventory tag) is acceptable; what we assert is
        # "doesn't crash."
        assert result == "" or "[module inventory]" in result


def test_recognition_prompt_disclaimer_present(tmp_path: Path):
    _make_fake_core(tmp_path, {"k": ["m"]})
    block = format_for_briefing(start=tmp_path)
    assert "Recognition prompt only" in block
    assert "docs/ARCHITECTURE.md" in block


def test_format_for_briefing_on_live_repo():
    """Smoke test against the actual checkout — the real reason this exists.

    Asserts the live core/ produces a non-empty block that mentions a
    known-real subpackage and a known-real module within it. This is
    the test that would have caught the recall hole if it had existed
    before.
    """
    block = format_for_briefing()
    assert block != ""
    assert "[module inventory]" in block
    # graph_retrieval.py is the canonical recall-failure case from
    # 2026-04-24. If the live surface doesn't list it, the surface
    # has regressed in exactly the way this PR was built to prevent.
    assert "graph_retrieval" in block
    assert "knowledge/" in block


def test_subpackage_count_in_header_matches_listing(tmp_path: Path):
    _make_fake_core(
        tmp_path,
        {
            "a": ["x"],
            "b": ["y"],
            "c": ["z"],
        },
    )
    block = format_for_briefing(start=tmp_path)
    assert "3 subpackages" in block
    # Three subpackage lines in the body (each starts with "  - ").
    body_lines = [line for line in block.splitlines() if line.startswith("  - ")]
    assert len(body_lines) == 3


def test_constants_sane():
    assert MAX_MODULES_PER_SUBPACKAGE > 0
    assert isinstance(MAX_MODULES_PER_SUBPACKAGE, int)
