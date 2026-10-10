"""When the gate hands over a whole file, its message stops arguing.

Aria, 2026-10-10: the refusal pasted the file AND a long closing speech ending
"So open it", so the file was read twice, once inline and once by a Read call.
Delivery in full is the read (Andrew 2026-08-17), so the closing must say that
and stop. A file too long to inline still gets the open-it demand: the pair is
the point, since "short" alone is satisfied by a gate that never asks.
"""

from __future__ import annotations

import pytest

from divineos.core import read_gate


@pytest.fixture
def isolated_gate(tmp_path, monkeypatch):
    monkeypatch.setattr(read_gate, "STATE_DIR", tmp_path)
    monkeypatch.setattr(read_gate, "STATE_FILE", tmp_path / "pending.json")
    monkeypatch.setattr(read_gate, "CLEAR_LOG", tmp_path / "clears.jsonl")
    monkeypatch.setattr(read_gate, "REARM_LOG", tmp_path / "rearms.jsonl")
    monkeypatch.setattr(read_gate, "SEEN_READS", tmp_path / "seen.json")
    monkeypatch.setattr(read_gate, "is_pytest_scratch", lambda _target: False)
    return tmp_path


def test_a_whole_delivery_does_not_ask_for_a_second_open(isolated_gate):
    small = isolated_gate / "small.md"
    small.write_text("# small\n\nfits whole\n", encoding="utf-8")
    assert read_gate.require_read("prior-writing", str(small), "top match")[0]

    blocked, message = read_gate.gate_status()

    assert blocked
    assert "fits whole" in message
    assert "So open it" not in message
    assert "no need to open it again" in message.lower()
    assert len(message) < 1200


def test_a_truncated_delivery_still_asks_for_the_open(isolated_gate):
    big = isolated_gate / "big.md"
    big.write_text("\n".join(f"line {i}" for i in range(400)), encoding="utf-8")
    assert read_gate.require_read("prior-writing", str(big), "top match")[0]

    blocked, message = read_gate.gate_status()

    assert blocked
    assert "open it" in message.lower()
    assert "no need to open it again" not in message.lower()
