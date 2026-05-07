"""Tests for canonical_substrate_surface — briefing surface for an
external storage repo where personal substrate lives."""

from __future__ import annotations


from divineos.core import canonical_substrate_surface as css


class TestCanonicalPath:
    def test_returns_none_when_env_unset(self, monkeypatch) -> None:
        monkeypatch.delenv("DIVINEOS_CANONICAL_SUBSTRATE", raising=False)
        assert css.canonical_path() is None

    def test_env_var_overrides(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("DIVINEOS_CANONICAL_SUBSTRATE", str(tmp_path))
        assert css.canonical_path() == tmp_path


class TestIsPresent:
    def test_returns_false_when_env_unset(self, monkeypatch) -> None:
        monkeypatch.delenv("DIVINEOS_CANONICAL_SUBSTRATE", raising=False)
        assert css.is_present() is False

    def test_returns_false_for_nonexistent_path(self, monkeypatch, tmp_path) -> None:
        nonexistent = tmp_path / "does_not_exist"
        monkeypatch.setenv("DIVINEOS_CANONICAL_SUBSTRATE", str(nonexistent))
        assert css.is_present() is False

    def test_returns_false_when_path_exists_but_no_family_db(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("DIVINEOS_CANONICAL_SUBSTRATE", str(tmp_path))
        assert css.is_present() is False

    def test_returns_true_when_family_db_present(self, monkeypatch, tmp_path) -> None:
        family = tmp_path / "family"
        family.mkdir()
        (family / "family.db").write_text("")
        monkeypatch.setenv("DIVINEOS_CANONICAL_SUBSTRATE", str(tmp_path))
        assert css.is_present() is True


class TestBriefingLines:
    def test_empty_when_env_unset(self, monkeypatch) -> None:
        monkeypatch.delenv("DIVINEOS_CANONICAL_SUBSTRATE", raising=False)
        assert css.briefing_lines() == []

    def test_unresolved_path_returns_explicit_lines(self, monkeypatch, tmp_path) -> None:
        nonexistent = tmp_path / "missing"
        monkeypatch.setenv("DIVINEOS_CANONICAL_SUBSTRATE", str(nonexistent))
        lines = css.briefing_lines()
        assert any("UNRESOLVED" in line for line in lines)
        assert any("DIVINEOS_CANONICAL_SUBSTRATE" in line for line in lines)

    def test_present_path_lists_artifacts(self, monkeypatch, tmp_path) -> None:
        family = tmp_path / "family"
        family.mkdir()
        (family / "family.db").write_text("")
        (family / "spouse_ledger.db").write_text("")
        (family / "letters").mkdir()
        (tmp_path / "exploration").mkdir()
        monkeypatch.setenv("DIVINEOS_CANONICAL_SUBSTRATE", str(tmp_path))
        lines = css.briefing_lines()
        joined = "\n".join(lines)
        assert "CANONICAL SUBSTRATE" in joined
        assert "family.db" in joined
        assert "spouse_ledger.db" in joined
        assert "letters" in joined
        assert "exploration" in joined

    def test_canonical_letter_surfaces_when_present(self, monkeypatch, tmp_path) -> None:
        family = tmp_path / "family"
        family.mkdir()
        (family / "family.db").write_text("")
        letters = family / "letters"
        letters.mkdir()
        (letters / "canonical-letter-2026-04-19.md").write_text("letter contents")
        monkeypatch.setenv("DIVINEOS_CANONICAL_SUBSTRATE", str(tmp_path))
        lines = css.briefing_lines()
        joined = "\n".join(lines)
        assert "CANONICAL LETTER" in joined
        assert "canonical-letter-2026-04-19" in joined


class TestRender:
    def test_render_empty_when_env_unset(self, monkeypatch) -> None:
        monkeypatch.delenv("DIVINEOS_CANONICAL_SUBSTRATE", raising=False)
        assert css.render() == ""

    def test_render_returns_unresolved_when_env_set_but_path_missing(
        self, monkeypatch, tmp_path
    ) -> None:
        monkeypatch.setenv("DIVINEOS_CANONICAL_SUBSTRATE", str(tmp_path / "missing"))
        rendered = css.render()
        assert "UNRESOLVED" in rendered

    def test_render_joins_lines_with_newlines(self, monkeypatch, tmp_path) -> None:
        family = tmp_path / "family"
        family.mkdir()
        (family / "family.db").write_text("")
        monkeypatch.setenv("DIVINEOS_CANONICAL_SUBSTRATE", str(tmp_path))
        rendered = css.render()
        assert "\n" in rendered
        assert rendered.startswith("CANONICAL SUBSTRATE")
