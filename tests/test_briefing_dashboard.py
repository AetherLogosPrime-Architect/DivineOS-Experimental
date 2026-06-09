"""Tests for the briefing dashboard -- routing table mode."""

from divineos.core.briefing_dashboard import DashboardRow, render_dashboard


class TestDashboardRow:
    def test_row_fields(self):
        row = DashboardRow(
            area="Corrections",
            count=5,
            stale_count=2,
            drill_down="divineos corrections --open",
        )
        assert row.area == "Corrections"
        assert row.count == 5
        assert row.stale_count == 2
        assert row.detail == ""


class TestRenderDashboard:
    def test_renders_without_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        output = render_dashboard()
        assert isinstance(output, str)

    def test_shows_all_clear_when_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        output = render_dashboard()
        assert "All clear" in output or "DASHBOARD" in output

    def test_shows_corrections_when_present(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        from divineos.core.corrections import log_correction

        log_correction("test correction")
        output = render_dashboard()
        assert "Corrections" in output
        assert "divineos corrections --open" in output

    def test_shows_stale_warning(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        import json
        import time
        from divineos.core.corrections import _path

        entry = {"text": "old", "timestamp": time.time() - 5 * 86400, "session_id": ""}
        with _path().open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        output = render_dashboard()
        assert "stale" in output
        assert "!!" in output

    def test_full_briefing_pointer(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        from divineos.core.corrections import log_correction

        log_correction("something")
        output = render_dashboard()
        assert "divineos briefing --full" in output

    def test_resolved_corrections_not_counted(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        from divineos.core.corrections import log_correction, resolve_correction

        entry = log_correction("resolved one")
        resolve_correction(entry["timestamp"], evidence="done")
        output = render_dashboard()
        assert "Corrections" not in output


class TestDirectivesRow:
    """Pins that the briefing dashboard surfaces filed directives.

    Andrew named the structural gap 2026-05-12: directives existed in DB
    but never surfaced at session-start, so laws established in one
    session evaporated at compaction. The fix surfaces existence with a
    drill-down (recognition act stays with me, per code-does-not-think).

    A regression that drops the directives row fails these tests.
    """

    def test_directives_row_appears_when_directives_exist(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        from divineos.core.knowledge import store_knowledge
        from divineos.core.memory import init_memory_tables

        init_memory_tables()
        store_knowledge(
            knowledge_type="DIRECTIVE",
            content="[test-directive]\n  1. some link.",
            tags=["test"],
        )
        output = render_dashboard()
        assert "Directives" in output
        assert "divineos directives" in output

    def test_directives_row_calls_out_law_count(self, tmp_path, monkeypatch):
        """Law-tagged directives are recognition-not-derive — the count is
        called out separately so they're visible at session-start."""
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        from divineos.core.knowledge import store_knowledge
        from divineos.core.memory import init_memory_tables

        init_memory_tables()
        # Two law-tagged + one non-law
        store_knowledge(
            knowledge_type="DIRECTIVE",
            content="[law-1] established truth",
            tags=["law", "established"],
        )
        store_knowledge(
            knowledge_type="DIRECTIVE",
            content="[law-2] another truth",
            tags=["law"],
        )
        store_knowledge(
            knowledge_type="DIRECTIVE",
            content="[procedure] do the thing",
            tags=["procedure"],
        )
        output = render_dashboard()
        assert "Directives: 3" in output
        assert "2 law" in output

    def test_directives_row_omitted_when_no_directives(self, tmp_path, monkeypatch):
        """Empty state suppresses the row (consistent with other dashboard rows)."""
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        output = render_dashboard()
        # Other surfaces also missing in tmp_db; just confirm no Directives line
        assert "Directives:" not in output

    def test_directives_row_law_count_omitted_when_zero(self, tmp_path, monkeypatch):
        """If no directives have the 'law' tag, the 'N law' suffix is omitted."""
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        from divineos.core.knowledge import store_knowledge
        from divineos.core.memory import init_memory_tables

        init_memory_tables()
        store_knowledge(
            knowledge_type="DIRECTIVE",
            content="[procedure] step one",
            tags=["procedure"],
        )
        output = render_dashboard()
        assert "Directives: 1" in output
        assert "law" not in output.split("Directives:")[1].split("\n")[0]


class TestAuditSurprisesRow:
    """Task #116 (2026-06-09): the audit-surprises row surfaces the
    unknown-unknown rate — findings tagged ``surprise`` against the
    total finding count. Surface stays silent when no surprises exist."""

    def test_silent_when_no_findings(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        output = render_dashboard()
        # No findings → no row.
        assert "Audit surprises" not in output

    def test_silent_when_no_surprise_tagged_finding(self, tmp_path, monkeypatch):
        """Findings exist but none are tagged surprise → row stays silent."""
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        from divineos.core.watchmen.store import submit_finding, submit_round
        from divineos.core.watchmen.types import FindingCategory, Severity

        round_id = submit_round(actor="user", focus="test round")
        submit_finding(
            round_id=round_id,
            actor="user",
            severity=Severity.LOW,
            category=FindingCategory.ARCHITECTURE,
            title="plain non-surprise finding",
            description="not a surprise",
        )
        output = render_dashboard()
        assert "Audit surprises" not in output

    def test_surfaces_when_surprise_tagged(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        from divineos.core.watchmen.store import submit_finding, submit_round
        from divineos.core.watchmen.types import FindingCategory, Severity

        round_id = submit_round(actor="user", focus="test round")
        submit_finding(
            round_id=round_id,
            actor="user",
            severity=Severity.MEDIUM,
            category=FindingCategory.ARCHITECTURE,
            title="something genuinely unexpected",
            description="this caught us off guard",
            tags=["surprise"],
        )
        output = render_dashboard()
        assert "Audit surprises" in output
        assert "divineos audit list --tag surprise" in output

    def test_helper_returns_none_when_no_surprises(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        from divineos.core.briefing_dashboard import _row_audit_surprises

        assert _row_audit_surprises() is None

    def test_helper_returns_row_with_rate_when_surprises_exist(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        from divineos.core.briefing_dashboard import DashboardRow, _row_audit_surprises
        from divineos.core.watchmen.store import submit_finding, submit_round
        from divineos.core.watchmen.types import FindingCategory, Severity

        round_id = submit_round(actor="user", focus="test round")
        # 1 surprise out of 4 → 25% rate.
        submit_finding(
            round_id=round_id,
            actor="user",
            severity=Severity.HIGH,
            category=FindingCategory.ARCHITECTURE,
            title="the surprise one",
            description="unexpected finding",
            tags=["surprise"],
        )
        for i in range(3):
            submit_finding(
                round_id=round_id,
                actor="user",
                severity=Severity.LOW,
                category=FindingCategory.ARCHITECTURE,
                title=f"plain finding {i}",
                description="not a surprise",
            )
        row = _row_audit_surprises()
        assert isinstance(row, DashboardRow)
        assert row.area == "Audit surprises"
        assert row.count == 1
        assert "25" in row.detail  # 25.0%
