"""The lane that reads the folders we write in: pins two to five of the adapter tests.

Written before the loader exists (2026-11-23). Stacked on the registry (folder_registry.py) and the
hurt-words hold (pain_hold.py, with "writing" already a held source). Each pin is a rule from the
memory walk, tested against real folders in a temp home with a real registry file; only the vector
encoder is replaced by the deterministic one the existing drawer tests use, because the model is not
the thing under test here.

The contract these tests propose (Aria may change any of it, and the tests change with it):
  - ``_load_writing()`` in memory_linkage_retriever reads the registry at
    ``$DIVINEOS_SHARED_DIR/registry/folders.jsonl`` and returns one item per file in each ``read``
    folder, source "writing", title = the registry's arrival text (title, whose, think-with label for
    the other seat's), content = the opening only (what is embedded), path = the pointer.
  - ``_shape_content("writing", ...)`` shows the pointer and no body.
  - one item per folder per turn.
  - ``warm()`` embeds the writing lane's texts, so a vector exists before the first reply that needs it.
Pin one (the hold names the source) is in test_the_writing_lane_keeps_the_hold_the_other_lanes_keep.
"""

from __future__ import annotations

import math
import time

import numpy as np
import pytest

from divineos.core import folder_registry as reg
from divineos.core import memory_linkage_retriever as v1
from divineos.core import memory_linkage_retriever_v2 as v2
from divineos.core import vector_drawer
from divineos.core.memory_linkage_retriever import _CachedItem

BODY_FAR_IN = "the small one climbed onto the third chair and said home"
LABEL = reg.THINK_WITH_LABEL


def _fake_encode_many(batch):
    out = []
    for text in batch:
        rng = np.random.default_rng(abs(hash(text)) % (2**32))
        vec = rng.standard_normal(384).astype(np.float32)
        out.append(vec / np.linalg.norm(vec))
    return np.vstack(out)


def _unit(angle_deg: float) -> np.ndarray:
    a = math.radians(angle_deg)
    return np.array([math.cos(a), math.sin(a)], dtype=float)


def _item(
    item_id: str, angle: float, *, content: str = "an opening", path: str = ""
) -> _CachedItem:
    return _CachedItem(
        id=item_id,
        source="writing",  # type: ignore[arg-type]
        tier="topic",  # type: ignore[arg-type]
        title=item_id,
        content=content,
        path=path,
        filed_at_unix=time.time() - 86400,
        importance_score=0.5,
        embedding=_unit(angle),
    )


@pytest.fixture(autouse=True)
def _home(monkeypatch, tmp_path):
    monkeypatch.setenv("DIVINEOS_SHARED_DIR", str(tmp_path))
    monkeypatch.setenv("DIVINEOS_VECTOR_DRAWER", str(tmp_path / "vectors.db"))
    monkeypatch.setattr(vector_drawer, "_READER", None)
    v2._reset_v2_state_for_tests()
    v1._LANE_STATE.update(missing=0, drawer_error=None)
    yield
    v2._reset_v2_state_for_tests()


def _registered_folder(tmp_path, name: str, whose: str, files: dict[str, str]):
    folder = tmp_path / name
    folder.mkdir()
    for fname, text in files.items():
        (folder / fname).write_text(text, encoding="utf-8")
    reg.register_folder(tmp_path / "registry" / "folders.jsonl", folder, whose=whose, kind="test")
    return folder


def _long_file(title: str) -> str:
    return (
        f"# {title}\n\nThe opening says what this is about.\n\n"
        + ("filler line\n" * 600)
        + BODY_FAR_IN
    )


def _fill_drawer_for(items) -> None:
    vector_drawer.fill([i.content for i in items], encode_many=_fake_encode_many)


# --------------------------------------------------------------------------------- the loader


def test_the_loader_returns_each_registered_file_labelled_with_whose_it_is(tmp_path, monkeypatch):
    _registered_folder(tmp_path, "hers", "aria", {"a.md": _long_file("Her dream")})
    _registered_folder(tmp_path, "ours", "shared", {"b.md": _long_file("A shared night")})
    import divineos.core.sibling_audit_rounds as seats

    monkeypatch.setattr(seats, "this_seat", lambda: "aether")
    monkeypatch.setattr(vector_drawer, "_bulk_encoder", lambda: _fake_encode_many)
    monkeypatch.setattr(v1, "_embed_text_impl", lambda _t: np.ones(4, dtype=np.float32))

    items = {i.title.split(" (")[0]: i for i in v1._load_writing()}

    assert set(items) == {"Her dream", "A shared night"}
    assert all(i.source == "writing" for i in items.values())
    assert "aria's" in items["Her dream"].title and LABEL in items["Her dream"].title
    assert (
        "shared's" in items["A shared night"].title and LABEL not in items["A shared night"].title
    )


