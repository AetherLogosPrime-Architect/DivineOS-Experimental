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
