"""Tests for the related-failure scanner."""

from divineos.core.related_failure_scanner import scan_for_related


class TestScanForRelated:
    def test_short_patterns_skipped(self):
        """Patterns < 10 chars produce too many false matches."""
        result = scan_for_related("/foo.py", "x = 1")
        assert result is None

    def test_empty_pattern_skipped(self):
        result = scan_for_related("/foo.py", "")
        assert result is None

    def test_none_when_no_matches(self, tmp_path):
        """No matches returns None."""
        test_file = tmp_path / "test.py"
        test_file.write_text("unique_pattern_xyz_12345")
        result = scan_for_related(
            str(test_file),
            "this_pattern_does_not_exist_anywhere_in_any_file",
            repo_root=str(tmp_path),
        )
        assert result is None

    def test_multiline_uses_longest_line(self):
        """Multi-line patterns use the longest line for search."""
        # Just verify it doesn't crash on multiline input
        result = scan_for_related(
            "/foo.py",
            "short\nthis_is_a_much_longer_line_that_should_be_picked\nalso short",
        )
        # Result depends on whether rg/grep finds matches; we just test no crash
        assert result is None or "RELATED-PATTERN" in result
