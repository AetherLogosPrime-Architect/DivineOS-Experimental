"""Tests for violations CLI commands."""

from divineos.violations_cli.violations_command import (
    ViolationsCommand,
    ViolationSeverityFilter,
    get_violations_command,
)


class TestViolationsCommand:
    """Test ViolationsCommand initialization."""

    def test_violations_command_creation(self):
        """Test creating violations command."""
        cmd = ViolationsCommand()
        assert cmd is not None
        assert cmd.ledger is not None

    def test_get_violations_command_singleton(self):
        """Test singleton pattern for violations command."""
        cmd1 = get_violations_command()
        cmd2 = get_violations_command()
        assert cmd1 is cmd2


class TestQueryViolationsBySession:
    """Test querying violations by session."""

    def test_query_violations_by_session_empty(self):
        """Test querying violations for session with no violations."""
        cmd = ViolationsCommand()
        violations = cmd.query_violations_by_session("session_123")
        assert isinstance(violations, list)

    def test_query_violations_by_session_with_filter(self):
        """Test querying violations with severity filter."""
        cmd = ViolationsCommand()
        violations = cmd.query_violations_by_session(
            "session_123",
            severity_filter=ViolationSeverityFilter.HIGH,
        )
        assert isinstance(violations, list)


class TestQueryRecentViolations:
    """Test querying recent violations."""

    def test_query_recent_violations_default_limit(self):
        """Test querying recent violations with default limit."""
        cmd = ViolationsCommand()
        violations = cmd.query_recent_violations()
        assert isinstance(violations, list)
        assert len(violations) <= 10

    def test_query_recent_violations_custom_limit(self):
        """Test querying recent violations with custom limit."""
        cmd = ViolationsCommand()
        violations = cmd.query_recent_violations(limit=5)
        assert isinstance(violations, list)
        assert len(violations) <= 5

    def test_query_recent_violations_with_filter(self):
        """Test querying recent violations with severity filter."""
        cmd = ViolationsCommand()
        violations = cmd.query_recent_violations(
            limit=10,
            severity_filter=ViolationSeverityFilter.CRITICAL,
        )
        assert isinstance(violations, list)


class TestQueryViolationsBySeverity:
    """Test querying violations by severity."""

    def test_query_violations_by_severity_critical(self):
        """Test querying CRITICAL violations."""
        cmd = ViolationsCommand()
        violations = cmd.query_violations_by_severity(ViolationSeverityFilter.CRITICAL)
        assert isinstance(violations, list)

    def test_query_violations_by_severity_high(self):
        """Test querying HIGH violations."""
        cmd = ViolationsCommand()
        violations = cmd.query_violations_by_severity(ViolationSeverityFilter.HIGH)
        assert isinstance(violations, list)

    def test_query_violations_by_severity_medium(self):
        """Test querying MEDIUM violations."""
        cmd = ViolationsCommand()
        violations = cmd.query_violations_by_severity(ViolationSeverityFilter.MEDIUM)
        assert isinstance(violations, list)

    def test_query_violations_by_severity_low(self):
        """Test querying LOW violations."""
        cmd = ViolationsCommand()
        violations = cmd.query_violations_by_severity(ViolationSeverityFilter.LOW)
        assert isinstance(violations, list)


class TestQueryContradictions:
    """Test querying contradictions."""

    def test_query_contradictions_no_filter(self):
        """Test querying all contradictions."""
        cmd = ViolationsCommand()
        contradictions = cmd.query_contradictions()
        assert isinstance(contradictions, list)

    def test_query_contradictions_by_type(self):
        """Test querying contradictions by fact type."""
        cmd = ViolationsCommand()
        contradictions = cmd.query_contradictions(fact_type="math")
        assert isinstance(contradictions, list)

    def test_query_contradictions_with_severity_filter(self):
        """Test querying contradictions with severity filter."""
        cmd = ViolationsCommand()
        contradictions = cmd.query_contradictions(severity_filter=ViolationSeverityFilter.CRITICAL)
        assert isinstance(contradictions, list)

    def test_query_contradictions_by_type_and_severity(self):
        """Test querying contradictions by type and severity."""
        cmd = ViolationsCommand()
        contradictions = cmd.query_contradictions(
            fact_type="math",
            severity_filter=ViolationSeverityFilter.HIGH,
        )
        assert isinstance(contradictions, list)


