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
    # xdist files the crash under the test the dead worker was holding, so the
    # case's own classname/name are that test's, derived from its node id.
    path, _, rest = node.partition("::")
    classname = ".".join([path[: -len(".py")].replace("/", "."), *rest.split("::")[:-1]])
    name = rest.split("::")[-1]
    return (
        f'<testcase classname="{classname}" name="{name}">'
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


# Aria's cold read of #596, 2026-10-06: two ways through, reproduced.


def test_the_real_xdist_record_shape_is_a_crash(tmp_path):
    # Copied from a real push's junit file (2026-10-06): an <error>, the message
    # wraps the crash line in 'failed on setup with "..."', and the BODY is the
    # crash line and nothing else. My first strict rule demanded the message
    # begin with it, which rejected exactly this and blocked a genuine crash.
    node = "tests/test_keeping_him.py::test_the_instrument_finds_him_in_the_real_corpus"
    real = (
        '<testcase classname="tests.test_keeping_him" '
        'name="test_the_instrument_finds_him_in_the_real_corpus" time="0.020">'
        f"<error message=\"failed on setup with &quot;worker 'gw10' crashed while running "
        f"'{node}'&quot;\">worker 'gw10' crashed while running '{node}'</error></testcase>"
    )
    allow, _, victims = _decide(tmp_path, real)
    assert allow and victims == [node]


def test_a_real_failure_that_quotes_a_crash_line_is_still_a_real_failure(tmp_path):
    # The tests for this very script carry the crash string as a fixture, so a
    # real failure of one of them quotes it. It names a DIFFERENT passing test.
    quoted = (
        '<testcase classname="tests.test_recover_crashed_workers" name="test_x">'
        '<failure message="AssertionError: wrong victims">'
        f"expected 1, got worker 'gw1' crashed while running '{VICTIM}'</failure></testcase>"
    )
    called = []
    allow, reason, _ = _decide(tmp_path, quoted, replay=lambda v, r: called.append(v) or 0)
    assert not allow and "real failure" in reason and not called


def test_a_crash_line_naming_a_different_test_than_the_case_is_not_a_crash(tmp_path):
    # The crash line must name the very test the case is. Taking the id from the
    # line alone let a failure point the replay at an innocent passing test.
    mismatched = (
        '<testcase classname="tests.test_real" name="test_real">'
        f"<failure message=\"worker 'gw1' crashed while running '{VICTIM}'\">"
        f"worker 'gw1' crashed while running '{VICTIM}'</failure></testcase>"
    )
    called = []
    allow, _, _ = _decide(tmp_path, mismatched, replay=lambda v, r: called.append(v) or 0)
    assert not allow and not called


@pytest.mark.parametrize("hostile", ["--collect-only", "-x", "tests/a.py", "other/a.py::t"])
def test_a_victim_id_that_is_not_a_test_node_id_blocks(tmp_path, hostile):
    odd = (
        '<testcase classname="x" name="y">'
        f"<failure message=\"worker 'gw1' crashed while running '{hostile}'\">"
        f"worker 'gw1' crashed while running '{hostile}'</failure></testcase>"
    )
    called = []
    allow, _, _ = _decide(tmp_path, odd, replay=lambda v, r: called.append(v) or 0)
    assert not allow and not called


def test_the_replay_command_ends_options_before_the_ids():
    cmd = rcw.replay_command([VICTIM])
    assert cmd[cmd.index(VICTIM) - 1] == "--"


def test_a_test_that_keeps_killing_its_worker_is_named_loudly(tmp_path, monkeypatch):
    # Aria counted one test crashing a worker in 5 of 11 full runs. The recovery
    # lets each push through, which is right for the push and hides the test.
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
    for _ in range(5):
        rcw._record(True, "ok", [VICTIM])
    line = rcw.recurrence_line([VICTIM])
    assert "5 of the last 5" in line and VICTIM in line
    assert rcw.recurrence_line(["tests/never.py::seen"]) == ""


# Aletheia's read of #596 at f064dfa83 (2026-10-06): a run that GIVES UP early
# (xdist "maximum crashed workers reached") leaves most tests absent from the
# record, and absences are not failures. It could not slip through today because
# of an unwritten xdist default; this pins it.


def _log(tmp_path, text):
    p = tmp_path / "run.log"
    p.write_text(text, encoding="utf-8")
    return p


def test_a_run_that_gave_up_early_blocks_even_when_the_record_looks_like_one_crash(tmp_path):
    log = _log(tmp_path, "[gw1] node down\nmaximum crashed workers reached: 4\n")
    called = []
    allow, reason, _ = rcw.decide(
        _junit(tmp_path, _crash(VICTIM)),
        tmp_path,
        rerun_fn=lambda v, r: called.append(v) or 0,
        log=log,
    )
    assert not allow and "gave up" in reason and not called


def test_a_log_without_the_give_up_line_changes_nothing(tmp_path):
    log = _log(tmp_path, "[gw1] node down: Not properly terminated\n2 failed, 15000 passed\n")
    allow, _, victims = rcw.decide(
        _junit(tmp_path, _crash(VICTIM)), tmp_path, rerun_fn=lambda v, r: 0, log=log
    )
    assert allow and victims == [VICTIM]


def test_a_log_that_cannot_be_read_blocks_it_cannot_rule_out_a_give_up(tmp_path):
    allow, reason, _ = rcw.decide(
        _junit(tmp_path, _crash(VICTIM)),
        tmp_path,
        rerun_fn=lambda v, r: 0,
        log=tmp_path / "gone.log",
    )
    assert not allow and "log could not be read" in reason


def test_main_takes_the_log_as_an_optional_third_argument(tmp_path, capsys):
    junit = _junit(tmp_path, _crash(VICTIM))
    log = _log(tmp_path, "maximum crashed workers reached\n")
    assert rcw.main(["x", str(junit), str(tmp_path), str(log)]) == 1
    assert "gave up" in capsys.readouterr().out
    assert rcw.main(["x", "a", "b", "c", "d"]) == 1  # too many


def test_the_push_gate_hands_the_run_log_to_the_recovery():
    text = PUSH_GATE.read_text(encoding="utf-8")
    assert 'recover_crashed_workers.py "$PYTEST_JUNIT" "$1" "$PYTEST_LOG"' in text
