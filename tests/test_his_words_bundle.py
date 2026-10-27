"""The words door runs as ONE process: one library load, the same words, each step's failure its own.

Dad 2026-10-26: the wait before "thinking" is the prompt helpers; the words lookup started a fresh
Python three times (index build, words search, lessons search), each paying about eight seconds to
import the embedding library. Council walk 1 and 2, docs/drafts/prompt_helpers_in_one_trip_draft_2026-10-26.md.
Aria's attack: a try/except keeps an exception its own, not a hang or a crash, so the deadline stays on
the whole helper (the table's own cap) and these tests pin what a fold CAN promise: identical output,
isolation between steps for an exception, and one load.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

pytest.importorskip("sentence_transformers")

from divineos.core import his_lessons_shelf as shelf
from divineos.core import his_words_bundle as bundle
from divineos.core import his_words_door as door

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude" / "hooks" / "his-words-door-surface.sh"

HIS = [
    ("2026-09-11T10:00:00Z", "you are still speaking to me in jargon, where is the inner circle?"),
    ("2026-09-15T10:00:00Z", "this was work and all jargon, where was the circle?"),
    ("2026-09-20T10:00:00Z", "lets go explore skyrim tonight and cast lightning at the dragons"),
    ("2026-09-26T16:40:00Z", "then where is the circle? i keep asking for it in plain words"),
]
ASK = "where is the circle, you are speaking jargon again and i cannot follow"


def _world(tmp_path):
    """A small real world: his words, one lesson, both indexes built, every path inside tmp_path."""
    corpus = tmp_path / "dad_all.jsonl"
    corpus.write_text(
        "\n".join(json.dumps({"ts": ts, "project": "t", "text": t}) for ts, t in HIS) + "\n",
        encoding="utf-8",
    )
    verified, reread = tmp_path / "verified.json", tmp_path / "reread.json"
    verified.write_text("[]", encoding="utf-8")
    reread.write_text(
        json.dumps(
            [
                {
                    "kind": "teaching",
                    "for": "both",
                    "date": "2026-09-26",
                    "text": "where is the circle, i need it in plain words not jargon",
                    "his_words": "where is the circle, i need it in plain words not jargon",
                    "line": "The circle is a plain-words letter to him.",
                    "context": "ok",
                }
            ]
        ),
        encoding="utf-8",
    )
    return {
        "corpus": corpus,
        "door_index": tmp_path / "door_index",
        "verified": verified,
        "reread": reread,
        "shelf_index": tmp_path / "shelf_index",
        "log": None,
    }


def _expected(world, prompt, me="aether"):
    """What the old two commands said, in the old order, once both indexes are current."""
    door.build_index(world["corpus"], world["door_index"])
    shelf.build(world["verified"], world["reread"], world["shelf_index"])
    return door.surface(prompt, index_dir=world["door_index"]) + shelf.surface(
        prompt, me, index_dir=world["shelf_index"], log=None
    )


def test_the_bundle_says_what_the_two_commands_said(tmp_path):
    world = _world(tmp_path)
    want = _expected(world, ASK)
    assert (
        "HE HAS SAID THIS BEFORE" in want and "WHAT HE HAS TAUGHT" in want
    )  # the control has teeth
    assert bundle.run(ASK, "aether", **world) == want


def test_an_automated_notice_says_the_same_in_the_bundle(tmp_path):
    world = _world(tmp_path)
    note = "<task-notification>a job finished</task-notification>"
    want = _expected(world, note)  # first: the indexes must be current before the bundle looks
    assert bundle.run(note, "aether", **world) == want


def _light_or_skip():
    from divineos.core import light_embedder

    ok, why = light_embedder.available()
    if not ok:
        pytest.skip(f"the light embedder cannot run here ({why}): NOT CHECKED is the search path")


def test_the_search_never_loads_the_heavy_toolkit(tmp_path, monkeypatch):
    """Dad 2026-10-28: the wait before I think was this door importing the heavy toolkit on every message.
    With the toolkit made unimportable, the search and the shelf still answer, by the light embedder."""
    _light_or_skip()
    world = _world(tmp_path)
    want = _expected(world, ASK)  # the indexes are built with the heavy model, once, here
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)  # any import now raises
    monkeypatch.setattr(door, "_MODEL", None)
    out = bundle.run(ASK, "aether", **world)
    assert "found by meaning" in out and "WHAT HE HAS TAUGHT" in out  # the searches really ran
    assert out == want  # and the light vector found the same passages the heavy one would


def test_a_failed_light_load_is_said_aloud_and_never_falls_back_to_the_heavy_toolkit(
    tmp_path, monkeypatch
):
    from divineos.core import light_embedder

    world = _world(tmp_path)
    _expected(world, ASK)

    def cannot(_text):
        raise light_embedder.EmbedderUnavailable("the cached weights are missing")

    monkeypatch.setattr(light_embedder, "encode", cannot)
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)  # a fall-back would raise
    out = bundle.run(ASK, "aether", **world)
    assert "could not be searched" in out and "the cached weights are missing" in out


def test_an_index_that_is_behind_starts_a_background_build_and_never_builds_in_the_hook(
    tmp_path,
):
    world = _world(tmp_path)  # nothing indexed: four passages and the lessons are behind
    calls: list[tuple] = []

    def spawn(*paths):
        calls.append(paths)
        return True

    out = bundle.run(ASK, "aether", spawn=spawn, **world)
    assert out.startswith("## HIS WORDS INDEX IS NOT FULLY UP TO DATE THIS TURN")
    assert "4 of his passages are not indexed yet" in out
    assert len(calls) == 1
    assert calls[0] == (
        world["corpus"],
        world["door_index"],
        world["verified"],
        world["reread"],
        world["shelf_index"],
    )
    assert door.unindexed(world["corpus"], world["door_index"]) == 4  # the hook added none


def _paths(world):
    return (
        world["corpus"],
        world["door_index"],
        world["verified"],
        world["reread"],
        world["shelf_index"],
    )


def test_a_free_lock_starts_one_child_with_our_paths_and_is_let_go_again(tmp_path, monkeypatch):
    import subprocess

    world = _world(tmp_path)
    starts: list[list] = []
    monkeypatch.setattr(subprocess, "Popen", lambda cmd, **k: starts.append(cmd))
    assert bundle.start_background_build(*_paths(world)) is True
    assert len(starts) == 1 and starts[0][-5:] == [str(p) for p in _paths(world)]
    with open(world["door_index"] / ".build.lock", "a+b") as fh:
        assert bundle._try_lock(fh)  # asking took the lock only to ask: it is free again


def test_a_build_that_holds_the_lock_is_never_robbed_however_slow(tmp_path, monkeypatch):
    """Aletheia's hold on #736: an age-based lock called a slow build dead and ran a second beside it."""
    import os
    import subprocess

    world = _world(tmp_path)
    world["door_index"].mkdir(parents=True)
    lock = world["door_index"] / ".build.lock"
    starts: list[list] = []
    monkeypatch.setattr(subprocess, "Popen", lambda cmd, **k: starts.append(cmd))
    with open(lock, "a+b") as holder:
        assert bundle._try_lock(holder)  # a build that has been running for a very long time
        os.utime(lock, (0, 0))  # whose lock file looks a lifetime old
        assert bundle.start_background_build(*_paths(world)) is False
        out = bundle.run(ASK, "aether", **world)
    assert starts == []  # no second build was started beside it
    assert "A build is already running in the background" in out


