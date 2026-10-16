"""`divineos linkage why`: a read-only window onto one turn's scoring."""

from __future__ import annotations

import math
import time

import numpy as np
import pytest
from click.testing import CliRunner

from divineos.core import light_embedder
from divineos.core import memory_linkage_retriever_v2 as v2
from divineos.core.memory_linkage_retriever import _CachedItem


def _unit(angle_deg: float) -> np.ndarray:
    a = math.radians(angle_deg)
    return np.array([math.cos(a), math.sin(a)], dtype=float)


def _item(item_id: str, angle_deg: float, content: str = "a chunk about one thing") -> _CachedItem:
    return _CachedItem(
        id=item_id,
        source="knowledge",  # type: ignore[arg-type]
        tier="topic",  # type: ignore[arg-type]
        title=f"item {item_id}",
        content=content,
        path="",
        filed_at_unix=time.time() - 86400,
        importance_score=0.5,
        embedding=_unit(angle_deg),
    )


@pytest.fixture(autouse=True)
def _fresh_state():
    v2._reset_v2_state_for_tests()
    yield
    v2._reset_v2_state_for_tests()


def _turn_at(monkeypatch, angle_deg: float) -> None:
    monkeypatch.setattr(v2, "_embed_topic", lambda _topic: _unit(angle_deg))


def test_the_closest_items_pass_and_the_nearest_below_the_bar_are_shown(monkeypatch):
    v2._inject_test_cache({"knowledge": [_item(f"i{n}", n * 20) for n in range(10)]})
    _turn_at(monkeypatch, 0)
    (entry,) = v2.explain_turn("words of a turn", near_misses=2)
    rows = entry["rows"]
    sims = [r["similarity"] for r in rows]
    assert entry["source"] == "knowledge" and entry["items"] == 10
    assert rows[0]["id"] == "i0" and rows[0]["passed"] is True
    passers = [r for r in rows if r["passed"]]
    misses = [r for r in rows if not r["passed"]]
    assert passers and len(misses) == 2
    assert sims[: len(passers)] == sorted(sims[: len(passers)], reverse=True)
    assert all(m["similarity"] < entry["bar"] for m in misses)


def test_each_row_carries_the_numbers_the_retriever_used_and_the_chunk_it_compared(monkeypatch):
    v2._inject_test_cache({"knowledge": [_item("a", 0, "first line here\nsecond line")]})
    _turn_at(monkeypatch, 0)
    (entry,) = v2.explain_turn("x")
    row = entry["rows"][0]
    assert set(row) == {
        "id",
        "title",
        "similarity",
        "passed",
        "importance",
        "recency_days",
        "rank",
        "chunk_chars",
        "first_line",
    }
    assert row["first_line"] == "first line here" and row["chunk_chars"] == len(
        "first line here\nsecond line"
    )
    assert row["importance"] == 0.5


def test_asking_why_never_changes_the_priming_state_or_what_arrives_next(monkeypatch):
    v2._inject_test_cache({"knowledge": [_item(f"i{n}", n * 20) for n in range(10)]})
    _turn_at(monkeypatch, 0)
    v2._PRIMED_STATE["i3"] = (time.time(), "i0")
    before = dict(v2._PRIMED_STATE)
    v2.explain_turn("words of a turn")
    assert v2._PRIMED_STATE == before
    # and a real turn, run after a window, primes exactly what it would have without one
    v2._PRIMED_STATE.clear()
    v2.explain_turn("words of a turn")
    assert v2._PRIMED_STATE == {}


def test_empty_words_score_nothing():
    v2._inject_test_cache({"knowledge": [_item("a", 0)]})
    assert v2.explain_turn("") == []


def test_an_embedder_that_cannot_run_is_an_error_never_an_empty_table(monkeypatch):
    v2._inject_test_cache({"knowledge": [_item("a", 0)]})
    monkeypatch.setattr(v2, "_embed_topic", lambda _topic: None)
    with pytest.raises(RuntimeError, match="nothing was scored"):
        v2.explain_turn("words of a turn")


def test_the_command_refuses_loudly_when_the_embedder_cannot_run(monkeypatch):
    from divineos.cli import cli

    monkeypatch.setattr(light_embedder, "available", lambda: (False, "no model here"))
    result = CliRunner().invoke(cli, ["linkage", "why", "some", "words"])
    assert result.exit_code != 0 and "cannot run: no model here" in result.output
