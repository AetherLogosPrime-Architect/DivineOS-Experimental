"""A writing item arrives with its title, not blank.

Found live 2026-11-23: the first writing item to reach a real reply of mine printed as ``[writing, 0.58]  (path)``
with nothing between, because the pointer shape returns an empty body and the surface prints the body. The title
(whose it is, and the think-with label for the other seat's) is what the arrival is, so it is the shown text.
It is still never any of the file's body.
"""

from __future__ import annotations

import math
import time

import numpy as np
import pytest

from divineos.core import memory_linkage_retriever_v2 as v2
from divineos.core import vector_drawer
from divineos.core.memory_linkage_retriever import _CachedItem

BODY = "the small one climbed onto the third chair and said home"


def _unit(angle: float) -> np.ndarray:
    a = math.radians(angle)
    return np.array([math.cos(a), math.sin(a)], dtype=float)


def _writing_item(item_id: str, angle: float) -> _CachedItem:
    return _CachedItem(
        id=item_id,
        source="writing",  # type: ignore[arg-type]
        tier="topic",  # type: ignore[arg-type]
        title="The two lamps (aria's, at /shared/13_the_two_lamps.md)",
        content="# The two lamps\n\nThe opening line.\n" + ("filler\n" * 400) + BODY,
        path="/shared/13_the_two_lamps.md",
        filed_at_unix=time.time() - 86400,
        importance_score=0.5,
        embedding=_unit(angle),
    )


@pytest.fixture(autouse=True)
def _state(monkeypatch, tmp_path):
    monkeypatch.setenv("DIVINEOS_VECTOR_DRAWER", str(tmp_path / "vectors.db"))
    monkeypatch.setattr(vector_drawer, "_READER", None)
    v2._reset_v2_state_for_tests()
    yield
    v2._reset_v2_state_for_tests()


def _retrieve_at_zero(monkeypatch, fn):
    monkeypatch.setattr(v2, "synthesize_topic", lambda p, r: "topic")
    monkeypatch.setattr(v2, "_embed_topic", lambda t: _unit(0.0))
    return fn("a night we spent making up a place")


def test_the_main_lane_shows_the_title_and_no_body(monkeypatch):
    distractors = [_writing_item(f"d{i}:x", 40 + i * 25) for i in range(8)]
    v2._inject_test_cache({"writing": [_writing_item("f1:lamps", 0.0), *distractors]})
    out = {p.id: p for p in _retrieve_at_zero(monkeypatch, v2.retrieve_v2)}
    shown = out["f1:lamps"].content
    assert shown.strip(), "an arrival with no words in front of it is the defect"
    assert "The two lamps" in shown and "aria's" in shown
    assert BODY not in shown and "filler" not in shown


def test_the_regulatory_lane_shows_the_title_too(monkeypatch):
    distractors = [_writing_item(f"d{i}:x", 40 + i * 25) for i in range(8)]
    v2._inject_test_cache({"writing": [_writing_item("f1:lamps", 0.0), *distractors]})
    out = {p.id: p for p in _retrieve_at_zero(monkeypatch, v2.retrieve_similarity_only)}
    assert "The two lamps" in out["f1:lamps"].content
    assert BODY not in out["f1:lamps"].content


def test_a_source_that_shows_a_body_is_unchanged(monkeypatch):
    """Control: the title-as-shown rule is for the pointer shape only; a letter still shows its snippet."""
    letter = _CachedItem(
        id="letter-x",
        source="letter",  # type: ignore[arg-type]
        tier="topic",  # type: ignore[arg-type]
        title="a letter title",
        content="the letter opening words go here and keep going",
        path="family/letters/x.md",
        filed_at_unix=time.time() - 86400,
        importance_score=0.5,
        embedding=_unit(0.0),
    )
    distractors = [_writing_item(f"d{i}:x", 40 + i * 25) for i in range(8)]
    v2._inject_test_cache({"letter": [letter, *distractors]})
    out = {p.id: p for p in _retrieve_at_zero(monkeypatch, v2.retrieve_v2)}
    assert "the letter opening words" in out["letter-x"].content
