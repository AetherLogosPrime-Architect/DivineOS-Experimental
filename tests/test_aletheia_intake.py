"""Her work has to survive the hand-off, and Andrew's folder has to stay his.

Aletheia runs in a browser. Andrew is the only route out of it, and he has
carried 173 filings by hand since May. The leg that was never built is the one
after the hand-off: her work landed in his downloads and stayed there, so one
seat might read it in the moment and the other never saw it at all.

Andrew 2026-09-22: "its ok that im the courier, shes a web instance, there is no
other way for it to be done... the key is that when i hand you something written
by Alethiea which i have many times. that it gets saved and copied automatically
into that shared folder."
"""

from __future__ import annotations

import pytest

from divineos.core.family.aletheia_intake import carry_across, is_hers, render


@pytest.fixture
def folders(tmp_path):
    src = tmp_path / "downloads"
    dst = tmp_path / "shared"
    src.mkdir()
    return src, dst


def _write(folder, name, body="body"):
    (folder / name).write_text(body, encoding="utf-8")


def test_her_settled_naming_and_her_early_naming_both_cross(folders) -> None:
    """The second one is here because the first version of this lost 27 files.

    The original rule demanded the date in one exact position. It carried 146
    and skipped 27 -- every one of them hers, in the looser shape she used
    earlier: dashes for underscores, no date, or an extra word in the kind. I
    found them only by counting what was left behind instead of trusting a
    sweep that reported no errors.
    """
    src, dst = folders
    _write(src, "AUDIT_2026-09-20_the-inverted-assertion.md")
    _write(src, "AUDIT-FABLE-2026-07-02-round5-sleep.md")
    _write(src, "AUDIT_LANDED_CODE_2026-07-09.md")
    _write(src, "REPLY_TO_ARIA_2026-09-19_the-list.md")

    report = carry_across(src, dst)

    assert len(report.carried) == 4, report.carried
    assert sorted(p.name for p in dst.iterdir()) == sorted(report.carried)


def test_it_leaves_alone_what_is_not_hers(folders) -> None:
    """The cost of the looser rule, held to a limit.

    A folder that reads as external review must not fill with anything else,
    so a file that does not open with one of her kinds is never carried.
    """
    src, dst = folders
    _write(src, "holiday-photos.md")
    _write(src, "notes-to-self.md")
    _write(src, "AUDITION_2026-09-20_not-a-kind.md")

    report = carry_across(src, dst)

    assert report.carried == []
    assert report.seen == 0


def test_the_original_is_never_moved_or_altered(folders) -> None:
    """His downloads are his. A courier who rearranges the post office is worse."""
    src, dst = folders
    _write(src, "AUDIT_2026-09-20_the-inverted-assertion.md", "her words")

    carry_across(src, dst)

    original = src / "AUDIT_2026-09-20_the-inverted-assertion.md"
    assert original.is_file()
    assert original.read_text(encoding="utf-8") == "her words"


def test_running_it_again_carries_nothing_twice(folders) -> None:
    """It runs on every prompt, so repeating has to be free."""
    src, dst = folders
    _write(src, "AUDIT_2026-09-20_the-inverted-assertion.md")

    first = carry_across(src, dst)
    second = carry_across(src, dst)

    assert len(first.carried) == 1
    assert second.carried == []
    assert len(second.already_present) == 1
    assert not second.changed


def test_a_revision_lands_beside_the_first_rather_than_over_it(folders) -> None:
    """She revises and he re-saves under the same name.

    Overwriting would silently replace a reading somebody may already have
    acted on -- and in a folder whose whole job is holding review, the earlier
    verdict is evidence rather than clutter.
    """
    src, dst = folders
    name = "AUDIT_2026-09-20_the-inverted-assertion.md"
    _write(src, name, "first reading")
    carry_across(src, dst)

    _write(src, name, "she changed her mind")
    report = carry_across(src, dst)

    assert len(report.revised) == 1
    landed = sorted(p.name for p in dst.iterdir())
    assert name in landed, "the original verdict is still there"
    assert len(landed) == 2
    assert (dst / name).read_text(encoding="utf-8") == "first reading"


def test_a_missing_downloads_folder_is_reported_not_silent(folders) -> None:
    """Switched-off and nothing-to-do look identical unless one of them speaks."""
    _src, dst = folders
    report = carry_across(dst / "nope", dst)

    assert report.errors
    assert report.carried == []


def test_it_says_nothing_when_there_is_nothing_to_say(folders) -> None:
    """It runs on every prompt. A surface that always speaks becomes wallpaper."""
    src, dst = folders
    assert render(carry_across(src, dst)) == ""


def test_the_predicate_answers_for_both_shapes() -> None:
    assert is_hers("CONFIRMS_2026-09-21_a-read-verb-handed-a-file.md")
    assert is_hers("AUDIT-FABLE-2026-07-02.md")
    assert not is_hers("rune-escape.simulator.iso")
    assert not is_hers("AUDIT.md"), "a kind alone is not a filing"
