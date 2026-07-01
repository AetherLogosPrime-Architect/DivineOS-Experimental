"""Tests for the Warden-pattern context dedup module.

Lock the invariants: byte-identical content within TTL dedups; any change
re-emits full; TTL-expired repeats re-emit full; clear() resets state.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from divineos.core import context_dedup


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(context_dedup, "_STATE_DIR", tmp_path)
    monkeypatch.setattr(context_dedup, "_STATE_FILE", tmp_path / "state.json")
    yield


def test_first_emit_returns_true_no_pointer():
    emit, pointer = context_dedup.should_emit("active_needs", "hello world")
    assert emit is True
    assert pointer is None


def test_identical_repeat_returns_pointer():
    context_dedup.should_emit("active_needs", "hello world")
    emit, pointer = context_dedup.should_emit("active_needs", "hello world")
    assert emit is False
    assert pointer is not None
    assert "ACTIVE NEEDS" in pointer
    assert "unchanged" in pointer


def test_changed_content_reemits():
    context_dedup.should_emit("active_needs", "hello world")
    emit, pointer = context_dedup.should_emit("active_needs", "hello world v2")
    assert emit is True
    assert pointer is None


def test_different_source_ids_dont_collide():
    context_dedup.should_emit("active_needs", "same text")
    emit, pointer = context_dedup.should_emit("lepos_walk", "same text")
    assert emit is True
    assert pointer is None


def test_empty_content_always_emits():
    emit, _ = context_dedup.should_emit("x", "")
    assert emit is True
    emit, _ = context_dedup.should_emit("x", "   \n  ")
    assert emit is True


def test_ttl_expiry_reemits():
    context_dedup.should_emit("s", "content")
    import json

    state_path: Path = context_dedup._STATE_FILE
    state = json.loads(state_path.read_text())
    state["s"]["ts"] = int(time.time()) - context_dedup._TTL_SECONDS - 10
    state_path.write_text(json.dumps(state))
    emit, pointer = context_dedup.should_emit("s", "content")
    assert emit is True
    assert pointer is None


def test_clear_wipes_state():
    context_dedup.should_emit("s", "content")
    context_dedup.clear()
    emit, _ = context_dedup.should_emit("s", "content")
    assert emit is True


def test_clear_without_state_is_noop():
    context_dedup.clear()
    context_dedup.clear()


def test_pointer_is_short_relative_to_content():
    long_content = "line\n" * 500
    context_dedup.should_emit("big_block", long_content)
    _, pointer = context_dedup.should_emit("big_block", long_content)
    assert pointer is not None
    assert len(pointer) < len(long_content) // 10


# --- semantic_key coverage (Aletheia condition, letter #17) ---


def test_semantic_key_identical_dedups():
    key = {"needs": [{"id": "a", "text": "x"}]}
    context_dedup.should_emit("s", "rendered", semantic_key=key)
    emit, pointer = context_dedup.should_emit("s", "rendered", semantic_key=key)
    assert emit is False
    assert pointer is not None


def test_semantic_key_change_reemits_even_when_content_same():
    # The whole point of semantic_key: catch state changes the render omits.
    key1 = {"needs": [{"id": "a", "text": "x", "binds": ["gate1"]}]}
    key2 = {"needs": [{"id": "a", "text": "x", "binds": ["gate2"]}]}
    rendered = "same rendered text ignoring binds field"
    context_dedup.should_emit("s", rendered, semantic_key=key1)
    emit, pointer = context_dedup.should_emit("s", rendered, semantic_key=key2)
    assert emit is True
    assert pointer is None


def test_semantic_key_dict_ordering_stable():
    # Same dict, keys in different insertion order — must dedup.
    key1 = {"a": 1, "b": 2}
    key2 = {"b": 2, "a": 1}
    context_dedup.should_emit("s", "x", semantic_key=key1)
    emit, _ = context_dedup.should_emit("s", "x", semantic_key=key2)
    assert emit is False


def test_semantic_key_falls_back_on_non_serializable():
    # Non-JSON-serializable objects fall back to content hashing rather
    # than raising — fail-open observability boundary.
    class Weird:
        pass

    emit, _ = context_dedup.should_emit("s", "content", semantic_key=Weird())
    assert emit is True
    emit, _ = context_dedup.should_emit("s", "content", semantic_key=Weird())
    # Second call: fallback used content hash on same content, dedups.
    assert emit is False
