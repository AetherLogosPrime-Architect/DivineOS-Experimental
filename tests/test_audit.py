"""Tests for the test quality audit system."""

from pathlib import Path

from divineos.analysis.test_audit import (
    AuditSummary,
    _classify_assertion,
    _classify_coverage,
    _classify_data,
    audit_test_directory,
    format_audit_report,
)


class TestClassifyData:
    """Data source classification."""

    def test_real_db_detected(self):
        source = "conn = _get_connection()\ninit_db()\n"
        assert _classify_data(source) == "real_db"

    def test_synthetic_detected(self):
        source = "mock = Mock()\n"
        assert _classify_data(source) == "synthetic"

    def test_no_data_detected(self):
        source = "x = 1 + 1\nassert x == 2\n"
        assert _classify_data(source) == "no_data"

    def test_mock_overrides_real(self):
        source = "conn = _get_connection()\nmock = Mock()\n"
        assert _classify_data(source) == "synthetic"

    def test_env_var_is_real(self):
        source = 'monkeypatch.setenv("DIVINEOS_DB", str(db_path))\n'
        assert _classify_data(source) == "real_db"


class TestClassifyAssertion:
    """Assertion type classification."""

    def test_behavior_assertion(self):
        source = "assert result == 42\n"
        assert _classify_assertion(source) == "behavior"

    def test_structure_assertion(self):
        source = "assert isinstance(x, dict)\nassert len(items) == 3\n"
        assert _classify_assertion(source) == "structure"

    def test_mixed_assertion(self):
        source = "assert isinstance(x, dict)\nassert x == 42\n"
        assert _classify_assertion(source) == "mixed"

    def test_pytest_raises_is_behavior(self):
        source = "with pytest.raises(ValueError):\n    do_bad()\n"
        assert _classify_assertion(source) == "behavior"


class TestClassifyCoverage:
    """Coverage type classification."""

    def test_failure_mode_by_name(self):
        assert _classify_coverage("test_rejects_invalid_type", "x = 1") == "failure_mode"

    def test_failure_mode_by_raises(self):
        assert _classify_coverage("test_something", "pytest.raises(ValueError)") == "failure_mode"

    def test_happy_path(self):
        assert _classify_coverage("test_creates_entry", "assert kid") == "happy_path"

    def test_edge_case_by_name(self):
        assert _classify_coverage("test_boundary_value", "assert len(r) == 0") == "edge_case"

    def test_no_crash_pattern(self):
        assert _classify_coverage("test_no_data_returns_empty", "r = f()") == "failure_mode"


class TestAuditDirectory:
    """Full directory audit."""

    def test_audits_real_test_directory(self):
        test_dir = Path(__file__).parent
        summary = audit_test_directory(test_dir)
        assert summary.total_tests > 0
        assert summary.total_files > 0
        assert summary.total_tests == (summary.real_db + summary.synthetic + summary.no_data)
        assert summary.total_tests == (summary.behavior + summary.structure + summary.mixed)
        assert summary.total_tests == (
            summary.failure_mode + summary.edge_case + summary.happy_path
        )


class TestFormatReport:
    """Report formatting."""

    def test_format_includes_percentages(self):
        summary = AuditSummary(
            total_tests=100,
            total_files=10,
            real_db=60,
            synthetic=10,
            no_data=30,
            behavior=70,
            structure=20,
            mixed=10,
            failure_mode=25,
            edge_case=5,
            happy_path=70,
        )
        report = format_audit_report(summary)
        assert "100 tests" in report
        assert "60%" in report  # real_db
        assert "70%" in report  # behavior or happy_path

    def test_format_shows_inline_schemas(self):
        summary = AuditSummary(
            total_tests=10,
            total_files=1,
            inline_schemas=3,
            schema_files=["test_foo.py"],
        )
        report = format_audit_report(summary)
        assert "Inline CREATE TABLE" in report
        assert "test_foo.py" in report

    def test_format_clean_schemas(self):
        summary = AuditSummary(total_tests=10, total_files=1)
        report = format_audit_report(summary)
        assert "production init" in report
