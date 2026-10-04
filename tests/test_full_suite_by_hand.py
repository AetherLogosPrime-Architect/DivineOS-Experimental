"""The full suite is the push's job: a hand-run of the whole tests folder is
refused, named files and narrowed runs pass (Dad, four times, latest 2026-10-03)."""

from __future__ import annotations

import pytest

from divineos.core.full_suite_by_hand import decide

REFUSED = [
    "pytest tests/ -q --tb=short",
    "pytest tests/ -q -n auto",
    "python -m pytest tests/ -q -n auto --tb=line -p no:cacheprovider",
    'cd C:/wcopy && PYTHONPATH=src "/c/DIVINE OS/DivineOS-Experimental/.venv/Scripts/python.exe" -m pytest tests/ -q -n auto',
    "pytest",
    "pytest -q",
    "pytest tests",
    "pytest tests/ tests/test_a.py",
    ".venv/Scripts/pytest.exe tests/",
]

PASSED = [
    "pytest tests/test_a.py -q",
    "pytest tests/test_a.py tests/test_b.py::test_c -x",
    "pytest tests/ -k doorbell -q",
    "pytest tests/ --collect-only -q",
    "python -m pytest tests/test_a.py -q -n 4",
    'git commit -m "run pytest tests/ later"',
    "echo pytest tests/",
    "ls tests/",
]


@pytest.mark.parametrize("cmd", REFUSED)
def test_a_hand_run_of_the_whole_suite_is_refused(cmd):
    reason = decide(cmd)
    assert reason and "THE FULL SUITE IS THE PUSH'S JOB" in reason
    assert "15-20 mins" in reason


@pytest.mark.parametrize("cmd", PASSED)
def test_named_files_narrowed_runs_and_other_commands_pass(cmd):
    assert decide(cmd) is None


def test_the_refusal_hands_over_the_tests_for_what_changed(tmp_path, monkeypatch):
    import divineos.core.full_suite_by_hand as fs

    monkeypatch.setattr(fs, "changed_tests", lambda repo: ["tests/test_a.py", "tests/test_b.py"])
    reason = decide("pytest tests/ -q", repo=tmp_path)
    assert "pytest tests/test_a.py tests/test_b.py -q" in reason


def test_with_nothing_mapped_it_says_so_rather_than_an_empty_command(tmp_path, monkeypatch):
    import divineos.core.full_suite_by_hand as fs

    monkeypatch.setattr(fs, "changed_tests", lambda repo: [])
    assert "No changed file maps to a test file" in decide("pytest tests/", repo=tmp_path)


def test_it_is_registered_before_every_command():
    from divineos.core import hook_router, hook_surfaces

    hook_router.clear()
    hook_surfaces.install()
    assert "full_suite_by_hand" in hook_router.registered("PreToolUse")


def test_the_router_refuses_through_the_real_dispatch():
    from divineos.core import hook_router, hook_surfaces

    hook_router.clear()
    hook_surfaces.install()
    payload = {"tool_name": "Bash", "tool_input": {"command": "pytest tests/ -q"}}
    result = hook_router.dispatch("PreToolUse", payload)
    assert any(o.name == "full_suite_by_hand" for o in result.refusals)
