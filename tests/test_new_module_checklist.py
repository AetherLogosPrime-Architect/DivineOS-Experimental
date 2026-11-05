"""The new-module checklist names the exact fix for each way a first push fails.

Every test builds a throwaway git repo in tmp, stages a change, and runs the
real script against it. Nothing here mocks the script or git.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "new_module_checklist.py"

_TREE_DOC = """# Architecture

## The tree

```
src/divineos/
  cli/
    __init__.py
  core/
    ledger.py          Append-only event store
    knowledge/
      _base.py         DB connection
```
"""

_EXIT_TEST = "_PRE_TOOL_USE_HOOKS_WHEN_WRITTEN = 2\n"

_GATE_TEST = """_NON_GATING_HOOKS: frozenset[str] = frozenset(
    {
        "_lib.sh",
        # mentions old-hook.sh in a comment only, which must not count
        "declared-hook.sh",
    }
)
"""


def _with_tree_line(name: str) -> str:
    return _TREE_DOC.replace("    knowledge/", f"    {name}       Something\n    knowledge/")


def _settings(pre_tool_use_commands: int) -> str:
    hooks = [{"type": "command", "command": f"h{i}.sh"} for i in range(pre_tool_use_commands)]
    return json.dumps({"hooks": {"PreToolUse": [{"matcher": "*", "hooks": hooks}]}})


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    _write(tmp_path, "docs/ARCHITECTURE.md", _TREE_DOC)
    _write(tmp_path, "tests/test_every_exit_passes_every_gate.py", _EXIT_TEST)
    _write(tmp_path, "tests/test_gate_deny_messages_name_remedy.py", _GATE_TEST)
    _write(tmp_path, ".claude/settings.json", _settings(2))
    _write(tmp_path, "src/divineos/core/ledger.py", "x = 1\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "base")
    return tmp_path


def _run(repo: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), "--repo", str(repo)],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout + proc.stderr


def _stage(repo: Path, rel: str, text: str) -> None:
    _write(repo, rel, text)
    _git(repo, "add", rel)


def test_nothing_staged_is_silent(repo):
    assert _run(repo) == (0, "")


def test_unrelated_added_file_is_silent(repo):
    _stage(repo, "README.md", "hi\n")
    assert _run(repo) == (0, "")


def test_modified_core_file_is_silent(repo):
    _stage(repo, "src/divineos/core/ledger.py", "x = 2\n")
    assert _run(repo) == (0, "")


def test_new_core_module_missing_tree_line_prints_the_exact_line(repo):
    _stage(repo, "src/divineos/core/brand_new.py", "x = 1\n")
    code, out = _run(repo)
    assert code == 0
    assert "docs/ARCHITECTURE.md" in out
    # at the indent the other core/ files use (4 spaces)
    assert "\n    brand_new.py   " in out


def test_new_core_module_with_tree_line_is_quiet_about_the_tree(repo):
    _stage(repo, "docs/ARCHITECTURE.md", _with_tree_line("brand_new.py"))
    _stage(repo, "src/divineos/core/brand_new.py", "x = 1\n")
    code, out = _run(repo)
    assert code == 0
    assert "docs/ARCHITECTURE.md" not in out


def test_basename_in_prose_elsewhere_does_not_count_as_a_tree_line(repo):
    doc = _TREE_DOC + "\nProse that mentions brand_new.py in passing.\n"
    _stage(repo, "docs/ARCHITECTURE.md", doc)
    _stage(repo, "src/divineos/core/brand_new.py", "x = 1\n")
    _, out = _run(repo)
    assert "\n    brand_new.py   " in out


def test_same_basename_in_another_directory_does_not_count(repo):
    doc = _TREE_DOC.replace("    __init__.py", "    __init__.py\n    brand_new.py   cli one")
    _stage(repo, "docs/ARCHITECTURE.md", doc)
    _stage(repo, "src/divineos/core/brand_new.py", "x = 1\n")
    _, out = _run(repo)
    assert "\n    brand_new.py   " in out


def test_nested_core_module_is_checked_under_its_own_directory(repo):
    _stage(repo, "src/divineos/core/knowledge/deep.py", "x = 1\n")
    _, out = _run(repo)
    assert "\n      deep.py   " in out  # one level deeper than core/ files


def test_new_core_module_prints_the_prereg_reminder(repo):
    _stage(repo, "docs/ARCHITECTURE.md", _with_tree_line("brand_new.py"))
    _stage(repo, "src/divineos/core/brand_new.py", "x = 1\n")
    _, out = _run(repo)
    assert "prereg" in out


def test_settings_change_with_matching_count_is_silent(repo):
    _stage(repo, ".claude/settings.json", _settings(2) + "\n")
    assert _run(repo) == (0, "")


def test_settings_change_with_new_pretooluse_count_prints_the_number(repo):
    _stage(repo, ".claude/settings.json", _settings(3))
    code, out = _run(repo)
    assert code == 0
    assert "_PRE_TOOL_USE_HOOKS_WHEN_WRITTEN = 3" in out
    assert "was 2" in out


def test_settings_count_is_read_from_the_staged_version(repo):
    _stage(repo, ".claude/settings.json", _settings(3))
    _write(repo, ".claude/settings.json", _settings(2))  # unstaged edit back
    _, out = _run(repo)
    assert "= 3" in out


def test_new_hook_not_declared_prints_the_exact_entry(repo):
    _stage(repo, ".claude/hooks/fresh-hook.sh", "#!/bin/bash\nexit 0\n")
    code, out = _run(repo)
    assert code == 0
    assert '"fresh-hook.sh",' in out
    assert "_NON_GATING_HOOKS" in out


def test_new_hook_declared_is_silent(repo):
    _stage(repo, ".claude/hooks/declared-hook.sh", "#!/bin/bash\nexit 0\n")
    assert _run(repo) == (0, "")


def test_hook_named_only_in_a_comment_is_not_declared(repo):
    _stage(repo, ".claude/hooks/old-hook.sh", "#!/bin/bash\nexit 0\n")
    _, out = _run(repo)
    assert '"old-hook.sh",' in out


def test_all_four_present_prints_only_the_prereg_reminder(repo):
    _stage(repo, "docs/ARCHITECTURE.md", _with_tree_line("brand_new.py"))
    _stage(repo, "src/divineos/core/brand_new.py", "x = 1\n")
    _stage(repo, ".claude/settings.json", _settings(2))
    _stage(repo, ".claude/hooks/declared-hook.sh", "#!/bin/bash\nexit 0\n")
    _, out = _run(repo)
    assert "prereg" in out
    assert "docs/ARCHITECTURE.md" not in out
    assert "_PRE_TOOL_USE" not in out
    assert "_NON_GATING_HOOKS" not in out


def test_rename_into_core_is_reported_as_an_added_module(repo):
    _git(repo, "mv", "src/divineos/core/ledger.py", "src/divineos/core/renamed.py")
    _, out = _run(repo)
    assert "\n    renamed.py   " in out


def test_missing_architecture_doc_says_it_could_not_look(repo):
    _git(repo, "rm", "-q", "-f", "docs/ARCHITECTURE.md")
    _stage(repo, "src/divineos/core/brand_new.py", "x = 1\n")
    code, out = _run(repo)
    assert code == 0
    assert "could not look" in out.lower()


def test_missing_pinned_constant_says_it_could_not_look(repo):
    _git(repo, "rm", "-q", "-f", "tests/test_every_exit_passes_every_gate.py")
    _stage(repo, ".claude/settings.json", _settings(3))
    code, out = _run(repo)
    assert code == 0
    assert "could not look" in out.lower()


def test_unreadable_settings_says_it_could_not_look(repo):
    _stage(repo, ".claude/settings.json", "{ not json")
    code, out = _run(repo)
    assert code == 0
    assert "could not look" in out.lower()


def test_not_a_git_repo_says_so_and_exits_zero(tmp_path, monkeypatch):
    # The suite's temp folders live inside this project's own repo, so without a
    # ceiling git would walk upward and find that one.
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    code, out = _run(tmp_path)
    assert code == 0
    assert "could not look" in out.lower()
