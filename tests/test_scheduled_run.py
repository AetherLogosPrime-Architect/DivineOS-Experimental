"""Tests for scheduled_run — headless mode scaffolding for Routines.

Locked invariants:

1. Default context is NOT headless.
2. headless_run flips the flag inside, clears it on exit.
3. Nested headless_run raises RuntimeError.
4. is_command_allowed_headless enforces the v0.1 whitelist.
5. Findings collected in the context manager land in the end event.
6. SCHEDULED_RUN_* events are distinct from SESSION_* — session-counting
   code that queries SESSION_START/END naturally excludes them.
7. recent_scheduled_runs returns end events in reverse chronological order.
8. unresolved_findings_summary returns empty string when runs are clean.
"""

from __future__ import annotations

import os

import pytest

from divineos.core.scheduled_run import (
    EVENT_SCHEDULED_RUN_END,
    EVENT_SCHEDULED_RUN_START,
    RunFindings,
    headless_run,
    is_command_allowed_headless,
    is_headless,
    recent_scheduled_runs,
    unresolved_findings_summary,
)


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path):
    os.environ["DIVINEOS_DB"] = str(tmp_path / "ledger.db")
    try:
        from divineos.core.ledger import init_db

        init_db()
        yield
    finally:
        os.environ.pop("DIVINEOS_DB", None)


class TestHeadlessContext:
    def test_default_is_not_headless(self):
        assert is_headless() is False

    def test_context_flips_flag(self):
        assert is_headless() is False
        with headless_run("anti-slop"):
            assert is_headless() is True
        assert is_headless() is False

    def test_context_clears_on_exception(self):
        with pytest.raises(ValueError):
            with headless_run("anti-slop"):
                assert is_headless() is True
                raise ValueError("boom")
        assert is_headless() is False

    def test_nested_headless_raises(self):
        with headless_run("anti-slop"):
            with pytest.raises(RuntimeError, match="Nested headless runs"):
                with headless_run("health"):
                    pass


class TestWhitelist:
    def test_whitelisted_commands_allowed(self):
        for cmd in ("anti-slop", "health", "verify", "inspect", "audit", "progress"):
            allowed, reason = is_command_allowed_headless(cmd)
            assert allowed, f"{cmd} should be allowed: {reason}"
            assert reason == ""

    def test_non_whitelisted_refused(self):
        for cmd in ("learn", "emit", "forget", "mode", "briefing"):
            allowed, reason = is_command_allowed_headless(cmd)
            assert not allowed
            assert "not in headless whitelist" in reason


class TestRunFindings:
    def test_default_clean(self):
        f = RunFindings()
        assert f.is_clean() is True
        assert f.to_dict()["clean"] is True

    def test_failures_make_unclean(self):
        f = RunFindings()
        f.failures.append("something broke")
        assert f.is_clean() is False
        assert f.to_dict()["clean"] is False
        assert "something broke" in f.to_dict()["failures"]


class TestEventEmission:
    def test_start_and_end_events_emitted(self):
        from divineos.core.ledger import get_connection

        with headless_run("anti-slop", trigger="cron") as findings:
            findings.notes.append("all good")

        conn = get_connection()
        try:
            start_rows = conn.execute(
                "SELECT payload FROM system_events WHERE event_type = ?",
                (EVENT_SCHEDULED_RUN_START,),
            ).fetchall()
            end_rows = conn.execute(
                "SELECT payload FROM system_events WHERE event_type = ?",
                (EVENT_SCHEDULED_RUN_END,),
            ).fetchall()
        finally:
            conn.close()

        assert len(start_rows) == 1
        assert len(end_rows) == 1

    def test_events_distinct_from_session(self):
        """Session-counting code queries SESSION_START/SESSION_END.
        Scheduled events use distinct types, so they naturally don't
        appear in session counts."""
        from divineos.core.ledger import get_connection

        with headless_run("health"):
            pass

        conn = get_connection()
        try:
            session_count = conn.execute(
                "SELECT COUNT(*) FROM system_events "
                "WHERE event_type IN ('SESSION_START', 'SESSION_END')"
            ).fetchone()[0]
        finally:
            conn.close()
        assert session_count == 0

    def test_findings_in_end_payload(self):
        import json

        from divineos.core.ledger import get_connection

        with headless_run("anti-slop") as findings:
            findings.failures.append("detector X failed")
            findings.notes.append("ran in 0.1s")
            findings.metrics["count"] = 42

        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT payload FROM system_events WHERE event_type = ? "
                "ORDER BY timestamp DESC LIMIT 1",
                (EVENT_SCHEDULED_RUN_END,),
            ).fetchone()
        finally:
            conn.close()

        data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        assert data["clean"] is False
        assert "detector X failed" in data["failures"]
        assert "ran in 0.1s" in data["notes"]
        assert data["metrics"]["count"] == 42
        assert data["duration_sec"] >= 0


class TestQueries:
    def test_recent_runs_reverse_chronological(self):
        with headless_run("anti-slop"):
            pass
        with headless_run("health"):
            pass
        with headless_run("verify"):
            pass

        runs = recent_scheduled_runs(limit=10)
        assert len(runs) == 3
        # Most recent first
        assert runs[0]["command"] == "verify"
        assert runs[-1]["command"] == "anti-slop"
        for r in runs:
            assert r["clean"] is True

    def test_recent_runs_empty_when_none(self):
        assert recent_scheduled_runs() == []

    def test_unresolved_summary_empty_on_clean(self):
        with headless_run("anti-slop"):
            pass
        assert unresolved_findings_summary() == ""

    def test_unresolved_summary_surfaces_failures(self):
        with headless_run("anti-slop") as f:
            f.failures.append("principle:consent missing")

        summary = unresolved_findings_summary()
        assert "unresolved finding-set" in summary
        assert "anti-slop" in summary
        assert "principle:consent missing" in summary

    def test_unresolved_summary_cuts_at_last_clean_run(self):
        # failure, then clean, then failure — only the most recent
        # failure should surface (the earlier one is resolved).
        with headless_run("anti-slop") as f:
            f.failures.append("old failure")
        with headless_run("health"):
            pass  # clean — this is the cutoff
        with headless_run("verify") as f:
            f.failures.append("new failure")

        summary = unresolved_findings_summary()
        assert "new failure" in summary
        assert "old failure" not in summary