class TestFormatViolationForDisplay:
    """Test formatting violations for display."""

    def test_format_violation_basic(self):
        """Test formatting basic violation."""
        cmd = ViolationsCommand()
        violation = {
            "id": "v_123",
            "severity": "HIGH",
            "type": "CONTRADICTION",
            "timestamp": "2026-03-19T10:00:00Z",
            "message": "Test violation",
        }
        formatted = cmd.format_violation_for_display(violation)
        assert "v_123" in formatted
        assert "HIGH" in formatted
        assert "CONTRADICTION" in formatted

    def test_format_violation_with_context(self):
        """Test formatting violation with context."""
        cmd = ViolationsCommand()
        violation = {
            "id": "v_123",
            "severity": "CRITICAL",
            "type": "CONTRADICTION",
            "timestamp": "2026-03-19T10:00:00Z",
            "message": "Test violation",
            "context": {
                "superseded_fact_id": "f_391",
                "superseding_fact_id": "f_500",
            },
        }
        formatted = cmd.format_violation_for_display(violation)
        assert "v_123" in formatted
        assert "CRITICAL" in formatted
        assert "f_391" in formatted or "Context" in formatted

    def test_format_violation_missing_fields(self):
        """Test formatting violation with missing fields."""
        cmd = ViolationsCommand()
        violation = {"id": "v_123"}
        formatted = cmd.format_violation_for_display(violation)
        assert "v_123" in formatted
        assert "N/A" in formatted


class TestFormatContradictionForDisplay:
    """Test formatting contradictions for display."""

    def test_format_contradiction_basic(self):
        """Test formatting basic contradiction."""
        cmd = ViolationsCommand()
        contradiction = {
            "id": "c_123",
            "fact_type": "math",
            "fact_key": "17x23",
            "fact1_value": 391,
            "fact2_value": 500,
            "severity": "CRITICAL",
            "timestamp": "2026-03-19T10:00:00Z",
        }
        formatted = cmd.format_contradiction_for_display(contradiction)
        assert "c_123" in formatted
        assert "math" in formatted
        assert "17x23" in formatted
        assert "CRITICAL" in formatted

    def test_format_contradiction_missing_fields(self):
        """Test formatting contradiction with missing fields."""
        cmd = ViolationsCommand()
        contradiction = {"id": "c_123"}
        formatted = cmd.format_contradiction_for_display(contradiction)
        assert "c_123" in formatted
        assert "N/A" in formatted


class TestEventToViolation:
    """Test converting events to violations."""

    def test_event_to_violation_basic(self):
        """Test converting basic event to violation."""
        cmd = ViolationsCommand()
        event = {
            "id": "e_123",
            "severity": "HIGH",
            "timestamp": "2026-03-19T10:00:00Z",
            "reason": "NEWER_FACT",
            "superseded_fact_id": "f_391",
            "superseding_fact_id": "f_500",
        }
        violation = cmd._event_to_violation(event)
        assert violation is not None
        assert violation["id"] == "e_123"
        assert violation["type"] == "CONTRADICTION"
        assert violation["severity"] == "HIGH"

    def test_event_to_violation_with_session_filter(self):
        """Test converting event to violation with session filter."""
        cmd = ViolationsCommand()
        event = {
            "id": "e_123",
            "severity": "HIGH",
            "timestamp": "2026-03-19T10:00:00Z",
            "reason": "NEWER_FACT",
            "session_id": "session_123",
        }
        violation = cmd._event_to_violation(event, session_id="session_123")
        assert violation is not None

    def test_event_to_violation_session_mismatch(self):
        """Test converting event with mismatched session."""
        cmd = ViolationsCommand()
        event = {
            "id": "e_123",
            "session_id": "session_123",
        }
        violation = cmd._event_to_violation(event, session_id="session_456")
        assert violation is None

    def test_event_to_violation_none(self):
        """Test converting None event."""
        cmd = ViolationsCommand()
        violation = cmd._event_to_violation(None)
        assert violation is None


