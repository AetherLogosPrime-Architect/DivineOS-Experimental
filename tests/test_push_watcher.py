"""The push watcher's assembler: pure, tested without a machine, and with the controls that prove it can see.

Each test here pins a decision from the nine-lens walk (walk-193e1c70464f). The recorders that touch real processes are
tested separately (planted fault and its absence); this file is the part that reads a log and decides what to say.

WHAT THIS DOES NOT COVER: that the pre-push hook starts the watcher (the wiring slice), and the real sampler against a
real killed worker (the planted-fault test, which needs processes).
"""

import importlib.util
import re
import sys
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[1] / "scripts" / "push_watcher.py"
_spec = importlib.util.spec_from_file_location("push_watcher", _PATH)
pw = importlib.util.module_from_spec(_spec)
sys.modules["push_watcher"] = pw
_spec.loader.exec_module(pw)


def _w(pid, ppid=100, n=0, k="present"):
    return {"k": k, "n": n, "pid": pid, "ppid": ppid, "name": "python.exe", "worker": True}


def _end(pid, n, ppid=100, worker=True, name="python.exe"):
    return {"k": "ended", "n": n, "pid": pid, "ppid": ppid, "name": name, "worker": worker}


def _parent(pid=100):
    return {"k": "present", "n": 0, "pid": pid, "ppid": 1, "name": "python.exe", "worker": False}


def _tick(n):
    return {"k": "tick", "n": n}


def _real_death_log():
    """One worker ends at sample 20; its parent and a sibling are still there 30 samples later."""
    return [_parent(), _w(11), _w(12), _end(11, 20), _tick(50)]


def _normal_end_log():
    """The ordinary end of a run: the workers and the parent leave together."""
    return [_parent(), _w(11), _w(12), _end(11, 50), _end(12, 50), _end(100, 50), _tick(50)]


# -- CONTROLS FIRST: the instrument must find a case it should find, and stay quiet on one it should not.


def test_control_a_real_death_is_found():
    assert [d["pid"] for d in pw.real_deaths(_real_death_log())] == [11]


def test_control_the_normal_end_of_a_run_is_not_a_death():
    assert pw.real_deaths(_normal_end_log()) == []


def test_a_worker_with_no_living_sibling_is_not_called_a_death():
    log = [_parent(), _w(11), _end(11, 20), _tick(50)]
    assert pw.real_deaths(log) == []


# -- Lamport: order is by sample number, and the same sample is concurrent.


def test_order_is_by_sample_number():
    log = _real_death_log() + [
        {"k": "ended", "n": 18, "pid": 300, "ppid": 1, "name": "git.exe", "worker": False},
        {"k": "ended", "n": 20, "pid": 301, "ppid": 1, "name": "bash.exe", "worker": False},
        {"k": "started", "n": 22, "pid": 302, "ppid": 1, "name": "python.exe", "worker": False},
    ]
    order = {a["name"]: a["order"] for a in pw.around(log, 20)}
    assert order == {"git.exe": "before", "bash.exe": "concurrent", "python.exe": "after"}


# -- Hoare / Turing: the heartbeat keeps a dead watcher apart from a quiet push.


def test_zero_looks_is_watcher_failed_never_nothing_seen():
    report = pw.assemble([], exit_code=1, output_tail="something odd happened")
    assert report["outcome"] == pw.WATCHER_FAILED


def test_looked_and_saw_nothing_is_nothing_seen():
    report = pw.assemble([_parent(), _tick(40)], exit_code=1, output_tail="something odd happened")
    assert report["outcome"] == pw.NOTHING_SEEN and report["samples"] == 40


def test_a_named_event_beats_the_family():
    """An ordinary test failure that also saw a worker die is still NAMED: the machine did interfere."""
    report = pw.assemble(_real_death_log(), exit_code=1, output_tail="3 failed in 40s")
    assert report["outcome"] == pw.NAMED


def test_a_config_change_alone_is_named():
    log = [
        _parent(),
        {"k": "cfg", "n": 7, "before": "bare = false", "after": "bare = true"},
        _tick(30),
    ]
    assert pw.assemble(log, 1, "")["outcome"] == pw.NAMED


# -- Aristotle: an ordinary failure is classified first and is not counted as a watcher miss.


@pytest.mark.parametrize(
    "tail,family",
    [
        ("BLOCKED by something", "gate_refusal"),
        ("! [remote rejected] main -> main", "remote_rejected"),
        ("FAILED tests/test_x.py::test_y", "tests_failed"),
        ("node down: Not properly terminated", "infrastructure"),
        ("nothing helpful", "unknown"),
    ],
)
def test_the_family_comes_from_the_push_own_words(tail, family):
    assert pw.classify(1, tail) == family


def test_exit_zero_is_passed_and_says_nothing():
    report = pw.assemble([_parent(), _tick(10)], 0, "")
    assert report["outcome"] == "PASSED" and pw.final_line(report) == ""


def test_an_ordinary_failure_is_not_mine_when_the_machine_showed_nothing():
    report = pw.assemble([_parent(), _tick(40)], 1, "FAILED tests/test_x.py")
    assert report["outcome"] == pw.NOT_MINE


# -- Angelou: the last line is for Dad.


