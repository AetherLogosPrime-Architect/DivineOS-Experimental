"""The memory link searches what HE said, not what I was just saying.

2026-10-06, measured on 30 of his real messages from one session, rated blind:
the live query was my last six conversation records with his message appended at
the END. The search model keeps only the first 256 tokens, and those records ran
to a median 643, so in 17 of 25 messages none of his words reached the model.
Results: 8% useful when searching that way, 42% when searching his message alone,
and every useful item the live way found, his message alone found too.

So the query is his message and nothing else. A message too short to search on, or
an automated notice, is not searched and SAYS so (his rule, 2026-10-05: "never have
it show nothing, if its unsure make it say its unsure"), instead of searching
whatever text happened to be nearby.
"""

from __future__ import annotations

import json

import pytest

from divineos.core import memory_linkage

HEAD = "## THE PAST ON THIS (memory link)"


@pytest.fixture
def calls(monkeypatch):
    """Record what the lane asks the retriever, and answer with one real-shaped item."""
    seen: list[tuple[str, str | None]] = []

    def fake(prompt, context=None):
        seen.append((prompt, context))
        return [
            memory_linkage.MemoryLinkagePayload(
                source="correction",
                id="c1",
                tier="constraint",
                similarity=0.62,
                recency_days=3,
                importance_score=0.5,
                composite_rank=0.7,
                title="t",
                content="a teaching of his about the thing he just said",
                matched_reason="r",
                content_kind="correction",
                path_or_ref="",
            )
        ]

    monkeypatch.setattr(memory_linkage, "retrieve_for_context", fake)
    return seen


def _long_transcript(tmp_path):
    """A transcript whose recent turns are long, like mine: the old query put this first."""
    p = tmp_path / "t.jsonl"
    rows = []
    for i in range(6):
        rows.append(
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": f"work chatter number {i} " * 80}],
                },
            }
        )
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return p


def test_the_query_is_his_message_and_nothing_else(calls, tmp_path):
    msg = "why not do a full council walk on it to find ways to improve it"
    block = memory_linkage.compose_block(msg, str(_long_transcript(tmp_path)))
    assert calls == [(msg, None)]  # control: it did search, and with no recent context
    assert "a teaching of his" in block.text  # and what it found reached the block


def test_a_message_too_short_to_search_on_is_not_searched_and_says_so(calls, tmp_path):
    block = memory_linkage.compose_block("ok go", str(_long_transcript(tmp_path)))
    assert calls == []
    assert HEAD in block.text and "too short" in block.text


def test_an_automated_notice_is_not_searched_and_says_so(calls, tmp_path):
    notice = "<task-notification>the background task finished and here is its long summary</task-notification>"
    block = memory_linkage.compose_block(notice, str(_long_transcript(tmp_path)))
    assert calls == []
    assert HEAD in block.text and "automated notice" in block.text


def test_the_boundary_four_words_search_and_three_do_not(calls):
    memory_linkage.compose_block("one two three", None)
    assert calls == []
    memory_linkage.compose_block("one two three four", None)
    assert [c[0] for c in calls] == ["one two three four"]
