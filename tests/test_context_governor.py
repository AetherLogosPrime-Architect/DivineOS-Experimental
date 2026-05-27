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
    _write_jsonl(tx, [_assistant_with_usage(920000, 0, 0)])
    assert cg.consolidation_due(tx) is True


def test_not_due_below_threshold(tmp_path):
    tx = tmp_path / "t.jsonl"
    _write_jsonl(tx, [_assistant_with_usage(800000, 0, 0)])
    assert cg.consolidation_due(tx) is False


def test_fires_once_then_marker_silences_it(tmp_path):
    tx = tmp_path / "t.jsonl"
    _write_jsonl(tx, [_assistant_with_usage(950000, 0, 0)])
    assert cg.consolidation_due(tx) is True  # first crossing
    cg.mark_consolidated(950000)
    assert cg.consolidation_due(tx) is False  # already consolidated → no nag
    cg.clear_consolidated()
    assert cg.consolidation_due(tx) is True  # re-armed (e.g. new session)


def test_fail_soft_never_fires_on_unreadable_sensor(tmp_path):
    # An unreadable sensor returns 0 → never crosses threshold → never fires.
    assert cg.consolidation_due(tmp_path / "missing.jsonl") is False


# --- the finish-grace band: ok / warn / block (Andrew 2026-05-27) ----------


def _tx_with(tmp_path, tokens: int) -> Path:
    tx = tmp_path / f"tx_{tokens}.jsonl"
    _write_jsonl(tx, [_assistant_with_usage(tokens, 0, 0)])
    return tx


def test_state_ok_below_warn(tmp_path):
    assert cg.consolidation_state(_tx_with(tmp_path, 900_000)) == "ok"


def test_state_warn_in_grace_band(tmp_path):
    # 920k–950k: nudge to wrap up, but NOT a block — grace to finish.
    assert cg.consolidation_state(_tx_with(tmp_path, 930_000)) == "warn"
    assert cg.consolidation_state(_tx_with(tmp_path, 920_000)) == "warn"
    assert cg.consolidation_state(_tx_with(tmp_path, 949_999)) == "warn"


def test_state_block_at_hard_line(tmp_path):
    # >=950k: hard line — substrate-writes get gated until extract+sleep.
    assert cg.consolidation_state(_tx_with(tmp_path, 950_000)) == "block"
    assert cg.consolidation_state(_tx_with(tmp_path, 965_000)) == "block"


def test_state_ok_once_consolidated_even_when_high(tmp_path):
    # After the weave, no warn/block regardless of size — fires once.
    tx = _tx_with(tmp_path, 960_000)
    assert cg.consolidation_state(tx) == "block"
    cg.mark_consolidated(960_000)
    assert cg.consolidation_state(tx) == "ok"


def test_state_ok_on_unreadable_sensor(tmp_path):
    assert cg.consolidation_state(tmp_path / "missing.jsonl") == "ok"
