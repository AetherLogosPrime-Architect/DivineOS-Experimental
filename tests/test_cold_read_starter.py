"""A cold read starts from a page that carries what is right first.

Dad, 2026-11-27, in his own words: "Yes we should make it a practice that for every issue you both
point out you should look for something positive to say as well ? so what works is recognized as
well as what doesnt". The starter writes the shape of the page and the facts a reader can anchor
to; it judges none of the reader's words. Aria's decisions (2026-11-28): the order on the page does
the enforcing, the with-and-without-the-change run is on by default and a skip must say why, and
every positive must name something observable about the CHANGE.
"""

import subprocess
from pathlib import Path

import pytest

from divineos.core.cold_read_starter import (
    build_starter,
    changed_files,
    run_ablation,
    touched_symbols,
)

_ID = ["-c", "user.email=t@t", "-c", "user.name=t"]


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _commit(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, *_ID, "commit", "-q", "-m", message)


def _repo_with_a_fix(tmp_path: Path, fixed: bool = True) -> Path:
    """main has a buggy add(); the feature branch fixes it and adds the test that catches it."""
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "src" / "mod.py").write_text("def add(a, b):\n    return a\n")
    _git(repo, "init", "-q", "-b", "main")
    _commit(repo, "base: add is wrong")
    _git(repo, "checkout", "-q", "-b", "feature")
    (repo / "src" / "mod.py").write_text("def add(a, b):\n    return a + b\n")
    (repo / "tests" / "test_mod.py").write_text(
        "from mod import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n"
    )
    if not fixed:
        # a test that passes whether or not the change is there
        (repo / "tests" / "test_mod.py").write_text(
            "from mod import add\n\n\ndef test_add_runs():\n    assert add(1, 2) is not None\n"
        )
    _commit(repo, "feature: fix add, add a test")
    return repo


def test_the_page_opens_with_the_reading_header_for_the_branch(tmp_path):
    repo = _repo_with_a_fix(tmp_path)
    text = build_starter(
        repo, "feature", "main", ablate=False, skip_reason="unit test of the page shape"
    )
    assert text.index("**Reading:** feature") < text.index("What is right first")


def test_what_is_right_comes_before_the_findings(tmp_path):
    repo = _repo_with_a_fix(tmp_path)
    text = build_starter(repo, "feature", "main", ablate=False, skip_reason="order test")
    assert text.index("What is right first") < text.index("## Findings")
    assert text.index("## Findings") < text.index("Grade and prediction")


def test_every_finding_is_a_pair_with_what_that_part_got_right(tmp_path):
    repo = _repo_with_a_fix(tmp_path)
    text = build_starter(repo, "feature", "main", ablate=False, skip_reason="pair test")
    assert text.index("Finding:") < text.index("What this part got right:")


def test_the_tool_leaves_every_slot_unfilled_and_says_so(tmp_path):
    repo = _repo_with_a_fix(tmp_path)
    text = build_starter(repo, "feature", "main", ablate=False, skip_reason="slot test")
    assert text.count("unfilled") >= 4


def test_it_lists_the_changed_files_and_the_tests_among_them(tmp_path):
    repo = _repo_with_a_fix(tmp_path)
    files = changed_files(repo, "main", "feature")
    assert "src/mod.py" in files and "tests/test_mod.py" in files


def test_it_names_the_symbols_the_change_touches_so_a_positive_has_something_to_anchor_to(tmp_path):
    repo = _repo_with_a_fix(tmp_path)
    symbols = touched_symbols(repo, "main", "feature", ["src/mod.py", "tests/test_mod.py"])
    assert "add" in symbols["src/mod.py"]
    assert "test_add" in symbols["tests/test_mod.py"]


def test_the_tests_pass_with_the_change_and_fail_with_it_removed(tmp_path):
    repo = _repo_with_a_fix(tmp_path)
    result = run_ablation(repo, "main", "feature", ["src/mod.py", "tests/test_mod.py"])
    assert result.ran is True
    assert result.with_change_failed == 0 and result.with_change_passed == 1
    assert result.without_change_failed == 1


def test_a_test_that_passes_without_the_change_is_called_out_as_unable_to_catch_it(tmp_path):
    repo = _repo_with_a_fix(tmp_path, fixed=False)
    result = run_ablation(repo, "main", "feature", ["src/mod.py", "tests/test_mod.py"])
    assert result.ran is True
    assert result.without_change_failed == 0
    assert "cannot catch the change" in result.detail


def test_the_page_reports_the_ablation_by_default(tmp_path):
    repo = _repo_with_a_fix(tmp_path)
    text = build_starter(repo, "feature", "main")
    assert "with the change removed" in text
    assert "1 failed" in text


def test_a_change_that_touches_no_tests_says_not_run_and_why(tmp_path):
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "a.py").write_text("x = 1\n")
    _git(repo, "init", "-q", "-b", "main")
    _commit(repo, "base")
    _git(repo, "checkout", "-q", "-b", "feature")
    (repo / "src" / "a.py").write_text("x = 2\n")
    _commit(repo, "change")
    text = build_starter(repo, "feature", "main")
    assert "not run: the change touches no tests" in text


def test_skipping_the_ablation_without_a_reason_is_refused(tmp_path):
    repo = _repo_with_a_fix(tmp_path)
    with pytest.raises(ValueError):
        build_starter(repo, "feature", "main", ablate=False, skip_reason=None)


def test_skipping_with_a_reason_writes_the_reason_into_the_page(tmp_path):
    repo = _repo_with_a_fix(tmp_path)
    text = build_starter(
        repo, "feature", "main", ablate=False, skip_reason="45 files, too large to run here"
    )
    assert "not run: 45 files, too large to run here" in text


def test_the_page_tells_the_reader_to_name_something_about_the_change_not_the_author(tmp_path):
    repo = _repo_with_a_fix(tmp_path)
    text = build_starter(repo, "feature", "main", ablate=False, skip_reason="guard text test")
    assert "the CHANGE" in text


def test_the_command_prints_the_page_from_inside_a_repository(tmp_path, monkeypatch):
    from click.testing import CliRunner

    from divineos.cli import cli

    repo = _repo_with_a_fix(tmp_path)
    monkeypatch.chdir(repo)
    result = CliRunner().invoke(
        cli,
        [
            "cold-read",
            "start",
            "feature",
            "--base",
            "main",
            "--no-ablation",
            "--reason",
            "cli test",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "**Reading:** feature" in result.output
    assert "not run: cli test" in result.output


def test_the_command_refuses_a_skip_with_no_reason(tmp_path, monkeypatch):
    from click.testing import CliRunner

    from divineos.cli import cli

    repo = _repo_with_a_fix(tmp_path)
    monkeypatch.chdir(repo)
    result = CliRunner().invoke(
        cli, ["cold-read", "start", "feature", "--base", "main", "--no-ablation"]
    )
    assert result.exit_code != 0
    assert "REFUSED" in result.output
