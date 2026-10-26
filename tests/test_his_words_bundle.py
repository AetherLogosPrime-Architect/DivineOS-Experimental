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
    assert bundle.run(note, "aether", **world) == _expected(world, note)


def test_the_embedding_library_is_loaded_once_for_the_search_the_shelf_and_the_build(
    tmp_path, monkeypatch
):
    import sentence_transformers

    world = _world(tmp_path)
    _expected(world, ASK)  # both indexes current, so the search and the shelf both need the model
    with world["corpus"].open(
        "a", encoding="utf-8"
    ) as f:  # and a new passage, so the build does too
        f.write(
            json.dumps(
                {"ts": "2026-10-26T09:00:00Z", "project": "t", "text": "a new thing he said"}
            )
            + "\n"
        )
    loads: list[int] = []
    real = sentence_transformers.SentenceTransformer

    class Counting(real):  # type: ignore[misc, valid-type]
        def __init__(self, *a, **k):
            loads.append(1)
            super().__init__(*a, **k)

    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", Counting)
    monkeypatch.setattr(door, "_MODEL", None)
    out = bundle.run(ASK, "aether", **world)
    assert len(loads) == 1, f"the model was loaded {len(loads)} times in one process"
    assert "WHAT HE HAS TAUGHT" in out and "found by meaning" in out  # the searches really ran
    assert door.unindexed(world["corpus"], world["door_index"]) == 0  # and the build really ran


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


def test_an_index_that_is_still_catching_up_says_so_first(tmp_path, monkeypatch):
    world = _world(tmp_path)
    monkeypatch.setattr(
        door, "MAX_EMBED_PER_RUN", 1
    )  # four passages, one per run: behind after this run
    out = bundle.run(ASK, "aether", **world)
    assert out.startswith("## HIS WORDS INDEX IS NOT FULLY UP TO DATE THIS TURN")


def test_the_hook_starts_python_once_for_the_whole_door():
    # The structure that makes the one load possible: one interpreter start, not three.
    starts = re.findall(r'"\$PY" -m divineos\.core\.', HOOK.read_text(encoding="utf-8"))
    assert len(starts) == 1, f"the hook starts Python {len(starts)} times"
