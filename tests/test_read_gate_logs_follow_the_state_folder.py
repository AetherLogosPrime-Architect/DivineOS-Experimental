"""The read gate's logs follow the state folder, so tests cannot pollute the live ones.

Measured 2026-10-11 (Aria and Aether): about 63 percent of one seat's clears log and
about 78 percent of the other's (by line) was pytest fixture debris. The module froze
three paths (the re-arm log, the seen-reads accumulator, the clears log) when it
loaded, before any fixture ran, so tests that patched ``STATE_DIR`` still wrote into
the live files. Every measure of the gate, including the review of how much its
deliveries are used, was inflated.

The module now resolves each path from ``STATE_DIR`` at call time, and an autouse
fixture in conftest points ``STATE_DIR`` at the test's own folder, so a test that
forgets to patch is still safe. These tests pin both halves and the invariant that
would catch a fourth frozen path by name.
"""

from __future__ import annotations

import json
from pathlib import Path

from divineos.core import read_gate

# Captured at import, before any fixture runs: where the module froze its folder.
# In a normal run this is the live home, so the tests below also read as an event
# measure: the live files are not touched by anything in this module.
_FROZEN_DIR = read_gate.STATE_DIR
_LOG_NAMES = ("read_gate_clears.jsonl", "read_gate_rearms.jsonl", "read_gate_seen.json")


def _snapshot() -> dict[str, bytes | None]:
    out: dict[str, bytes | None] = {}
    for name in _LOG_NAMES:
        path = _FROZEN_DIR / name
        out[name] = path.read_bytes() if path.is_file() else None
    return out


def _last_row(folder: Path) -> dict:
    lines = (folder / "read_gate_clears.jsonl").read_text(encoding="utf-8").splitlines()
    return json.loads(lines[-1])


def test_a_test_that_patches_nothing_cannot_reach_the_live_logs():
    """The autouse fixture is what makes this pass: nothing here patches STATE_DIR."""
    before = _snapshot()
    read_gate.record_clear("gate-x", "some/entry.md", "full-file")
    read_gate._accumulate_seen_reads("transcript-1", [("Read", "some/entry.md", None)])
    assert _snapshot() == before, "a read-gate write reached the folder the module froze at import"
    assert read_gate.STATE_DIR != _FROZEN_DIR
    assert (read_gate.STATE_DIR / "read_gate_clears.jsonl").is_file()


def test_every_log_follows_the_state_folder_when_it_is_patched(tmp_path, monkeypatch):
    scratch = tmp_path / "scratch"
    monkeypatch.setattr(read_gate, "STATE_DIR", scratch)
    before = _snapshot()
    read_gate.record_clear("gate-y", "a/b.md", "limit=3")
    read_gate._accumulate_seen_reads("t", [("Read", "a/b.md", None)])
    assert _snapshot() == before
    assert (scratch / "read_gate_clears.jsonl").is_file()
    assert (scratch / "read_gate_seen.json").is_file()
    assert read_gate._rearm_log() == scratch / "read_gate_rearms.jsonl"


def test_no_module_level_path_is_frozen_under_the_loaded_folder():
    """A fourth frozen path fails here by name. STATE_FILE is the one documented seam
    (tests patch it by name) and moving it is a separate piece."""
    frozen = [
        name
        for name, value in vars(read_gate).items()
        if isinstance(value, Path)
        and name not in {"STATE_DIR", "STATE_FILE"}
        and _FROZEN_DIR in value.parents
    ]
    assert frozen == [], f"module-level paths fixed at import: {frozen}"


def test_a_clear_records_the_transcript_key_the_module_already_holds(tmp_path, monkeypatch):
    monkeypatch.setattr(read_gate, "STATE_DIR", tmp_path)
    (tmp_path / "read_gate_seen.json").write_text(
        json.dumps({"transcript": "session-42.jsonl", "reads": []}), encoding="utf-8"
    )
    read_gate.record_clear("gate-z", "c/d.md", "full-file")
    assert _last_row(tmp_path)["transcript"] == "session-42.jsonl"


def test_a_clear_with_no_known_session_carries_no_invented_one(tmp_path, monkeypatch):
    monkeypatch.setattr(read_gate, "STATE_DIR", tmp_path)
    read_gate.record_clear("gate-z", "c/d.md", "full-file")
    assert "transcript" not in _last_row(tmp_path)
