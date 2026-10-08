"""The cut-away tool is tested against a tiny project whose right answers are known from outside.

The tool was wrong four times on 2026-10-07 before it was right, each time with a confident
number: a function re-exported by a package hid its real home (172 of 181 tests called cut off
when 180 were connected); scripts the test loaded itself were invisible; one script loaded under
two names; concurrent runs deleted each other's scratch folders. Tests written by the tool's
author would share the author's premise, so these cases are built the other way round: a
miniature product with deliberate fakes, honest tests, and each of those blind-spot shapes, and
the verdicts are asserted against what is true by construction.

The deliberate fakes are the controls that matter most. A tool that called everything connected
would pass every honest-test assertion here; it cannot pass the fakes.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

# CUTAWAY_UNDER_TEST points the whole file at a mutated copy of the tool, which is how these
# tests are themselves checked (change the tool one line at a time; the tests must go red).
_SCRIPT = Path(
    os.environ.get("CUTAWAY_UNDER_TEST")
    or Path(__file__).resolve().parents[1] / "scripts" / "cutaway.py"
)
_spec = importlib.util.spec_from_file_location("cutaway", _SCRIPT)
assert _spec and _spec.loader
cutaway = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = cutaway  # dataclasses resolve annotations through sys.modules
_spec.loader.exec_module(cutaway)

FILES = {
    "ctl/__init__.py": "from ctl.calc import clamp  # re-exported, as real packages do\n",
    "ctl/calc.py": (
        "CONSTANT_LIST = (1, 2, 3)\n\n\n"
        "def clamp(x, lo, hi):\n    return max(lo, min(hi, x))\n\n\n"
        "def is_adult(age):\n    return age >= 18\n\n\n"
        "def total(items):\n    return sum(items)\n"
    ),
    "ctl/cli.py": (
        "import click\n\n\n@click.group()\ndef cli():\n    pass\n\n\n"
        "def register(group, prefix='hello'):\n"
        "    @group.command()\n    @click.argument('name')\n"
        "    def greet(name):\n        click.echo(f'{prefix} {name}')\n\n"
        "    @group.command()\n    @click.argument('name')\n"
        "    def strict(name):\n"
        "        if not name.strip():\n            raise click.UsageError('name required')\n"
        "        click.echo(name)\n\n\nregister(cli)\n"
    ),
    "scripts/tool.py": "def shout(text):\n    return text.upper()\n",
    "tests/test_honest.py": (
        "from ctl.calc import clamp, is_adult, total\n\n\n"
        "def test_clamp():\n    assert clamp(5, 0, 10) == 5\n    assert clamp(-1, 0, 10) == 0\n\n\n"
        "def test_adult():\n    assert is_adult(18) is True\n    assert is_adult(17) is False\n\n\n"
        "def test_total():\n    assert total([1, 2, 3]) == 6\n"
    ),
    "tests/test_fakes.py": (
        "from ctl import calc\nfrom ctl.calc import CONSTANT_LIST\n\n\n"
        "def test_fake_always_true():\n    assert True\n\n\n"
        "def test_fake_imports_but_never_calls():\n    assert len(CONSTANT_LIST) == 3\n\n\n"
        "def test_fake_swallows_the_failure():\n"
        "    try:\n        calc.total([1])\n    except Exception:\n        pass\n    assert True\n\n\n"
        "def test_fake_asserts_on_its_own_input():\n    value = 41 + 1\n    assert value == 42\n\n\n"
        "def test_fake_mocks_the_thing_it_tests(monkeypatch):\n"
        "    monkeypatch.setattr(calc, 'total', lambda xs: 99)\n    assert calc.total([1]) == 99\n"
    ),
    "tests/test_reexport.py": (
        "from ctl import clamp\n\n\ndef test_clamp_through_the_package():\n"
        "    assert clamp(50, 0, 10) == 10\n"
    ),
    "tests/test_script.py": (
        "import importlib.util\nfrom pathlib import Path\n\n"
        "_spec = importlib.util.spec_from_file_location(\n"
        "    'tool', Path(__file__).resolve().parents[1] / 'scripts' / 'tool.py')\n"
        "tool = importlib.util.module_from_spec(_spec)\n_spec.loader.exec_module(tool)  # never put in sys.modules\n\n\n"
        "def test_shout():\n    assert tool.shout('a') == 'A'\n"
    ),
    "tests/test_cli.py": (
        "from click.testing import CliRunner\n\nfrom ctl.cli import cli\n\n\n"
        "def test_greet_says_hello():\n"
        "    result = CliRunner().invoke(cli, ['greet', 'bob'])\n"
        "    assert result.exit_code == 0 and 'hello bob' in result.output\n\n\n"
        "def test_strict_refuses_but_only_checks_the_exit_code():\n"
        "    assert CliRunner().invoke(cli, ['strict', ' ']).exit_code != 0\n\n\n"
        "def test_strict_refuses_and_says_why():\n"
        "    result = CliRunner().invoke(cli, ['strict', ' '])\n"
        "    assert result.exit_code != 0 and 'name required' in result.output\n"
    ),
    "tests/test_subprocess.py": (
        "import subprocess\nimport sys\n\n\ndef test_runs_the_product_in_a_child_process():\n"
        "    out = subprocess.run([sys.executable, '-c', 'import ctl.calc as c; print(c.total([1, 2]))'],\n"
        "                         capture_output=True, text=True)\n    assert out.stdout.strip() == '3'\n"
    ),
    "tests/test_red.py": "def test_already_red():\n    assert False\n",
    "tests/test_empty.py": "VALUE = 1  # a test file that collects no tests\n",
}


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> object:
    root = tmp_path_factory.mktemp("miniproject")
    for rel, body in FILES.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    return cutaway.Project(
        repo=root,
        src_paths=(root,),
        product_prefix="ctl",
        extra_roots=("scripts",),
        cli_module="ctl.cli",
    )


@pytest.fixture(scope="module")
def results(project) -> dict[str, dict]:
    # two workers on purpose: concurrent runs must not delete each other's scratch folders
    files = sorted((project.repo / "tests").glob("test_*.py"))
    return cutaway.sweep(files, 2, project)


def _verdicts(results: dict[str, dict], filename: str) -> dict[str, str]:
    verdicts = results[f"tests/{filename}"]["verdicts"]
    return {nodeid.rsplit("::", 1)[-1]: v for nodeid, v in verdicts.items()}


class TestHonestTestsAreConnected:
    def test_every_honest_test_is_connected(self, results):
        assert set(_verdicts(results, "test_honest.py").values()) == {"CONNECTED"}

    def test_a_function_re_exported_by_the_package_is_cut_where_it_is_defined(self, results):
        # the first version called 172 of 181 such tests cut off
        assert _verdicts(results, "test_reexport.py") == {
            "test_clamp_through_the_package": "CONNECTED"
        }

    def test_a_script_the_test_loaded_itself_without_registering_is_cut(self, results):
        assert _verdicts(results, "test_script.py") == {"test_shout": "CONNECTED"}

    def test_a_cli_command_defined_in_a_closure_is_cut(self, results):
        assert _verdicts(results, "test_cli.py")["test_greet_says_hello"] == "CONNECTED"


class TestTheCheckerLeavesItselfAlone:
    def test_a_scan_root_holding_the_plugin_does_not_cut_the_plugin(self, project):
        # 2026-10-08: the plugin lives in scripts/, a root it scans as product. It cut its
        # own _stub_code_with, every test after the first failed in setup, and the full sweep
        # reported "nothing weak" over 3,256 tests it had not measured. The real scripts
        # folder is named here as an extra root so the plugin is inside the scan.
        own_folder = str(_SCRIPT.parent)
        scanning_itself = cutaway.Project(
            repo=project.repo,
            src_paths=project.src_paths,
            product_prefix=project.product_prefix,
            extra_roots=("scripts", own_folder),
            cli_module=project.cli_module,
        )
        got = cutaway.sweep([project.repo / "tests" / "test_honest.py"], 1, scanning_itself)
        counts = got["tests/test_honest.py"]["counts"]
        assert counts == {"CONNECTED": 3}, counts


class TestDeliberateFakesAreCaught:
    """If any of these reads CONNECTED the tool is blind."""

    def test_the_five_fakes(self, results):
        assert _verdicts(results, "test_fakes.py") == {
            "test_fake_always_true": "DISCONNECTED",
            "test_fake_imports_but_never_calls": "DISCONNECTED",
            "test_fake_swallows_the_failure": "SWALLOWED",
            "test_fake_asserts_on_its_own_input": "DISCONNECTED",
            "test_fake_mocks_the_thing_it_tests": "DISCONNECTED",
        }

    def test_a_refusal_test_that_only_checks_the_exit_code_swallows_a_crash(self, results):
        cli = _verdicts(results, "test_cli.py")
        assert cli["test_strict_refuses_but_only_checks_the_exit_code"] == "SWALLOWED"
        assert cli["test_strict_refuses_and_says_why"] == "CONNECTED"


class TestKindsAreKeptApart:
    def test_a_product_run_in_a_child_process_is_labeled_not_called_fake(self, results):
        assert set(_verdicts(results, "test_subprocess.py").values()) == {"OUT-OF-PROCESS?"}

    def test_a_test_that_is_already_red_is_not_measured_as_a_verdict(self, results):
        assert set(_verdicts(results, "test_red.py").values()) == {"BASELINE-NOT-GREEN"}

    def test_a_file_that_collects_nothing_could_not_be_measured(self, results):
        res = results["tests/test_empty.py"]
        assert res["status"] == "could-not-measure"
        assert res["why"]


class TestClassifyIsPure:
    def _report(self, **tests):
        return {"results": {k: {"outcome": o, "hits": h} for k, (o, h) in tests.items()}}

    def test_each_verdict(self):
        base = self._report(
            a=("passed", 0), b=("passed", 0), c=("passed", 0), d=("passed", 0), e=("failed", 0)
        )
        cut = self._report(a=("failed", 3), b=("passed", 0), c=("passed", 2), d=("failed", 0))
        assert cutaway.classify(base, cut) == {
            "a": "CONNECTED",
            "b": "DISCONNECTED",
            "c": "SWALLOWED",
            "d": "OTHER-RED",
            "e": "BASELINE-NOT-GREEN",
        }

    def test_a_skipped_test_is_called_skipped_not_broken(self):
        base = self._report(a=("skipped", 0), b=("setup-skipped", 0), c=("failed", 0))
        assert cutaway.classify(base, {"results": {}}) == {
            "a": "SKIPPED",
            "b": "SKIPPED",
            "c": "BASELINE-NOT-GREEN",
        }

    def test_a_test_that_did_not_run_under_the_cut_is_not_called_clean(self):
        base = self._report(a=("passed", 0))
        assert cutaway.classify(base, {"results": {}}) == {"a": "NOT-RUN-UNDER-CUT"}

    def test_a_fixture_that_broke_is_its_own_verdict(self):
        base = self._report(a=("passed", 0))
        cut = {"results": {"a": {"outcome": "setup-failed", "hits": 0}}}
        assert cutaway.classify(base, cut) == {"a": "FIXTURE-BROKE"}


def _ok(**counts):
    return {"status": "ok", "counts": counts}


class TestTheRatchet:
    def test_a_new_weak_test_in_a_clean_file_is_a_violation(self):
        violations, unmeasured = cutaway.ratchet({"t.py": _ok(DISCONNECTED=1)}, {})
        assert violations == [{"file": "t.py", "verdict": "DISCONNECTED", "now": 1, "allowed": 0}]
        assert unmeasured == []

    def test_a_file_at_or_below_its_floor_passes(self):
        floor = {"t.py": {"DISCONNECTED": 3, "SWALLOWED": 1}}
        assert cutaway.ratchet({"t.py": _ok(DISCONNECTED=3, SWALLOWED=0)}, floor) == ([], [])

    def test_one_above_the_floor_fails_even_when_the_file_is_otherwise_old(self):
        floor = {"t.py": {"DISCONNECTED": 3}}
        violations, _ = cutaway.ratchet({"t.py": _ok(DISCONNECTED=4)}, floor)
        assert [v["now"] for v in violations] == [4]

    def test_connected_and_out_of_process_never_count_against_a_file(self):
        assert cutaway.ratchet({"t.py": _ok(CONNECTED=50, **{"OUT-OF-PROCESS?": 9})}, {}) == (
            [],
            [],
        )

    def test_could_not_measure_is_reported_apart_and_is_not_a_pass(self):
        res = {"t.py": {"status": "could-not-measure", "why": "collected no tests", "counts": {}}}
        violations, unmeasured = cutaway.ratchet(res, {})
        assert violations == [] and unmeasured == ["t.py: collected no tests"]


class TestTheFloorCannotBeLoosenedQuietly:
    def test_a_rise_without_a_reason_is_refused(self):
        with pytest.raises(ValueError, match="would rise above the recorded floor"):
            cutaway.updated_floor(
                {"t.py": _ok(DISCONNECTED=2)}, {"t.py": {"DISCONNECTED": 1}}, None
            )

    def test_a_rise_with_a_reason_stores_the_reason_beside_the_count(self):
        new = cutaway.updated_floor(
            {"t.py": _ok(DISCONNECTED=2)},
            {"t.py": {"DISCONNECTED": 1}},
            "scans repo files, not code",
        )
        assert new["t.py"] == {"DISCONNECTED": 2, "reasons": ["scans repo files, not code"]}

    def test_a_fall_is_recorded_freely(self):
        new = cutaway.updated_floor(
            {"t.py": _ok(DISCONNECTED=1)}, {"t.py": {"DISCONNECTED": 5}}, None
        )
        assert new["t.py"] == {"DISCONNECTED": 1}

    def test_a_file_with_nothing_bad_left_leaves_the_floor(self):
        new = cutaway.updated_floor({"t.py": _ok(CONNECTED=4)}, {"t.py": {"DISCONNECTED": 5}}, None)
        assert "t.py" not in new

    def test_an_unmeasured_file_keeps_its_old_floor(self):
        res = {"t.py": {"status": "could-not-measure", "why": "x", "counts": {}}}
        assert cutaway.updated_floor(res, {"t.py": {"DISCONNECTED": 5}}, None)["t.py"] == {
            "DISCONNECTED": 5
        }


class TestAPushOverManyFilesDoesNotDieOnOne:
    def test_a_named_archived_file_is_skipped_and_said_so(self, capsys):
        # --staged and --all always skipped the archive; --files forgot, and a push over 70
        # files came back exit 2 because one archived file collected nothing (2026-10-08)
        assert cutaway.main(["--files", "tests/_archive/test_nothing.py"]) == 0
        out = capsys.readouterr().out
        assert "skipped 1 archived file(s)" in out
        assert "no test files selected" in out

    def test_a_child_that_dies_before_its_report_is_tried_a_second_time(self, project, monkeypatch):
        calls = {"n": 0}
        real_run = cutaway.subprocess.run

        def flaky(cmd, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                return None  # died: no report written
            return real_run(cmd, **kwargs)

        monkeypatch.setattr(cutaway.subprocess, "run", flaky)
        got = cutaway.run_pytest(project.repo / "tests" / "test_honest.py", [], False, project)
        assert calls["n"] == 2
        assert "error" not in got and got["results"]

    def test_a_file_unmeasurable_in_the_crowd_gets_one_run_alone(self, project, monkeypatch):
        crowded = project.repo / "tests" / "test_a.py"
        steady = project.repo / "tests" / "test_b.py"
        calls: list[str] = []

        def fake(path, proj):
            calls.append(path.name)
            if path.name == "test_a.py" and calls.count("test_a.py") == 1:
                return {"status": "could-not-measure", "why": "no report: FileNotFoundError"}
            return {"status": "ok", "counts": {"CONNECTED": 1}, "verdicts": {}}

        monkeypatch.setattr(cutaway, "analyze_file", fake)
        got = cutaway.sweep([crowded, steady], 2, project)
        assert got["tests/test_a.py"]["status"] == "ok"
        assert calls.count("test_a.py") == 2 and calls.count("test_b.py") == 1

    def test_a_file_that_collects_nothing_is_not_rerun(self, project, monkeypatch):
        calls: list[str] = []

        def fake(path, proj):
            calls.append(path.name)
            return {"status": "could-not-measure", "why": "collected no tests"}

        monkeypatch.setattr(cutaway, "analyze_file", fake)
        cutaway.sweep([project.repo / "tests" / "test_empty.py"], 2, project)
        assert calls == ["test_empty.py"]

    def test_two_silences_in_a_row_are_reported_as_they_are(self, project, monkeypatch):
        monkeypatch.setattr(cutaway.subprocess, "run", lambda cmd, **kwargs: None)
        got = cutaway.run_pytest(project.repo / "tests" / "test_honest.py", [], False, project)
        assert got["error"].startswith("no report")


def test_every_child_process_the_tool_starts_passes_the_no_window_flag():
    """2026-10-07: the first version did not, and covered Dad's screen with console windows."""
    source = _SCRIPT.read_text(encoding="utf-8")
    assert source.count("subprocess.run(") == source.count("creationflags=NO_WINDOW")
    assert 'NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)' in source
