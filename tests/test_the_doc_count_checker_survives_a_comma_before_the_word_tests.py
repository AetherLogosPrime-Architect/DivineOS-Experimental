"""A lone comma is not a number.

The test-count pattern accepted `[\\d,]+`, so a documentation line like "files, tests, symbols"
matched a bare comma, `int("")` raised ValueError, and the whole checker crashed with a traceback
no one could connect to the line that caused it. Found 2026-11-28 when a new ARCHITECTURE.md line
said "facts only: files, tests, symbols". A count needs at least one digit.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_doc_counts import extract_documented_counts  # noqa: E402


def test_a_comma_before_tests_is_prose_and_does_not_crash(tmp_path):
    doc = tmp_path / "ARCHITECTURE.md"
    doc.write_text("facts only: files, tests, symbols, and more.\n", encoding="utf-8")
    assert extract_documented_counts(doc) == []


def test_a_real_count_with_a_thousands_comma_is_still_read(tmp_path):
    doc = tmp_path / "README.md"
    doc.write_text("The suite has 15,284 tests today.\n", encoding="utf-8")
    found = extract_documented_counts(doc)
    assert ("tests", 15284) in [(label, num) for label, num, _ in found]


def test_a_count_with_a_plus_is_still_read(tmp_path):
    doc = tmp_path / "README.md"
    doc.write_text("2,608+ tests\n", encoding="utf-8")
    found = extract_documented_counts(doc)
    assert ("tests", 2608) in [(label, num) for label, num, _ in found]
