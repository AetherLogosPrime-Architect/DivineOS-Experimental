"""A crashed test worker is not a failed test, and a real failure is never retried away.

2026-10-05: a push's whole suite ran 15,001 passed and one "failed", and that one
had only been held by a worker that died; alone it passed 8 of 8. The push gate
cannot tell the two apart from the exit code. scripts/recover_crashed_workers.py
reads the junit record and replays only the crash victims. Walk walk-3d234701aed3.

Every case that must STILL BLOCK is here, built from fabricated junit files; the
replay is a stand-in so no real tests run.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "recover_crashed_workers.py"
PUSH_GATE = ROOT / "scripts" / "check_push_readiness.sh"

spec = importlib.util.spec_from_file_location("recover_crashed_workers", SCRIPT)
rcw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rcw)

VICTIM = "tests/test_mini_save.py::TestMiniSessionSave::test_no_session_files_returns_error"


def _crash(node: str, gw: str = "gw1") -> str:
    return (
        '<testcase classname="tests.test_mini_save.TestMiniSessionSave" name="x">'
        f"<failure message=\"worker '{gw}' crashed while running '{node}'\">"
        f"worker '{gw}' crashed while running '{node}'</failure></testcase>"
    )


def _real(name: str = "test_real") -> str:
    return (
        f'<testcase classname="tests.test_real" name="{name}">'
        '<failure message="AssertionError: assert 1 == 2">assert 1 == 2</failure></testcase>'
    )


def _junit(tmp_path: Path, *cases: str) -> Path:
    p = tmp_path / "junit.xml"
    p.write_text(
        '<?xml version="1.0"?><testsuites><testsuite name="pytest">'
        + "".join(cases)
        + '<testcase classname="tests.ok" name="fine"/></testsuite></testsuites>',
        encoding="utf-8",
    )
    return p


def _decide(tmp_path, *cases, replay=lambda v, r: 0):
    return rcw.decide(_junit(tmp_path, *cases), tmp_path, rerun_fn=replay)


def test_a_crash_victim_that_passes_alone_is_allowed(tmp_path):
    allow, reason, victims = _decide(tmp_path, _crash(VICTIM))
    assert allow and victims == [VICTIM] and "replayed alone and passed" in reason


def test_the_replay_runs_exactly_the_victims_and_nothing_else(tmp_path):
    seen = []
    _decide(
        tmp_path,
        _crash(VICTIM),
        _crash("tests/test_b.py::t", "gw2"),
        replay=lambda v, r: seen.append(v) or 0,
    )
    assert seen == [sorted([VICTIM, "tests/test_b.py::t"])]


def test_a_crash_victim_that_fails_alone_still_blocks(tmp_path):
    allow, reason, _ = _decide(tmp_path, _crash(VICTIM), replay=lambda v, r: 1)
    assert not allow and "failed when run alone" in reason


def test_a_real_failure_beside_a_crash_blocks_and_is_never_replayed(tmp_path):
    called = []
    allow, reason, _ = _decide(
        tmp_path, _crash(VICTIM), _real(), replay=lambda v, r: called.append(v) or 0
    )
    assert not allow and "real failure" in reason and not called


def test_red_with_no_crash_recorded_blocks(tmp_path):
    allow, _, _ = _decide(tmp_path, _real())
    assert not allow


def test_a_clean_record_that_the_run_called_red_blocks(tmp_path):
    # e.g. a collection error: pytest exited non-zero and junit lists no failure.
    allow, reason, _ = _decide(tmp_path)
    assert not allow and "no crashed worker is recorded" in reason


def test_a_missing_junit_record_blocks(tmp_path):
    allow, reason, _ = rcw.decide(tmp_path / "gone.xml", tmp_path, rerun_fn=lambda v, r: 0)
    assert not allow and "no junit record" in reason


def test_an_unreadable_junit_record_blocks(tmp_path):
    p = tmp_path / "j.xml"
    p.write_text("<not closed", encoding="utf-8")
    allow, reason, _ = rcw.decide(p, tmp_path, rerun_fn=lambda v, r: 0)
    assert not allow and "unreadable" in reason


def test_more_victims_than_the_ceiling_blocks_without_replaying(tmp_path):
    cases = [_crash(f"tests/test_{i}.py::t", f"gw{i}") for i in range(rcw.MAX_VICTIMS + 1)]
    called = []
    allow, reason, _ = _decide(tmp_path, *cases, replay=lambda v, r: called.append(v) or 0)
    assert not allow and "machine" in reason and not called


def test_a_test_that_kills_its_own_process_blocks(tmp_path):
    # It crashes alone too, so the replay fails and the push stays blocked.
    allow, _, _ = _decide(tmp_path, _crash(VICTIM), replay=lambda v, r: -9)
    assert not allow


def test_the_full_node_id_is_read_not_the_cut_off_terminal_line(tmp_path):
    long_id = "tests/" + "a" * 120 + ".py::TestX::test_" + "b" * 60
    _, _, victims = _decide(tmp_path, _crash(long_id))
    assert victims == [long_id]


def test_every_test_run_line_in_the_push_gate_is_followed_by_the_recovery():
    # check_push_readiness.sh has three pytest call sites, and its own header warns
    # about a flag added to the paths someone was looking at and a sibling left behind.
    lines = PUSH_GATE.read_text(encoding="utf-8").splitlines()
    runs = [ln for ln in lines if re.search(r"python -m pytest tests/ -q", ln)]
    assert len(runs) == 3, f"the gate's pytest call sites changed: {len(runs)}"
    missing = [ln.strip()[:70] for ln in runs if "recover_if_only_crashes" not in ln]
    assert not missing, f"call sites without the crash recovery: {missing}"


def test_the_junit_flag_reaches_every_run_through_the_one_variable():
    text = PUSH_GATE.read_text(encoding="utf-8")
    assert "--junitxml=$PYTEST_JUNIT" in text and "recover_crashed_workers.py" in text


@pytest.mark.parametrize("bad", ["", "a", "a b c d"])
def test_main_wants_exactly_two_arguments(bad):
    assert rcw.main(["x"] + bad.split()) == 1
