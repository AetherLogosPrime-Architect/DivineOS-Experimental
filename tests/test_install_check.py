"""Tests for install_check — CLI-install-location divergence warning.

Falsifiability:
  - When cwd and installed-package toplevels match, return None (silent).
  - When they differ, return a one-line warning naming the fix
    (`pip install -e .`).
  - Suppression env var shortcircuits to None, cheaply.
  - Non-git cwd returns None (no expectation to check).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from divineos.core import install_check


@pytest.fixture(autouse=True)
def _reset_install_check_cache():
    """Each test sees a fresh cache — per-process cache must not leak."""
    install_check._reset_cache_for_tests()
    yield
    install_check._reset_cache_for_tests()


class TestSuppressionEnv:
    def test_env_var_set_returns_none(self, monkeypatch) -> None:
        monkeypatch.setenv("DIVINEOS_SUPPRESS_INSTALL_WARNING", "1")
        assert install_check.check_install_divergence() is None

    def test_env_var_truthy_short_circuits_before_subprocess(self, monkeypatch) -> None:
        """Suppression should skip the expensive git subprocess."""
        monkeypatch.setenv("DIVINEOS_SUPPRESS_INSTALL_WARNING", "1")
        with patch.object(install_check, "_git_toplevel") as mock_toplevel:
            install_check.check_install_divergence()
            mock_toplevel.assert_not_called()


class TestDivergenceDetection:
    def test_same_toplevel_returns_none(self, monkeypatch) -> None:
        monkeypatch.delenv("DIVINEOS_SUPPRESS_INSTALL_WARNING", raising=False)
        same = Path("/some/repo")
        with (
            patch.object(install_check, "_git_toplevel", return_value=same),
            patch.object(
                install_check, "_installed_package_root", return_value=same / "src" / "divineos"
            ),
        ):
            assert install_check.check_install_divergence() is None

    def test_different_toplevels_returns_warning(self, monkeypatch) -> None:
        monkeypatch.delenv("DIVINEOS_SUPPRESS_INSTALL_WARNING", raising=False)
        cwd_top = Path("/repo/worktree-a")
        pkg_top = Path("/repo/worktree-b")
        pkg_root = pkg_top / "src" / "divineos"

        def fake_toplevel(path: Path) -> Path:
            # cwd asks for its toplevel → cwd_top
            # pkg_root asks for its toplevel → pkg_top
            if path == pkg_root or str(path).startswith(str(pkg_top)):
                return pkg_top
            return cwd_top

        with (
            patch.object(install_check, "_git_toplevel", side_effect=fake_toplevel),
            patch.object(install_check, "_installed_package_root", return_value=pkg_root),
        ):
            msg = install_check.check_install_divergence()
            assert msg is not None
            assert "install warning" in msg
            assert "pip install -e" in msg

    def test_not_in_git_tree_returns_none(self, monkeypatch) -> None:
        monkeypatch.delenv("DIVINEOS_SUPPRESS_INSTALL_WARNING", raising=False)
        with patch.object(install_check, "_git_toplevel", return_value=None):
            assert install_check.check_install_divergence() is None

    def test_pkg_unresolvable_returns_none(self, monkeypatch) -> None:
        monkeypatch.delenv("DIVINEOS_SUPPRESS_INSTALL_WARNING", raising=False)
        with (
            patch.object(install_check, "_git_toplevel", return_value=Path("/repo")),
            patch.object(install_check, "_installed_package_root", return_value=None),
        ):
            assert install_check.check_install_divergence() is None


class TestCaching:
    def test_second_call_skips_subprocess(self, monkeypatch) -> None:
        """Per-process cache: first call computes, subsequent calls reuse."""
        monkeypatch.delenv("DIVINEOS_SUPPRESS_INSTALL_WARNING", raising=False)
        with (
            patch.object(install_check, "_git_toplevel") as mock_top,
            patch.object(
                install_check, "_installed_package_root", return_value=Path("/repo/src/divineos")
            ),
        ):
            mock_top.return_value = Path("/repo")
            install_check.check_install_divergence()
            install_check.check_install_divergence()
            install_check.check_install_divergence()
            # Called twice during first computation (cwd + pkg); second/third
            # invocations hit cache and don't call at all.
            assert mock_top.call_count == 2
