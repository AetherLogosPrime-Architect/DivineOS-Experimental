"""Tests for the context-size governor (the live working-memory vital sign +
the once-per-session consolidation trigger).

Load-bearing properties: (1) context size is read from the transcript usage
numbers; (2) consolidation_due fires only when over threshold AND not yet
consolidated this session; (3) it fires once, not every turn past the line
(the nag failure-mode the prereg falsifier names); (4) fail-soft — an
unreadable sensor returns 0 and never fires spuriously.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from divineos.core import context_governor as cg


def _write_jsonl(path: Path, records: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")


def _assistant_with_usage(read: int, creation: int, inp: int) -> dict:
    return {
        "type": "assistant",
        "message": {
            "content": [{"type": "text", "text": "hi"}],
            "usage": {
                "cache_read_input_tokens": read,
                "cache_creation_input_tokens": creation,
                "input_tokens": inp,
            },
        },
    }


@pytest.fixture(autouse=True)
def _isolate_marker(tmp_path, monkeypatch):
    # Point the marker at a temp file so tests never touch the real one.
    marker = tmp_path / "context_consolidated.json"
    monkeypatch.setattr(cg, "_marker_path", lambda: marker)
    yield


def test_current_context_tokens_sums_usage(tmp_path):
    tx = tmp_path / "t.jsonl"
    _write_jsonl(tx, [_assistant_with_usage(764821, 1756, 2)])
    assert cg.current_context_tokens(tx) == 766579


def test_current_context_tokens_uses_latest_record(tmp_path):
    tx = tmp_path / "t.jsonl"
    _write_jsonl(
        tx,
        [
            _assistant_with_usage(100, 0, 0),
            _assistant_with_usage(900000, 1000, 5),  # latest = the one that counts
        ],
    )
    assert cg.current_context_tokens(tx) == 901005


def test_missing_or_empty_transcript_is_zero(tmp_path):
    assert cg.current_context_tokens(tmp_path / "nope.jsonl") == 0
    assert cg.current_context_tokens(None) == 0
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    assert cg.current_context_tokens(empty) == 0


def test_due_fires_over_threshold(tmp_path):
    tx = tmp_path / "t.jsonl"
    _write_jsonl(tx, [_assistant_with_usage(cg.HARD_THRESHOLD, 0, 0)])
    assert cg.consolidation_due(tx) is True


def test_not_due_below_threshold(tmp_path):
    tx = tmp_path / "t.jsonl"
    _write_jsonl(tx, [_assistant_with_usage(800000, 0, 0)])
    assert cg.consolidation_due(tx) is False


def test_not_due_in_old_warn_band(tmp_path):
    # 940k is below the 950k hard line (lowered 2026-06-28 from 970k).
    tx = tmp_path / "t.jsonl"
    _write_jsonl(tx, [_assistant_with_usage(940_000, 0, 0)])
    assert cg.consolidation_due(tx) is False


def test_fires_once_then_marker_silences_it(tmp_path):
    tx = tmp_path / "t.jsonl"
    _write_jsonl(tx, [_assistant_with_usage(980_000, 0, 0)])
    assert cg.consolidation_due(tx) is True  # first crossing
    cg.mark_consolidated(980_000)
    assert cg.consolidation_due(tx) is False  # already consolidated → no nag
    cg.clear_consolidated()
    assert cg.consolidation_due(tx) is True  # re-armed (e.g. new session)


def test_fail_soft_never_fires_on_unreadable_sensor(tmp_path):
    # An unreadable sensor returns 0 → never crosses threshold → never fires.
    assert cg.consolidation_due(tmp_path / "missing.jsonl") is False


# --- two-state read: ok / block (collapsed 2026-06-19 from ok / warn / block)


def _tx_with(tmp_path, tokens: int) -> Path:
    tx = tmp_path / f"tx_{tokens}.jsonl"
    _write_jsonl(tx, [_assistant_with_usage(tokens, 0, 0)])
    return tx


def test_state_ok_below_hard(tmp_path):
    # Everything below HARD_THRESHOLD is quiet. Hard line is 950k (lowered
    # 2026-06-28 from 970k after a compaction landed mid-extract).
    assert cg.consolidation_state(_tx_with(tmp_path, 900_000)) == "ok"
    assert cg.consolidation_state(_tx_with(tmp_path, 940_000)) == "ok"
    assert cg.consolidation_state(_tx_with(tmp_path, cg.HARD_THRESHOLD - 1)) == "ok"


def test_state_block_at_hard_line(tmp_path):
    # >=HARD_THRESHOLD: hard line — substrate-writes get gated until extract.
    assert cg.consolidation_state(_tx_with(tmp_path, cg.HARD_THRESHOLD)) == "block"
    assert cg.consolidation_state(_tx_with(tmp_path, cg.HARD_THRESHOLD + 15_000)) == "block"


def test_state_ok_once_consolidated_even_when_high(tmp_path):
    # After the weave, no warn/block regardless of size — fires once.
    above_hard = cg.HARD_THRESHOLD + 10_000
    tx = _tx_with(tmp_path, above_hard)
    assert cg.consolidation_state(tx) == "block"
    cg.mark_consolidated(above_hard)
    assert cg.consolidation_state(tx) == "ok"


def test_state_ok_on_unreadable_sensor(tmp_path):
    assert cg.consolidation_state(tmp_path / "missing.jsonl") == "ok"


# --- the surfaced text: warn nudge / block channel / ok-silence -------------


def test_governor_context_empty_when_ok(tmp_path):
    assert cg.build_governor_context(_tx_with(tmp_path, 900_000)) == ""


def test_governor_context_empty_in_old_warn_band(tmp_path):
    # Below the 950k hard line is silent.
    assert cg.build_governor_context(_tx_with(tmp_path, 940_000)) == ""
    assert cg.build_governor_context(_tx_with(tmp_path, cg.HARD_THRESHOLD - 1)) == ""


def test_governor_context_block_is_channel_message(tmp_path):
    out = cg.build_governor_context(_tx_with(tmp_path, cg.HARD_THRESHOLD + 5_000))
    # Post-2026-07-15 message uses doorway-not-cliff framing (need
    # 89b507d8) — check for the header markers that carry the block
    # semantics without hardcoding a specific verb like "BLOCKED".
    assert "CONTEXT GOVERNOR" in out
    assert "WEAVE-BEFORE-DOORWAY" in out
    # The channel out is named — never a dead end.
    assert "extract" in out and "sleep" in out


def test_governor_context_silent_once_consolidated(tmp_path):
    above_hard = cg.HARD_THRESHOLD + 10_000
    tx = _tx_with(tmp_path, above_hard)
    cg.mark_consolidated(above_hard)
    assert cg.build_governor_context(tx) == ""


def test_governor_channel_message_names_extract_and_sleep(tmp_path):
    msg = cg.governor_channel_message(_tx_with(tmp_path, cg.HARD_THRESHOLD + 10_000))
    assert "extract" in msg and "sleep" in msg
    # Post-2026-07-15 doorway-not-cliff framing (need 89b507d8).
    assert "CONTEXT GOVERNOR" in msg
    assert "doorway" in msg


def test_governor_context_empty_on_unreadable_sensor(tmp_path):
    assert cg.build_governor_context(tmp_path / "missing.jsonl") == ""


# --- task #119: ceiling is overridable + reflects last-confirmed cliff ------


def test_compaction_ceiling_default_is_current_cliff():
    """Last-confirmed value: 2026-06-09 (Anthropic moved it from 970k).
    If this assertion fails, the cliff drifted again — update the
    literal in context_governor.py and date the comment."""
    assert cg.COMPACTION_CEILING == 999_000


def test_compaction_ceiling_env_override(monkeypatch):
    """A session that observes a drifted cliff can override without code
    change via DIVINEOS_COMPACTION_CEILING."""
    monkeypatch.setenv("DIVINEOS_COMPACTION_CEILING", "1050000")
    assert cg._read_ceiling_override() == 1_050_000


def test_compaction_ceiling_bad_override_falls_through(monkeypatch):
    """Garbage values do not poison the ceiling — silent fall-through."""
    monkeypatch.setenv("DIVINEOS_COMPACTION_CEILING", "not-a-number")
    assert cg._read_ceiling_override() is None
    monkeypatch.setenv("DIVINEOS_COMPACTION_CEILING", "50")  # below 100k floor
    assert cg._read_ceiling_override() is None


def test_block_channel_message_uses_dynamic_ceiling(tmp_path):
    """The block message's cliff number must reflect COMPACTION_CEILING,
    not a hardcoded literal — otherwise a future ceiling-update would
    leave the father-facing instruction stale."""
    msg = cg.governor_channel_message(_tx_with(tmp_path, cg.HARD_THRESHOLD + 5_000))
    assert f"{cg.COMPACTION_CEILING:,}" in msg
