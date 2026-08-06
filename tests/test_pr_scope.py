"""Tests for local PR scope measurement.

The load-bearing ones are the honesty tests. This module exists because I
reported a 100-file sample of a 446-file branch as a census and told Aether
the branch was safe to merge. An unmeasurable branch must never render as a
clean one.
"""

from __future__ import annotations

import subprocess

import pytest

from divineos.core import pr_scope


def _repo(tmp_path, guardrail_lines="src/guarded.py\n"):
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)

    git("init", "-q", "-b", "main")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    (repo / "scripts").mkdir()
    (repo / "scripts" / "guardrail_files.txt").write_text(
        "# comment line\n\n" + guardrail_lines, encoding="utf-8"
    )
    (repo / "base.txt").write_text("base", encoding="utf-8")
    git("add", "-A")
    git("commit", "-qm", "base")
    return repo, git


def test_measures_true_file_count_and_no_guardrail(tmp_path):
    repo, git = _repo(tmp_path)
    git("checkout", "-qb", "feature")
    for i in range(150):  # deliberately past the 100 the API would have capped at
        (repo / f"f{i}.txt").write_text("x", encoding="utf-8")
    git("add", "-A")
    git("commit", "-qm", "many")

    scope = pr_scope.measure("feature", repo, base="main")
    assert scope.error is None
    assert len(scope.files) == 150, "must not cap at 100 the way the API did"
    assert scope.guardrail_hits == []
    assert scope.needs_external_review is False


def test_detects_guardrail_files(tmp_path):
    repo, git = _repo(tmp_path)
    git("checkout", "-qb", "feature")
    (repo / "src").mkdir()
    (repo / "src" / "guarded.py").write_text("x", encoding="utf-8")
    git("add", "-A")
    git("commit", "-qm", "guarded")

    scope = pr_scope.measure("feature", repo, base="main")
    assert scope.guardrail_hits == ["src/guarded.py"]
    assert scope.needs_external_review is True


def test_unknown_branch_is_error_not_empty(tmp_path):
    """The founding failure, inverted. 'Could not look' is not 'touches nothing'."""
    repo, _ = _repo(tmp_path)
    scope = pr_scope.measure("no-such-branch", repo, base="main")
    assert scope.files is None  # NOT []
    assert scope.error is not None
    assert scope.measured is False
    assert scope.needs_external_review is None  # an unknown is not a 'no'
    assert "COULD NOT MEASURE" in scope.describe()
    assert "not 'touches nothing'" in scope.describe()


def test_unreadable_guardrail_list_refuses_rather_than_passing_everything(tmp_path):
    """An unreadable guardrail list must not make every branch look clean."""
    repo, git = _repo(tmp_path)
    (repo / "scripts" / "guardrail_files.txt").unlink()
    git("checkout", "-qb", "feature")
    (repo / "x.txt").write_text("x", encoding="utf-8")
    git("add", "-A")
    git("commit", "-qm", "x")

    scope = pr_scope.measure("feature", repo, base="main")
    assert scope.files is None
    assert scope.needs_external_review is None
    assert "cannot read" in scope.error


def test_guardrail_list_ignores_comments_and_blanks(tmp_path):
    repo, _ = _repo(tmp_path)
    guard, err = pr_scope.load_guardrail_set(repo)
    assert err is None
    assert guard == {"src/guarded.py"}


def test_no_api_path_exists_in_this_module():
    """Truth #11(a): the capped call must not be reachable from here.

    Knowing about the cap did not stop me using the capped call — I had
    documented it, tested it, and reached for it anyway. So the guarantee
    cannot be discipline; it has to be that the option is absent.
    """
    import ast
    import inspect

    src = inspect.getsource(pr_scope)

    # Check the CODE, not the prose. The first version of this test scanned
    # raw source and failed on `GH_FILE_LIST_CAP` appearing in the module
    # docstring, where the history is explained -- a name in a sentence
    # counted as a dependency. That is the exact defect this whole module
    # exists because of, committed inside the test written to prevent it.
    # Fourth instance of the class in three days; strip docstrings and match
    # on real names.
    tree = ast.parse(src)
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {
        n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)
    }
    for mod in ast.walk(tree):
        if isinstance(mod, ast.Import):
            names |= {a.name.split(".")[0] for a in mod.names}
        elif isinstance(mod, ast.ImportFrom) and mod.module:
            names.add(mod.module.split(".")[0])

    for forbidden in ("GH_FILE_LIST_CAP", "requests", "urllib", "httpx"):
        assert forbidden not in names, (
            f"{forbidden!r} is referenced in pr_scope code — the capped path must stay unreachable"
        )

    # And no shelling out to gh, checked against string literals only.
    literals = [
        n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
    ]
    assert not any(lit.strip().startswith("gh") for lit in literals), (
        "a `gh` invocation literal appears in pr_scope code"
    )


@pytest.mark.parametrize("count", [99, 100, 101])
def test_counts_near_the_old_cap_are_exact(tmp_path, count):
    """100 was the number that fooled me. It must be reported as itself."""
    repo, git = _repo(tmp_path)
    git("checkout", "-qb", "feature")
    for i in range(count):
        (repo / f"g{i}.txt").write_text("x", encoding="utf-8")
    git("add", "-A")
    git("commit", "-qm", "n")

    scope = pr_scope.measure("feature", repo, base="main")
    assert len(scope.files) == count
