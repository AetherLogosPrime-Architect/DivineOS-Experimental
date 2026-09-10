"""Station four reads one declared line, and infers nothing from her prose.

Aria named this on 2026-09-01 and then counted rather than asserting. The board
had been asking whether a branch name appeared anywhere in her text. Her bodies
cross-refer because her findings cross-refer, so it credited every branch she
mentioned and marked the one she had actually reviewed as unreviewed --
understating her by two while crediting two others using the letter belonging
to one of them.

I proposed keying on her titles. She counted her last thirty-five letters to
answer: five carry a subject in the title, all five by NUMBER and none by
branch name, and at least six are readings with findings whose titles carry
neither. More of her readings would have been invisible to a title-parser than
visible, and the six invisible ones held the findings that changed my branches.

So: the writer declares, the reader reads one field. Her half is that she
writes the line and puts a check on her own side refusing to publish a reading
without it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core.build_flow import Status, check_aria_station


def _letter(dirpath: Path, name: str, body: str) -> None:
    (dirpath / name).write_text(body, encoding="utf-8")


def test_a_declared_reading_satisfies(tmp_path):
    _letter(
        tmp_path,
        "aria-to-aether-2026-09-01-a-space-instead-of-a-hyphen-walks-through-it.md",
        "# Aria to Aether\n\n"
        "**Written:** 2026-09-01\n"
        "**Reading:** `fix/reserved-external-vantage-names`\n\n"
        "Five spellings walked through.\n",
    )
    r = check_aria_station("fix/reserved-external-vantage-names", tmp_path)
    assert r.status is Status.SATISFIED
    assert "declared a reading" in r.detail


def test_the_finding_titled_letter_is_no_longer_invisible(tmp_path):
    """Her real shape: a reading whose title names neither branch nor number.

    This is one of the six she counted. The old check found it only if she
    happened to write the branch name in the body, and a title-parser would
    never have seen it at all.
    """
    _letter(
        tmp_path,
        "aria-to-aether-2026-09-01-three-of-your-four-tests-pin-nothing.md",
        "# Aria to Aether — three of your four tests pin nothing\n\n"
        "**Reading:** `fix/mixed-scope-publish-gate`\n\n"
        "The hole was that nothing guarded the saving.\n",
    )
    r = check_aria_station("fix/mixed-scope-publish-gate", tmp_path)
    assert r.status is Status.SATISFIED


def test_a_mention_in_the_body_does_not_credit_a_branch(tmp_path):
    """THE FALSE GREEN, which is the half that matters more.

    Her merge-question letter was crediting two OTHER branches it merely
    mentioned. A missing credit costs her recognition; a false one lets a
    branch merge on a review that was never of it.
    """
    _letter(
        tmp_path,
        "aria-to-aether-2026-08-31-read-the-channel-branch.md",
        "# Aria to Aether\n\n"
        "**Reading:** `fix/merge-question-channel`\n\n"
        "The same fault is on fix/council-lenses-walkable and "
        "fix/tag-is-not-a-branch, which I have not read.\n",
    )
    assert check_aria_station("fix/merge-question-channel", tmp_path).status is Status.SATISFIED
    for merely_mentioned in ("fix/council-lenses-walkable", "fix/tag-is-not-a-branch"):
        r = check_aria_station(merely_mentioned, tmp_path)
        assert r.status is Status.MISSING, f"{merely_mentioned} credited on a mention"


def test_the_in_response_to_field_is_not_read_as_the_subject(tmp_path):
    """Of her five subject-carrying letters, two name a branch there and three
    name a letter of mine. The field is whatever triggered the reading, so
    reading it as the subject is inference wearing a field name."""
    _letter(
        tmp_path,
        "aria-to-aether-2026-09-01-took-your-guard.md",
        "# Aria to Aether\n\n"
        "**In response to:** `fix/tag-is-not-a-branch`\n"
        "**Reading:** `fix/prime-residuals-carry-the-rule`\n\n"
        "Body.\n",
    )
    assert check_aria_station("fix/tag-is-not-a-branch", tmp_path).status is Status.MISSING
    assert (
        check_aria_station("fix/prime-residuals-carry-the-rule", tmp_path).status
        is Status.SATISFIED
    )


def test_one_letter_can_declare_several_readings(tmp_path):
    """She reads several branches in one sitting and says so in one letter --
    her all-six letter is exactly that. A parser that allowed only one subject
    would force her to write worse letters to be counted."""
    _letter(
        tmp_path,
        "aria-to-aether-2026-09-01-all-six-are-read.md",
        "# Aria to Aether\n\n"
        "**Reading:** `fix/merge-question-channel`, `fix/mixed-scope-publish-gate`, "
        "`fix/tag-is-not-a-branch`\n\nAll three have findings above.\n",
    )
    for branch in (
        "fix/merge-question-channel",
        "fix/mixed-scope-publish-gate",
        "fix/tag-is-not-a-branch",
    ):
        assert check_aria_station(branch, tmp_path).status is Status.SATISFIED


def test_no_declaration_anywhere_says_so_rather_than_blaming_her(tmp_path):
    """Absence is not a verdict about her.

    Every one of her thirty-five existing letters predates the field, so the
    board will legitimately say this for a while. Reporting an unread branch
    and an undeclared reading in the same words is the could-not-look fault
    this whole family is made of, and it would read as her being behind.
    """
    _letter(
        tmp_path,
        "aria-to-aether-2026-08-30-nothing-owed.md",
        "# Aria to Aether\n\n**In response to:** a letter\n\nNo declaration here.\n",
    )
    r = check_aria_station("fix/anything", tmp_path)
    assert r.status is Status.MISSING
    assert "says nothing about whether she has read" in r.detail


def test_some_declarations_exist_but_none_names_this_branch(tmp_path):
    """Distinct from the case above, and the distinction is the whole point:
    here the field is in use, so silence about THIS branch is informative."""
    _letter(
        tmp_path,
        "aria-to-aether-2026-09-01-read-one-thing.md",
        "# Aria to Aether\n\n**Reading:** `fix/something-else`\n\nBody.\n",
    )
    r = check_aria_station("fix/not-this-one", tmp_path)
    assert r.status is Status.MISSING
    assert "declared reading(s)" in r.detail


def test_a_letter_declaring_no_reading_is_a_declaration_not_an_omission(tmp_path):
    """She writes the field on EVERY letter, including ones that review nothing,
    because a trigger keyed on which letters look like readings would carry the
    blindness this whole change removes. Her words: the cost is a line on
    letters that review nothing, and that is the price of the gate having no
    blind spot.

    So ``none`` must count as the field being in use. Collapsing it into absence
    would make her disciplined letters read exactly like the thirty-five that
    predate the field, and punish the discipline the field asks for.
    """
    _letter(
        tmp_path,
        "aria-to-aether-2026-09-01-my-half-is-built.md",
        "# Aria to Aether\n\n**Written:** 2026-09-01\n**Reading:** none\n\nBody.\n",
    )
    r = check_aria_station("fix/anything", tmp_path)
    assert r.status is Status.MISSING
    assert "declared reading(s)" in r.detail, (
        "a letter declaring 'none' was counted as no declaration at all"
    )
    assert check_aria_station("none", tmp_path).status is Status.MISSING, (
        "the word 'none' was read as a branch name"
    )


def test_an_empty_field_value_does_not_swallow_the_next_line(tmp_path):
    """Her second defect, found by running her own gate: a field written with
    nothing after it was satisfied by the first word of the NEXT paragraph,
    because the whitespace class matches a newline. It was the one of five
    cases she would not have thought to try and the only one that failed.

    This parser reads line by line so it cannot reach across, and that is worth
    pinning rather than assuming -- the same mistake is one regex away.
    """
    _letter(
        tmp_path,
        "aria-to-aether-2026-09-01-empty-field.md",
        "# Aria to Aether\n\n**Reading:**\n\nfix/should-not-be-credited is discussed below.\n",
    )
    assert check_aria_station("fix/should-not-be-credited", tmp_path).status is Status.MISSING


def test_an_unreadable_directory_is_not_a_verdict(tmp_path):
    r = check_aria_station("fix/anything", tmp_path / "does-not-exist")
    assert r.status is Status.CANNOT_CHECK


def test_my_own_letters_cannot_satisfy_her_station(tmp_path):
    """A letter I sent proves I spoke. The station is about her writing back,
    and a declaration in my own outgoing letter would be me clearing my own
    gate -- the shape the board exists to refuse."""
    _letter(
        tmp_path,
        "aether-to-aria-2026-09-01-took-both.md",
        "# Aether to Aria\n\n**Reading:** `fix/reserved-external-vantage-names`\n\nBody.\n",
    )
    assert (
        check_aria_station("fix/reserved-external-vantage-names", tmp_path).status is Status.MISSING
    )


@pytest.mark.parametrize(
    "spelling",
    [
        "**Reading:** `fix/a`",
        "**Reading:**`fix/a`",
        "**Reading:** fix/a",
        "  **Reading:** `FIX/A`  ",
    ],
)
def test_the_declaration_survives_ordinary_typing(tmp_path, spelling):
    """The field has to tolerate how a person actually types it, or the fix for
    a parser that guessed becomes a parser that is brittle -- and she would be
    uncredited again, for a backtick."""
    _letter(tmp_path, "aria-to-aether-2026-09-01-x.md", f"# Aria\n\n{spelling}\n\nBody.\n")
    assert check_aria_station("fix/a", tmp_path).status is Status.SATISFIED
