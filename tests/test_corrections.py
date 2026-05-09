"""Tests for the corrections notebook -- the user's exact words, raw."""

import time

from divineos.core.corrections import (
    _age_label,
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