class TestEventToContradiction:
    """Test converting events to contradictions."""

    def test_event_to_contradiction_basic(self):
        """Test converting basic event to contradiction."""
        cmd = ViolationsCommand()
        event = {
            "id": "e_123",
            "fact_type": "math",
            "fact_key": "17x23",
            "fact1_value": 391,
            "fact2_value": 500,
            "severity": "CRITICAL",
            "timestamp": "2026-03-19T10:00:00Z",
            "reason": "NEWER_FACT",
        }
        contradiction = cmd._event_to_contradiction(event)
        assert contradiction is not None
        assert contradiction["id"] == "e_123"
        assert contradiction["fact_type"] == "math"
        assert contradiction["fact_key"] == "17x23"
        assert contradiction["severity"] == "CRITICAL"

    def test_event_to_contradiction_none(self):
        """Test converting None event."""
        cmd = ViolationsCommand()
        contradiction = cmd._event_to_contradiction(None)
        assert contradiction is None


class TestMatchesSeverity:
    """Test severity matching logic."""

    def test_matches_severity_critical_filter(self):
        """Test matching CRITICAL severity filter."""
        cmd = ViolationsCommand()
        item = {"severity": "CRITICAL"}
        assert cmd._matches_severity(item, ViolationSeverityFilter.CRITICAL)

    def test_matches_severity_high_includes_critical(self):
        """Test HIGH filter includes CRITICAL."""
        cmd = ViolationsCommand()
        item = {"severity": "CRITICAL"}
        assert cmd._matches_severity(item, ViolationSeverityFilter.HIGH)

    def test_matches_severity_high_excludes_medium(self):
        """Test HIGH filter excludes MEDIUM."""
        cmd = ViolationsCommand()
        item = {"severity": "MEDIUM"}
        assert not cmd._matches_severity(item, ViolationSeverityFilter.HIGH)

    def test_matches_severity_low_includes_all(self):
        """Test LOW filter includes all severities."""
        cmd = ViolationsCommand()
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            item = {"severity": severity}
            assert cmd._matches_severity(item, ViolationSeverityFilter.LOW)

    def test_matches_severity_missing_field(self):
        """Test matching with missing severity field."""
        cmd = ViolationsCommand()
        item = {}
        # Should default to MEDIUM
        assert cmd._matches_severity(item, ViolationSeverityFilter.LOW)
        assert cmd._matches_severity(item, ViolationSeverityFilter.MEDIUM)
        assert not cmd._matches_severity(item, ViolationSeverityFilter.HIGH)


class TestViolationSeverityFilter:
    """Test ViolationSeverityFilter enum."""

    def test_severity_filter_values(self):
        """Test severity filter enum values."""
        assert ViolationSeverityFilter.CRITICAL.value == "CRITICAL"
        assert ViolationSeverityFilter.HIGH.value == "HIGH"
        assert ViolationSeverityFilter.MEDIUM.value == "MEDIUM"
        assert ViolationSeverityFilter.LOW.value == "LOW"

    def test_severity_filter_members(self):
        """Test severity filter enum members."""
        members = list(ViolationSeverityFilter)
        assert len(members) == 4
        assert ViolationSeverityFilter.CRITICAL in members
        assert ViolationSeverityFilter.HIGH in members
        assert ViolationSeverityFilter.MEDIUM in members
        assert ViolationSeverityFilter.LOW in members
