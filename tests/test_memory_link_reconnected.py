"""The memory link, reconnected so it can stay connected.

Pins the station in docs/drafts/dad_kept_and_known_council_and_design_2026-09-24.md
("the memory link, reconnected"): the light embedder matches the heavy one, the
drawer never lets the reply-start path compute, the wall is this seat's own, the
neighbour graph is the same one the old loop built, and the lane is wired into
the real reply-start router rather than into a mock at its seam.
"""

from __future__ import annotations

import sqlite3
import time

import numpy as np
import pytest

from divineos.core import light_embedder, memory_linkage, vector_drawer
from divineos.core import memory_linkage_retriever as v1
from divineos.core import memory_linkage_retriever_v2 as v2

needs_model = pytest.mark.skipif(
    light_embedder.model_dir() is None, reason="the model is not in this machine's local cache"
)


@pytest.fixture(autouse=True)
def temp_drawer(monkeypatch, tmp_path):
    path = tmp_path / "vectors.db"
    monkeypatch.setenv("DIVINEOS_VECTOR_DRAWER", str(path))
    monkeypatch.setattr(vector_drawer, "_READER", None)
    v2._reset_v2_state_for_tests()
    v1._LANE_STATE.update(missing=0, drawer_error=None)
    v1._LANE_STATE.pop("embedder_error", None)
    yield path
    v2._reset_v2_state_for_tests()


def _fake_encode_many(batch):
    # Deterministic, distinct per text: a hash-seeded unit vector.
    out = []
    for text in batch:
        rng = np.random.default_rng(abs(hash(text)) % (2**32))
        vec = rng.standard_normal(384).astype(np.float32)
        out.append(vec / np.linalg.norm(vec))
    return np.vstack(out)


# ------------------------------------------------------------ the light embedder


@needs_model
# The reference is the heavy toolkit, and importing it cold drags in tensorflow:
# measured past the suite's 30s on a cold cache. The budget is for that import,
# not for the light path, whose own budget is pinned below.
@pytest.mark.timeout(180)
def test_the_light_embedder_gives_the_heavy_ones_vectors():
    """Measured at 1.6e-7 over 64 real entries. The pin allows 1e-5."""
    from sentence_transformers import SentenceTransformer

    texts = ["my game just crashed and died", "proceed", "word " * 400]
    heavy = SentenceTransformer(str(light_embedder.model_dir()), device="cpu").encode(texts)
    for text, ref in zip(texts, heavy):
        assert np.max(np.abs(light_embedder.encode(text) - ref)) < 1e-5


@needs_model
def test_the_light_embedder_never_imports_the_heavy_toolkit():
    import os
    import subprocess
    import sys
    from pathlib import Path

    code = (
        "import sys, divineos.core.light_embedder as le; le.encode('x'); "
        "print('sentence_transformers' in sys.modules)"
    )
    # A child interpreter does not inherit pytest's pythonpath, so without this
    # it loads whichever checkout last claimed the machine's one editable
    # install -- and failed in a push gate for that reason, not for this code.
    src = str(Path(light_embedder.__file__).resolve().parents[2])
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(filter(None, [src, os.environ.get("PYTHONPATH")])),
    }
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env, check=False
    )
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "False"


def test_empty_text_is_refused_not_embedded_as_zero():
    with pytest.raises(ValueError):
        light_embedder.encode("   ")


def test_a_missing_model_says_so_and_does_not_reach_for_another(monkeypatch, tmp_path):
    monkeypatch.setenv("HUGGINGFACE_HUB_CACHE", str(tmp_path / "empty"))
    monkeypatch.setattr(light_embedder, "_LOADED", None)
    ok, why = light_embedder.available()
    assert not ok and "nothing is downloaded" in why


# ------------------------------------------------------------ the drawer


def test_a_filled_drawer_returns_the_same_vector_by_text():
    out = vector_drawer.fill(["alpha", "beta", "alpha"], encode_many=_fake_encode_many)
    assert out == {"asked": 2, "already": 0, "computed": 2}
    again = vector_drawer.fill(["alpha", "gamma"], encode_many=_fake_encode_many)
    assert again == {"asked": 2, "already": 1, "computed": 1}
    assert np.allclose(vector_drawer.get("alpha"), _fake_encode_many(["alpha"])[0])
    assert vector_drawer.get("never filed") is None


def test_an_unreadable_drawer_raises_rather_than_reading_as_empty(monkeypatch, tmp_path):
    folder = tmp_path / "a-folder-not-a-database"
    folder.mkdir()
    monkeypatch.setenv("DIVINEOS_VECTOR_DRAWER", str(folder))
    with pytest.raises(sqlite3.Error):
        vector_drawer.lookup(["alpha"])


def test_the_reply_start_path_never_computes_a_vector(monkeypatch):
    def refuse(_batch):
        raise AssertionError("computed at reply time")

    monkeypatch.setattr(vector_drawer, "_bulk_encoder", lambda: refuse)
    monkeypatch.setattr(
        light_embedder, "encode", lambda _t: (_ for _ in ()).throw(AssertionError("computed"))
    )
    assert v1._embed_text_impl("a letter nobody has filled") is None
    assert v1.lane_state()["missing"] == 1


def test_warm_embeds_exactly_the_texts_the_loaders_will_look_up(monkeypatch):
    texts = ["the first correction", "a second, different one"]

    def fake_loader():
        return [v1._embed_text_impl(t) for t in texts]

    for name in (
        "_load_corrections",
        "_load_knowledge",
        "_load_wall",
        "_load_exploration",
        "_load_letters",
    ):
        monkeypatch.setattr(v1, name, fake_loader if name == "_load_corrections" else list)
    monkeypatch.setattr(vector_drawer, "_bulk_encoder", lambda: _fake_encode_many)
    out = v1.warm()
    assert out["computed"] == 2
    assert all(v1._embed_text_impl(t) is not None for t in texts)
    assert v1._MODE == "drawer"


