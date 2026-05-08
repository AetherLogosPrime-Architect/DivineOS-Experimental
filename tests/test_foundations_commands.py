"""Tests for the divineos foundations CLI (read + list).

Verifies recognition-shape preamble fires by default, --no-preamble
suppresses it, layer resolution handles multiple input shapes, and the
real foundations directory is correctly located.
"""

from __future__ import annotations

from pathlib import Path

import click.testing
import pytest

from divineos.cli.foundations_commands import (
    _foundations_dir,
    _parse_layer_header,
    _resolve_layer_path,
    register,
)


@pytest.fixture
def cli_runner():
    return click.testing.CliRunner()


@pytest.fixture
def cli_with_foundations():
    """Build a click.Group with foundations registered."""
    import click

    @click.group()
    def root() -> None:
        pass

    register(root)
    return root


def _make_layer_file(tmp_path: Path, name: str, body: str) -> Path:
    foundations = tmp_path / "docs" / "foundations"
    foundations.mkdir(parents=True, exist_ok=True)
    p = foundations / name
    p.write_text(body, encoding="utf-8")
    (tmp_path / ".git").mkdir(exist_ok=True)
    return p


class TestParseLayerHeader:
    def test_extracts_title(self):
        text = "# Layer 0 — Foundations\n\n**Version**: v2\n"
        h = _parse_layer_header(text)
        assert h["title"] == "Layer 0 — Foundations"

    def test_extracts_version_status_dependencies(self):
        text = (
            "# Layer 1 — Pentagonal Force\n\n"
            "**Version**: v1\n"
            "**Status**: Builds on Layer 0\n"
            "**Dependencies**: Layer 0\n"
            "**Authors**: Aether\n"
        )
        h = _parse_layer_header(text)
        assert h["version"] == "v1"
        assert h["status"] == "Builds on Layer 0"
        assert h["dependencies"] == "Layer 0"
        assert h["authors"] == "Aether"

    def test_handles_missing_fields(self):
        h = _parse_layer_header("# Layer 0 — Title\n")
        assert h.get("title") == "Layer 0 — Title"
        assert "version" not in h

    def test_empty_text(self):
        assert _parse_layer_header("") == {}


class TestResolveLayerPath:
    def test_digit_resolves_to_layer_n_md(self, tmp_path):
        _make_layer_file(tmp_path, "layer_0.md", "# Layer 0 — Foundations\n")
        base = tmp_path / "docs" / "foundations"
        result = _resolve_layer_path("0", base)
        assert result is not None
        assert result.name == "layer_0.md"

    def test_layer_n_resolves(self, tmp_path):
        _make_layer_file(tmp_path, "layer_3.md", "# Layer 3 — X\n")
        base = tmp_path / "docs" / "foundations"
        result = _resolve_layer_path("layer_3", base)
        assert result is not None
        assert result.name == "layer_3.md"

    def test_full_filename_resolves(self, tmp_path):
        _make_layer_file(tmp_path, "layer_5.md", "# Layer 5 — Y\n")
        base = tmp_path / "docs" / "foundations"
        result = _resolve_layer_path("layer_5.md", base)
        assert result is not None
        assert result.name == "layer_5.md"

    def test_unknown_returns_none(self, tmp_path):
        _make_layer_file(tmp_path, "layer_0.md", "# Layer 0\n")
        base = tmp_path / "docs" / "foundations"
        assert _resolve_layer_path("99", base) is None
        assert _resolve_layer_path("nonsense", base) is None


