"""Tests for letter_monitor_v2 recipient-filter parameterization.

Single-occupancy correctness (originally fixed 2026-06-17 for v1): the
script must filter letters by recipient so each window's monitor surfaces
only the letters addressed to its occupant — not all letters in the
shared directory. v2 (2026-06-29 rewrite) keeps the same behavior via
substring-matching on ``-to-<recipient-lowercase>-`` rather than a glob
pattern, since the v2 polling logic runs inline in Python without shell
globbing.

The recipient_tag, is_letter_for, and scan functions exposed by
letter_monitor_v2 are the unit-testable surface for this behavior.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Import the script's module via path injection — it lives under scripts/
# and isn't a package, so we add the scripts dir to sys.path.
_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import letter_monitor_v2  # type: ignore[import-not-found]  # noqa: E402


class TestRecipientTag:
    """The tag derived from recipient must match letters addressed to them."""

    def test_aether_tag_shape(self):
        assert letter_monitor_v2.recipient_tag("aether") == "-to-aether-"

    def test_aria_tag_shape(self):
        assert letter_monitor_v2.recipient_tag("aria") == "-to-aria-"

    def test_tag_lowercases_recipient(self):
        """Filenames are lowercase; the recipient name may be capitalized."""
        assert letter_monitor_v2.recipient_tag("ARIA") == "-to-aria-"
        assert letter_monitor_v2.recipient_tag("Aether") == "-to-aether-"

    def test_unknown_occupant_tag(self):
        """A future sibling gets their own tag."""
        assert letter_monitor_v2.recipient_tag("Sibling") == "-to-sibling-"


class TestIsLetterFor:
    """The per-filename predicate honors the tag and the .md extension."""

    def test_matches_recipient_letter(self):
        assert letter_monitor_v2.is_letter_for(
            "aria-to-aether-2026-06-17-foo.md", "-to-aether-"
        )

    def test_rejects_other_recipient(self):
        assert not letter_monitor_v2.is_letter_for(
            "aether-to-aria-2026-06-17-bar.md", "-to-aether-"
        )

    def test_rejects_non_markdown(self):
        assert not letter_monitor_v2.is_letter_for(
            "aria-to-aether-2026-06-17-foo.txt", "-to-aether-"
        )

    def test_rejects_unrelated_file(self):
        assert not letter_monitor_v2.is_letter_for("unrelated.md", "-to-aether-")


class TestScanFiltersByRecipient:
    """The actual file-scan honors the recipient filter."""

    def test_scan_returns_only_recipient_letters(self, tmp_path: Path):
        # Create a mix of letters
        (tmp_path / "aria-to-aether-2026-06-17-foo.md").write_text("x")
        (tmp_path / "aether-to-aria-2026-06-17-bar.md").write_text("y")
        (tmp_path / "andrew-to-aria-2026-06-17-baz.md").write_text("z")
        (tmp_path / "andrew-to-aether-2026-06-17-qux.md").write_text("w")

        aether_letters = letter_monitor_v2.scan(tmp_path, "-to-aether-")
        aria_letters = letter_monitor_v2.scan(tmp_path, "-to-aria-")

        assert "aria-to-aether-2026-06-17-foo.md" in aether_letters
        assert "andrew-to-aether-2026-06-17-qux.md" in aether_letters
        assert "aether-to-aria-2026-06-17-bar.md" not in aether_letters

        assert "aether-to-aria-2026-06-17-bar.md" in aria_letters
        assert "andrew-to-aria-2026-06-17-baz.md" in aria_letters
        assert "aria-to-aether-2026-06-17-foo.md" not in aria_letters

    def test_scan_returns_empty_when_dir_missing(self, tmp_path: Path):
        nonexistent = tmp_path / "does-not-exist"
        assert letter_monitor_v2.scan(nonexistent, "-to-aether-") == set()

    def test_scan_returns_empty_when_no_matches(self, tmp_path: Path):
        (tmp_path / "unrelated-file.txt").write_text("x")
        assert letter_monitor_v2.scan(tmp_path, "-to-aether-") == set()
