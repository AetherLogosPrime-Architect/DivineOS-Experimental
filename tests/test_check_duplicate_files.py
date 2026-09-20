"""The duplicate-file check, pinned against the case that earned it.

A 488-line module existed twice, byte for byte, for a month. One copy was
live -- every test imported it and the audit path called it. The other had no
caller and no test, and the orphan checker could not see it because that
checker asks about modules that HAVE tests and no caller. Outside the question
by construction rather than by neglect.

These use real files on disk rather than reasoning about the matcher, because
the fault being pinned is one nobody found by reading.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import check_duplicate_files as mod  # noqa: E402


@pytest.fixture
def scanned(tmp_path, monkeypatch):
    """Point the check at a throwaway tree instead of the repository.

    Rewriting the roots rather than the finder keeps the real walk under
    test: a fixture that replaced the candidate collector would be testing
    a stub of the thing it is meant to check.
    """
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "nested").mkdir()
    monkeypatch.setattr(mod, "REPO", tmp_path)
    monkeypatch.setattr(mod, "_SEARCH_ROOTS", ("src",))
    return tmp_path


def _write(path: Path, filler: str = "x") -> None:
    """Long enough to clear the floor, which exists so one-line re-exports
    and empty package markers are not reported as twins."""
    path.write_text("# a module\n" + f"# {filler * 80}\n" * 8, encoding="utf-8")


class TestTheCaseThatEarnedIt:
    def test_two_identical_files_are_reported(self, scanned):
        _write(scanned / "src" / "detector.py")
        shutil.copy(scanned / "src" / "detector.py", scanned / "src" / "nested" / "detector.py")
        found = mod.find_duplicates()
        assert len(found) == 1
        _, paths = found[0]
        assert "src/detector.py" in paths
        assert "src/nested/detector.py" in paths

    def test_one_byte_of_difference_is_not_a_duplicate(self, scanned):
        """Identical is a FACT; similar needs a threshold, and a threshold is
        a number people argue with. This under-reports on purpose, and the
        limit is asserted rather than left implicit for someone to discover."""
        _write(scanned / "src" / "a.py", filler="x")
        _write(scanned / "src" / "nested" / "a.py", filler="y")
        assert mod.find_duplicates() == []

    def test_short_identical_files_are_ignored(self, scanned):
        for p in (scanned / "src" / "s.py", scanned / "src" / "nested" / "s.py"):
            p.write_text("from x import y\n", encoding="utf-8")
        assert mod.find_duplicates() == []

    def test_declared_duplication_stands_aside(self, scanned):
        body = "# duplicate-by-design: vendored verbatim, upstream owns it\n" + "# pad\n" * 200
        for p in (scanned / "src" / "v.py", scanned / "src" / "nested" / "v.py"):
            p.write_text(body, encoding="utf-8")
        assert mod.find_duplicates() == []


class TestNothingScannedIsNotNothingFound:
    def test_an_empty_scan_refuses_rather_than_reporting_clean(self, tmp_path, monkeypatch):
        """The fake-green shape, inside the check written against a blind spot.

        If the walk finds no files at all the check knows nothing, and knowing
        nothing must not exit the same way as knowing it is clean.
        """
        monkeypatch.setattr(mod, "REPO", tmp_path)
        monkeypatch.setattr(mod, "_SEARCH_ROOTS", ("does-not-exist",))
        monkeypatch.setattr(sys, "argv", ["check_duplicate_files.py"])
        assert mod.main() != 0

    def test_the_repository_itself_is_actually_walked(self):
        """Guard the guard: if the real walk returns nothing, every case above
        is vacuous and the check is decoration."""
        assert len(mod._candidates()) > 100
