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
