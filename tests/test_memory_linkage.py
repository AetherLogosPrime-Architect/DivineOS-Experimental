"""Tests for the memory-linkage injection surface (consumer side).

Locks the invariants that the retriever side (Aria) will land against:
- Payload dict shape stays stable (§3 workbench contract)
- Semantic-key material catches tier / reason / rank / content changes
  (Aletheia's hash-what-drives rule, load-bearing across four surfaces now)
- Mock retriever is the default and returns empty (safe stub state)
- set_retriever seam works so the retriever module can rebind at import
"""

from __future__ import annotations

import pytest

from divineos.core import memory_linkage
from divineos.core.memory_linkage import (
    MemoryLinkagePayload,
    render_payload,
    retrieve_for_context,
    set_retriever,
)


@pytest.fixture(autouse=True)
def _restore_default_retriever():
    """Every test starts from the mock-retriever baseline."""
    original = memory_linkage._ACTIVE_RETRIEVER
    yield
    memory_linkage._ACTIVE_RETRIEVER = original


def _payload(**overrides) -> MemoryLinkagePayload:
    base = dict(
        source="correction",
        id="test-001",
        tier="constraint",
        similarity=0.87,
        recency_days=3,
        importance_score=0.9,
        composite_rank=0.85,
        title="test-title",
        content="the lesson body",
        matched_reason="test-tag-match",
        content_kind="full",
        path_or_ref="",
    )
    base.update(overrides)
    return MemoryLinkagePayload(**base)


# --- default state (safe stub) ---


def test_default_retriever_returns_empty():
    """Stub state: no injection until Aria's retriever binds."""
    assert retrieve_for_context("any prompt at all here", None) == []


def test_empty_prompt_returns_empty():
    assert retrieve_for_context("", None) == []


# --- semantic-key material (§3 + §6 contract) ---


def test_semantic_key_includes_tier():
    """Tier is a driver of injection behavior — must be in the hash key."""
    p = _payload(tier="constraint")
    key = p.as_semantic_key()
    assert key["tier"] == "constraint"


def test_semantic_key_changes_when_tier_flips():
    """Tier flip constraint→topic must invalidate hash even if render is
    identical. This is the Q2 anti-erosion property: the retriever
    downweighting a constraint-tier item to topic must not silently
    collapse to a pointer on Warden's side."""
    a = _payload(tier="constraint").as_semantic_key()
    b = _payload(tier="topic").as_semantic_key()
    assert a != b


def test_semantic_key_changes_when_matched_reason_changes():
    """Same item, different reason for firing = different injection.
    Warden must re-emit so the reason is visible."""
    a = _payload(matched_reason="reason-a").as_semantic_key()
    b = _payload(matched_reason="reason-b").as_semantic_key()
    assert a != b


def test_semantic_key_changes_when_composite_rank_changes():
    """Rank shift is a state change worth re-emitting."""
    a = _payload(composite_rank=0.85).as_semantic_key()
    b = _payload(composite_rank=0.72).as_semantic_key()
    assert a != b


def test_semantic_key_identical_when_all_fields_identical():
    """The dedup baseline: two identical payloads produce identical keys."""
    a = _payload().as_semantic_key()
    b = _payload().as_semantic_key()
    assert a == b


# --- retriever seam ---


def test_set_retriever_rebinds_module():
    def fake_retriever(prompt, context=None):
        return [_payload(title="from-fake")]

    set_retriever(fake_retriever)
    result = retrieve_for_context("some prompt", None)
    assert len(result) == 1
    assert result[0].title == "from-fake"


def test_retriever_receives_prompt_and_context():
    seen = {}

    def spy(prompt, context=None):
        seen["prompt"] = prompt
        seen["context"] = context
        return []

    set_retriever(spy)
    retrieve_for_context("my prompt", "prior conversation")
    assert seen["prompt"] == "my prompt"
    assert seen["context"] == "prior conversation"


# --- rendering ---


def test_render_full_payload_inlines_content():
    p = _payload(content_kind="full", content="the full body text")
    rendered = render_payload(p)
    assert "the full body text" in rendered
    assert "PRIOR SUBSTRATE" in rendered
    assert "correction" in rendered


def test_render_snippet_includes_path():
    p = _payload(
        content_kind="snippet",
        content="opening lines of the entry",
        path_or_ref="exploration/aether/47_test.md",
    )
    rendered = render_payload(p)
    assert "opening lines of the entry" in rendered
    assert "exploration/aether/47_test.md" in rendered


def test_render_names_tier_and_source():
    p = _payload(source="wall", tier="topic")
    rendered = render_payload(p)
    assert "wall" in rendered
    assert "topic" in rendered


def test_render_shows_matched_reason_and_rank():
    p = _payload(matched_reason="tag-hit: consciousness", composite_rank=0.73)
    rendered = render_payload(p)
    assert "tag-hit: consciousness" in rendered
    assert "0.73" in rendered
