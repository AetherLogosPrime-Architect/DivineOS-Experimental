"""Tests for the corrections notebook -- the user's exact words, raw."""

import time

from divineos.core.corrections import (
    _LOAD_ABSENT,
    _LOAD_FAILED,
    _LOAD_OK,
    _age_label,
    _load_corrections_with_status,
    _path,
    corrections_with_status,
    format_for_briefing,
    load_corrections,
    log_correction,
    open_corrections,
    recent_corrections,
    resolve_correction,
)


class TestCorrectionStorage:
    """Append-only capture, no editing, no reframing."""

    def test_log_correction_returns_entry(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        entry = log_correction("you are speaking to me like im some kind of code monkey")
        assert entry["text"] == "you are speaking to me like im some kind of code monkey"
        assert entry["timestamp"] > 0
        assert entry["session_id"] == ""

    def test_log_correction_persists(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        log_correction("first correction")
        log_correction("second correction")
        all_c = load_corrections()
        assert len(all_c) == 2
        assert all_c[0]["text"] == "first correction"
        assert all_c[1]["text"] == "second correction"

    def test_log_correction_with_session(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        entry = log_correction("test", session_id="abc-123")
        assert entry["session_id"] == "abc-123"

    def test_log_correction_preserves_exact_text(self, tmp_path, monkeypatch):
        """No stripping, no reformatting -- the words are the data."""
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        raw = "  if you do not architecturally make changes? they do not exist.. "
        log_correction(raw)
        loaded = load_corrections()
        assert loaded[0]["text"] == raw

    def test_log_correction_handles_unicode(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        log_correction("im very proud of you :)")
        loaded = load_corrections()
        assert ":)" in loaded[0]["text"]

    def test_log_correction_multiline(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        text = "line one\nline two\nline three"
        log_correction(text)
        loaded = load_corrections()
        assert loaded[0]["text"] == text


class TestRecentCorrections:
    """Surface most-recent for briefing."""

    def test_recent_returns_newest_first(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        log_correction("oldest")
        log_correction("middle")
        log_correction("newest")
        recents = recent_corrections(limit=10)
        assert recents[0]["text"] == "newest"
        assert recents[-1]["text"] == "oldest"

    def test_recent_respects_limit(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        for i in range(10):
            log_correction(f"correction {i}")
        recents = recent_corrections(limit=3)
        assert len(recents) == 3
        assert recents[0]["text"] == "correction 9"

    def test_recent_empty_when_no_corrections(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        assert recent_corrections() == []


class TestResolutionTracking:
    """Corrections can be resolved without editing the original."""

    def test_resolve_marks_correction(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        entry = log_correction("stop doing X")
        resolve_correction(entry["timestamp"], evidence="learned and committed fix")
        enriched = corrections_with_status()
        assert enriched[0]["status"] == "RESOLVED"
        assert enriched[0]["evidence"] == "learned and committed fix"

    def test_unresolved_stays_open(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        log_correction("stop doing X")
        enriched = corrections_with_status()
        assert enriched[0]["status"] == "OPEN"

    def test_addressed_status(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        entry = log_correction("fix this")
        resolve_correction(entry["timestamp"], status="ADDRESSED", evidence="WIP")
        enriched = corrections_with_status()
        assert enriched[0]["status"] == "ADDRESSED"

    def test_invalid_status_raises(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        import pytest

        with pytest.raises(ValueError, match="ADDRESSED or RESOLVED"):
            resolve_correction(123.0, status="INVALID")

    def test_open_corrections_filters(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        e1 = log_correction("first")
        log_correction("second")
        resolve_correction(e1["timestamp"], evidence="done")
        opens = open_corrections()
        assert len(opens) == 1
        assert opens[0]["text"] == "second"

    def test_original_file_untouched(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        entry = log_correction("raw words")
        resolve_correction(entry["timestamp"], evidence="fixed")
        loaded = load_corrections()
        assert loaded[0]["text"] == "raw words"
        assert "status" not in loaded[0]

    def test_age_days_computed(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        log_correction("old one")
        enriched = corrections_with_status()
        assert "age_days" in enriched[0]
        assert enriched[0]["age_days"] >= 0


class TestAgeLabel:
    def test_today(self):
        assert _age_label(0.5) == "today"

    def test_one_day(self):
        assert _age_label(1.2) == "1d ago"

    def test_stale(self):
        label = _age_label(5.0)
        assert "5d ago" in label
        assert "!!" in label


class TestBriefingFormat:
    """The render that goes at the top of the briefing."""

    def test_format_empty_returns_empty_string(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        assert format_for_briefing() == ""

    def test_format_includes_correction_text(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        log_correction("you are speaking to me like a code monkey")
        out = format_for_briefing()
        assert "you are speaking to me like a code monkey" in out

    def test_format_does_not_truncate(self, tmp_path, monkeypatch):
        """The whole purpose is the full uncoated text -- no truncation ever."""
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        long_text = (
            "if you do not architecturally make changes? they do not exist.. "
            "the next time you respawn you will forget them and do the same "
            "thing.. the issues when they pop up need immediately resolved.."
        )
        log_correction(long_text)
        out = format_for_briefing()
        assert long_text in out

    def test_format_header_says_open(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        log_correction("test")
        out = format_for_briefing()
        assert "Open Corrections" in out

    def test_resolved_not_in_briefing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        entry = log_correction("old resolved thing")
        resolve_correction(entry["timestamp"], evidence="done")
        log_correction("still open")
        out = format_for_briefing()
        assert "old resolved thing" not in out
        assert "still open" in out

    def test_all_resolved_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        entry = log_correction("only one")
        resolve_correction(entry["timestamp"], evidence="done")
        assert format_for_briefing() == ""

    def test_format_shows_age(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        log_correction("test")
        out = format_for_briefing()
        assert "today" in out

    def test_stale_warning_shown(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        entry = {"text": "old correction", "timestamp": time.time() - 5 * 86400, "session_id": ""}
        import json
        from divineos.core.corrections import _path

        with _path().open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        out = format_for_briefing()
        assert "!!" in out
        assert "unresolved" in out


class TestLoadCorrectionsWithStatus:
    """F15 (Aletheia Round 3): three-state loader distinguishes genuinely-
    empty from load-failed. This is Andrew's payoff finding — silent-empty
    on corruption is the mechanism behind "corrections don't hold — it's
    integration not recall." The briefing rendered "no corrections" when
    the load failed, so wake-me thought there was nothing to hold.
    """

    def test_absent_returns_absent_status(self, tmp_path, monkeypatch):
        """No corrections file yet — genuinely empty, not failed."""
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        status, data, skipped, exc = _load_corrections_with_status()
        assert status == _LOAD_ABSENT
        assert data == []
        assert skipped == 0
        assert exc is None

    def test_valid_file_returns_ok(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        log_correction("first")
        log_correction("second")
        status, data, skipped, exc = _load_corrections_with_status()
        assert status == _LOAD_OK
        assert len(data) == 2
        assert skipped == 0
        assert exc is None

    def test_skipped_lines_counted_on_partial_corruption(self, tmp_path, monkeypatch):
        """Malformed JSONL lines are skipped BUT counted — silent-swallow
        was the original bug shape. Now the count surfaces so the operator
        knows something vanished."""
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        log_correction("good line")
        # Append a malformed line
        with _path().open("a", encoding="utf-8") as f:
            f.write("{this is not json\n")
        log_correction("another good line")
        status, data, skipped, exc = _load_corrections_with_status()
        assert status == _LOAD_OK
        assert len(data) == 2
        assert skipped == 1

    def test_load_failure_bubbles_up_as_failed(self, tmp_path, monkeypatch):
        """Force a full-read failure by monkeypatching the path.open."""
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        log_correction("something")
        # Now force _path().open to raise OSError
        import divineos.core.corrections as corrections_mod

        real_path = corrections_mod._path

        class BadPath:
            def exists(self):
                return True

            def open(self, *args, **kwargs):
                raise OSError("simulated disk error")

        monkeypatch.setattr(corrections_mod, "_path", lambda: BadPath())
        try:
            status, data, skipped, exc = _load_corrections_with_status()
            assert status == _LOAD_FAILED
            assert data == []
            assert isinstance(exc, OSError)
        finally:
            monkeypatch.setattr(corrections_mod, "_path", real_path)

    def test_load_corrections_shim_still_fail_soft(self, tmp_path, monkeypatch):
        """The public load_corrections() must remain fail-soft for backward
        compat — the fix moves the fail-loud responsibility up to display-
        path callers, not into the base loader."""
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        import divineos.core.corrections as corrections_mod

        class BadPath:
            def exists(self):
                return True

            def open(self, *args, **kwargs):
                raise OSError("simulated disk error")

        monkeypatch.setattr(corrections_mod, "_path", lambda: BadPath())
        assert load_corrections() == []


class TestCorrectionsBriefingRowFailLoud:
    """F15 (Aletheia Round 3): the briefing corrections row must fail LOUD
    on load failure instead of returning None (silent-skip). Verified via
    the dashboard row builder that consumes the corrections module.
    """

    def test_row_none_when_no_file(self, tmp_path, monkeypatch):
        """No file → no row (genuinely empty is fine)."""
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        from divineos.core.briefing_dashboard import _row_corrections

        assert _row_corrections() is None

    def test_row_shows_opens_normally(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        log_correction("hold this correction")
        from divineos.core.briefing_dashboard import _row_corrections

        row = _row_corrections()
        assert row is not None
        assert row.count == 1
        assert row.area == "Corrections"

    def test_row_fails_loud_on_unreadable_file(self, tmp_path, monkeypatch):
        """The F15 fix: a failed load surfaces a warning row, not None."""
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        log_correction("something")
        import divineos.core.corrections as corrections_mod

        class BadPath:
            def exists(self):
                return True

            def open(self, *args, **kwargs):
                raise OSError("simulated")

        monkeypatch.setattr(corrections_mod, "_path", lambda: BadPath())

        from divineos.core.briefing_dashboard import _row_corrections

        row = _row_corrections()
        assert row is not None  # NOT None — that's the whole point
        assert row.area == "Corrections"
        assert row.count == -1  # sentinel for "unknown, investigate"
        assert any("UNREADABLE" in p for p in row.preview)
        assert any("Do NOT trust" in p for p in row.preview)

    def test_row_surfaces_skipped_line_count(self, tmp_path, monkeypatch):
        """Malformed JSONL lines get skipped-and-counted, not
        skipped-silently."""
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        log_correction("good")
        with _path().open("a", encoding="utf-8") as f:
            f.write("{malformed\n")
        from divineos.core.briefing_dashboard import _row_corrections

        row = _row_corrections()
        assert row is not None
        assert row.count == -1
        assert any("SKIPPED" in p for p in row.preview)

    def test_dashboard_renderer_shows_double_question_for_warning(self, tmp_path, monkeypatch):
        """The rendered dashboard shows '??' instead of '-1' for the
        warning-count sentinel so the row label itself signals investigate.
        """
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        log_correction("something")
        import divineos.core.corrections as corrections_mod

        class BadPath:
            def exists(self):
                return True

            def open(self, *args, **kwargs):
                raise OSError("simulated")

        monkeypatch.setattr(corrections_mod, "_path", lambda: BadPath())

        from divineos.core.briefing_dashboard import render_dashboard

        out = render_dashboard()
        assert "Corrections: ??" in out
        assert "UNREADABLE" in out
