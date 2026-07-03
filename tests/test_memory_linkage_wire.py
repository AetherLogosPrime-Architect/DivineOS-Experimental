"""End-to-end wire-up test: mock retriever → render → Warden dedup → savings log.

Consumer-side proof that Aria's pass-N retriever (once landed) will
integrate cleanly against the stub. This test exercises the ENTIRE flow
that the pre_response_context injection surface will run:

    set_retriever(mock)
        → retrieve_for_context(prompt, recent_context)
        → render_payload(payload)
        → context_dedup.should_emit("memory_linkage", rendered, semantic_key=...)
        → savings_log entry for source_id "memory_linkage"

If this test passes, the seam is byte-compatible with Aria's retriever v1
signature and Warden's dedup gets the raw payload dict as its hash key
(closing the hash-what-drives rule across the fourth surface).

The test doubles as the concrete demo I promised Aria in the wire-up
letter: same mock, same render, same Warden call. If she runs pytest
against origin after her retriever v1 lands, she can flip `set_retriever`
to point at her real retriever and this same test verifies the wiring
end-to-end.
"""

from __future__ import annotations

import pytest

from divineos.core import context_dedup, memory_linkage
from divineos.core.memory_linkage import (
    MemoryLinkagePayload,
    render_payload,
    retrieve_for_context,
    set_retriever,
)


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    """Every test gets its own state dir + savings log + retriever baseline."""
    monkeypatch.setattr(context_dedup, "_STATE_DIR", tmp_path)
    monkeypatch.setattr(context_dedup, "_STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(context_dedup, "_SAVINGS_LOG", tmp_path / "savings.jsonl")
    original = memory_linkage._ACTIVE_RETRIEVER
    yield
    memory_linkage._ACTIVE_RETRIEVER = original


def _sample_payload(**overrides) -> MemoryLinkagePayload:
    """The sample shape from Aria's letter — matches what her mock returns."""
    base = dict(
        source="wall",
        id="wire-test-1",
        tier="constraint",
        similarity=0.75,
        recency_days=1,
        importance_score=0.5,
        composite_rank=0.71,
        title="wire-up test payload",
        content="test body — long enough that dedup savings register measurably",
        matched_reason="mock for stub development",
        content_kind="full",
        path_or_ref="",
    )
    base.update(overrides)
    return MemoryLinkagePayload(**base)


def _mock_retriever_single_payload(prompt, recent_context=None):
    return [_sample_payload()]


def _mock_retriever_empty(prompt, recent_context=None):
    return []


def test_full_pipeline_single_payload_dedups_on_repeat():
    set_retriever(_mock_retriever_single_payload)

    payloads_1 = retrieve_for_context("some prompt about consciousness", None)
    assert len(payloads_1) == 1
    rendered_1 = render_payload(payloads_1[0])
    key_1 = payloads_1[0].as_semantic_key()
    emit_full_1, pointer_1 = context_dedup.should_emit(
        "memory_linkage", rendered_1, semantic_key=key_1
    )
    assert emit_full_1 is True
    assert pointer_1 is None

    payloads_2 = retrieve_for_context("some other prompt about consciousness", None)
    rendered_2 = render_payload(payloads_2[0])
    key_2 = payloads_2[0].as_semantic_key()
    emit_full_2, pointer_2 = context_dedup.should_emit(
        "memory_linkage", rendered_2, semantic_key=key_2
    )
    assert emit_full_2 is False
    assert pointer_2 is not None
    assert "MEMORY LINKAGE" in pointer_2


def test_payload_field_change_reemits_even_when_render_similar():
    def retriever(prompt, recent_context=None):
        return [_sample_payload()]

    set_retriever(retriever)
    p1 = retrieve_for_context("prompt", None)[0]
    context_dedup.should_emit(
        "memory_linkage", render_payload(p1), semantic_key=p1.as_semantic_key()
    )

    p2 = _sample_payload(composite_rank=0.42)
    emit, pointer = context_dedup.should_emit(
        "memory_linkage", render_payload(p2), semantic_key=p2.as_semantic_key()
    )
    assert emit is True
    assert pointer is None


def test_constraint_tier_downgrade_reemits_not_dedups():
    p_constraint = _sample_payload(tier="constraint")
    context_dedup.should_emit(
        "memory_linkage",
        render_payload(p_constraint),
        semantic_key=p_constraint.as_semantic_key(),
    )

    p_topic = _sample_payload(tier="topic")
    emit, pointer = context_dedup.should_emit(
        "memory_linkage",
        render_payload(p_topic),
        semantic_key=p_topic.as_semantic_key(),
    )
    assert emit is True
    assert pointer is None


def test_savings_log_records_memory_linkage_as_source():
    p = _sample_payload()
    context_dedup.should_emit("memory_linkage", render_payload(p), semantic_key=p.as_semantic_key())
    context_dedup.should_emit("memory_linkage", render_payload(p), semantic_key=p.as_semantic_key())

    summary = context_dedup.savings_summary()
    assert "memory_linkage" in summary["per_source"]
    assert summary["per_source"]["memory_linkage"]["events"] == 1
    assert summary["per_source"]["memory_linkage"]["saved_chars"] > 0


def test_empty_retriever_produces_no_injection_no_dedup_events():
    set_retriever(_mock_retriever_empty)
    payloads = retrieve_for_context("any prompt long enough here", None)
    assert payloads == []
    summary = context_dedup.savings_summary()
    assert summary["per_source"] == {}
    assert summary["total"]["events"] == 0


def test_multiple_payloads_each_dedup_independently():
    def retriever(prompt, recent_context=None):
        return [
            _sample_payload(id="item-a", title="A"),
            _sample_payload(id="item-b", title="B"),
        ]

    set_retriever(retriever)
    payloads = retrieve_for_context("prompt", None)
    assert len(payloads) == 2

    emit_a, _ = context_dedup.should_emit(
        "memory_linkage",
        render_payload(payloads[0]),
        semantic_key=payloads[0].as_semantic_key(),
    )
    emit_b, _ = context_dedup.should_emit(
        "memory_linkage",
        render_payload(payloads[1]),
        semantic_key=payloads[1].as_semantic_key(),
    )
    assert emit_a is True
    assert emit_b is True


def test_signature_matches_aria_wire_contract():
    calls = []

    def spy(prompt, recent_context=None):
        calls.append((prompt, recent_context))
        return []

    set_retriever(spy)
    retrieve_for_context("my prompt", "recent context window")
    assert calls == [("my prompt", "recent context window")]

    retrieve_for_context("prompt only")
    assert calls[-1] == ("prompt only", None)