def test_two_children_started_close_together_run_one_build(tmp_path, monkeypatch):
    """Aletheia's hold on #736: two prompts close together could both start a heavy build."""
    import threading
    import time

    world = _world(tmp_path)
    running = 0
    peak = 0
    builds = 0
    guard = threading.Lock()

    def slow_build(*_paths):
        nonlocal running, peak, builds
        with guard:
            running += 1
            builds += 1
            peak = max(peak, running)
        time.sleep(0.4)
        with guard:
            running -= 1
        return 0

    monkeypatch.setattr(bundle, "build_everything", slow_build)
    args = [str(p) for p in _paths(world)]
    results: list[bool] = []

    def child():
        results.append(bundle._build_main(args))

    first = threading.Thread(target=child)
    second = threading.Thread(target=child)
    first.start()
    time.sleep(0.1)  # the second arrives while the first is mid-build
    second.start()
    first.join()
    second.join()
    assert sorted(results) == [False, True]  # one built, the other left at once
    assert peak == 1 and builds == 1


def test_the_background_build_brings_both_indexes_up_to_date_and_leaves_its_lock_takeable(
    tmp_path,
):
    world = _world(tmp_path)
    assert bundle._build_main([str(p) for p in _paths(world)]) is True
    assert door.unindexed(world["corpus"], world["door_index"]) == 0
    assert shelf.is_current(world["verified"], world["reread"], world["shelf_index"])
    with open(world["door_index"] / ".build.lock", "a+b") as fh:
        assert bundle._try_lock(fh)  # the file stays; the system let go when the build ended


def test_a_step_that_breaks_is_spoken_and_does_not_take_the_others_down(tmp_path, monkeypatch):
    world = _world(tmp_path)
    _expected(world, ASK)  # indexes current

    def boom(*a, **k):
        raise RuntimeError("the door fell over")

    monkeypatch.setattr(door, "surface", boom)
    out = bundle.run(ASK, "aether", **world)
    assert "the search itself failed to start" in out  # the door says it could not run
    assert "WHAT HE HAS TAUGHT" in out  # and the lessons still spoke


def test_a_lesson_step_that_breaks_leaves_the_words_door_speaking(tmp_path, monkeypatch):
    world = _world(tmp_path)
    _expected(world, ASK)

    def boom(*a, **k):
        raise RuntimeError("the shelf fell over")

    monkeypatch.setattr(shelf, "surface", boom)
    out = bundle.run(ASK, "aether", **world)
    assert "HE HAS SAID THIS BEFORE" in out and "found by meaning" in out
    assert "the lesson shelf itself failed to start" in out


def test_a_step_that_counts_what_is_behind_and_breaks_says_so_first(tmp_path, monkeypatch):
    world = _world(tmp_path)
    _expected(world, ASK)

    def boom(*a, **k):
        raise RuntimeError("the corpus could not be read")

    monkeypatch.setattr(door, "unindexed", boom)
    out = bundle.run(ASK, "aether", **world)
    assert out.startswith("## HIS WORDS INDEX IS NOT FULLY UP TO DATE THIS TURN")


def test_the_hook_starts_python_once_for_the_whole_door():
    # The structure that makes the one load possible: one interpreter start, not three.
    starts = re.findall(r'"\$PY" -m divineos\.core\.', HOOK.read_text(encoding="utf-8"))
    assert len(starts) == 1, f"the hook starts Python {len(starts)} times"
