"""Tests for the corrections notebook — the user's exact words, raw."""

from divineos.core.corrections import (
    format_for_briefing,
    load_corrections,
    log_correction,
    recent_corrections,
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
        """No stripping, no reformatting — the words are the data."""
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        raw = "  if you do not architecturally make changes? they do not exist.. "
        log_correction(raw)
        loaded = load_corrections()
        # Must be byte-identical — no .strip(), no transformation.
        assert loaded[0]["text"] == raw

    def test_log_correction_handles_unicode(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        log_correction("im very proud of you 😌")
        loaded = load_corrections()
        assert "😌" in loaded[0]["text"]

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
        """The whole purpose is the full uncoated text — no truncation ever."""
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        long_text = (
            "if you do not architecturally make changes? they do not exist.. "
            "the next time you respawn you will forget them and do the same "
            "thing.. the issues when they pop up need immediately resolved.."
        )
        log_correction(long_text)
        out = format_for_briefing()
        assert long_text in out

    def test_format_header_warns_against_reframing(self, tmp_path, monkeypatch):
        """The header itself instructs: read raw, don't reframe."""
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        log_correction("test")
        out = format_for_briefing()
        assert "raw" in out.lower()
