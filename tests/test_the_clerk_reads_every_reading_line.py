"""The clerk reads EVERY `**Reading:**` line in a letter, not only the first.

2026-10-11: Aria's letter declared two branches on two separate Reading lines. The clerk
read the first and dropped the second without a word, so the second branch showed
"none of Aria's readings names this branch" while she had in fact read it. The design
(station four reads a declared field, infers nothing from prose) is unchanged; only the
silent drop is gone. Same real function, real letters on disk.
"""

from __future__ import annotations

from pathlib import Path

from divineos.core.build_flow import Status, check_aria_station


def _letter(dirpath: Path, name: str, body: str) -> None:
    (dirpath / name).write_text(body, encoding="utf-8")


def test_two_reading_lines_credit_both_branches(tmp_path):
    _letter(
        tmp_path,
        "aria-to-aether-2026-10-11-i-read-two.md",
        "# Aria to Aether\n\n"
        "**Reading:** aether/the-first-branch\n"
        "**Reading:** aether/the-second-branch\n\nBody.\n",
    )
    for branch in ("aether/the-first-branch", "aether/the-second-branch"):
        assert check_aria_station(branch, tmp_path, "aether").status is Status.SATISFIED, branch


def test_the_second_line_still_counts_when_the_first_says_none(tmp_path):
    _letter(
        tmp_path,
        "aria-to-aether-2026-10-11-none-then-one.md",
        "# Aria to Aether\n\n**Reading:** none\n**Reading:** aether/the-real-one\n\nBody.\n",
    )
    assert check_aria_station("aether/the-real-one", tmp_path, "aether").status is Status.SATISFIED


def test_lines_and_commas_can_be_mixed(tmp_path):
    _letter(
        tmp_path,
        "aria-to-aether-2026-10-11-mixed.md",
        "# Aria to Aether\n\n"
        "**Reading:** aether/a, aether/b\n\nSome prose in between.\n\n**Reading:** aether/c\n",
    )
    for branch in ("aether/a", "aether/b", "aether/c"):
        assert check_aria_station(branch, tmp_path, "aether").status is Status.SATISFIED, branch


def test_a_branch_only_mentioned_in_prose_is_still_not_credited(tmp_path):
    """The control: reading more lines must not start reading prose."""
    _letter(
        tmp_path,
        "aria-to-aether-2026-10-11-mention.md",
        "# Aria to Aether\n\n**Reading:** aether/a\n**Reading:** aether/b\n\n"
        "I also looked at aether/c in passing, without reading it.\n",
    )
    assert check_aria_station("aether/c", tmp_path, "aether").status is not Status.SATISFIED


def test_only_the_header_is_read_not_a_quoted_or_fenced_or_indented_declaration(tmp_path):
    """Aria's cold read of 628: collecting every line widens what a pasted declaration can
    credit. The declaration lives in the header, above the first `---`, outside a code fence,
    and not indented as a quoted block."""
    _letter(
        tmp_path,
        "aria-to-aether-2026-10-11-header-only.md",
        "# Aria to Aether\n\n**Reading:** aether/real\n\n---\n\n"
        "**Reading:** aether/below-the-line\n\n"
        "```\n**Reading:** aether/fenced\n```\n\n"
        "    **Reading:** aether/indented\n\n\t**Reading:** aether/tabbed\n",
    )
    assert check_aria_station("aether/real", tmp_path, "aether").status is Status.SATISFIED
    for branch in (
        "aether/below-the-line",
        "aether/fenced",
        "aether/indented",
        "aether/tabbed",
    ):
        assert check_aria_station(branch, tmp_path, "aether").status is not Status.SATISFIED, branch


def test_a_letter_with_no_separator_still_reads_the_whole_letter(tmp_path):
    """The old behaviour for a letter that has no `---` at all (every test letter before
    the machinery's own headers): the declaration is found wherever the header lives."""
    _letter(
        tmp_path,
        "aria-to-aether-2026-10-11-no-separator.md",
        "# Aria to Aether\n\nSome words first.\n\n**Reading:** aether/no-sep\n\nBody.\n",
    )
    assert check_aria_station("aether/no-sep", tmp_path, "aether").status is Status.SATISFIED


def test_a_miss_names_what_the_newest_letter_did_declare(tmp_path):
    """Aria's second suggestion: a miss should read as a miss on the field, not a silent drop."""
    _letter(
        tmp_path,
        "aria-to-aether-2026-10-11-declares-two.md",
        "# Aria to Aether\n\n**Reading:** aether/one, aether/two\n\nBody.\n",
    )
    result = check_aria_station("aether/three", tmp_path, "aether")
    assert result.status is not Status.SATISFIED
    assert "aether/one" in result.detail and "aether/two" in result.detail
    assert "declares" in result.detail


def test_a_line_that_merely_starts_like_one_but_is_another_field_is_not_read(tmp_path):
    _letter(
        tmp_path,
        "aria-to-aether-2026-10-11-other-field.md",
        "# Aria to Aether\n\n**Reading list:** aether/x\n**Reading:** aether/y\n\nBody.\n",
    )
    assert check_aria_station("aether/y", tmp_path, "aether").status is Status.SATISFIED
    assert check_aria_station("aether/x", tmp_path, "aether").status is not Status.SATISFIED
