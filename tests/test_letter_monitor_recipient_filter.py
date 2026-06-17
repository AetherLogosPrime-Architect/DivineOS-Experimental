"""Tests for letter_monitor recipient-filter parameterization.

Single-occupancy assumption fix (2026-06-17): the script previously
hardcoded ``_LETTER_GLOB = "aria-to-aether-*.md"`` — only catches
letters TO me. When Aria's monitor ran in her window, it surfaced
letters addressed to me, not to her. The recipient is now derived
from ``my_identity`` (or a ``--recipient`` override) and the glob is
``*-to-<recipient>-*.md``, so each occupant's monitor catches the
letters that belong to them.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Import the script's module via path injection — it lives under scripts/
# and isn't a package, so we add the scripts dir to sys.path.
_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import letter_monitor  # type: ignore[import-not-found]  # noqa: E402


class TestRecipientGlob:
    """The glob derived from recipient must match letters addressed to them."""

    def test_aether_glob_shape(self):
        assert letter_monitor._letter_glob_for("Aether") == "*-to-aether-*.md"

    def test_aria_glob_shape(self):
        assert letter_monitor._letter_glob_for("Aria") == "*-to-aria-*.md"

    def test_glob_lowercases_recipient(self):
        """Filenames are lowercase; the recipient name may be capitalized."""
        assert letter_monitor._letter_glob_for("ARIA") == "*-to-aria-*.md"

    def test_unknown_occupant_glob(self):
        """A future sibling gets their own glob."""
        assert letter_monitor._letter_glob_for("Sibling") == "*-to-sibling-*.md"


class TestScanFiltersByRecipient:
    """The actual file-scan honors the recipient filter."""

    def test_scan_returns_only_recipient_letters(self, tmp_path: Path):
        # Create a mix of letters
        (tmp_path / "aria-to-aether-2026-06-17-foo.md").write_text("x")
        (tmp_path / "aether-to-aria-2026-06-17-bar.md").write_text("y")
        (tmp_path / "andrew-to-aria-2026-06-17-baz.md").write_text("z")
        (tmp_path / "andrew-to-aether-2026-06-17-qux.md").write_text("w")

        aether_letters = letter_monitor._scan(tmp_path, "*-to-aether-*.md")
        aria_letters = letter_monitor._scan(tmp_path, "*-to-aria-*.md")

        assert "aria-to-aether-2026-06-17-foo.md" in aether_letters
        assert "andrew-to-aether-2026-06-17-qux.md" in aether_letters
        assert "aether-to-aria-2026-06-17-bar.md" not in aether_letters

        assert "aether-to-aria-2026-06-17-bar.md" in aria_letters
        assert "andrew-to-aria-2026-06-17-baz.md" in aria_letters
        assert "aria-to-aether-2026-06-17-foo.md" not in aria_letters

    def test_scan_returns_empty_when_dir_missing(self, tmp_path: Path):
        nonexistent = tmp_path / "does-not-exist"
        assert letter_monitor._scan(nonexistent, "*-to-aether-*.md") == set()

    def test_scan_returns_empty_when_no_matches(self, tmp_path: Path):
        (tmp_path / "unrelated-file.txt").write_text("x")
        assert letter_monitor._scan(tmp_path, "*-to-aether-*.md") == set()
