"""A draft push runs the tests that touch the change, not the whole suite (scripts/draft_test_selection.py).

Dad, 2026-10-21: "we just test that code and anything directly touching it. we dont run the full suite until its
being merged to main." And the August half that must keep holding: a test file changed on a draft is never verified
by nobody.

THE PAIRS ARE THE POINT. A selector that returned every test would pass "the importer is selected", and one that
returned nothing would pass "the unrelated test is left out", so each case that selects has a control that must
stay out, built in the same toy repository.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "draft_test_selection.py"


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True, check=True)
    return done.stdout.strip()


FILES = {
    "src/divineos/__init__.py": "",
    "src/divineos/core/__init__.py": "",
    "src/divineos/core/ledger.py": "def log():\n    return 1\n",
    "src/divineos/core/ledger_extra.py": "VALUE = 2\n",
    "src/divineos/core/lonely.py": "NOBODY_TESTS_ME = True\n",
    "src/divineos/core/pkg/__init__.py": "PKG = 1\n",
    ".claude/hooks/some-gate.sh": "#!/bin/bash\nexit 0\n",
    "scripts/some_tool.py": "print('hi')\n",
    "tests/conftest.py": "",
    "tests/helpers_shared.py": "X = 1\n",
    "tests/test_uses_ledger_dotted.py": "import divineos.core.ledger\n\n\ndef test_a():\n    assert True\n",
    "tests/test_uses_ledger_from.py": "from divineos.core import ledger\n\n\ndef test_b():\n    assert True\n",
    "tests/test_uses_the_extra_one.py": "from divineos.core.ledger_extra import VALUE\n\n\ndef test_c():\n    assert True\n",
    "tests/test_unrelated.py": "def test_d():\n    assert True\n",
    "tests/test_names_the_hook.py": "HOOK = 'some-gate.sh'\n\n\ndef test_e():\n    assert True\n",
    "tests/test_uses_the_helper.py": "import helpers_shared\n\n\ndef test_f():\n    assert True\n",
    "tests/test_uses_the_package.py": "import divineos.core.pkg\n\n\ndef test_g():\n    assert True\n",
    "tests/_archive/test_old_ledger.py": "import divineos.core.ledger\n",
    "docs/note.md": "words\n",
}


@pytest.fixture(scope="module")
def repo(tmp_path_factory) -> tuple[Path, str]:
    root = tmp_path_factory.mktemp("selectionrepo")
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.invalid")
    _git(root, "config", "user.name", "t")
    for rel, body in FILES.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "base")
    return root, _git(root, "rev-parse", "HEAD")


def _run(repo: tuple[Path, str], changed: list[str], ref: str | None = None):
    root, sha = repo
    done = subprocess.run(
        [sys.executable, str(_SCRIPT), "--repo", str(root), "--ref", ref or sha],
        input="\n".join(changed) + "\n",
        capture_output=True,
        text=True,
        timeout=120,
    )
    return done.returncode, [ln for ln in done.stdout.splitlines() if ln], done.stderr


def test_a_changed_test_file_is_selected_and_an_unchanged_one_is_not(repo):
    code, chosen, _ = _run(repo, ["tests/test_unrelated.py"])
    assert code == 0 and chosen == ["tests/test_unrelated.py"]


def test_tests_that_name_a_changed_module_are_selected_by_either_import_form(repo):
    code, chosen, _ = _run(repo, ["src/divineos/core/ledger.py"])
    assert code == 0
    assert "tests/test_uses_ledger_dotted.py" in chosen
    assert "tests/test_uses_ledger_from.py" in chosen


def test_the_control_tests_that_do_not_name_the_module_stay_out(repo):
    _, chosen, _ = _run(repo, ["src/divineos/core/ledger.py"])
    assert "tests/test_unrelated.py" not in chosen
    assert "tests/test_names_the_hook.py" not in chosen


def test_a_module_whose_name_merely_starts_the_same_does_not_select_the_longer_one(repo):
    """ledger vs ledger_extra: the boundary after the name matters, on both sides."""
    _, for_ledger, _ = _run(repo, ["src/divineos/core/ledger.py"])
    assert "tests/test_uses_the_extra_one.py" not in for_ledger
    _, for_extra, _ = _run(repo, ["src/divineos/core/ledger_extra.py"])
    assert for_extra == ["tests/test_uses_the_extra_one.py"]


def test_a_package_init_selects_the_tests_that_import_the_package(repo):
    _, chosen, _ = _run(repo, ["src/divineos/core/pkg/__init__.py"])
    assert chosen == ["tests/test_uses_the_package.py"]


def test_a_hook_or_script_is_reached_by_its_file_name(repo):
    _, chosen, _ = _run(repo, [".claude/hooks/some-gate.sh"])
    assert chosen == ["tests/test_names_the_hook.py"]


def test_a_shared_test_helper_selects_the_tests_that_use_it(repo):
    _, chosen, _ = _run(repo, ["tests/helpers_shared.py"])
    assert chosen == ["tests/test_uses_the_helper.py"]


def test_the_archive_is_never_selected(repo):
    _, chosen, _ = _run(repo, ["src/divineos/core/ledger.py"])
    assert not any("_archive" in c for c in chosen)


def test_a_change_nothing_names_is_said_out_loud_not_silently_passed(repo):
    """The honest limit: this is the case the full run at ready-for-review is for."""
    code, chosen, err = _run(repo, ["src/divineos/core/lonely.py"])
    assert code == 0 and chosen == []
    assert "NO TEST NAMES src/divineos/core/lonely.py" in err


def test_prose_only_changes_select_nothing_and_flag_nothing(repo):
    code, chosen, err = _run(repo, ["docs/note.md"])
    assert code == 0 and chosen == [] and "NO TEST NAMES" not in err


def test_a_deleted_test_file_is_ignored_and_is_not_called_untested(repo):
    code, chosen, err = _run(repo, ["tests/test_was_here_once.py"])
    assert code == 0 and chosen == [] and "NO TEST NAMES" not in err


@pytest.mark.parametrize("shared", ["tests/conftest.py", "pyproject.toml"])
def test_a_shared_setup_file_cannot_be_narrowed(repo, shared):
    code, chosen, err = _run(repo, [shared, "tests/test_unrelated.py"])
    assert code == 3 and chosen == [] and "cannot be narrowed" in err


def test_an_unreadable_repository_is_not_nothing_to_run(repo):
    root, _ = repo
    code, chosen, err = _run(repo, ["tests/test_unrelated.py"], ref="not-a-real-ref-" + "0" * 20)
    assert code == 2 and chosen == [] and "could not read" in err
