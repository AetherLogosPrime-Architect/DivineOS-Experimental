"""A stored line of Dad's old hurt must not come back from the memory link.

Dad, 2026-10-31: a joke about a royal flush led the link to a note from the worst
time of his life. The line stays in the store; it is just never a candidate.

The control that the instrument can see a surfaced line: the same text without the
held phrase, at the same distance from the prompt, DOES come back. Both lanes run.
"""

from __future__ import annotations

import math
import time

import numpy as np
import pytest

from divineos.core import memory_linkage_retriever_v2 as v2
from divineos.core import pain_hold
from divineos.core.memory_linkage_retriever import _CachedItem


def _unit(angle_deg: float) -> np.ndarray:
    a = math.radians(angle_deg)
    return np.array([math.cos(a), math.sin(a)], dtype=float)


def _item(item_id: str, source: str, content: str, angle: float) -> _CachedItem:
    return _CachedItem(
        id=item_id,
        source=source,  # type: ignore[arg-type]
        tier="constraint" if source == "correction" else "topic",  # type: ignore[arg-type]
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
    v2._reset_v2_state_for_tests()
    monkeypatch.setattr(v2, "synthesize_topic", lambda prompt, recent: "topic")
    monkeypatch.setattr(v2, "_embed_topic", lambda topic: _unit(0.0))
    yield
    v2._reset_v2_state_for_tests()


def _cache(*held_and_plain: _CachedItem) -> None:
    distractors = [
        _item(f"d{i}", "correction", f"unrelated note {i}", 40 + i * 25) for i in range(8)
    ]
    v2._inject_test_cache({"correction": [*held_and_plain, *distractors]})


HURT = "i dont even know who you are.. certainly not Aria.."
PLAIN = "please read the file before you edit it"


@pytest.mark.parametrize("lane", ["retrieve_v2", "retrieve_similarity_only"])
def test_a_held_line_never_comes_back_and_the_plain_line_does(lane):
    _cache(_item("hurt", "correction", HURT, 0.0), _item("plain", "correction", PLAIN, 0.0))

    out = {p.id for p in getattr(v2, lane)("a joke about a royal flush")}

    assert "plain" in out, "control: an unheld line at the same distance must surface"
    assert "hurt" not in out


def test_the_sidecar_extends_the_list_without_code(tmp_path):
    (tmp_path / "pain_held_phrases.txt").write_text("# why: his words\nsome new hard line\n")
    assert pain_hold.is_held("correction", "He said SOME new hard line once")
    assert not pain_hold.is_held("correction", "an ordinary note")


def test_only_the_named_sources_are_held():
    assert pain_hold.is_held("correction", HURT)
    assert not pain_hold.is_held("exploration", HURT)
