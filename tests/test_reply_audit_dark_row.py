"""A dead reply audit must be loud in the briefing: counted by how often the hook STARTED, not by the clock.

The 2026-10-04 break ran the hook on every Stop for twenty days and completed none of them. The existing "Detector
Chain -- DARK" slot lived in the full HUD, a room nobody opens at session start. See
docs/drafts/a_dead_reply_audit_is_never_silent_draft_2026-10-24.md.
"""

from __future__ import annotations

import json

from divineos.core.briefing_dashboard import DARK_START_THRESHOLD, _row_reply_audit_dark

HOOK = "post-response-audit.sh"


def _timing(path, hook, starts_at):
    rows = [
        {"id": f"{hook}-{i}", "hook": hook, "phase": "start", "ts_ms": int(t * 1000)}
        for i, t in enumerate(starts_at)
    ]
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _heartbeat(path, ts):
    path.write_text(
        json.dumps({"ts": ts, "detectors_run": 37, "errors_this_run": 0}), encoding="utf-8"
    )


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
    return tmp_path / "hook_timing.jsonl", tmp_path / "detector_chain_heartbeat.json"


def test_many_starts_and_no_heartbeat_since_is_dark(tmp_path, monkeypatch):
    timing, hb = _setup(tmp_path, monkeypatch)
    _heartbeat(hb, 1000.0)
    _timing(timing, HOOK, [1001.0 + i for i in range(DARK_START_THRESHOLD + 5)])
    row = _row_reply_audit_dark()
    assert row is not None
    assert "audit" in row.area.lower()
    assert str(DARK_START_THRESHOLD + 5) in row.detail


def test_a_fresh_heartbeat_is_silent_even_with_many_old_starts(tmp_path, monkeypatch):
    timing, hb = _setup(tmp_path, monkeypatch)
    _timing(timing, HOOK, [1001.0 + i for i in range(DARK_START_THRESHOLD + 5)])
    _heartbeat(hb, 5000.0)  # later than every start: the hook is completing
    assert _row_reply_audit_dark() is None


def test_few_starts_after_the_heartbeat_is_silent(tmp_path, monkeypatch):
    timing, hb = _setup(tmp_path, monkeypatch)
    _heartbeat(hb, 1000.0)
    _timing(timing, HOOK, [1001.0 + i for i in range(DARK_START_THRESHOLD - 1)])
    assert _row_reply_audit_dark() is None  # a quiet morning is not a dead audit


def test_other_hooks_starting_do_not_count(tmp_path, monkeypatch):
    timing, hb = _setup(tmp_path, monkeypatch)
    _heartbeat(hb, 1000.0)
    _timing(timing, "some-other-hook.sh", [1001.0 + i for i in range(DARK_START_THRESHOLD + 50)])
    assert _row_reply_audit_dark() is None


def test_no_heartbeat_at_all_with_many_starts_is_dark(tmp_path, monkeypatch):
    timing, hb = _setup(tmp_path, monkeypatch)
    assert not hb.exists()
    _timing(timing, HOOK, [1001.0 + i for i in range(DARK_START_THRESHOLD + 1)])
    assert _row_reply_audit_dark() is not None


def test_no_timing_log_is_silent(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    assert _row_reply_audit_dark() is None  # a fresh machine has nothing to say


def test_the_control_is_alive_the_log_is_the_one_the_row_reads(tmp_path, monkeypatch):
    """A dead control and a blind instrument return the same silence, so prove the row reads THIS log."""
    timing, hb = _setup(tmp_path, monkeypatch)
    _heartbeat(hb, 1000.0)
    _timing(timing, HOOK, [1001.0 + i for i in range(DARK_START_THRESHOLD)])
    assert _row_reply_audit_dark() is not None
    timing.unlink()
    assert _row_reply_audit_dark() is None
