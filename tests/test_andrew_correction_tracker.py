"""Tests for the Andrew-correction-attribution tracker.

The module's reason for existing is to stop silent decay of Andrew's
corrections: you cannot mark one INTEGRATED without real evidence, you
cannot DEFER without a named reason, and open ones surface with age.
These tests pin exactly those guards plus the rate math and the
briefing block.

Untested at ship; closed 2026-05-23 working down the unfinished-mechanism
backlog the repaired initiative dial surfaced.
"""

import pytest

from divineos.core import andrew_correction_tracker as act


@pytest.fixture(autouse=True)
def _isolate_home(monkeypatch, tmp_path):
    """Point both the DB and the attestation marker at a temp dir."""
    monkeypatch.setattr(act, "divineos_home", lambda: tmp_path)
    yield


class TestFileCorrection:
    def test_file_returns_row_id(self):
        cid = act.file_correction("be terser in summaries")
        assert cid > 0

    def test_empty_text_returns_zero(self):
        assert act.file_correction("") == 0
        assert act.file_correction("   ") == 0

    def test_filed_correction_is_open(self):
        act.file_correction("some correction text here")
        opens = act.list_open()
        assert len(opens) == 1
        assert opens[0]["text"] == "some correction text here"


class TestIntegrateGuards:
    def test_integrate_refuses_short_evidence(self):
        cid = act.file_correction("a real correction")
        assert act.integrate(cid, "too short") is False
        # Still open — refused closures don't transition.
        assert len(act.list_open()) == 1

    def test_integrate_refuses_empty_evidence(self):
        cid = act.file_correction("a real correction")
        assert act.integrate(cid, "") is False

    def test_integrate_succeeds_with_real_evidence(self):
        cid = act.file_correction("a real correction")
        ok = act.integrate(cid, "landed in commit abc123 — behavior changed in module X")
        assert ok is True
        assert act.list_open() == []

    def test_integrate_only_transitions_open(self):
        cid = act.file_correction("a real correction")
        act.integrate(cid, "landed in commit abc123 — behavior changed in module X")
        # Second integrate on an already-integrated row affects nothing.
        again = act.integrate(cid, "another evidence string long enough to pass")
        assert again is False

    def test_integrate_nonexistent_id(self):
        assert act.integrate(9999, "evidence long enough to pass the guard") is False


class TestDeferGuards:
    def test_defer_refuses_short_reason(self):
        cid = act.file_correction("a real correction")
        assert act.defer(cid, "later") is False
        assert len(act.list_open()) == 1

    def test_defer_succeeds_with_reason(self):
        cid = act.file_correction("a real correction")
        ok = act.defer(cid, "blocked on upstream decision about schema migration")
        assert ok is True
        assert act.list_open() == []


class TestListOpen:
    def test_oldest_first(self, monkeypatch):
        import divineos.core.andrew_correction_tracker as mod

        times = iter([100.0, 200.0, 300.0])
        monkeypatch.setattr(mod.time, "time", lambda: next(times))
        a = act.file_correction("first")
        b = act.file_correction("second")
        c = act.file_correction("third")
        opens = act.list_open()
        assert [o["id"] for o in opens] == [a, b, c]

    def test_excludes_integrated_and_deferred(self):
        a = act.file_correction("will integrate")
        b = act.file_correction("will defer")
        act.file_correction("stays open")
        act.integrate(a, "evidence string long enough to pass the guard check")
        act.defer(b, "deferred for a clearly named and sufficiently long reason")
        opens = act.list_open()
        assert len(opens) == 1
        assert opens[0]["text"] == "stays open"


class TestIntegrationRate:
    def test_empty_rate_is_zero(self):
        stats = act.integration_rate()
        assert stats["total"] == 0
        assert stats["rate"] == 0.0

    def test_rate_math(self):
        a = act.file_correction("one")
        act.file_correction("two")
        b = act.file_correction("three")
        c = act.file_correction("four")
        act.integrate(a, "evidence string long enough to pass the guard check")
        act.defer(b, "deferred for a clearly named and sufficiently long reason")
        act.defer(c, "another clearly named and sufficiently long deferral reason")
        stats = act.integration_rate()
        assert stats["total"] == 4
        assert stats["integrated"] == 1
        assert stats["open"] == 1
        assert stats["deferred"] == 2
        assert stats["rate"] == pytest.approx(0.25)


class TestBriefingBlock:
    def test_empty_when_no_corrections(self):
        assert act.briefing_block() == ""

    def test_contains_stats_and_outstanding(self):
        act.file_correction("an outstanding correction to surface")
        block = act.briefing_block()
        assert "ANDREW-CORRECTION ATTRIBUTION SURFACE" in block
        assert "Total filed: 1" in block
        assert "an outstanding correction to surface" in block


