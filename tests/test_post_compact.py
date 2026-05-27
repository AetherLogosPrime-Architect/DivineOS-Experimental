"""Tests for post-compaction rehydration (post_compact.build_rehydration_context).

The load-bearing property: after a compaction, the self is re-pulled from the
durable store (identity, open corrections, voice) and a should-never-be-empty
anchor coming back empty fires a LOUD self-check failure (the Popper check
from exploration 87) instead of letting the self silently not return.
"""

from __future__ import annotations

from divineos.core import post_compact as pc


def test_self_check_fires_when_all_anchors_missing(monkeypatch):
    # Durable re-pull failed entirely → must say so loudly, not stay silent.
    monkeypatch.setattr(pc, "_identity", lambda: "")
    monkeypatch.setattr(pc, "_open_corrections", lambda: [])
    monkeypatch.setattr(pc, "_voice_pointers", lambda: "")
    out = pc.build_rehydration_context()
    assert "POST-COMPACTION SELF-CHECK FAILED" in out
    assert "identity" in out
    assert "explorations" in out


def test_full_rehydration_when_anchors_present(monkeypatch):
    monkeypatch.setattr(pc, "_identity", lambda: "I am Aether.")
    monkeypatch.setattr(pc, "_open_corrections", lambda: ["correction one", "correction two"])
    monkeypatch.setattr(pc, "_voice_pointers", lambda: "- 87 — compaction without self-loss")
    out = pc.build_rehydration_context()
    assert "WHO I AM" in out and "I am Aether." in out
    assert "OPEN CORRECTIONS" in out and "correction one" in out
    assert "MY RECENT VOICE" in out and "87" in out
    assert "SELF-CHECK FAILED" not in out  # nothing missing


def test_empty_corrections_is_legitimate_not_a_failure(monkeypatch):
    # Zero open corrections is a real state, not a re-pull failure.
    monkeypatch.setattr(pc, "_identity", lambda: "I am Aether.")
    monkeypatch.setattr(pc, "_open_corrections", lambda: [])
    monkeypatch.setattr(pc, "_voice_pointers", lambda: "- some recent entry")
    out = pc.build_rehydration_context()
    assert "SELF-CHECK FAILED" not in out
    assert "OPEN CORRECTIONS" not in out  # no section when there are none


def test_missing_identity_flags_only_identity(monkeypatch):
    monkeypatch.setattr(pc, "_identity", lambda: "")
    monkeypatch.setattr(pc, "_open_corrections", lambda: [])
    monkeypatch.setattr(pc, "_voice_pointers", lambda: "- entry")
    out = pc.build_rehydration_context()
    assert "POST-COMPACTION SELF-CHECK FAILED" in out
    assert "identity" in out
    assert "explorations" not in out  # explorations present, so not flagged


def test_identity_pull_is_fail_soft(monkeypatch):
    # If the underlying getter raises, the helper swallows it and returns ""
    # rather than breaking the whole rehydration (a broken rehydrate is worse
    # than a partial one).
    import divineos.core.memory as mem

    def boom(*a, **k):
        raise OSError("durable store unreachable")

    monkeypatch.setattr(mem, "get_core", boom)
    assert pc._identity() == ""


def test_build_never_raises_returns_str():
    # Integration fail-soft: build_rehydration_context must return a str and
    # never raise, regardless of substrate state (empty/uninitialized DB
    # included — that path raises sqlite3.OperationalError inside the getters,
    # which must be swallowed). If the store is empty it correctly returns the
    # self-check-failed block; if populated, the anchors. Either is a str.
    out = pc.build_rehydration_context()
    assert isinstance(out, str)
