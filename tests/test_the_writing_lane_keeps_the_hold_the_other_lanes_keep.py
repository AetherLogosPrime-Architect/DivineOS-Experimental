"""The lane that reads the folders we write in must keep the hurt-words hold the other lanes keep.

Written before the lane exists (2026-11-23, pin one of the adapter tests; Aether's hole one in the
memory walk). The hold in ``pain_hold.is_held`` returns False at once for any source outside
``HELD_SOURCES``, so a new lane's items skip it by default. Dreams, letters, evenings and the walk
quote Dad constantly, and the lane that reads them would hand back through a door the hold was
never built for.

A held line is a synthetic phrase added through the sidecar (the extra-phrases door), never his
real words. The control that the instrument can see a surfaced line: the same lane, the same
distance, an unheld line DOES come back, in both retrieval paths.
"""

from __future__ import annotations

import math
import time

import numpy as np
import pytest

from divineos.core import memory_linkage_retriever_v2 as v2
from divineos.core import pain_hold
from divineos.core.memory_linkage_retriever import _CachedItem

WRITING = "writing"
SYNTHETIC_HELD = "a made up hard line for the writing lane only"
PLAIN = "a quiet evening spent making up a place together"


def _unit(angle_deg: float) -> np.ndarray:
    a = math.radians(angle_deg)
    return np.array([math.cos(a), math.sin(a)], dtype=float)


def _item(item_id: str, content: str, angle: float, source: str = WRITING) -> _CachedItem:
    return _CachedItem(
        id=item_id,
        source=source,  # type: ignore[arg-type]
        tier="topic",  # type: ignore[arg-type]
        title=item_id,
        content=content,
        path="",
        filed_at_unix=time.time() - 86400,
        importance_score=0.5,
        embedding=_unit(angle),
    )


@pytest.fixture(autouse=True)
def _clean(monkeypatch, tmp_path):
    monkeypatch.setenv("DIVINEOS_SHARED_DIR", str(tmp_path))
    (tmp_path / "pain_held_phrases.txt").write_text(
        f"# synthetic, for the test\n{SYNTHETIC_HELD}\n"
    )
    v2._reset_v2_state_for_tests()
    monkeypatch.setattr(v2, "synthesize_topic", lambda prompt, recent: "topic")
    monkeypatch.setattr(v2, "_embed_topic", lambda topic: _unit(0.0))
    yield
    v2._reset_v2_state_for_tests()


def _cache(*writing_items: _CachedItem) -> None:
    distractors = [_item(f"d{i}", f"an unrelated file {i}", 40 + i * 25) for i in range(8)]
    v2._inject_test_cache({WRITING: [*writing_items, *distractors]})


def test_the_writing_source_is_a_held_source():
    assert WRITING in pain_hold.HELD_SOURCES


def test_the_synthetic_phrase_is_held_for_the_writing_source_and_only_through_the_sidecar():
    assert pain_hold.is_held(WRITING, f"he said {SYNTHETIC_HELD} once")
    assert not pain_hold.is_held(WRITING, PLAIN)


@pytest.mark.parametrize("lane", ["retrieve_v2", "retrieve_similarity_only"])
def test_a_held_line_in_a_writing_file_never_comes_back_and_the_plain_one_does(lane):
    _cache(_item("held", SYNTHETIC_HELD, 0.0), _item("plain", PLAIN, 0.0))

    out = {p.id for p in getattr(v2, lane)("a night we spent making up a place")}

    assert "plain" in out, "control: an unheld writing file at the same distance must surface"
    assert "held" not in out
