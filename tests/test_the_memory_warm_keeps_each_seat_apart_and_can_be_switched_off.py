"""The saved-memory warm keeps each seat's state apart, can be switched off, and never holds anything up.

Found 2026-11-23 while landing the module: its queue, lock and log lived in one folder shared by both seats, while
each run verified against the memory folder of whichever seat's process was running, so a save by one seat queued
behind the other seat's run ended ``verified: false`` with ``computed 0``. These tests pin the separation, the off
switch, the seat on every log row, the hook that never blocks, and the lane that reads only the folder it is told.
Written before the change: every test in the first four groups fails against the module as it ran before.
"""

from __future__ import annotations

import io
import json
import os
import runpy
import sys
from pathlib import Path

import numpy as np
import pytest

from divineos.core import memory_linkage_retriever as r
from divineos.core import memory_saved_warm as msw

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _no_real_home(tmp_path, monkeypatch):
    """Nothing here may touch the real ~/.divineos, even when run against the module as it was."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    monkeypatch.delenv("DIVINEOS_HOME", raising=False)
    monkeypatch.delenv("DIVINEOS_MEMBER", raising=False)


def _seat(monkeypatch, tmp_path, name):
    home = tmp_path / name
    home.mkdir(exist_ok=True)
    monkeypatch.setenv("DIVINEOS_HOME", str(home))
    return home


def _memory(tmp_path):
    memory = tmp_path / "memory"
    memory.mkdir(exist_ok=True)
    note = memory / "a-note-dad-2026-11-23.md"
    note.write_text("x")
    return memory, note


def _rows(home):
    log = home / "memory_warm_log.jsonl"
    return [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []


# --- the state is per seat -------------------------------------------------------------------------


def test_the_state_directory_is_the_seats_own_home(tmp_path, monkeypatch) -> None:
    a = _seat(monkeypatch, tmp_path, "aria")
    assert msw.state_dir() == a
    b = _seat(monkeypatch, tmp_path, "aether")
    assert msw.state_dir() == b != a


def test_two_seats_never_share_a_queue(tmp_path, monkeypatch) -> None:
    memory, note = _memory(tmp_path)
    a = _seat(monkeypatch, tmp_path, "aria")
    assert msw.on_write(note, directory=memory, spawn=lambda base: None) == "started"
    assert (a / "memory_warm.queue").exists()
    b = _seat(monkeypatch, tmp_path, "aether")
    assert not (b / "memory_warm.queue").exists()


def test_a_save_while_the_other_seats_run_is_live_starts_its_own_run(tmp_path, monkeypatch) -> None:
    """The case that actually happened: A's run is live, B saves. B must not queue behind A's run."""
    memory, note = _memory(tmp_path)
    _seat(monkeypatch, tmp_path, "aria")
    lock = msw._paths()[
        "lock"
    ]  # wherever THIS seat's lock lives, so the test cannot pass vacuously
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(str(os.getpid()))  # a live run: this process is alive
    _seat(monkeypatch, tmp_path, "aether")
    started = []
    out = msw.on_write(note, directory=memory, spawn=lambda base: started.append(base))
    assert out == "started" and len(started) == 1


# --- the off switch --------------------------------------------------------------------------------


def test_an_off_file_switches_the_warm_off_and_says_so(tmp_path, monkeypatch) -> None:
    memory, note = _memory(tmp_path)
    a = _seat(monkeypatch, tmp_path, "aria")
    (a / "memory_warm.off").write_text("")
    started = []
    out = msw.on_write(note, directory=memory, spawn=lambda base: started.append(base))
    assert out == "switched-off" and started == []
    assert [row["event"] for row in _rows(a)] == ["switched-off"]
    assert not (a / "memory_warm.queue").exists()


def test_the_off_file_of_one_seat_leaves_the_other_running(tmp_path, monkeypatch) -> None:
    memory, note = _memory(tmp_path)
    a = _seat(monkeypatch, tmp_path, "aria")
    (a / "memory_warm.off").write_text("")
    started = []
    assert msw.on_write(note, directory=memory, spawn=lambda base: started.append(base)) == (
        "switched-off"
    )
    _seat(monkeypatch, tmp_path, "aether")
    assert (
        msw.on_write(note, directory=memory, spawn=lambda base: started.append(base)) == "started"
    )
    assert len(started) == 1


def test_with_no_off_file_nothing_changes(tmp_path, monkeypatch) -> None:
    memory, note = _memory(tmp_path)
    _seat(monkeypatch, tmp_path, "aria")
    assert msw.on_write(note, directory=memory, spawn=lambda base: None) == "started"


# --- every row names the seat ----------------------------------------------------------------------


def test_every_log_row_carries_the_seat_that_wrote_it(tmp_path, monkeypatch) -> None:
    memory, note = _memory(tmp_path)
    a = _seat(monkeypatch, tmp_path, "aria")
    msw.on_write(note, directory=memory, spawn=lambda base: None)
    msw._paths()["lock"].write_text(str(os.getpid()))
    msw.on_write(note, directory=memory, spawn=lambda base: None)  # queued behind the live run
    rows = _rows(a)
    assert [r_["event"] for r_ in rows] == ["started", "queued"]
    assert all(r_.get("seat") == "aria" for r_ in rows)


# --- the hook's own state is never inside the memory folder ----------------------------------------


def test_the_hooks_own_state_is_never_inside_the_memory_folder(tmp_path, monkeypatch) -> None:
    memory, _note = _memory(tmp_path)
    a = _seat(monkeypatch, tmp_path, "aria")
    assert memory not in msw.state_dir().parents and msw.state_dir() != memory
    own = a / "memory_warm_log.jsonl"
    own.write_text("{}\n")
    started = []
    assert msw.on_write(own, directory=memory, spawn=lambda base: started.append(base)) == (
        "not-a-memory-file"
    )
    assert started == []


# --- the hook never holds anything up ---------------------------------------------------------------


def test_whatever_on_write_raises_the_hook_exits_zero_and_says_so(
    tmp_path, monkeypatch, capsys
) -> None:
    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(msw, "on_write", boom)
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(tmp_path / "x.md")}}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(
            str(ROOT / ".claude" / "hooks" / "memory_saved_warm.py"), run_name="__main__"
        )
    assert exc.value.code == 0
    assert "broke" in capsys.readouterr().err


# --- the memory-folder lane reads only the folder it is told ---------------------------------------


def _one_vector(monkeypatch):
    monkeypatch.setattr(r, "_embed_text_impl", lambda text: np.ones(3, dtype=np.float32))


def _note(folder: Path, name: str, body: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(
        f"---\nname: {name}\ndescription: {name}\n---\n\n{body}\n", encoding="utf-8"
    )


def test_a_seat_never_reads_the_other_seats_notes(tmp_path, monkeypatch) -> None:
    _one_vector(monkeypatch)
    aria, aether = tmp_path / "aria-memory", tmp_path / "aether-memory"
    _note(aria, "only-aria.md", "a note that is hers")
    _note(aether, "only-aether.md", "a note that is his")
    monkeypatch.setattr(r, "_memory_files_dir", lambda: aria)
    assert [i.id for i in r._load_memory_files()] == ["memory-only-aria"]
    monkeypatch.setattr(r, "_memory_files_dir", lambda: aether)
    assert [i.id for i in r._load_memory_files()] == ["memory-only-aether"]


def test_the_folder_is_keyed_by_the_checkout_so_two_checkouts_have_two_folders(monkeypatch) -> None:
    monkeypatch.setattr(r, "_REPOSITORY_ROOT", Path("C:/DIVINE OS/DivineOS-Experimental-Aria-new"))
    one = r._memory_files_dir()
    monkeypatch.setattr(r, "_REPOSITORY_ROOT", Path("C:/DIVINE OS/DivineOS-Experimental"))
    two = r._memory_files_dir()
    assert one != two and one.name == two.name == "memory"


def test_an_empty_or_missing_memory_folder_gives_an_empty_lane_not_an_error(
    tmp_path, monkeypatch
) -> None:
    _one_vector(monkeypatch)
    monkeypatch.setattr(r, "_memory_files_dir", lambda: tmp_path / "does-not-exist")
    assert r._load_memory_files() == []
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setattr(r, "_memory_files_dir", lambda: empty)
    assert r._load_memory_files() == []


def test_the_index_and_a_note_with_no_body_are_skipped(tmp_path, monkeypatch) -> None:
    _one_vector(monkeypatch)
    folder = tmp_path / "m"
    _note(folder, "real.md", "something to find")
    (folder / "MEMORY.md").write_text("- [index](real.md)\n", encoding="utf-8")
    (folder / "frontmatter-only.md").write_text("---\nname: x\n---\n", encoding="utf-8")
    monkeypatch.setattr(r, "_memory_files_dir", lambda: folder)
    assert [i.id for i in r._load_memory_files()] == ["memory-real"]


def test_the_lane_is_registered_where_main_lists_its_loaders() -> None:
    """Built-but-unwired is the failure: read the real source, not a fixture."""
    src = (ROOT / "src" / "divineos" / "core" / "memory_linkage_retriever.py").read_text(
        encoding="utf-8"
    )
    assert '_EMBEDDING_CACHE["wall"] = _load_wall() + _load_memory_files()' in src
    assert src.count("_load_memory_files,") >= 1  # in warm()'s loader tuple
