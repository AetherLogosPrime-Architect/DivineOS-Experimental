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


# -- Aletheia's third hole (2026-10-23): the watcher recognised Python only by a fixed list of names, so under python3
# (the name on many Linux systems) it never saw its workers and reported "nothing seen" while blind.


@pytest.mark.parametrize(
    "name",
    [
        "python",
        "python.exe",
        "pythonw.exe",
        "python3",
        "python3.12",
        "python3.12.exe",
        "Python3.EXE",
        "python2.7",
    ],
)
def test_python_is_recognised_by_the_shape_of_its_name(name):
    assert pw.is_python_name(name), name


@pytest.mark.parametrize(
    "name",
    [
        "ipython",
        "python-config",
        "pythonic",
        "notpython",
        "python3x",
        "python3.",
        "python.exe.exe",
        "pythonw.exe.bak",
        "",
    ],
)
def test_lookalikes_are_not_python(name):
    """The shape match must not be 'anything with python in it', or every editor helper counts as a test worker."""
    assert not pw.is_python_name(name), name


def test_the_test_runner_and_dash_are_logged_without_an_exe_suffix():
    assert {"pytest", "dash", "bash", "sh", "git"} <= set(pw.LOGGED_NAMES)


# -- Aletheia's hole (2026-10-23): a machine-level crash must OUTRANK the ordinary failed-test line that it causes.


@pytest.mark.parametrize(
    "tail,kind",
    [
        ("Traceback ...\nMemoryError\n=== 1 failed in 4.1s ===", "ran out of memory"),
        ("FAILED tests/test_x.py::test_y - AssertionError\nMemoryError", "ran out of memory"),
        ("tests/test_a.py ..\nKilled\n", "was killed from outside"),
        ("+++++++ Timeout +++++++\nFAILED tests/test_slow.py::test_hang", "timed out"),
        ("OSError: [Errno 28] No space left on device\n3 failed", "ran out of disk space"),
        ("Segmentation fault (core dumped)\n1 failed", "crashed"),
        ("Fatal Python error: Aborted\n2 failed", "crashed"),
        ("fatal: unable to access: Could not resolve host: github.com", "lost the network"),
    ],
)
def test_a_machine_crash_outranks_the_ordinary_failed_line_it_causes(tail, kind):
    assert pw.classify(1, tail) == "infrastructure", tail
    assert pw.infra_kind(tail) == kind


@pytest.mark.parametrize(
    "tail,family",
    [
        (
            "FAILED tests/test_x.py::test_y - AssertionError: 1 != 2\n=== 1 failed in 2s ===",
            "tests_failed",
        ),
        ("[push-readiness] BLOCKED - lint failures", "gate_refusal"),
        ("! [remote rejected] main -> main (protected)", "remote_rejected"),
    ],
)
def test_control_ordinary_failures_are_still_ordinary(tail, family):
    """The instrument must still file a plain failure as plain, or 'infrastructure first' is just 'everything is'."""
    assert pw.classify(1, tail) == family
    assert pw.infra_kind(tail) == ""


def test_an_out_of_memory_run_says_so_in_plain_words_and_is_not_the_ordinary_bucket():
    report = pw.assemble([_parent(), _tick(40)], 1, "MemoryError\n=== 1 failed in 4s ===")
    assert report["outcome"] == pw.NOTHING_SEEN and report["family"] == "infrastructure"
    line = pw.final_line(report)
    assert (
        "the machine ran out of memory, not the code" in line
        and "did not catch which process" in line
    )
    assert not re.search(r"\b[0-9a-f]{7,}\b", line)


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
    # A KNOWN path with no file is a push stopped before the tests (False). No path at all is "could not look" (None),
    # NOT "the tests did not run": Aether, reading fd34d0c49.
    assert pw.fresh_tail(tmp_path / "nope.log", [_begun(1000.0)]) == ("", False)
    assert pw.fresh_tail(None, [_begun(1000.0)]) == ("", None)


def test_a_push_stopped_before_the_tests_is_not_mine_even_with_zero_looks():
    """A check refused it in under a second, before the first look finished. Zero looks is expected there, and it must
    not read as the watcher having failed; but ordinary test failures with zero looks still must."""
    report = pw.assemble([], exit_code=1, output_tail="", tests_ran=False)
    assert report["outcome"] == pw.NOT_MINE and report["family"] == "stopped_before_tests"
    assert (
        pw.assemble([], 1, "FAILED tests/test_x.py", tests_ran=True)["outcome"] == pw.WATCHER_FAILED
    )


