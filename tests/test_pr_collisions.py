"""Tests for `divineos pr-collisions`.

The load-bearing ones are the honesty tests: an unreadable PR list must not
read as "no collisions", and a truncated file set must not read as a complete
one. Both were live failures this substrate hit before the command existed.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from divineos.cli import prs_commands as pc


def test_collisions_finds_shared_files():
    pr_files = {
        405: ["docs/ARCHITECTURE.md", "README.md", "a.py"],
        407: ["docs/ARCHITECTURE.md", "b.py"],
        411: ["docs/ARCHITECTURE.md", "README.md"],
    }
    out = pc.collisions(pr_files)
    paths = [p for p, _ in out]
    assert paths[0] == "docs/ARCHITECTURE.md"  # most contended first
    assert dict(out)["docs/ARCHITECTURE.md"] == [405, 407, 411]
    assert dict(out)["README.md"] == [405, 411]
    assert "a.py" not in paths  # single-owner files are not collisions


def test_letters_excluded_by_default():
    """27 of 44 overlapping files on the 2026-08-05 survey were letters."""
    pr_files = {
        1: ["family/letters/x.md", "src/a.py"],
        2: ["family/letters/x.md", "src/a.py"],
    }
    default = dict(pc.collisions(pr_files))
    assert "family/letters/x.md" not in default
    assert "src/a.py" in default

    with_letters = dict(pc.collisions(pr_files, include_letters=True))
    assert "family/letters/x.md" in with_letters


def test_no_collisions_when_disjoint():
    pr_files = {1: ["a.py"], 2: ["b.py"], 3: ["c.py"]}
    assert pc.collisions(pr_files) == []


def test_single_pr_never_collides_with_itself():
    pr_files = {1: ["a.py", "a.py"]}
    # A duplicated path within one PR is not two owners.
    assert pc.collisions(pr_files) == []


def test_unreadable_pr_list_exits_nonzero_and_says_so(monkeypatch):
    """The failure this command exists to avoid committing itself.

    'Could not read' must never render as 'nothing found'.
    """
    monkeypatch.setattr(pc, "_open_prs_with_files", lambda: ({}, [], "gh: not authenticated"))
    runner = CliRunner()
    import click

    grp = click.Group()
    pc.register(grp)
    result = runner.invoke(grp, ["pr-collisions"])
    assert result.exit_code == 2
    assert "COULD NOT READ" in result.output
    assert "not 'no collisions'" in result.output
    assert "Nothing was checked" in result.output


def test_empty_pr_list_is_reported_as_empty_not_as_failure(monkeypatch):
    monkeypatch.setattr(pc, "_open_prs_with_files", lambda: ({}, [], None))
    runner = CliRunner()
    import click

    grp = click.Group()
    pc.register(grp)
    result = runner.invoke(grp, ["pr-collisions"])
    assert result.exit_code == 0
    assert "No open PRs" in result.output


def test_truncated_file_list_is_flagged_loudly(monkeypatch):
    """A PR at exactly the API cap under-reports, and must say so.

    Hit live on 2026-08-05: #405 returned exactly 100 files and the only
    reason the truncation was caught is that the number looked suspiciously
    round.
    """
    pr_files = {405: ["f%d.py" % i for i in range(pc.GH_FILE_LIST_CAP)], 407: ["f0.py"]}
    monkeypatch.setattr(pc, "_open_prs_with_files", lambda: (pr_files, [405], None))
    runner = CliRunner()
    import click

    grp = click.Group()
    pc.register(grp)
    result = runner.invoke(grp, ["pr-collisions"])
    assert result.exit_code == 0
    assert "TRUNCATED" in result.output
    assert "#405" in result.output
    assert "floor, not a total" in result.output


def test_no_truncation_note_when_nothing_capped(monkeypatch):
    monkeypatch.setattr(pc, "_open_prs_with_files", lambda: ({1: ["a.py"], 2: ["a.py"]}, [], None))
    runner = CliRunner()
    import click

    grp = click.Group()
    pc.register(grp)
    result = runner.invoke(grp, ["pr-collisions"])
    assert "TRUNCATED" not in result.output
    assert "a.py" in result.output


@pytest.mark.parametrize("owners,expected_high", [(4, True), (2, False)])
def test_contention_count_drives_emphasis(owners, expected_high, monkeypatch):
    pr_files = {n: ["hot.py"] for n in range(1, owners + 1)}
    monkeypatch.setattr(pc, "_open_prs_with_files", lambda: (pr_files, [], None))
    runner = CliRunner()
    import click

    grp = click.Group()
    pc.register(grp)
    result = runner.invoke(grp, ["pr-collisions"])
    assert f"{owners}x" in result.output
    assert result.exit_code == 0
