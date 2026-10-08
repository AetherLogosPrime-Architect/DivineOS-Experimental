"""Proof-test (pile round eight): the cut-away checker's "out of process?" label is chosen by a word in the file.

`scripts/cutaway.py` (`analyze_file`) relabels every DISCONNECTED test in a file as OUT-OF-PROCESS? when
the file's text contains `subprocess` or `bash` (any case), whether or not the test runs anything in a
child process. In the round-seven trial two ordinary in-process tests were relabelled that way
(`tests/test_hook_layer.py`: fixture strings like "#!/bin/bash"; `tests/test_gravity_classifier.py`: an
argument named `bash_command`). The ratchet counts only DISCONNECTED and SWALLOWED, so a relabelled test
never counts against a file's floor.

This test builds a tiny project where the right answer is known by construction (the same way
`tests/test_cutaway.py` does) and asks the tool about three files holding the SAME in-process test that
never depends on the code it names. It does not change the checker.

This file lives on a branch cut from `aria/the-cutaway-checker`, because the checker is not on main.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "cutaway.py"
_spec = importlib.util.spec_from_file_location("cutaway_for_label_repro", _SCRIPT)
assert _spec and _spec.loader
cutaway = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = cutaway
_spec.loader.exec_module(cutaway)

WEAK = "def test_weak_never_calls_the_code():\n    assert 1 + 1 == 2\n"
HEAD = "from ctl import calc\n\n\n"

FILES = {
    "ctl/__init__.py": "",
    "ctl/calc.py": "def total(items):\n    return sum(items)\n",
    # the same weak test, three ways: plain, with the word bash in a string, with the word in a comment
    "tests/test_weak_plain.py": HEAD + WEAK,
    "tests/test_weak_mentions_bash.py": HEAD + 'SCRIPT = "#!/bin/bash\\nexit 0\\n"\n\n\n' + WEAK,
    "tests/test_weak_mentions_subprocess.py": HEAD
    + "# a note: nothing here uses subprocess\n\n\n"
    + WEAK,
    # control: a test that really does run the product in a child process
    "tests/test_real_child_process.py": (
        "import subprocess\nimport sys\n\n\ndef test_runs_the_product_in_a_child_process():\n"
        "    out = subprocess.run([sys.executable, '-c', 'import ctl.calc as c; print(c.total([1, 2]))'],\n"
        "                         capture_output=True, text=True)\n    assert out.stdout.strip() == '3'\n"
    ),
}


@pytest.fixture(scope="module")
def verdicts(tmp_path_factory) -> dict[str, set[str]]:
    root = tmp_path_factory.mktemp("label_project")
    for rel, body in FILES.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    project = cutaway.Project(
        repo=root, src_paths=(root,), product_prefix="ctl", extra_roots=(), cli_module=""
    )
    out = {}
    for name in FILES:
        if name.startswith("tests/test_"):
            result = cutaway.analyze_file(root / name, project)
            assert result["status"] == "ok", (name, result)
            out[name] = set(result["verdicts"].values())
    return out


def test_control_the_plain_weak_test_is_disconnected(verdicts):
    assert verdicts["tests/test_weak_plain.py"] == {"DISCONNECTED"}


def test_control_a_real_child_process_test_is_labelled_out_of_process(verdicts):
    assert verdicts["tests/test_real_child_process.py"] == {"OUT-OF-PROCESS?"}


@pytest.mark.xfail(
    strict=True,
    reason="reproduces: the word `bash` anywhere in the file relabels an in-process weak test",
)
def test_the_word_bash_in_a_string_does_not_hide_a_weak_in_process_test(verdicts):
    assert verdicts["tests/test_weak_mentions_bash.py"] == {"DISCONNECTED"}, verdicts


@pytest.mark.xfail(
    strict=True,
    reason="reproduces: the word `subprocess` in a comment relabels an in-process weak test",
)
def test_the_word_subprocess_in_a_comment_does_not_hide_a_weak_in_process_test(verdicts):
    assert verdicts["tests/test_weak_mentions_subprocess.py"] == {"DISCONNECTED"}, verdicts
