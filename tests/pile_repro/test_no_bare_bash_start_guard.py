"""Guard-as-a-test (pile round ten): no test starts bash by a bare name outside the house finder.

On Windows the bare name `bash` can find a do-nothing stand-in (the WSL relay), so a test that
starts it that way fails there for a reason that has nothing to do with the code it names. The house
answer is `tests._bash_resolver.bash_executable()`, which tries the shell before trusting it.

This file READS every test file's syntax tree and applies two rules. It is marked as an expected
failure because main breaks the second rule today; it is not wired into anything, and it changes no
test file. When the files are repaired the strict expected failure passes and rings.

  Rule 1, the literal: a call whose first argument is a list or tuple starting with the plain string
          "bash" or "sh" (for example subprocess.run(["bash", script])).
  Rule 2, the unchecked lookup: a file that asks shutil.which("bash") and then shows none of: an
          import of bash_executable, a refusal of the stand-in by the folder name System32 (in code,
          not in a comment), or a try-out of the shell (a command list with "-c" and "echo ok" or
          "exit 7"). Such a file takes whatever the lookup returns and runs it.

What it cannot see, so nobody reads silence as coverage: a finder reached through an import under
another name; a shell started inside a command string; a probe that only looks like one. It also
flags one file that I judged safe by reading (it skips on Windows unless Git Bash is in a Git
folder), because it shows none of the three signs; that is a false flag, kept visible on purpose
rather than excused by a list, since a list of excused files is a new place for the slip to hide.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TESTS = REPO / "tests"
THIS_FILE = Path(__file__).resolve()
FINDER = TESTS / "_bash_resolver.py"
SHELL_NAMES = {"bash", "sh"}
PROBE_ENDS = {"echo ok", "exit 7"}


def bare_literal_lines(tree: ast.AST) -> list[int]:
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and node.args:
            first = node.args[0]
            if isinstance(first, (ast.List, ast.Tuple)) and first.elts:
                head = first.elts[0]
                if isinstance(head, ast.Constant) and head.value in SHELL_NAMES:
                    lines.append(node.lineno)
    return lines


def which_bash_lines(tree: ast.AST) -> list[int]:
    lines = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "which"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == "bash"
        ):
            lines.append(node.lineno)
    return lines


def shows_a_check(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and any(
            alias.name == "bash_executable" for alias in node.names
        ):
            return True
        if isinstance(node, ast.Compare):
            parts = [node.left, *node.comparators]
            if any(isinstance(p, ast.Constant) and p.value == "System32" for p in parts):
                return True
        if isinstance(node, (ast.List, ast.Tuple)):
            words = [e.value for e in node.elts if isinstance(e, ast.Constant)]
            if "-c" in words and any(w in PROBE_ENDS for w in words):
                return True
    return False


def findings_in(source: str) -> dict[str, list[int]]:
    tree = ast.parse(source)
    found: dict[str, list[int]] = {}
    literal = bare_literal_lines(tree)
    if literal:
        found["literal"] = literal
    lookup = which_bash_lines(tree)
    if lookup and not shows_a_check(tree):
        found["unchecked_lookup"] = lookup
    return found


def scanned_files() -> list[Path]:
    return [
        path
        for path in sorted(TESTS.rglob("*.py"))
        if path.resolve() not in (THIS_FILE, FINDER.resolve()) and "_archive" not in path.parts
    ]


def scan_all_tests() -> tuple[int, dict[str, dict[str, list[int]]]]:
    flagged: dict[str, dict[str, list[int]]] = {}
    files = scanned_files()
    for path in files:
        found = findings_in(path.read_text(encoding="utf-8", errors="replace"))
        if found:
            flagged[path.relative_to(REPO).as_posix()] = found
    return len(files), flagged


# --- controls: made-up sources, so a "no" cannot be a broken instrument ---------------------------


def test_control_a_bare_literal_start_is_flagged():
    assert findings_in('import subprocess\nsubprocess.run(["bash", "x.sh"])\n') == {"literal": [2]}


def test_control_a_tuple_and_the_plain_sh_name_are_flagged_too():
    assert "literal" in findings_in('import subprocess\nsubprocess.run(("sh", "x.sh"))\n')


def test_control_starting_the_shell_from_a_variable_is_not_a_literal():
    assert findings_in('import subprocess\nsubprocess.run([BASH, "x.sh"])\n') == {}


def test_control_other_programs_by_bare_name_are_not_this_rules_business():
    assert findings_in('import subprocess\nsubprocess.run(["git", "status"])\n') == {}


def test_control_an_unchecked_lookup_is_flagged():
    source = 'import shutil\nBASH = shutil.which("bash")\n'
    assert findings_in(source) == {"unchecked_lookup": [2]}


def test_control_the_house_finder_import_clears_a_lookup():
    source = (
        "import shutil\nfrom tests._bash_resolver import bash_executable\n"
        'x = shutil.which("bash")\n'
    )
    assert findings_in(source) == {}


def test_control_refusing_the_stand_in_by_folder_name_in_code_clears_a_lookup():
    source = 'import shutil\nb = shutil.which("bash")\nok = b and "System32" not in b\n'
    assert findings_in(source) == {}


def test_control_the_stand_in_named_only_in_a_comment_does_not_clear_a_lookup():
    source = 'import shutil\n# System32 is the stand-in\nb = shutil.which("bash")\n'
    assert "unchecked_lookup" in findings_in(source)


def test_control_trying_the_shell_before_trusting_it_clears_a_lookup():
    source = (
        'import shutil, subprocess\nb = shutil.which("bash")\n'
        'subprocess.run([b, "-c", "echo ok"])\n'
    )
    assert findings_in(source) == {}


def test_control_the_scan_really_reads_the_test_folder_and_sees_the_lookup_pattern():
    files = scanned_files()
    assert len(files) > 200, (
        f"only {len(files)} test files were read; the scan may be pointed wrong"
    )
    lookups = 0
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        lookups += 1 if which_bash_lines(tree) else 0
    assert lookups >= 20, f"expected many files that ask which('bash'); saw {lookups}"
    assert FINDER.exists()


@pytest.mark.xfail(
    strict=True,
    reason="reproduces: test files on main run a shell found by a bare lookup without trying it "
    "(round ten); see the draft for the list",
)
def test_no_test_file_starts_bash_by_a_bare_name_outside_the_house_finder():
    scanned, flagged = scan_all_tests()
    lines = [f"{path}: {kinds}" for path, kinds in flagged.items()]
    assert not flagged, (
        f"{len(flagged)} of {scanned} test files start bash by a bare name or take an untried "
        "lookup result:\n" + "\n".join(lines)
    )
