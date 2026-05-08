"""Tests for the orphan-modules detector's re-export and unwired-marker logic.

Round-2 audit (2026-05-07) found the detector flagged 22 modules as orphans;
~15 were false positives from re-export shapes the static check didn't follow.
These tests pin the new ``_is_reexported_through_parent_init`` logic and the
extended unwired-marker check (AGENT_RUNTIME or PHASE_1_STAGED).
"""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from scripts.check_orphan_modules import (  # noqa: E402
    _is_intentionally_unwired,
    _is_reexported_through_parent_init,
)


class TestUnwiredMarker:
    """Modules with AGENT_RUNTIME or PHASE_1_STAGED markers are not flagged."""

    def test_agent_runtime_marker_recognized(self, tmp_path):
        f = tmp_path / "marked.py"
        f.write_text('"""Some module.\n\n# AGENT_RUNTIME - invoked from a hook."""\n')
        assert _is_intentionally_unwired(f) is True

    def test_phase_1_staged_marker_recognized(self, tmp_path):
        f = tmp_path / "marked.py"
        f.write_text('"""Some module.\n\n# PHASE_1_STAGED - awaiting wiring."""\n')
        assert _is_intentionally_unwired(f) is True

    def test_no_marker_returns_false(self, tmp_path):
        f = tmp_path / "plain.py"
        f.write_text('"""A regular module."""\n')
        assert _is_intentionally_unwired(f) is False

    def test_marker_past_window_not_recognized(self, tmp_path):
        """Marker after the first ~2000 chars is not recognized."""
        f = tmp_path / "late.py"
        padding = "# pad\n" * 500
        f.write_text(padding + "# AGENT_RUNTIME\n")
        assert _is_intentionally_unwired(f) is False


class TestReexportedThroughParentInit:
    """Modules reached only via parent __init__.py re-export are correctly
    recognized as wired (not orphans)."""

    def test_register_cli_pattern_recognized(self, tmp_path, monkeypatch):
        """``mod.register(cli)`` call in __init__.py wires the module."""
        import scripts.check_orphan_modules as m

        monkeypatch.setattr(m, "SRC", tmp_path)
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("from .mod import register\nmod.register(cli)\n")
        mod = pkg / "mod.py"
        mod.write_text("def register(cli): pass\n")
        assert _is_reexported_through_parent_init(mod) is True

    def test_unwired_module_returns_false(self, tmp_path, monkeypatch):
        """Module with no __init__.py reference is not re-exported."""
        import scripts.check_orphan_modules as m

        monkeypatch.setattr(m, "SRC", tmp_path)
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("# empty init\n")
        mod = pkg / "mod.py"
        mod.write_text("# placeholder\n")
        assert _is_reexported_through_parent_init(mod) is False

    def test_real_repo_council_experts_not_flagged(self):
        """Smoke test: the 6 council experts that round-2 audit flagged as
        false positives are now correctly recognized as wired."""
        from pathlib import Path as _P

        repo_root = _P(__file__).resolve().parent.parent
        for expert in ["feynman", "hinton", "holmes", "pearl", "turing", "yudkowsky"]:
            expert_path = (
                repo_root / "src" / "divineos" / "core" / "council" / "experts" / f"{expert}.py"
            )
            if expert_path.exists():
                assert _is_reexported_through_parent_init(expert_path), (
                    f"Expected {expert}.py to be recognized as re-exported via experts/__init__.py"
                )

    def test_real_repo_register_cli_modules_not_flagged(self):
        """Smoke test: decision_commands and sleep_commands (register(cli) pattern)
        are now correctly recognized as wired."""
        from pathlib import Path as _P

        repo_root = _P(__file__).resolve().parent.parent
        for cmd in ["decision_commands", "sleep_commands"]:
            cmd_path = repo_root / "src" / "divineos" / "cli" / f"{cmd}.py"
            if cmd_path.exists():
                assert _is_reexported_through_parent_init(cmd_path), (
                    f"Expected {cmd}.py to be recognized as wired via register(cli)"
                )
