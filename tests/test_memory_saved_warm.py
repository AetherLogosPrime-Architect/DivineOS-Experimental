"""A saved memory is made findable by the house (core/memory_saved_warm.py and its PostToolUse door)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from divineos.core import memory_saved_warm as msw

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def world(tmp_path):
    memory = tmp_path / "memory"
    memory.mkdir()
    base = tmp_path / "state"
    base.mkdir()
    return memory, base


def _spawned():
    calls = []
    return calls, (lambda base: calls.append(base))


def _lines(base):
    log = base / "memory_warm_log.jsonl"
    return [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []


def test_a_memory_file_write_starts_one_background_run_and_logs_it(world) -> None:
    memory, base = world
    f = memory / "a-lesson-dad-2026-11-10.md"
    f.write_text("x")
    calls, spawn = _spawned()
    assert msw.on_write(f, directory=memory, base=base, spawn=spawn) == "started"
    assert len(calls) == 1
    assert [e["event"] for e in _lines(base)] == ["started"]


def test_any_other_file_starts_nothing_and_says_nothing(world, tmp_path) -> None:
    memory, base = world
    other = tmp_path / "notes.md"
    other.write_text("x")
    calls, spawn = _spawned()
    assert msw.on_write(other, directory=memory, base=base, spawn=spawn) == "not-a-memory-file"
    assert (
        msw.on_write(memory / "sub" / "x.md", directory=memory, base=base, spawn=spawn)
        == "not-a-memory-file"
    )
    assert (
        msw.on_write(memory / "notes.txt", directory=memory, base=base, spawn=spawn)
        == "not-a-memory-file"
    )
    assert (
        msw.on_write(memory / "MEMORY.md", directory=memory, base=base, spawn=spawn)
        == "not-a-memory-file"
    )
    assert calls == [] and _lines(base) == []


def test_a_save_during_a_run_is_queued_not_started_twice(world) -> None:
    memory, base = world
    calls, spawn = _spawned()
    first = memory / "one.md"
    second = memory / "two.md"
    for f in (first, second):
        f.write_text("x")
    assert msw.on_write(first, directory=memory, base=base, spawn=spawn) == "started"
    (base / "memory_warm.lock").write_text("123")  # the run has taken its lock
    assert msw.on_write(second, directory=memory, base=base, spawn=spawn) == "queued"
    assert len(calls) == 1
    assert (base / "memory_warm.pending").exists()


def test_a_dead_runs_stale_lock_is_taken_over(world) -> None:
    import os
    import time

    memory, base = world
    f = memory / "x.md"
    f.write_text("x")
    lock = base / "memory_warm.lock"
    lock.write_text("999")
    old = time.time() - msw.LOCK_STALE_SECONDS - 60
    os.utime(lock, (old, old))
    calls, spawn = _spawned()
    assert msw.on_write(f, directory=memory, base=base, spawn=spawn) == "started"
    assert len(calls) == 1


def test_a_failure_to_start_is_said_not_swallowed(world, capsys) -> None:
    memory, base = world
    f = memory / "x.md"
    f.write_text("x")

    def boom(_base):
        raise OSError("no process")

    assert msw.on_write(f, directory=memory, base=base, spawn=boom) == "could-not-start"
    assert "COULD NOT START" in capsys.readouterr().err
    assert _lines(base)[-1]["event"] == "could-not-start"


def test_the_run_reads_back_each_saved_file_and_logs_a_miss_as_a_miss(world) -> None:
    memory, base = world
    (base / "memory_warm.queue").write_text("has-vector.md\nno-vector.md\n")
    msw.run(base=base, warm=lambda: {"computed": 1}, have_vectors=lambda: {"has-vector.md"})
    done = [e for e in _lines(base) if e["event"] == "done"][0]
    assert done["verified"] == {"has-vector.md": True, "no-vector.md": False}
    assert not (base / "memory_warm.lock").exists()


def test_a_run_that_fails_logs_the_error_and_releases_the_lock(world) -> None:
    memory, base = world
    (base / "memory_warm.queue").write_text("x.md\n")

    def boom():
        raise RuntimeError("embedder missing")

    msw.run(base=base, warm=boom, have_vectors=lambda: set())
    assert [e["event"] for e in _lines(base)] == ["run-error"]
    assert not (base / "memory_warm.lock").exists()


def test_saves_that_arrive_during_a_run_make_it_go_round_again_once(world) -> None:
    memory, base = world
    (base / "memory_warm.queue").write_text("a.md\n")
    rounds = []

    def warm():
        rounds.append(1)
        if len(rounds) == 1:  # a second save lands while the first round is running
            (base / "memory_warm.queue").write_text("b.md\n")
            (base / "memory_warm.pending").write_text("1")
        return {"computed": 1}

    msw.run(base=base, warm=warm, have_vectors=lambda: {"a.md", "b.md"})
    assert len(rounds) == 2
    done = [e for e in _lines(base) if e["event"] == "done"]
    assert [e["files"] for e in done] == [["a.md"], ["b.md"]]


def test_the_run_never_writes_into_the_memory_folder(world) -> None:
    memory, base = world
    (base / "memory_warm.queue").write_text("a.md\n")
    msw.run(base=base, warm=lambda: {"computed": 0}, have_vectors=lambda: set())
    assert list(memory.iterdir()) == []


def test_the_run_uses_this_checkouts_own_python_not_the_global_one(tmp_path) -> None:
    """First live run, 2026-11-10: the global Python's divineos points at another checkout, the child died with
    'No module named divineos.core.memory_saved_warm', and the log still said started.

    Hermetic: it builds a fake checkout with a sealed venv and one without, so it proves the rule on any
    machine, including a clean clone where no ``.venv`` exists.
    """
    with_venv = tmp_path / "with"
    for sub in ("Scripts", "bin"):
        (with_venv / ".venv" / sub).mkdir(parents=True)
    sealed = with_venv / ".venv" / ("Scripts" if os.name == "nt" else "bin")
    sealed_python = sealed / ("python.exe" if os.name == "nt" else "python")
    sealed_python.write_text("")
    assert Path(msw._runner_python(with_venv)).resolve() == sealed_python.resolve()
    without = tmp_path / "without"
    without.mkdir()
    assert msw._runner_python(without) == sys.executable


def test_a_run_that_died_and_left_its_queue_is_said_on_the_next_save(world) -> None:
    memory, base = world
    (base / "memory_warm.queue").write_text("orphan.md\n")  # a previous run never consumed this
    f = memory / "next.md"
    f.write_text("x")
    calls, spawn = _spawned()
    assert msw.on_write(f, directory=memory, base=base, spawn=spawn) == "started"
    events = _lines(base)
    left = [e for e in events if e["event"] == "previous-run-left-the-queue"]
    assert left and left[0]["files"] == ["orphan.md"]


def test_the_background_run_asks_for_no_window() -> None:
    """The house refuses a launch that can put windows on Dad's screen; pin that the flag is the one used."""
    source = (ROOT / "src" / "divineos" / "core" / "memory_saved_warm.py").read_text(
        encoding="utf-8"
    )
    code = source.split('"""', 2)[2]  # the code after the docstring
    assert "CREATE_NO_WINDOW" in code
    assert "DETACHED" + "_PROCESS" not in code
