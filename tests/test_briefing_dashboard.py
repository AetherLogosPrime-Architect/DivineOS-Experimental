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


class TestAdvicePendingRow:
    """Task #113 (2026-06-09): the advice-pending row surfaces in the
    briefing when there's pending advice, stays silent otherwise.
    Respects no-track-records — informational, never a gate."""

    def test_silent_when_no_pending_advice(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        output = render_dashboard()
        # When there's no pending advice the row simply doesn't render.
        assert "Advice Pending" not in output

    def test_surfaces_pending_count(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        from divineos.core.advice_tracking import record_advice

        record_advice(
            content="Use the gravity classifier surface to flag borderline calls",
            category="diagnostic",
        )
        record_advice(
            content="Always pair preregs with a falsifier",
            category="discipline",
        )
        output = render_dashboard()
        assert "Advice Pending" in output
        assert "divineos advice pending" in output

    def test_row_function_returns_none_when_empty(self, tmp_path, monkeypatch):
        """The _row_advice_pending helper itself returns None when
        nothing's pending — pins the contract the dashboard relies on."""
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        from divineos.core.briefing_dashboard import _row_advice_pending

        assert _row_advice_pending() is None

    def test_row_function_returns_row_when_present(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        from divineos.core.advice_tracking import record_advice
        from divineos.core.briefing_dashboard import DashboardRow, _row_advice_pending

        record_advice(
            content="Surface pending advice in briefing",
            category="diagnostic",
        )
        row = _row_advice_pending()
        assert isinstance(row, DashboardRow)
        assert row.area == "Advice Pending"
        assert row.count == 1
        assert row.drill_down == "divineos advice pending"


class TestOpenPRsRow:
    """Andrew 2026-06-09: armed auto-merge sitting because sibling PRs
    squash-merged → branches went BEHIND main → auto-merge waits forever
    with no visible signal. This row makes the silent-blocked state
    loud-in-experience."""

    def test_silent_when_gh_unavailable(self, monkeypatch):
        import subprocess

        from divineos.core.briefing_dashboard import _row_open_prs

        def _missing_gh(*a, **kw):
            raise FileNotFoundError("gh not installed")

        monkeypatch.setattr(subprocess, "run", _missing_gh)
        assert _row_open_prs() is None

    def test_silent_on_gh_error(self, monkeypatch):
        import subprocess
        from unittest.mock import MagicMock

        from divineos.core.briefing_dashboard import _row_open_prs

        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **kw: MagicMock(returncode=1, stdout=""),
        )
        assert _row_open_prs() is None

    def test_silent_when_all_clean(self, monkeypatch):
        import subprocess
        from unittest.mock import MagicMock

        from divineos.core.briefing_dashboard import _row_open_prs

        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **kw: MagicMock(
                returncode=0,
                stdout='[{"number":1,"title":"x","mergeStateStatus":"CLEAN"}]',
            ),
        )
        # All clean → silent (nothing actionable to surface).
        assert _row_open_prs() is None

    def test_surfaces_behind_and_blocked(self, monkeypatch):
        import subprocess
        from unittest.mock import MagicMock

        from divineos.core.briefing_dashboard import DashboardRow, _row_open_prs

        stdout = (
            '['
            '{"number":1,"title":"a","mergeStateStatus":"BEHIND"},'
            '{"number":2,"title":"b","mergeStateStatus":"BLOCKED"},'
            '{"number":3,"title":"c","mergeStateStatus":"CLEAN"}'
            "]"
        )
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **kw: MagicMock(returncode=0, stdout=stdout),
        )
        row = _row_open_prs()
        assert isinstance(row, DashboardRow)
        assert row.area == "Open PRs"
        assert row.count == 3
        assert row.stale_count == 2  # behind + blocked
        assert "BEHIND" in row.detail
        assert "BLOCKED" in row.detail
        assert "1 ready" in row.detail
        # Preview names the action-needed PRs.
        joined = "\n".join(row.preview)
        assert "#1" in joined
        assert "#2" in joined

    def test_surfaces_unknown_only_state(self, monkeypatch):
        """All UNKNOWN (GitHub still computing) — still surfaces so the
        operator knows things are mid-flight, not silently stuck."""
        import subprocess
        from unittest.mock import MagicMock

        from divineos.core.briefing_dashboard import _row_open_prs

        stdout = (
            '[{"number":9,"title":"x","mergeStateStatus":"UNKNOWN"}]'
        )
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **kw: MagicMock(returncode=0, stdout=stdout),
        )
        row = _row_open_prs()
        assert row is not None
        assert "computing" in row.detail