def test_a_log_the_watcher_could_not_read_is_its_own_outcome_and_sentence():
    """Hoare's three states: the tests ran and left a log, the tests never ran (the log is old), and I could not look.
    The third used to be spoken as the second, with a confident cause for a push whose log was simply unreadable."""
    report = pw.assemble([_begun(1000.0), _tick(40)], 1, "", tests_ran=None)
    assert report["outcome"] == pw.COULD_NOT_LOOK and report["family"] == pw.COULD_NOT_READ_FAMILY
    line = pw.final_line(report)
    assert "could not read the test log" in line
    assert "ordinary way" not in line and "stopped it before the tests ran" not in line


def test_control_an_old_log_is_still_a_check_that_stopped_the_push():
    report = pw.assemble([_begun(1000.0), _tick(40)], 1, "", tests_ran=False)
    assert report["outcome"] == pw.NOT_MINE and report["family"] == "stopped_before_tests"


def test_the_finish_command_with_no_tail_file_says_it_could_not_read_the_log(tmp_path, capsys):
    """End to end through main(): the hook passes an EMPTY tail file when it could not resolve the home, and what Dad
    reads at the end of that push must be the 'could not read' sentence, not a confident cause."""
    raw = tmp_path / "raw.jsonl"
    raw.write_text(
        '{"k": "begin", "n": 1, "t": 1000.0}\n'
        + "".join(f'{{"k": "tick", "n": {n}, "t": {1000.0 + n}}}\n' for n in range(2, 12)),
        encoding="utf-8",
    )
    code = pw.main(["finish", "--raw", str(raw), "--exit", "1", "--out-dir", str(tmp_path / "out")])
    assert code == 0
    said = capsys.readouterr().err
    assert "could not read the test log" in said and "ordinary way" not in said, said


def test_a_watcher_that_wrote_nothing_is_not_read_as_tests_that_did_not_run(tmp_path, capsys):
    """Aether, reading 9f507f0bd: with an EMPTY raw log there is no timestamp to date the gate's log against, and the
    log used to be dismissed as old. Here the gate's own log says 3 failed, 40 passed: the tests DID run. The watcher
    must say it never got a look, not that a check stopped the push, and must not claim the machine showed nothing."""
    log = tmp_path / "last.log"
    log.write_text("3 failed, 40 passed in 12.5s\n", encoding="utf-8")
    assert pw.fresh_tail(log, []) == ("", None)
    raw = tmp_path / "raw.jsonl"  # never created: the watcher crashed at start
    code = pw.main(
        [
            "finish",
            "--raw",
            str(raw),
            "--exit",
            "1",
            "--out-dir",
            str(tmp_path / "out"),
            "--tail-file",
            str(log),
        ]
    )
    assert code == 0
    said = capsys.readouterr().err
    assert "never got a look" in said, said
    assert "stopped it before the tests ran" not in said and "showed nothing wrong" not in said, (
        said
    )


def test_a_death_the_watcher_saw_is_still_named_when_the_log_could_not_be_read():
    """The log is one source and the process table another: not being able to read the first must not hide the second."""
    report = pw.assemble(_real_death_log(), 1, "", tests_ran=None)
    assert report["outcome"] == pw.NAMED


def test_the_stopped_before_tests_sentence_is_plain():
    line = pw.final_line(pw.assemble([_begun(1000.0), _tick(4)], 1, "", tests_ran=False))
    assert "a check stopped it before the tests ran" in line


_SUMMARY_LINE = "=== 3 failed, 40 passed in 12.5s ==="


def test_the_whole_tree_ending_before_the_summary_is_its_own_outcome():
    """Aether's attack: a timeout, an out-of-memory kill or Ctrl-C ends every worker together, which the lone-death rule
    (a worker gone while its parent and a sibling stay) cannot see."""
    log = [_parent(), _w(11), _w(12), _end(11, 30), _end(12, 30), _end(100, 30), _tick(40)]
    report = pw.assemble(log, 1, "tests/test_x.py ....", tests_ran=True)
    assert report["outcome"] == pw.TREE_ENDED_EARLY
    line = pw.final_line(report)
    assert "ended before it finished" in line and "not to one helper dying" in line


def test_a_tree_that_ended_after_its_summary_is_not_early():
    log = [_parent(), _w(11), _w(12), _end(11, 30), _end(12, 30), _end(100, 30), _tick(40)]
    report = pw.assemble(log, 1, _SUMMARY_LINE, tests_ran=True)
    assert report["outcome"] != pw.TREE_ENDED_EARLY


