"""A dead reply audit must be loud in the briefing: counted by how often the hook STARTED, not by the clock.

The 2026-10-04 break ran the hook on every Stop for twenty days and completed none of them. The existing "Detector
Chain -- DARK" slot lived in the full HUD, a room nobody opens at session start. See
docs/drafts/a_dead_reply_audit_is_never_silent_draft_2026-10-24.md.

The hook writes its start rows to ${HOME}/.divineos/hook_timing.jsonl whatever seat it runs for, while the heartbeat is
per seat and lives in that seat's home. Every test here keeps those two in DIFFERENT folders, because a pair that share
one folder passed on the default seat and went silent on a member seat (Aria's reading of #715).
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _heartbeat(path, ts, detectors_run=37):
    path.write_text(
        json.dumps({"ts": ts, "detectors_run": detectors_run, "errors_this_run": 0}),
        encoding="utf-8",
    )


def _setup(tmp_path, monkeypatch):
    """The hook's log under HOME/.divineos; the seat's heartbeat in a separate member home."""
    home = tmp_path / "home"
    member = tmp_path / "member_home"
    home.mkdir()
    member.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("DIVINEOS_HOME", str(member))
    return home / ".divineos" / "hook_timing.jsonl", member / "detector_chain_heartbeat.json"


def test_many_starts_and_no_heartbeat_since_is_dark_on_a_member_seat(tmp_path, monkeypatch):
    timing, hb = _setup(tmp_path, monkeypatch)
    assert timing.parent != hb.parent  # the seat the row went silent on
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


def test_a_heartbeat_from_a_run_that_executed_no_detectors_does_not_count(tmp_path, monkeypatch):
    """Anyone calling run_audit writes a heartbeat, a test included (Aria wrote one this morning)."""
    timing, hb = _setup(tmp_path, monkeypatch)
    _timing(timing, HOOK, [1001.0 + i for i in range(DARK_START_THRESHOLD + 5)])
    _heartbeat(hb, 5000.0, detectors_run=0)  # fresh by the clock, but nothing ran
    assert _row_reply_audit_dark() is not None


def test_a_fresh_machine_with_neither_file_is_silent(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    assert _row_reply_audit_dark() is None


def test_a_missing_timing_log_while_a_heartbeat_exists_says_it_could_not_check(
    tmp_path, monkeypatch
):
    """A missing log must never read as health: that is the silence this row exists to end."""
    timing, hb = _setup(tmp_path, monkeypatch)
    _heartbeat(hb, 1000.0)
    assert not timing.exists()
    row = _row_reply_audit_dark()
    assert row is not None
    assert "could not" in row.area.lower() or "could not" in row.detail.lower()


def test_the_control_is_alive_the_log_is_the_one_the_row_reads(tmp_path, monkeypatch):
    """A dead control and a blind instrument return the same silence, so prove the row reads THIS log."""
    timing, hb = _setup(tmp_path, monkeypatch)
    _heartbeat(hb, 1000.0)
    _timing(timing, HOOK, [1001.0 + i for i in range(DARK_START_THRESHOLD)])
    fired = _row_reply_audit_dark()
    assert fired is not None and "DARK" in fired.area
    timing.unlink()
    after = _row_reply_audit_dark()
    assert (
        after is not None and "DARK" not in after.area
    )  # now it says it cannot check, not that it is dark
