"""The fault-planting tool (scripts/mutate_copy.py), tested against a small project whose answer is known.

The made-up project has code that IS tested (is_adult, double) and code nobody
tests (untested). So the right readout is known in advance: faults in the first
are caught, by a named test; faults in the second all survive. Without a known
answer, "it ran and printed something" would be the only evidence the tool
works, which is the exact trap the tool exists to catch in other tests.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "mutate_copy.py"
_spec = importlib.util.spec_from_file_location("mutate_copy", _SCRIPT)
mc = importlib.util.module_from_spec(_spec)
sys.modules["mutate_copy"] = mc  # a dataclass looks its own module up by name while loading
_spec.loader.exec_module(mc)

MODULE = "src/pkg/mod.py"
MOD_SOURCE = (
    "def is_adult(age):\n"
    '    label = "é"; return age >= 18\n'  # non-ASCII earlier on the SAME line as the fault
    "\n\n"
    "def double(x):\n"
    "    return x + x\n"
    "\n\n"
    "def untested(x):\n"
    "    return x > 5\n"
    "\n\n"
    "def both(a, b):\n"
    "    return a and b\n"
)
TESTS_SOURCE = (
    "from pkg.mod import is_adult, double, both\n\n"
    "def test_both():\n    assert both(True, True) is True\n    assert both(True, False) is False\n\n"
    "def test_adult_boundary():\n    assert is_adult(18) is True\n\n"
    "def test_minor():\n    assert not is_adult(17)\n\n"
    "def test_double():\n    assert double(2) == 4\n"
)


def _project(root: Path, mod_source: str = MOD_SOURCE, tests_source: str = TESTS_SOURCE) -> Path:
    (root / "src" / "pkg").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "pyproject.toml").write_text('[tool.pytest.ini_options]\npythonpath = ["src"]\n')
    (root / "src" / "pkg" / "__init__.py").write_text("")
    (root / "src" / "pkg" / "mod.py").write_text(mod_source, encoding="utf-8")
    (root / "tests" / "test_mod.py").write_text(tests_source, encoding="utf-8")
    return root


def _run(repo: Path, **kw):
    return mc.run(
        repo,
        MODULE,
        ["tests/test_mod.py"],
        include=("pyproject.toml", "src", "tests"),
        out=repo / "_readouts_outside_copy",
        progress=lambda *_: None,
        **kw,
    )


@pytest.fixture(scope="module")
def known(tmp_path_factory):
    repo = _project(tmp_path_factory.mktemp("known"))
    before = (repo / MODULE).read_bytes()
    report = _run(repo)
    return repo, before, report


def test_faults_in_tested_code_are_caught_by_a_named_test(known):
    _, _, report = known
    rows = [r for r in report["results"] if "age >= 18" in r["line_text"]]
    assert len(rows) >= 3
    assert all(r["outcome"] == "killed" for r in rows)
    assert all(r["killer"] and "test_mod.py::test_" in r["killer"] for r in rows)


def test_faults_in_untested_code_all_survive(known):
    _, _, report = known
    rows = [r for r in report["results"] if r["line_text"] == "return x > 5"]
    assert len(rows) >= 3
    assert all(r["outcome"] == "survived" for r in rows)


def test_the_live_file_is_never_touched_and_the_copy_is_removed(known):
    repo, before, report = known
    assert (repo / MODULE).read_bytes() == before
    assert Path(report["copy"]).name.startswith(
        "mutate-copy-"
    )  # the folder asked about is the tool's own
    assert not Path(report["copy"]).exists()


def test_a_non_ascii_character_earlier_on_the_line_does_not_shift_the_fault():
    data = MOD_SOURCE.encode("utf-8")
    muts = [m for m in mc.find_mutants(data) if m.kind == "compare" and "age" in m.line_text]
    assert muts
    for m in muts:
        text = (data[: m.start] + m.replacement.encode() + data[m.end :]).decode("utf-8")
        assert 'label = "é"' in text
        assert f"age {m.replacement} 18" in text


def test_red_tests_before_any_fault_refuse_the_run(tmp_path):
    repo = _project(tmp_path, tests_source="def test_red():\n    assert False\n")
    with pytest.raises(mc.MutateRefused, match="not green"):
        _run(repo)


def test_nothing_to_plant_is_a_refusal_and_not_a_pass(tmp_path):
    repo = _project(
        tmp_path, mod_source='NAME = "a"\n', tests_source="def test_ok():\n    assert True\n"
    )
    with pytest.raises(mc.MutateRefused, match="NOT a pass"):
        _run(repo)


def test_a_module_imported_from_outside_the_copy_is_refused(tmp_path):
    with pytest.raises(mc.MutateRefused, match="did not import from the copy"):
        mc.prove_copy_is_imported(tmp_path, "json")


def test_a_copy_inside_the_live_tree_is_refused(tmp_path):
    repo = _project(tmp_path)
    with pytest.raises(mc.MutateRefused, match="inside the live tree"):
        mc.make_copy(repo, ("src",), repo / "sub")


def test_sampling_is_repeatable_for_the_same_seed(tmp_path):
    repo = _project(tmp_path)
    a = _run(repo, limit=4, seed=3)
    b = _run(repo, limit=4, seed=3)
    assert [(r["line"], r["replacement"]) for r in a["results"]] == [
        (r["line"], r["replacement"]) for r in b["results"]
    ]
    assert len(a["results"]) == 4


def test_and_or_faults_are_planted_and_caught(known):
    _, _, report = known
    rows = [r for r in report["results"] if r["kind"] == "and-or"]
    assert rows and all(r["outcome"] == "killed" for r in rows)


def test_a_run_that_takes_too_long_is_a_timeout_and_not_caught(tmp_path):
    slow = "import time\n\ndef test_slow():\n    time.sleep(30)\n"
    repo = _project(tmp_path, tests_source=slow)
    outcome, code, killer, _ = mc.run_tests(repo, ["tests/test_mod.py"], timeout=3)
    assert (outcome, code, killer) == ("timeout", None, None)


def test_the_line_filter_plants_only_between_the_lines_and_refuses_an_empty_span(tmp_path):
    repo = _project(tmp_path)
    report = _run(repo, lines=(2, 2))
    assert report["results"] and {r["line"] for r in report["results"]} == {2}
    with pytest.raises(mc.MutateRefused, match="between lines"):
        _run(repo, lines=(500, 600))


def test_test_files_using_the_module_that_were_not_run_are_named(tmp_path):
    """A fault 'missed' by the files handed over may be caught by one that was not."""
    repo = _project(tmp_path)
    (repo / "tests" / "test_elsewhere.py").write_text(
        "from pkg.mod import double\n\ndef test_x():\n    assert double(1) == 2\n"
    )
    (repo / "tests" / "test_unrelated.py").write_text("def test_y():\n    assert True\n")
    report = _run(repo, lines=(6, 6))
    assert report["unrun_importers"] == ["tests/test_elsewhere.py"]
    assert "NOTE: 1 other test file(s)" in mc.summarize(report)


def test_a_crashed_test_run_is_errored_and_not_caught(tmp_path):
    repo = _project(
        tmp_path, tests_source="def test_broken(:\n    pass\n"
    )  # cannot even be collected
    outcome, code, killer, _ = mc.run_tests(repo, ["tests/test_mod.py"], timeout=120)
    assert outcome == "errored" and code != 1 and killer is None


def test_a_catch_that_does_not_repeat_is_flaky_and_not_counted(tmp_path, monkeypatch):
    """A check that is red once by chance, while a planted fault changes nothing it looks at, is
    indistinguishable from a catch unless the catch has to repeat (the walk's Popper lens).

    The flaky check below is red only on the second time it is ever run. The module's one function
    is never called, so no planted fault can be the reason it goes red."""
    monkeypatch.setenv("FLAKY_COUNTER", str(tmp_path / "count.txt"))
    flaky = (
        "import os, pathlib\n"
        "import pkg.mod  # noqa: F401\n\n"
        "def test_red_only_on_its_second_run_ever():\n"
        "    p = pathlib.Path(os.environ['FLAKY_COUNTER'])\n"
        "    n = int(p.read_text()) if p.exists() else 0\n"
        "    p.write_text(str(n + 1))\n"
        "    assert n != 1\n"
    )
    repo = _project(
        tmp_path / "proj", mod_source="def unused_flag():\n    return True\n", tests_source=flaky
    )
    report = _run(repo)
    assert [r["outcome"] for r in report["results"]] == ["flaky", "survived"]
    text = mc.summarize(report)
    assert "flaky 1" in text and "caught 0," in text


def test_a_timeout_ends_the_whole_process_tree(tmp_path, monkeypatch):
    """A run that is cut off must not leave the test's own subprocess running (the walk's Turing
    lens): a fault that makes code loop would otherwise leak one process per planted fault."""
    import time

    import psutil

    pid_file = tmp_path / "pid.txt"
    monkeypatch.setenv("GRANDCHILD_PID_FILE", str(pid_file))
    hanging = (
        "import os, subprocess, sys, time\n\n"
        "def test_starts_a_subprocess_then_hangs():\n"
        "    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
        "    open(os.environ['GRANDCHILD_PID_FILE'], 'w').write(str(child.pid))\n"
        "    time.sleep(120)\n"
    )
    repo = _project(tmp_path / "proj", tests_source=hanging)
    pid = None
    try:
        outcome, code, killer, _ = mc.run_tests(repo, ["tests/test_mod.py"], timeout=10)
        assert (outcome, code, killer) == ("timeout", None, None)
        pid = int(pid_file.read_text())
        deadline = time.time() + 5
        while psutil.pid_exists(pid) and time.time() < deadline:
            time.sleep(0.2)
        assert not psutil.pid_exists(pid), "a timed-out run left its test's own subprocess running"
    finally:
        if pid is None and pid_file.exists():
            pid = int(pid_file.read_text())
        if pid is not None and psutil.pid_exists(pid):
            psutil.Process(pid).kill()


def test_two_runs_in_the_same_second_do_not_share_a_readout_file(tmp_path, monkeypatch):
    monkeypatch.setattr(mc.time, "strftime", lambda *_: "20260101-000000")
    repo = _project(tmp_path / "proj")
    first = _run(repo, lines=(2, 2))
    second = _run(repo, lines=(2, 2))
    assert first["readout"] != second["readout"]


@pytest.mark.parametrize(
    "source", [b"def broken(:\n", b"x = '\xff\xfe'\n"], ids=["syntax", "bytes"]
)
def test_source_that_cannot_be_read_is_refused_with_a_reason(tmp_path, source):
    repo = _project(tmp_path / "proj")
    (repo / MODULE).write_bytes(source)
    with pytest.raises(mc.MutateRefused, match="could not be read as Python source"):
        _run(repo)


def test_the_readout_always_states_what_it_cannot_see(known):
    _, _, report = known
    text = mc.summarize(report)
    for kind in mc.PLANTED_KINDS:
        assert kind in text
    assert "not planted" in text and "first in run order" in text


def test_the_listed_kinds_are_exactly_the_kinds_the_tool_plants():
    """If a new kind of fault is added and the list is not, the readout would understate itself."""
    source = b"def f(a, b):\n    if a > 1 and b:\n        return a + b\n    return True\n"
    assert {m.kind for m in mc.find_mutants(source)} == set(mc.PLANTED_KINDS)


def test_timeouts_and_errors_are_not_counted_as_caught():
    row = {
        "line": 1,
        "kind": "compare",
        "line_text": "x",
        "original": "<",
        "replacement": ">",
        "killer": None,
    }
    report = {
        "module": "m",
        "found": 2,
        "planted": 2,
        "readout": "r",
        "results": [{**row, "outcome": "timeout"}, {**row, "outcome": "errored"}],
    }
    text = mc.summarize(report)
    assert "caught 0" in text and "timed out 1" in text and "errored 1" in text
    assert "gave a clear answer" not in text  # nothing was judged, so no percentage is claimed
