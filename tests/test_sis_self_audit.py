"""Tests for SIS Self-Audit -- the system auditing its own docstrings."""

from divineos.core.sis_self_audit import (
    DocstringAuditResult,
    _extract_module_docstring,
    audit_docstrings,
    audit_summary,
    format_audit_results,
)


class TestDocstringExtraction:
    """Extract module docstrings via AST parsing."""

    def test_extract_from_real_file(self, tmp_path):
        f = tmp_path / "example.py"
        f.write_text('"""This is a module docstring."""\nx = 1\n')
        result = _extract_module_docstring(f)
        assert result == "This is a module docstring."

    def test_extract_no_docstring(self, tmp_path):
        f = tmp_path / "no_doc.py"
        f.write_text("x = 1\n")
        result = _extract_module_docstring(f)
        assert result is None

    def test_extract_handles_syntax_error(self, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text("def whoops(\n")
        result = _extract_module_docstring(f)
        assert result is None

    def test_extract_multiline_docstring(self, tmp_path):
        f = tmp_path / "multi.py"
        f.write_text('"""Line one.\n\nLine two with details.\n"""\n')
        result = _extract_module_docstring(f)
        assert "Line one" in result
        assert "Line two" in result


class TestAuditDocstrings:
    """Full audit of a source directory."""

    def test_audit_clean_docstring(self, tmp_path):
        f = tmp_path / "clean.py"
        f.write_text('"""Session checkpoint saves state periodically to SQLite database."""\n')
        results = audit_docstrings(src_dir=tmp_path, threshold=0.05)
        assert len(results) >= 1
        assert not results[0].flagged

    def test_audit_esoteric_docstring(self, tmp_path):
        f = tmp_path / "esoteric.py"
        f.write_text(
            '"""Quantum consciousness resonates through the akashic field of pure vibration energy."""\n'
        )
        results = audit_docstrings(src_dir=tmp_path, threshold=0.01)
        # This should have high esoteric density
        assert len(results) >= 1
        assert results[0].esoteric_density > 0.01

    def test_audit_grounded_metaphor_passes(self, tmp_path):
        f = tmp_path / "grounded.py"
        f.write_text(
            '"""Body Awareness -- computational interoception.\n\n'
            "Monitors the physical state of the substrate: database sizes, table\n"
            'health, storage growth, resource efficiency.\n"""\n'
        )
        results = audit_docstrings(src_dir=tmp_path, threshold=0.05)
        if results:
            # Should pass because technical grounding is present
            assert results[0].verdict in ("ACCEPT", "TRANSLATE")

    def test_audit_skips_short_docstrings(self, tmp_path):
        f = tmp_path / "short.py"
        f.write_text('"""Init."""\n')
        results = audit_docstrings(src_dir=tmp_path)
        # Should skip docstrings under 20 chars
        assert len(results) == 0

    def test_audit_returns_sorted_results(self, tmp_path):
        (tmp_path / "clean.py").write_text(
            '"""Simple utility for string formatting and validation."""\n'
        )
        (tmp_path / "esoteric.py").write_text(
            '"""Consciousness vibrates through quantum resonance energy fields of pure awareness."""\n'
        )
        results = audit_docstrings(src_dir=tmp_path, threshold=0.01)
        if len(results) >= 2:
            # Flagged items should come first
            flagged_indices = [i for i, r in enumerate(results) if r.flagged]
            clean_indices = [i for i, r in enumerate(results) if not r.flagged]
            if flagged_indices and clean_indices:
                assert max(flagged_indices) < min(clean_indices)


class TestAuditOnRealCodebase:
    """Run the audit on the actual DivineOS source."""

    def test_real_codebase_audit_runs(self):
        results = audit_docstrings()
        assert len(results) > 0

    def test_real_codebase_summary(self):
        summary = audit_summary()
        assert summary["modules_scanned"] > 0
        assert isinstance(summary["clean"], bool)
        assert isinstance(summary["avg_integrity"], float)

    def test_summary_distinguishes_substance_from_register(self):
        """Two-axis summary (claim 6b6f4e5a): clean iff no SUBSTANCE flags.
        Register flags don't make the codebase 'unclean.'"""
        summary = audit_summary()
        assert "substance_flagged_count" in summary
        assert "register_flagged_count" in summary
        # Clean signal tracks substance only — register flags are
        # informational and shouldn't pull clean=False.
        assert summary["clean"] == (summary["substance_flagged_count"] == 0)
        # Backward-compat: flagged_count aliases substance_flagged_count
        assert summary["flagged_count"] == summary["substance_flagged_count"]


class TestFormatting:
    """Output formatting."""

    def test_format_clean_results(self):
        results = [
            DocstringAuditResult(
                module_path="core/ledger.py",
                docstring="Append-only event store.",
                esoteric_density=0.0,
                integrity_score=0.85,
                verdict="ACCEPT",
                flagged=False,
            )
        ]
        output = format_audit_results(results)
        assert "1 modules" in output or "Scanned 1" in output
        assert "Substance flags: 0" in output
        assert "Register flags: 0" in output

    def test_format_flagged_results(self):
        # Two-axis (claim 6b6f4e5a): substance_flagged for QUARANTINE,
        # register_flagged for TRANSLATE. Test both surface differently.
        results = [
            DocstringAuditResult(
                module_path="core/quantum.py",
                docstring="Quantum consciousness resonates...",
                esoteric_density=0.15,
                integrity_score=0.20,
                verdict="QUARANTINE",
                terms_found=["consciousness", "quantum"],
                flagged=True,
                substance_flagged=True,
            )
        ]
        output = format_audit_results(results)
        assert "SUBSTANCE FLAGS" in output
        assert "quantum.py" in output

    def test_format_register_flagged_separately(self):
        """Register flags surface as informational, not as substance flags."""
        results = [
            DocstringAuditResult(
                module_path="core/council/experts/kahneman.py",
                docstring="Kahneman Deep Wisdom...",
                esoteric_density=0.06,
                integrity_score=0.78,
                verdict="TRANSLATE",
                terms_found=["wisdom", "intuition"],
                flagged=False,
                register_flagged=True,
            )
        ]
        output = format_audit_results(results)
        assert "REGISTER FLAGS" in output
        assert "kahneman.py" in output
        # Should NOT appear under SUBSTANCE FLAGS — that's the whole point.
        assert "SUBSTANCE FLAGS" not in output