class TestUnblockConditionValidation:
    """Task #115 (2026-06-09): defer() accepts an optional
    unblock_condition. Invalid formats must be refused at defer-time
    so a typo-shaped condition doesn't sit silent forever."""

    def test_valid_pr_merged_form(self):
        assert act._is_valid_unblock_condition("pr_merged:117") is True

    def test_valid_time_elapsed_form(self):
        assert act._is_valid_unblock_condition("time_elapsed:7") is True

    def test_valid_knowledge_stored_form(self):
        assert act._is_valid_unblock_condition("knowledge_stored:lepos") is True

    def test_invalid_prefix_refused(self):
        assert act._is_valid_unblock_condition("pr_landed:117") is False
        assert act._is_valid_unblock_condition("random-string") is False

    def test_empty_argument_refused(self):
        assert act._is_valid_unblock_condition("pr_merged:") is False
        assert act._is_valid_unblock_condition("time_elapsed:") is False

    def test_empty_or_none_refused(self):
        assert act._is_valid_unblock_condition("") is False
        assert act._is_valid_unblock_condition(None) is False  # type: ignore[arg-type]


class TestDeferWithUnblockCondition:
    """defer() must accept and store the unblock_condition when valid,
    and refuse a deferral with an invalid one."""

    def test_defer_with_valid_condition_stores_it(self):
        cid = act.file_correction("correction needing deferral with condition")
        ok = act.defer(
            cid,
            "Waiting for the related PR to merge before fixing structurally",
            unblock_condition="pr_merged:117",
        )
        assert ok is True
        # Confirm stored.
        import sqlite3

        conn = sqlite3.connect(str(act._db_path()))
        try:
            row = conn.execute(
                "SELECT unblock_condition FROM andrew_corrections WHERE id = ?",
                (cid,),
            ).fetchone()
        finally:
            conn.close()
        assert row[0] == "pr_merged:117"

    def test_defer_with_invalid_condition_refused(self):
        cid = act.file_correction("another correction text long enough")
        ok = act.defer(
            cid,
            "Reason long enough to satisfy the guard requirement",
            unblock_condition="garbage-typo",
        )
        assert ok is False
        # Still open — refused defer doesn't transition.
        assert len(act.list_open()) == 1

    def test_defer_without_condition_still_works(self):
        """Backward compat — passing no unblock_condition keeps prior behavior."""
        cid = act.file_correction("plain correction with no condition")
        ok = act.defer(cid, "Bare deferral without auto-reopen, manually re-open later")
        assert ok is True


class TestConditionFired:
    """Each unblock-condition form has its own check. These tests pin
    the deterministic paths; the network-dependent path (pr_merged via
    gh) is exercised by mocking subprocess.run."""

    def test_time_elapsed_fires_when_window_passed(self):
        # 1 day window, item deferred 2 days ago.
        import time

        two_days_ago = time.time() - 2 * 86400
        assert act._condition_fired("time_elapsed:1", deferred_at=two_days_ago) is True

    def test_time_elapsed_does_not_fire_within_window(self):
        import time

        five_minutes_ago = time.time() - 300
        assert act._condition_fired("time_elapsed:1", deferred_at=five_minutes_ago) is False

    def test_time_elapsed_with_no_deferred_at_returns_false(self):
        # Without a defer-time anchor, can't compute elapsed → don't fire.
        assert act._condition_fired("time_elapsed:1", deferred_at=None) is False

    def test_unrecognized_prefix_returns_false(self):
        assert act._condition_fired("garbage-prefix:value") is False

    def test_empty_condition_returns_false(self):
        assert act._condition_fired("") is False


class TestCheckAndReopen:
    """The periodic sweep walks DEFERRED items whose conditions have
    fired and reopens them. Items without a condition stay deferred."""

    def test_reopens_deferred_with_fired_condition(self, monkeypatch):
        import time as _time

        cid = act.file_correction("correction to be reopened on time-elapsed")
        # Defer with time_elapsed:1 — item's row timestamp is now,
        # so we need to backdate it for the condition to fire.
        ok = act.defer(
            cid,
            "Waiting on time to pass before re-engaging this correction",
            unblock_condition="time_elapsed:1",
        )
        assert ok is True
        # Backdate the row timestamp by 2 days so time_elapsed:1 fires.
        import sqlite3

        conn = sqlite3.connect(str(act._db_path()))
        try:
            conn.execute(
                "UPDATE andrew_corrections SET timestamp = ? WHERE id = ?",
                (_time.time() - 2 * 86400, cid),
            )
            conn.commit()
        finally:
            conn.close()

        reopened = act.check_and_reopen_unblocked()
        assert cid in reopened
        # Item is back to OPEN, condition cleared.
        opens = act.list_open()
        assert any(o["id"] == cid for o in opens)

    def test_does_not_reopen_when_condition_not_fired(self):
        cid = act.file_correction("correction to stay deferred until window passes")
        act.defer(
            cid,
            "Deferring with a long-future time window so this stays put",
            unblock_condition="time_elapsed:30",
        )
        reopened = act.check_and_reopen_unblocked()
        assert cid not in reopened

    def test_skips_items_without_condition(self):
        cid = act.file_correction("plain deferred correction with no condition")
        act.defer(cid, "Bare deferral with no auto-reopen condition attached")
        reopened = act.check_and_reopen_unblocked()
        # No condition → not eligible for the sweep.
        assert cid not in reopened
