"""Tests for the bounded transcript reader.

Written when the module was finally wired, 2026-08-18. It was built
2026-08-03, found to have zero callers on 2026-08-09, and turned out never to
have reached main at all — it survived only on two unmerged branches, one of
them a backup. It had no tests either, which is part of the same story.

The cases that matter are not "does it parse JSONL". They are the two ways a
bounded read can lie: returning a fragment as though it were a record, and
returning a partial view without saying so.
"""

from __future__ import annotations

import json

from divineos.core.operating_loop.transcript_tail import (
    DEFAULT_TAIL_BYTES,
    read_tail_records,
)


def _write_jsonl(path, rows):
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return path


class TestSmallFileIsReadWhole:
    """Under the window, nothing is dropped and nothing is flagged."""

    def test_all_records_returned(self, tmp_path):
        f = _write_jsonl(tmp_path / "t.jsonl", [{"i": i} for i in range(50)])
        records, truncated = read_tail_records(f)
        assert [r["i"] for r in records] == list(range(50))
        assert truncated is False

    def test_empty_file(self, tmp_path):
        f = tmp_path / "t.jsonl"
        f.write_text("", encoding="utf-8")
        assert read_tail_records(f) == ([], False)

    def test_blank_lines_skipped(self, tmp_path):
        f = tmp_path / "t.jsonl"
        f.write_text('{"a":1}\n\n\n{"a":2}\n', encoding="utf-8")
        records, _ = read_tail_records(f)
        assert [r["a"] for r in records] == [1, 2]


class TestTruncationIsHonest:
    """The third word. A partial view that cannot say so is the failure this
    module exists inside the repair for."""

    def test_truncated_flag_set_when_file_exceeds_window(self, tmp_path):
        rows = [{"i": i, "pad": "x" * 200} for i in range(2000)]
        f = _write_jsonl(tmp_path / "t.jsonl", rows)
        assert f.stat().st_size > 1024
        records, truncated = read_tail_records(f, max_bytes=1024)
        assert truncated is True
        assert records, "a bounded read should still return the tail"

    def test_truncated_view_is_the_end_of_the_file(self, tmp_path):
        rows = [{"i": i, "pad": "x" * 200} for i in range(2000)]
        f = _write_jsonl(tmp_path / "t.jsonl", rows)
        records, _ = read_tail_records(f, max_bytes=4096)
        assert records[-1]["i"] == 1999, "the newest record must survive"
        assert records[0]["i"] > 0, "the oldest records are what gets dropped"

    def test_no_fragment_is_ever_returned_as_a_record(self, tmp_path):
        """A byte-offset seek lands mid-line almost every time. Half a line is
        not a record, and parsing one would be a silent corruption rather than
        a visible loss."""
        rows = [{"i": i, "pad": "y" * 137} for i in range(3000)]
        f = _write_jsonl(tmp_path / "t.jsonl", rows)
        for window in (500, 977, 4096, 10_000):
            records, _ = read_tail_records(f, max_bytes=window)
            for r in records:
                assert set(r) == {"i", "pad"}, f"fragment leaked at window={window}"
                assert len(r["pad"]) == 137


class TestFailsQuietAndEmpty:
    """Every caller is a detector running inside a hook. None may crash."""

    def test_missing_file(self, tmp_path):
        assert read_tail_records(tmp_path / "nope.jsonl") == ([], False)

    def test_directory_instead_of_file(self, tmp_path):
        assert read_tail_records(tmp_path) == ([], False)

    def test_malformed_lines_are_skipped_not_fatal(self, tmp_path):
        f = tmp_path / "t.jsonl"
        f.write_text('{"a":1}\nnot json at all\n{"a":2}\n{{{\n', encoding="utf-8")
        records, _ = read_tail_records(f)
        assert [r["a"] for r in records] == [1, 2]

    def test_non_dict_json_is_skipped(self, tmp_path):
        """A bare list or string is valid JSON and is not a record."""
        f = tmp_path / "t.jsonl"
        f.write_text('{"a":1}\n[1,2,3]\n"just a string"\n42\n', encoding="utf-8")
        records, _ = read_tail_records(f)
        assert records == [{"a": 1}]

    def test_invalid_utf8_does_not_raise(self, tmp_path):
        f = tmp_path / "t.jsonl"
        f.write_bytes(b'{"a":1}\n\xff\xfe bad bytes\n{"a":2}\n')
        records, _ = read_tail_records(f)
        assert [r["a"] for r in records] == [1, 2]


class TestWindowDefault:
    def test_default_is_four_megabytes(self):
        """Named rather than left as a magic number: the callers all window
        their own results, so this bounds work rather than correctness."""
        assert DEFAULT_TAIL_BYTES == 4 * 1024 * 1024
