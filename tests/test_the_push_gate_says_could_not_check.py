"""The push gate must tell "the suite failed" from "I could not run the suite".

A branch cut before the gate's own runner module reached main has no such module
in the scratch worktree the gate builds, so the runner dies with "No module named
divineos.core.subprocess_jobs" and the gate used to print "tests failing ... Do NOT
push red" about a branch with nothing wrong. That is could-not-look reported as
found-a-fault. These tests feed the decision fixed logs.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from divineos.core.push_gate_verdict import COULD_NOT_CHECK, FAILED, classify

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "check_push_readiness.sh"
_BASH = next(
    (
        c
        for c in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files (x86)\Git\bin\bash.exe")
        if Path(c).exists()
    ),
    shutil.which("bash"),
)

RUNNER_MISSING = (
    "/usr/bin/python: No module named divineos.core.subprocess_jobs\n"
    "[push-readiness] worktree at the pushed commit\n"
)
REAL_FAILURE = (
    "collected 3 items\n"
    "tests/test_b.py F\n"
    "=========================== short test summary info ===========================\n"
    "FAILED tests/test_b.py::test_b_thing\n"
    "1 failed, 2 passed in 0.42s\n"
)
NOTHING_COLLECTED = (
    "============================ no tests ran in 0.01s ============================\n"
)
OTHER_MISSING_MODULE = (
    "ModuleNotFoundError: No module named 'divineos.core.something_the_branch_needs'\n"
    "ERROR tests/test_x.py\n"
)


def test_a_missing_runner_module_is_could_not_check_and_names_the_module():
    verdict = classify(RUNNER_MISSING)
    assert verdict.kind == COULD_NOT_CHECK
    assert "subprocess_jobs" in verdict.reason


def test_a_real_failed_test_is_failed():
    assert classify(REAL_FAILURE).kind == FAILED


def test_a_missing_module_the_tests_need_is_a_real_fault_not_could_not_check():
    assert classify(OTHER_MISSING_MODULE).kind == FAILED


def test_collecting_nothing_is_could_not_check():
    verdict = classify(NOTHING_COLLECTED)
    assert verdict.kind == COULD_NOT_CHECK
    assert "no tests" in verdict.reason.lower()


def test_failures_win_when_tests_really_ran_even_if_the_runner_line_appears():
    assert classify(RUNNER_MISSING + REAL_FAILURE).kind == FAILED


def test_an_empty_log_is_could_not_check_not_a_pass_or_a_fault():
    assert classify("").kind == COULD_NOT_CHECK


@pytest.mark.skipif(_BASH is None, reason="bash not available")
@pytest.mark.parametrize(
    ("log_text", "expected_word", "expected_code"),
    [
        (REAL_FAILURE, "failed", "10"),
        (RUNNER_MISSING, "could_not_check", "11"),
        (NOTHING_COLLECTED, "could_not_check", "11"),  # exit 11 for "no tests ran"
    ],
)
def test_the_script_decides_from_the_log_with_distinct_words_and_exit_codes(
    tmp_path, log_text, expected_word, expected_code
):
    out, err = _run_script_function(tmp_path, "_gate_verdict_for_log", log_text)
    assert out.split()[:2] == [expected_word, expected_code], err


def _run_script_function(tmp_path, func, log_text, env_extra=None, arg=None):
    log = tmp_path / "pytest.log"
    log.write_text(log_text, encoding="utf-8")
    target = arg if arg is not None else log.as_posix()
    harness = f'eval "$(sed -n \'/^{func}()/,/^}}/p\' "{_SCRIPT.as_posix()}")"\n{func} "{target}"\n'
    result = subprocess.run(
        [_BASH, "-c", harness],
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
        timeout=60,
        env={**os.environ, **(env_extra or {})},
    )
    return result.stdout, result.stderr


@pytest.mark.skipif(_BASH is None, reason="bash not available")
def test_a_pythonpath_with_drive_letters_does_not_make_the_classifier_fall_back(tmp_path):
    """A ':'-joined PYTHONPATH broke when it already held 'C:\\x;D:\\y'; it fell back to failed 10."""
    out, err = _run_script_function(
        tmp_path,
        "_gate_verdict_for_log",
        RUNNER_MISSING,
        env_extra={"PYTHONPATH": r"C:\nonexistent_a;D:\nonexistent_b"},
    )
    assert out.split()[:2] == ["could_not_check", "11"], (out, err)
    assert "classifier could not run" not in out


@pytest.mark.skipif(_BASH is None or os.name != "nt", reason="needs Git bash on Windows")
def test_the_suite_runner_pythonpath_keeps_every_drive_letter_entry_whole(tmp_path):
    """The runner's own PYTHONPATH join must not fuse the new dir with a drive-letter entry."""
    out, err = _run_script_function(
        tmp_path,
        "_pythonpath_with",
        "",
        env_extra={"PYTHONPATH": r"C:\nonexistent_a;D:\nonexistent_b"},
        arg="/tmp/worktree/src",
    )
    parts = out.strip().split(";")
    assert parts[0].replace("\\", "/").endswith("/worktree/src"), parts
    assert parts[1:] == [r"C:\nonexistent_a", r"D:\nonexistent_b"], parts


def test_no_pythonpath_join_in_the_gate_uses_a_bare_colon():
    assert "${PYTHONPATH:+:$PYTHONPATH}" not in _SCRIPT.read_text(encoding="utf-8")


def test_the_cause_tells_a_missing_runner_from_nothing_collected():
    assert classify(RUNNER_MISSING).cause == "runner_missing"
    assert classify(NOTHING_COLLECTED).cause == "nothing_collected"
    assert classify("").cause == "no_output"


@pytest.mark.skipif(_BASH is None, reason="bash not available")
@pytest.mark.parametrize(
    ("cause", "says_update_main"),
    [("runner_missing", True), ("nothing_collected", False), ("no_output", False)],
)
def test_update_with_main_advice_is_printed_only_for_the_cause_it_fits(
    tmp_path, cause, says_update_main
):
    out, err = _run_script_function(tmp_path, "_gate_advice_for_cause", "", arg=cause)
    assert ("up to date with main" in out) is says_update_main, (out, err)


def test_the_exit_code_convention_names_the_new_code():
    text = _SCRIPT.read_text(encoding="utf-8")
    assert "11  — could not check" in text