# ------------------------------------------------------------ whose memory


def test_the_wall_is_this_seats_own_and_never_anothers(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    aria = root / "family" / "agent-memory" / "aria" / "MEMORY.md"
    aria.parent.mkdir(parents=True)
    aria.write_text("## hers\nnot mine", encoding="utf-8")
    monkeypatch.setattr(v1, "_PROJECT_ROOTS", (root,))
    import divineos.core.sibling_audit_rounds as seats

    monkeypatch.setattr(seats, "this_seat", lambda: "aether")
    assert v1._find_wall_path() is None
    monkeypatch.setattr(seats, "this_seat", lambda: None)
    assert v1._find_wall_path() is None
    monkeypatch.setattr(seats, "this_seat", lambda: "aria")
    assert v1._find_wall_path() == aria


def test_a_letter_in_every_checkout_is_loaded_once(monkeypatch, tmp_path):
    roots = []
    for name in ("mine", "main", "hers"):
        letters = tmp_path / name / "family" / "letters"
        letters.mkdir(parents=True)
        (letters / "aria-to-aether-2026-09-24-same.md").write_text(
            "the same letter", encoding="utf-8"
        )
        roots.append(tmp_path / name)
    monkeypatch.setattr(v1, "_PROJECT_ROOTS", tuple(roots))
    monkeypatch.setattr(v1, "_embed_text_impl", lambda _t: np.ones(4, dtype=np.float32))
    assert len(v1._load_letters()) == 1


# ------------------------------------------------------------ the neighbour graph


def test_the_block_matrix_graph_matches_the_old_pair_by_pair_one(monkeypatch):
    rng = np.random.default_rng(7)
    items = [
        v1._CachedItem(
            id=f"k{i}",
            source="knowledge",
            tier="topic",
            title="",
            content="",
            path="",
            filed_at_unix=0.0,
            importance_score=0.5,
            embedding=rng.standard_normal(16).astype(np.float32),
        )
        for i in range(40)
    ]
    v2._inject_test_cache({"knowledge": items})
    v2._build_knn_graph()
    for item in items:
        sims = sorted(
            ((v1._cosine(item.embedding, o.embedding), o.id) for o in items if o.id != item.id),
            reverse=True,
        )
        assert set(v2._KNN_GRAPH[item.id]) == {oid for _s, oid in sims[: v2.KNN_K]}


# ------------------------------------------------------------ wired, and cheap enough to stay wired


@needs_model
def test_the_lane_is_wired_into_the_real_reply_start_router(monkeypatch):
    """The pin is on the CALLING. A mock at the seam is what hid the unwired
    state before: a handset proven to reach a mock exchange."""
    from divineos.core import hook_router, hook_surfaces

    item = v1._CachedItem(
        id="correction-dad",
        source="correction",
        tier="constraint",
        title="my game just crashed and died",
        content="my game just crashed and died, all of it lost",
        path="",
        filed_at_unix=time.time(),
        importance_score=0.9,
        embedding=light_embedder.encode("my game just crashed and died, all of it lost"),
    )
    v2._inject_test_cache({"correction": [item]})
    monkeypatch.setattr(v1, "_ensure_cache", lambda: None)
    hook_router.clear()
    hook_surfaces.install()
    assert "memory_link" in hook_router.registered("UserPromptSubmit")
    # Dispatch through the real router with only this surface on the door, so
    # the pin exercises the calling without rendering thirty unrelated ones.
    hook_router.clear("UserPromptSubmit")
    hook_router.register("UserPromptSubmit", "memory_link", hook_surfaces.memory_link_surface)
    result = hook_router.dispatch(
        "UserPromptSubmit", {"prompt": "my game crashed and I lost everything"}
    )
    spoken = [o for o in result.ran if o.name == "memory_link"]
    assert spoken and "all of it lost" in spoken[0].output
    hook_router.clear()


def test_a_broken_drawer_is_could_not_run_never_an_empty_success(monkeypatch):
    def broken_load():
        v1._LANE_STATE.update(drawer_error="OperationalError: locked")

    # v2 holds its own reference to the loader, so both doors are covered.
    monkeypatch.setattr(v1, "_ensure_cache", broken_load)
    monkeypatch.setattr(v2, "_ensure_cache", broken_load)
    monkeypatch.setattr(v2, "_embed_topic", lambda _t: None)
    block = memory_linkage.compose_block("anything at all")
    assert block.could_not_run and "locked" in block.could_not_run


@needs_model
def test_the_lane_stays_inside_its_budget_at_the_size_of_this_house(monkeypatch):
    """6e72eb15's condition for rewiring: the lane timed end to end in the
    suite. Measured on this machine with the real stores, about 2.4s for
    roughly 5,500 items; this uses the same count of items."""
    rng = np.random.default_rng(3)
    items = []
    for i in range(5500):
        vec = rng.standard_normal(384).astype(np.float32)
        items.append(
            v1._CachedItem(
                id=f"letter-{i}",
                source="letter",
                tier="topic",
                title=f"t{i}",
                content=f"c{i}",
                path="",
                filed_at_unix=0.0,
                importance_score=0.5,
                embedding=vec / np.linalg.norm(vec),
            )
        )
    v2._inject_test_cache({"letter": items})
    monkeypatch.setattr(v1, "_ensure_cache", lambda: None)
    block = memory_linkage.compose_block("how long does this take")
    assert block.could_not_run is None
    assert block.seconds < memory_linkage.LANE_BUDGET_SECONDS