def test_the_embedded_text_is_the_opening_and_not_the_whole_file(tmp_path, monkeypatch):
    _registered_folder(tmp_path, "ours", "shared", {"b.md": _long_file("A shared night")})
    monkeypatch.setattr(v1, "_embed_text_impl", lambda _t: np.ones(4, dtype=np.float32))

    (item,) = v1._load_writing()

    assert "The opening says what this is about" in item.content
    assert BODY_FAR_IN not in item.content


def test_a_never_folder_is_not_loaded_and_says_nothing_about_its_files(tmp_path, monkeypatch):
    folder = tmp_path / "private"
    folder.mkdir()
    (folder / "x.md").write_text("# private\n\nnot for the link", encoding="utf-8")
    reg.register_folder(
        tmp_path / "registry" / "folders.jsonl",
        folder,
        whose="aether",
        kind="room",
        visibility="never",
        reason="a private room",
    )
    monkeypatch.setattr(v1, "_embed_text_impl", lambda _t: np.ones(4, dtype=np.float32))

    assert v1._load_writing() == []


# --------------------------------------------------------------------- pin two: no body, ever


def test_an_arrival_shows_the_pointer_and_never_the_body():
    kind, shown, path = v1._shape_content("writing", _long_file("A night"), "/shared/night.md")

    assert path == "/shared/night.md"
    assert BODY_FAR_IN not in shown
    assert "filler line" not in shown
    assert "The opening says" not in shown


def test_a_retrieved_writing_payload_carries_the_title_and_pointer_and_no_body():
    item = _item("f1:night", 0.0, content=_long_file("A night"), path="/shared/night.md")
    item = _CachedItem(**{**item.__dict__, "title": "A night (shared's, at /shared/night.md)"})
    distractors = [_item(f"d{i}", 40 + i * 25) for i in range(8)]
    v2._inject_test_cache({"writing": [item, *distractors]})
    out = {p.id: p for p in _retrieve_at_zero("a night we spent making up a place")}

    payload = out["f1:night"]
    assert "shared's" in payload.title
    assert payload.path_or_ref == "/shared/night.md"
    assert BODY_FAR_IN not in payload.content
    assert "filler line" not in payload.content


def _retrieve_at_zero(prompt: str):
    import pytest as _pt

    mp = _pt.MonkeyPatch()
    try:
        mp.setattr(v2, "synthesize_topic", lambda p, r: "topic")
        mp.setattr(v2, "_embed_topic", lambda t: _unit(0.0))
        return v2.retrieve_v2(prompt)
    finally:
        mp.undo()


# --------------------------------------------------------- pin three: one item per folder per turn


def test_one_item_per_folder_per_turn_so_one_big_folder_cannot_take_every_slot():
    same_folder = [_item(f"f1:dream{i}", 0.0, content=f"dream {i}") for i in range(4)]
    other = _item("f2:the-walk", 0.0, content="the walk")
    distractors = [_item(f"d{i}", 40 + i * 25) for i in range(8)]
    v2._inject_test_cache({"writing": [*same_folder, other, *distractors]})

    ids = [p.id for p in _retrieve_at_zero("a night we spent making up a place")]

    assert sum(1 for i in ids if i.startswith("f1:")) == 1, "one item per folder per turn"
    assert "f2:the-walk" in ids, "control: another folder's file at the same distance still arrives"


# ------------------------------------------- pin four: a vector exists before the reply that needs it


def test_warm_embeds_the_writing_lanes_texts_so_the_first_reply_finds_a_vector(
    tmp_path, monkeypatch
):
    _registered_folder(tmp_path, "ours", "shared", {"b.md": _long_file("A shared night")})
    for name in (
        "_load_corrections",
        "_load_knowledge",
        "_load_wall",
        "_load_exploration",
        "_load_letters",
        "_load_worklist",
        "_load_moments",
    ):
        monkeypatch.setattr(v1, name, list)
    monkeypatch.setattr(vector_drawer, "_bulk_encoder", lambda: _fake_encode_many)

    out = v1.warm()

    assert out["computed"] >= 1, "warm must have embedded the registered file's opening"
    (item,) = v1._load_writing()
    assert item.embedding is not None, (
        "the loader finds a stored vector for the opening, none missing"
    )
    assert v1.lane_state()["missing"] == 0