class TestListCommand:
    def test_list_shows_layers(self, tmp_path, monkeypatch, cli_runner, cli_with_foundations):
        _make_layer_file(
            tmp_path,
            "layer_0.md",
            "# Layer 0 — Foundations\n\n**Version**: v2\n**Status**: Ground\n",
        )
        _make_layer_file(
            tmp_path,
            "layer_1.md",
            "# Layer 1 — Pentagonal Force\n\n**Version**: v1\n",
        )
        monkeypatch.chdir(tmp_path)
        result = cli_runner.invoke(cli_with_foundations, ["foundations", "list"])
        assert result.exit_code == 0
        assert "Layer 0 — Foundations" in result.output
        assert "Layer 1 — Pentagonal Force" in result.output
        assert "v2" in result.output
        assert "v1" in result.output

    def test_list_marks_missing(self, tmp_path, monkeypatch, cli_runner, cli_with_foundations):
        # Only create layer_0; the rest are missing.
        _make_layer_file(tmp_path, "layer_0.md", "# Layer 0 — Foundations\n")
        monkeypatch.chdir(tmp_path)
        result = cli_runner.invoke(cli_with_foundations, ["foundations", "list"])
        assert result.exit_code == 0
        assert "[MISSING]" in result.output
        assert "layer_5.md [MISSING]" in result.output

    def test_list_handles_no_directory(
        self, tmp_path, monkeypatch, cli_runner, cli_with_foundations
    ):
        (tmp_path / ".git").mkdir()
        monkeypatch.chdir(tmp_path)
        result = cli_runner.invoke(cli_with_foundations, ["foundations", "list"])
        assert result.exit_code == 0
        assert "No docs/foundations/ directory" in result.output


class TestReadCommand:
    def test_read_includes_preamble_by_default(
        self, tmp_path, monkeypatch, cli_runner, cli_with_foundations
    ):
        _make_layer_file(
            tmp_path,
            "layer_0.md",
            "# Layer 0 — Foundations\n\n**Version**: v2\n\n## §0.1 Frame\n\nBody text.\n",
        )
        monkeypatch.chdir(tmp_path)
        result = cli_runner.invoke(cli_with_foundations, ["foundations", "read", "0"])
        assert result.exit_code == 0
        assert "RECOGNITION-SHAPE READING" in result.output
        assert "You authored this" in result.output
        assert "naming-what-already-operates" in result.output
        assert "Body text" in result.output  # actual content present
        assert "BEGIN DOCUMENT" in result.output
        assert "END DOCUMENT" in result.output

    def test_read_no_preamble_strips_framing(
        self, tmp_path, monkeypatch, cli_runner, cli_with_foundations
    ):
        _make_layer_file(tmp_path, "layer_0.md", "# Layer 0 — Foundations\n\nBody text only.\n")
        monkeypatch.chdir(tmp_path)
        result = cli_runner.invoke(
            cli_with_foundations, ["foundations", "read", "0", "--no-preamble"]
        )
        assert result.exit_code == 0
        assert "RECOGNITION-SHAPE" not in result.output
        assert "BEGIN DOCUMENT" not in result.output
        assert "Body text only" in result.output

    def test_read_unknown_layer_fails_cleanly(
        self, tmp_path, monkeypatch, cli_runner, cli_with_foundations
    ):
        _make_layer_file(tmp_path, "layer_0.md", "# Layer 0\n")
        monkeypatch.chdir(tmp_path)
        result = cli_runner.invoke(cli_with_foundations, ["foundations", "read", "99"])
        assert result.exit_code != 0
        assert "Could not resolve layer" in result.output

    def test_read_missing_directory_fails_cleanly(
        self, tmp_path, monkeypatch, cli_runner, cli_with_foundations
    ):
        (tmp_path / ".git").mkdir()
        monkeypatch.chdir(tmp_path)
        result = cli_runner.invoke(cli_with_foundations, ["foundations", "read", "0"])
        assert result.exit_code != 0
        assert "No docs/foundations/ directory" in result.output


class TestRealRepoIntegration:
    """The actual repository should have all 6 foundation layers."""

    def test_real_foundations_dir_resolves(self):
        d = _foundations_dir()
        assert d is not None, "real repo should have docs/foundations/"
        assert d.is_dir()

    def test_all_six_layers_exist(self):
        d = _foundations_dir()
        assert d is not None
        for n in range(6):
            assert (d / f"layer_{n}.md").is_file(), f"layer_{n}.md should exist"