@pytest.mark.parametrize(
    "tail",
    [
        "tests/test_x.py F.\n\n1 failed, 1 passed in 0.32s",
        "40 passed in 12.50s",
        "3 failed, 40 passed, 2 skipped in 12.5s",
        "1 error in 0.40s",
        "no tests ran in 0.01s",
        "=== 3 failed, 40 passed in 12.5s ===",
    ],
)
def test_the_end_of_a_run_is_recognised_with_the_bar_and_without_it(tail):
    """Aether, cold-reading #712: the push gate runs pytest with -q, which draws NO bar, and the first pattern required
    one. Every ordinary failure with workers then read as the whole tree ending early. Each shape pytest prints must
    count as a finished run."""
    log = [_parent(), _w(11), _w(12), _end(11, 30), _end(12, 30), _end(100, 30), _tick(40)]
    assert pw.assemble(log, 1, tail, tests_ran=True)["outcome"] != pw.TREE_ENDED_EARLY


@pytest.mark.parametrize(
    "tail",
    [
        "tests/test_x.py ....",
        "a test printed: failed in 2s and went on",
        "Traceback ...\nMemoryError",
        "",
    ],
)
def test_control_a_run_that_never_printed_its_end_is_still_early(tail):
    """The other direction: lines that merely look like a result, or no result at all, are not a finished run."""
    log = [_parent(), _w(11), _w(12), _end(11, 30), _end(12, 30), _end(100, 30), _tick(40)]
    assert pw.assemble(log, 1, tail, tests_ran=True)["outcome"] == pw.TREE_ENDED_EARLY


def test_a_lone_death_is_still_named_not_a_tree_ending():
    assert pw.assemble(_real_death_log(), 1, "tests ....", tests_ran=True)["outcome"] == pw.NAMED


def test_no_workers_at_all_is_never_a_tree_ending():
    assert not pw.tree_ended_early([_parent(), _tick(40)], "tests ....", True)


def _busy_quiet_then_death():
    """60 quiet samples in which git comes and goes often, then workers start, then one dies at sample 100."""
    events = [_parent()]
    for n in range(2, 60, 2):
        events.append(
            {"k": "started", "n": n, "pid": 500 + n, "ppid": 1, "name": "git.exe", "worker": False}
        )
    events += [
        dict(_w(11, n=60, k="started")),
        dict(_w(12, n=60, k="started")),
        _end(11, 100),
        _tick(130),
    ]
    events.append(
        {"k": "started", "n": 99, "pid": 900, "ppid": 1, "name": "git.exe", "worker": False}
    )
    events.append(
        {"k": "ended", "n": 99, "pid": 901, "ppid": 1, "name": "curl.exe", "worker": False}
    )
    return events


def test_activity_that_was_normal_in_the_quiet_stretch_is_not_blamed():
    """Aether answering Sagan: the control is the quiet minutes BEFORE the tests in the same push, at no extra cost."""
    events = _busy_quiet_then_death()
    by_name = {a["name"]: a["usual"] for a in pw.around(events, 100)}
    assert by_name["git.exe"] is True, (
        "git was busy before the tests too, so it says nothing about the death"
    )
    assert by_name["curl.exe"] is False, (
        "curl never ran in the quiet stretch, so it is worth naming"
    )


def test_too_little_quiet_stretch_is_unknown_and_counted_not_ignored():
    events = [_parent(), _w(11), _w(12), _end(11, 20), _tick(50)]
    events.append({"k": "ended", "n": 19, "pid": 9, "ppid": 1, "name": "git.exe", "worker": False})
    only = pw.around(events, 20)
    assert only[0]["usual"] is None
    assert "possible causes, not proven" in pw.final_line(pw.assemble(events, 1, ""))


def test_all_usual_activity_is_reported_as_normal_not_as_a_cause():
    events = _busy_quiet_then_death()[:-2]  # drop the two events around the death except git below
    events.append(
        {"k": "ended", "n": 99, "pid": 901, "ppid": 1, "name": "git.exe", "worker": False}
    )
    line = pw.final_line(pw.assemble(events, 1, ""))
    assert "no more than usual for this push" in line and "possible causes" not in line


def test_a_passing_push_writes_no_report(tmp_path):
    raw = tmp_path / "raw.jsonl"
    raw.write_text("")
    assert pw.finish(raw, 0, "", tmp_path / "reports") == ""
    assert not (tmp_path / "reports").exists()
