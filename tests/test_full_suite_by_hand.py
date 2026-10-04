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
    # Aletheia's five, 2026-10-03: the same folder, spelled differently.
    "pytest .",
    "pytest ./tests/../tests",
    "pytest $(pwd)/tests",
    "pytest tests//",
    "uv run pytest tests",
    "poetry run pytest tests/ -q",
    "python3 -m pytest tests",
    # Aria's three, 2026-10-04. A cd moves where the shell stands.
    "cd src && pytest ../tests",
    "cd tests && pytest",
    "cd tests && pytest .",
    'cd "src" && pytest ../tests -q',
    "cd $SOMEWHERE && pytest tests/test_a.py",
    # A glob is expanded by the shell after this check reads it.
    "pytest tests/*",
    "pytest tests/test_*.py",
    "pytest tests/test_[a-z]*.py",
    # An expression that selects nothing out, or everything.
    'pytest tests/ -k ""',
    'pytest tests/ -k "not zzz"',
    "pytest tests/ -k=",
    'pytest -m ""',
    'pytest tests/ -m "not slow"',
    "pytest tests/ -k",
    "cd ~ && pytest tests/test_a.py",
    "cd - && pytest tests/test_a.py",
    "pushd src && pytest ../tests",
    # Aletheia's fourth door, 2026-10-04: a run inside something the check
    # cannot see into counts as everything.
    "(cd src; pytest ../tests)",
    "{ cd src; pytest ../tests; }",
    'bash -c "cd src && pytest ../tests"',
    'sh -c "pytest"',
    'bash -lc "pytest tests/"',
    "python -c 'import pytest; pytest.main()'",
    # Aletheia's fifth, 2026-10-04: runner words in front of pytest.
    "timeout 600 pytest",
    "nohup pytest tests/",
    "time pytest",
    "exec pytest",
    "command pytest",
    "nice -n 10 pytest tests",
    "sudo pytest",
    "eval pytest",
    "xargs pytest",
    "timeout 600 python -m pytest tests/",
    # The price of failing closed, pinned so it stays a choice: a named file
    # inside a wrapper is refused too. Run it unwrapped.
    "(pytest tests/test_a.py)",
    'bash -c "pytest tests/test_a.py"',
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
    "pytest -m slow -q",
    "pytest tests/integration -q",
    "uv run pytest tests/test_a.py",
    # The other side of Aria's three.
    "cd docs && pytest ../tests/test_a.py",
    "cd src && pytest ../tests/test_a.py -q",
    "cd tests && pytest test_a.py",
    "pytest tests/test_a.py -k doorbell",
    "pytest tests/ -k=doorbell",
    'pytest tests/ -k "doorbell and not slow"',
    "pytest tests/test_not_star.py",
    # A runner in front of a named file is still a named file.
    "timeout 600 pytest tests/test_a.py",
    # Text that names pytest is data, not a run.
    "grep -rn pytest tests/",
    "git log --grep pytest",
    "cat tests/pytest.ini",
    "rg pytest tests",
    "ls tests/pytest_plugins.py",
    # Wrappers with no test run in them are not this check's business.
    "(cd docs; ls)",
    'bash -c "echo hi"',
    "python -c 'print(1)'",
    # An unmatched bracket must not make later commands refuse.
    "echo ) && pytest tests/test_a.py",
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
