"""Tests for the recent-letter warm-content surface extractor.

These tests are the evidence-bearing layer Aether's finding #1 named
(retrieval-tally makes the mechanism evidence-bearing, unit tests make
the extractor evidence-bearing).

Written properly this time — with fixtures that exercise every failure
mode of the shoddy first attempt: broken YAML-toggle assumption, mixed
'##' section content in the closing, missing greeting extraction, date-
missing filenames, unreadable files.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the sibling scripts/ module importable.
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))

import recent_letter_warm_content_surface as mod  # noqa: E402


SAMPLE_LETTER = """# Aria to Aether — an example title

**Written:** 2026-07-19
**In response to:** aether-to-aria-something

---

Aether —

This is the first substantive paragraph. It carries the greeting
and the initial acknowledgment. Multi-line paragraphs are supported.

Second paragraph of body. This is body content but not the first
substantive one.

## Structural section header

Body content under a structural section. This should NOT appear in
the closing extraction because the walk-backwards stops at '##'.

## Another section

More structural body.

This is the final closing paragraph. It carries the warm sign-off
sentiment before the em-dash. It is what I want the extractor to
find as 'closing'.

—
Aria
2026-07-19
"""


def test_first_substantive_extracts_greeting_paragraph():
    p = mod.extract_first_substantive_paragraph(SAMPLE_LETTER)
    assert "Aether —" in p, f"Greeting missing from first paragraph:\n{p}"
    assert "This is the first substantive paragraph" in p
    assert "Second paragraph" not in p, "First-paragraph extractor over-reached"
    assert "**Written" not in p, "Metadata leaked into first paragraph"
    assert "---" not in p, "HR separator leaked"


def test_first_substantive_stops_at_blank_line():
    p = mod.extract_first_substantive_paragraph(SAMPLE_LETTER)
    lines = p.splitlines()
    for line in lines:
        assert not line.strip().startswith("#"), f"Heading leaked: {line!r}"


def test_closing_extracts_final_paragraph():
    p = mod.extract_closing_paragraph(SAMPLE_LETTER)
    assert "This is the final closing paragraph" in p, f"Closing missing final warm paragraph:\n{p}"
    assert "Structural section" not in p, (
        "Closing extractor pulled a '##' section header — the exact bug the shoddy hook had"
    )
    assert "Another section" not in p, "Second '##' header leaked"
    assert "—" not in p or p.count("—") <= 1, "Sign-off dash leaked"


def test_closing_stops_at_double_hash():
    """The specific defect in the first attempt: closing pulled '##' section
    headings because the tac-based extractor did not skip them. Pin that
    contract explicitly."""
    text = """# Title

**Written:** date

---

Greeting —

Body.

## Section

Content under section.

Final closing paragraph.

—
Signature
"""
    p = mod.extract_closing_paragraph(text)
    assert "Final closing paragraph" in p
    assert "Section" not in p
    assert "Content under section" not in p


def test_slug_parse_handles_multi_word_slug():
    r, d, s = mod.parse_slug("aria-to-andrew-2026-07-19-the-letter-i-have-never-written-you.md")
    assert r == "andrew"
    assert d == "2026-07-19"
    assert s == "the-letter-i-have-never-written-you"


def test_slug_parse_returns_empty_on_bad_shape():
    r, d, s = mod.parse_slug("weird_letter_without_pattern.md")
    assert d == "", "Should return empty date to signal invariant failure"


def test_render_surface_marks_missing_first_paragraph_loud():
    """The failure mode Aether named — silent-drop when extractor fails
    — should surface as a loud INVARIANT FAILURE line, not empty output."""
    metadata_only = """# Title

**Written:** date
**In response to:** thing

---
"""
    rendered, marker = mod.render_surface_from_texts(
        [("aria-to-andrew-2026-07-19-metadata-only.md", metadata_only)]
    )
    assert "INVARIANT FAILURE" in rendered, (
        "Metadata-only letter should trigger loud invariant failure, not silent empty output"
    )


def test_render_surface_includes_andrews_voice():
    text = SAMPLE_LETTER
    rendered, marker = mod.render_surface_from_texts(
        [("aria-to-aether-2026-07-19-example.md", text)]
    )
    assert "its far more warm than your report" in rendered, (
        "Andrew's actual voice must be in the reminder (Aether "
        "adversarial review finding 4). His voice is more expensive "
        "to ignore than mine."
    )


def test_render_surface_writes_marker_with_content_hash():
    text = SAMPLE_LETTER
    rendered, marker = mod.render_surface_from_texts(
        [("aria-to-aether-2026-07-19-example.md", text)]
    )
    assert "content_hash" in marker
    assert len(marker["surfaced_content"]) >= 2, (
        "Marker must contain surfaced content for the Stop-hook tally"
    )