@pytest.mark.parametrize(
    "log,tail",
    [
        (_real_death_log(), "node down"),
        ([_parent(), _tick(40)], "something odd"),
        ([], "something odd"),
        ([_parent(), _tick(40)], "FAILED tests/test_x.py"),
    ],
)
def test_the_printed_line_has_no_ids_and_no_file_names(log, tail):
    line = pw.final_line(pw.assemble(log, 1, tail), report_path="C:/x/push-1.json")
    assert line
    body = line.split("Details for me and Aether:")[0]
    assert not re.search(r"\b[0-9a-f]{7,}\b", body), body
    assert not re.search(r"\.(py|sh|json|jsonl|md)\b", body), body
    assert not re.search(r"\bpid\b|\bppid\b", body, re.I), body


def test_the_candidates_are_never_called_causes():
    line = pw.final_line(
        pw.assemble(
            _real_death_log()
            + [{"k": "ended", "n": 19, "pid": 9, "ppid": 1, "name": "git.exe", "worker": False}],
            1,
            "",
        )
    )
    assert "caused" not in line and "possible causes, not proven" in line


def test_nothing_seen_says_what_it_cannot_see():
    line = pw.final_line(pw.assemble([_parent(), _tick(40)], 1, "odd"))
    assert "could not tell" in line and "anything that lives only a moment" in line


def test_the_blind_spot_printed_is_the_measured_interval_not_the_asked_for_one():
    """Found by the planted-fault test: the sampler asked for 0.25 s but one look took 2 s. The number printed to him
    must come from the log's own timestamps."""
    log = [
        {
            "k": "present",
            "n": 0,
            "t": 1000.0,
            "pid": 100,
            "ppid": 1,
            "name": "python.exe",
            "worker": False,
        },
        {"k": "tick", "n": 40, "t": 1092.0},
    ]
    assert pw.mean_interval(log) == pytest.approx(2.3)
    assert "about 2.3 seconds" in pw.final_line(pw.assemble(log, 1, "odd"))


# -- Beer: the watcher must not fill the disk.


def test_old_reports_are_dropped_past_the_cap(tmp_path):
    import os
    import time as _t

    for i in range(7):
        p = tmp_path / f"push-{i}.json"
        p.write_text("{}")
        p.with_suffix(".raw.jsonl").write_text("")
        os.utime(p, (_t.time() - 100 + i, _t.time() - 100 + i))
    assert pw.trim_reports(tmp_path, keep=3) == 4
    assert sorted(x.name for x in tmp_path.glob("push-*.json")) == [
        "push-4.json",
        "push-5.json",
        "push-6.json",
    ]
    assert not (tmp_path / "push-0.raw.jsonl").exists()


def test_finish_writes_a_report_and_returns_the_sentence(tmp_path):
    raw = tmp_path / "raw.jsonl"
    raw.write_text("\n".join(__import__("json").dumps(e) for e in _real_death_log()) + "\n")
    sentence = pw.finish(raw, 1, "node down", tmp_path / "reports")
    assert "disturbed by the machine itself" in sentence
    assert len(list((tmp_path / "reports").glob("push-*.json"))) == 1


def _begun(t):
    return {
        "k": "present",
        "n": 0,
        "t": t,
        "pid": 100,
        "ppid": 1,
        "name": "python.exe",
        "worker": False,
    }


def test_an_old_test_log_is_never_read_as_this_pushs_words(tmp_path):
    """The gate keeps ONE log across pushes. A log older than the watcher belongs to an earlier push."""
    import os

    log = tmp_path / "last.log"
    log.write_text("FAILED tests/test_old.py")
    os.utime(log, (900.0, 900.0))
    tail, ran = pw.fresh_tail(log, [_begun(1000.0)])
    assert (tail, ran) == ("", False)


def test_a_log_written_since_the_watcher_started_is_read(tmp_path):
    import os

    log = tmp_path / "last.log"
    log.write_text("FAILED tests/test_new.py")
    os.utime(log, (1100.0, 1100.0))
    tail, ran = pw.fresh_tail(log, [_begun(1000.0)])
    assert ran and "test_new" in tail


def test_a_missing_log_means_the_tests_did_not_run(tmp_path):
    assert pw.fresh_tail(tmp_path / "nope.log", [_begun(1000.0)]) == ("", False)
    assert pw.fresh_tail(None, [_begun(1000.0)]) == ("", False)


def test_a_push_stopped_before_the_tests_is_not_mine_even_with_zero_looks():
    """A check refused it in under a second, before the first look finished. Zero looks is expected there, and it must
    not read as the watcher having failed; but ordinary test failures with zero looks still must."""
    report = pw.assemble([], exit_code=1, output_tail="", tests_ran=False)
    assert report["outcome"] == pw.NOT_MINE and report["family"] == "stopped_before_tests"
    assert (
        pw.assemble([], 1, "FAILED tests/test_x.py", tests_ran=True)["outcome"] == pw.WATCHER_FAILED
    )


def test_the_stopped_before_tests_sentence_is_plain():
    line = pw.final_line(pw.assemble([_begun(1000.0), _tick(4)], 1, "", tests_ran=False))
    assert "a check stopped it before the tests ran" in line


def test_a_passing_push_writes_no_report(tmp_path):
    raw = tmp_path / "raw.jsonl"
    raw.write_text("")
    assert pw.finish(raw, 0, "", tmp_path / "reports") == ""
    assert not (tmp_path / "reports").exists()
