"""Tests for scripts/check_import_in_swallow.py.

The class it catches: a first-party import that cannot resolve, sitting inside
a handler that hides the failure. Three instances on 2026-08-25 across two
agents -- ``must_read.arm`` (the function is ``require_read``),
``get_correction_text`` (never existed), and Aria's import from a module that
does not exist inside a bare except. Each one a dead code path reporting
success forever.

THE FIRST RUN WAS MOSTLY WRONG AND THAT IS WHAT MOST OF THIS FILE PINS.
Eleven of thirteen findings were ``from divineos.core import gate_marker``
shapes -- a package importing one of its own files. The name never appears in
``__init__.py`` and resolves perfectly. Fifth time in one session an
instrument looked for the shape I pictured rather than the shape in the data,
caught by checking a sample against disk before reporting rather than by
shipping it.
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "check_import_in_swallow",
    Path(__file__).resolve().parents[1] / "scripts" / "check_import_in_swallow.py",
)
assert _SPEC and _SPEC.loader
checker = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(checker)


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "sample.py"
    path.write_text(body, encoding="utf-8")
    return path


def _handler(source: str) -> ast.ExceptHandler:
    return ast.parse(source).body[0].handlers[0]


class TestTheSubmoduleFalsePositive:
    """Eleven of the first thirteen findings. `from package import submodule`
    is a package importing one of its own files."""

    def test_importing_a_real_submodule_is_not_flagged(self, tmp_path, monkeypatch):
        monkeypatch.setattr(checker, "REPO_ROOT", tmp_path)
        core = tmp_path / "src" / "divineos" / "core"
        core.mkdir(parents=True)
        (core / "__init__.py").write_text("", encoding="utf-8")
        (core / "gate_marker.py").write_text("VALUE = 1\n", encoding="utf-8")
        monkeypatch.setattr(checker, "SRC_ROOT", tmp_path / "src")

        body = "try:\n    from divineos.core import gate_marker\nexcept Exception:\n    pass\n"
        assert checker._findings_in(_write(tmp_path, body)) == []

    def test_importing_a_submodule_that_does_not_exist_is_flagged(self, tmp_path, monkeypatch):
        monkeypatch.setattr(checker, "REPO_ROOT", tmp_path)
        core = tmp_path / "src" / "divineos" / "core"
        core.mkdir(parents=True)
        (core / "__init__.py").write_text("", encoding="utf-8")
        monkeypatch.setattr(checker, "SRC_ROOT", tmp_path / "src")

        body = "try:\n    from divineos.core import no_such_module\nexcept Exception:\n    pass\n"
        assert len(checker._findings_in(_write(tmp_path, body))) == 1

    def test_a_missing_function_in_a_real_module_is_still_flagged(self, tmp_path, monkeypatch):
        """The submodule allowance must not swallow the original class --
        get_correction_text lived in a module that existed."""
        monkeypatch.setattr(checker, "REPO_ROOT", tmp_path)
        core = tmp_path / "src" / "divineos" / "core"
        core.mkdir(parents=True)
        (core / "__init__.py").write_text("", encoding="utf-8")
        (core / "tracker.py").write_text("def integrate():\n    pass\n", encoding="utf-8")
        monkeypatch.setattr(checker, "SRC_ROOT", tmp_path / "src")

        body = (
            "try:\n"
            "    from divineos.core.tracker import get_correction_text\n"
            "except Exception:\n"
            "    pass\n"
        )
        findings = checker._findings_in(_write(tmp_path, body))
        assert len(findings) == 1
        assert "get_correction_text" in findings[0]


class TestWhatCountsAsASwallow:
    def test_bare_except_swallows(self):
        assert checker._handler_swallows(_handler("try:\n    x=1\nexcept:\n    pass\n")) is True

    def test_import_error_swallows(self):
        handler = _handler("try:\n    x=1\nexcept ImportError:\n    pass\n")
        assert checker._handler_swallows(handler) is True

    def test_a_narrow_non_import_handler_is_not_this_class(self):
        """OSError around an import is not the shape -- an ImportError would
        still be loud."""
        handler = _handler("try:\n    x=1\nexcept OSError:\n    pass\n")
        assert checker._handler_swallows(handler) is False

    def test_a_handler_that_reraises_is_loud_not_a_swallow(self):
        handler = _handler("try:\n    x=1\nexcept Exception:\n    raise\n")
        assert checker._handler_swallows(handler) is False

    def test_tuple_of_exceptions_counts_if_any_member_swallows(self):
        handler = _handler("try:\n    x=1\nexcept (OSError, ImportError):\n    pass\n")
        assert checker._handler_swallows(handler) is True


class TestScope:
    def test_third_party_absence_is_optionality_not_a_defect(self, tmp_path, monkeypatch):
        """`try: import hypothesis / except ImportError` is a legitimate
        pattern. Flagging it would bury the real findings under correct ones."""
        monkeypatch.setattr(checker, "REPO_ROOT", tmp_path)
        body = "try:\n    from hypothesis import given\nexcept ImportError:\n    pass\n"
        assert checker._findings_in(_write(tmp_path, body)) == []

    def test_an_unresolvable_import_outside_a_handler_is_not_flagged(self, tmp_path, monkeypatch):
        """Loud on the first run. The swallow is the load-bearing half."""
        monkeypatch.setattr(checker, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(checker, "SRC_ROOT", tmp_path / "src")
        body = "from divineos.core import nothing_here\n"
        assert checker._findings_in(_write(tmp_path, body)) == []

    def test_unparseable_file_fails_toward_flagging(self, tmp_path, monkeypatch):
        monkeypatch.setattr(checker, "REPO_ROOT", tmp_path)
        path = tmp_path / "broken.py"
        path.write_text("def f(:\n", encoding="utf-8")
        findings = checker._findings_in(path)
        assert len(findings) == 1
        assert "UNPARSEABLE" in findings[0]


class TestAgainstTheRealTree:
    """The four it found were checked by hand against disk before being
    trusted, after the first run's eleven were not."""

    def test_the_known_dead_paths_are_still_reported(self):
        path = checker.REPO_ROOT / "src" / "divineos" / "core" / "empirica" / "pointer_resolver.py"
        findings = "\n".join(checker._findings_in(path))
        assert "prereg.store" in findings
        assert "get_decision" in findings

    def test_a_module_full_of_correct_submodule_imports_is_silent(self):
        """correction_marker.py produced three of the eleven false positives
        and must now be clean."""
        path = checker.REPO_ROOT / "src" / "divineos" / "core" / "correction_marker.py"
        assert checker._findings_in(path) == []
