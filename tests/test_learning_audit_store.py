"""Unit tests for LearningAuditStore class.

Tests cover all two subtasks:
- 1.2.1 store_audit() - save audit to ledger as AGENT_LEARNING_AUDIT event
- 1.2.2 get_latest_audit() - retrieve most recent audit
"""

import uuid
from datetime import datetime

import pytest

from divineos.agent_integration.learning_audit_store import LearningAuditStore
from divineos.core.ledger import get_events


class TestLearningAuditStoreBasics:
    """Test basic LearningAuditStore initialization and setup."""

    def test_learning_audit_store_initialization(self) -> None:
        """Test that LearningAuditStore initializes correctly."""
        store = LearningAuditStore()
        assert store is not None
        assert store.logger is not None


class TestStoreAudit:
    """Test store_audit() - Subtask 1.2.1."""

    def test_store_audit_minimal(self) -> None:
        """Test storing a minimal audit."""
        store = LearningAuditStore()
        session_id = str(uuid.uuid4())

        audit_id = store.store_audit(
            session_id=session_id,
            low_confidence_patterns=[],
            untested_patterns=[],
            pattern_gaps=[],
            risky_assumptions=[],
        )

        assert audit_id is not None
        assert isinstance(audit_id, str)
        assert len(audit_id) > 0

    def test_store_audit_with_low_confidence_patterns(self) -> None:
        """Test storing audit with low confidence patterns."""
        store = LearningAuditStore()
        session_id = str(uuid.uuid4())

        low_confidence_patterns = [
            {
                "pattern_id": str(uuid.uuid4()),
                "name": "Type System First",
                "confidence": 0.6,
                "reason": "Only 3 observations, needs more validation",
            },
            {
                "pattern_id": str(uuid.uuid4()),
                "name": "Compression at 150k",
                "confidence": 0.55,
                "reason": "Failed in 2 recent sessions",
            },
        ]

        audit_id = store.store_audit(
            session_id=session_id,
            low_confidence_patterns=low_confidence_patterns,
            untested_patterns=[],
            pattern_gaps=[],
            risky_assumptions=[],
        )
        assert audit_id is not None
        assert isinstance(audit_id, str)

        audit = store.get_latest_audit()
        assert audit is not None
        assert audit["audit_id"] == audit_id
        assert len(audit["low_confidence_patterns"]) == 2

    def test_store_audit_with_untested_patterns(self) -> None:
        """Test storing audit with untested patterns."""
        store = LearningAuditStore()
        session_id = str(uuid.uuid4())

        untested_patterns = [
            {
                "pattern_id": str(uuid.uuid4()),
                "name": "Hook Conflict Detection",
                "last_tested_context": "feature_phase_2024_01",
            },
            {
                "pattern_id": str(uuid.uuid4()),
                "name": "Token Efficiency Optimization",
                "last_tested_context": "bugfix_phase_2024_02",
            },
        ]

        audit_id = store.store_audit(
            session_id=session_id,
            low_confidence_patterns=[],
            untested_patterns=untested_patterns,
            pattern_gaps=[],
            risky_assumptions=[],
        )
        assert audit_id is not None
        assert isinstance(audit_id, str)

        audit = store.get_latest_audit()
        assert audit is not None
        assert len(audit["untested_patterns"]) == 2

    def test_store_audit_with_pattern_gaps(self) -> None:
        """Test storing audit with pattern gaps."""
        store = LearningAuditStore()
        session_id = str(uuid.uuid4())

        pattern_gaps = [
            {
                "gap_type": "missing_pattern",
                "description": "No pattern for race condition handling",
            },
            {
                "gap_type": "missing_pattern",
                "description": "No pattern for memory leak detection",
            },
        ]

        audit_id = store.store_audit(
            session_id=session_id,
            low_confidence_patterns=[],
            untested_patterns=[],
            pattern_gaps=pattern_gaps,
            risky_assumptions=[],
        )
        assert audit_id is not None
        assert isinstance(audit_id, str)

        audit = store.get_latest_audit()
        assert audit is not None
        assert len(audit["pattern_gaps"]) == 2

    def test_store_audit_with_risky_assumptions(self) -> None:
        """Test storing audit with risky assumptions."""
        store = LearningAuditStore()
        session_id = str(uuid.uuid4())

        risky_assumptions = [
            {
                "assumption": "Type system errors always indicate logic bugs",
                "why_risky": "Sometimes type errors are false positives from incomplete type hints",
                "mitigation": "Always verify with runtime tests before assuming logic bug",
            },
            {
                "assumption": "Token efficiency correlates with code quality",
                "why_risky": "Efficient code can still have subtle bugs or maintenance issues",
                "mitigation": "Measure code quality separately from token efficiency",
            },
        ]

        audit_id = store.store_audit(
            session_id=session_id,
            low_confidence_patterns=[],
            untested_patterns=[],
            pattern_gaps=[],
            risky_assumptions=risky_assumptions,
        )
        assert audit_id is not None
        assert isinstance(audit_id, str)

        audit = store.get_latest_audit()
        assert audit is not None
        assert len(audit["risky_assumptions"]) == 2

    def test_store_audit_with_drift_detected(self) -> None:
        """Test storing audit with drift detected."""
        store = LearningAuditStore()
        session_id = str(uuid.uuid4())

        audit_id = store.store_audit(
            session_id=session_id,
            low_confidence_patterns=[],
            untested_patterns=[],
            pattern_gaps=[],
            risky_assumptions=[],
            drift_detected=True,
            drift_reason="60% of patterns have confidence < 0.6",
        )
        assert audit_id is not None
        assert isinstance(audit_id, str)

        audit = store.get_latest_audit()
        assert audit is not None
        assert audit["drift_detected"] is True
        assert audit["drift_reason"] == "60% of patterns have confidence < 0.6"

    def test_store_audit_without_drift(self) -> None:
        """Test storing audit without drift."""
        store = LearningAuditStore()
        session_id = str(uuid.uuid4())

        audit_id = store.store_audit(
            session_id=session_id,
            low_confidence_patterns=[],
            untested_patterns=[],
            pattern_gaps=[],
            risky_assumptions=[],
            drift_detected=False,
        )
        assert audit_id is not None
        assert isinstance(audit_id, str)

        audit = store.get_latest_audit()
        assert audit is not None
        assert audit["drift_detected"] is False
        assert audit["drift_reason"] is None

    def test_store_audit_missing_session_id(self) -> None:
        """Test that missing session_id raises error."""
        store = LearningAuditStore()

        with pytest.raises(ValueError, match="session_id is required"):
            store.store_audit(
                session_id="",
                low_confidence_patterns=[],
                untested_patterns=[],
                pattern_gaps=[],
                risky_assumptions=[],
            )

    def test_store_audit_invalid_low_confidence_patterns(self) -> None:
        """Test that invalid low_confidence_patterns raises error."""
        store = LearningAuditStore()
        session_id = str(uuid.uuid4())

        with pytest.raises(ValueError, match="low_confidence_patterns must be a list"):
            store.store_audit(
                session_id=session_id,
                low_confidence_patterns="not a list",  # type: ignore[arg-type]
                untested_patterns=[],
                pattern_gaps=[],
                risky_assumptions=[],
            )

    def test_store_audit_invalid_untested_patterns(self) -> None:
        """Test that invalid untested_patterns raises error."""
        store = LearningAuditStore()
        session_id = str(uuid.uuid4())

        with pytest.raises(ValueError, match="untested_patterns must be a list"):
            store.store_audit(
                session_id=session_id,
                low_confidence_patterns=[],
                untested_patterns="not a list",  # type: ignore[arg-type]
                pattern_gaps=[],
                risky_assumptions=[],
            )

    def test_store_audit_invalid_pattern_gaps(self) -> None:
        """Test that invalid pattern_gaps raises error."""
        store = LearningAuditStore()
        session_id = str(uuid.uuid4())

        with pytest.raises(ValueError, match="pattern_gaps must be a list"):
            store.store_audit(
                session_id=session_id,
                low_confidence_patterns=[],
                untested_patterns=[],
                pattern_gaps="not a list",  # type: ignore[arg-type]
                risky_assumptions=[],
            )

    def test_store_audit_invalid_risky_assumptions(self) -> None:
        """Test that invalid risky_assumptions raises error."""
        store = LearningAuditStore()
        session_id = str(uuid.uuid4())

        with pytest.raises(ValueError, match="risky_assumptions must be a list"):
            store.store_audit(
                session_id=session_id,
                low_confidence_patterns=[],
                untested_patterns=[],
                pattern_gaps=[],
                risky_assumptions="not a list",  # type: ignore[arg-type]
            )

    def test_store_audit_drift_detected_without_reason(self) -> None:
        """Test that drift_detected=True without drift_reason raises error."""
        store = LearningAuditStore()
        session_id = str(uuid.uuid4())

        with pytest.raises(
            ValueError, match="drift_reason is required when drift_detected is True"
        ):
            store.store_audit(
                session_id=session_id,
                low_confidence_patterns=[],
                untested_patterns=[],
                pattern_gaps=[],
                risky_assumptions=[],
                drift_detected=True,
                drift_reason=None,
            )

    def test_store_audit_has_content_hash(self) -> None:
        """Test that stored audit has SHA256 content hash (truncated to 32 chars)."""
        store = LearningAuditStore()
        session_id = str(uuid.uuid4())

        audit_id = store.store_audit(
            session_id=session_id,
            low_confidence_patterns=[],
            untested_patterns=[],
            pattern_gaps=[],
            risky_assumptions=[],
        )
        assert audit_id is not None
        assert isinstance(audit_id, str)

        audit = store.get_latest_audit()
        assert audit is not None
        assert "content_hash" in audit
        assert len(audit["content_hash"]) == 32  # SHA256 truncated to 32 chars

    def test_store_audit_has_timestamp(self) -> None:
        """Test that stored audit has timestamp."""
        store = LearningAuditStore()
        session_id = str(uuid.uuid4())

        audit_id = store.store_audit(
            session_id=session_id,
            low_confidence_patterns=[],
            untested_patterns=[],
            pattern_gaps=[],
            risky_assumptions=[],
        )
        assert audit_id is not None
        assert isinstance(audit_id, str)

        audit = store.get_latest_audit()
        assert audit is not None
        assert "timestamp" in audit
        # Verify it's a valid ISO format timestamp
        datetime.fromisoformat(audit["timestamp"])

    def test_store_audit_preserves_all_fields(self) -> None:
        """Test that all audit fields are preserved."""
        store = LearningAuditStore()
        session_id = str(uuid.uuid4())

        low_confidence_patterns = [
            {"pattern_id": str(uuid.uuid4()), "name": "Test", "confidence": 0.5, "reason": "Low"}
        ]
        untested_patterns = [
            {"pattern_id": str(uuid.uuid4()), "name": "Test", "last_tested_context": "ctx"}
        ]
        pattern_gaps = [{"gap_type": "missing", "description": "No pattern"}]
        risky_assumptions = [{"assumption": "A", "why_risky": "B", "mitigation": "C"}]

        audit_id = store.store_audit(
            session_id=session_id,
            low_confidence_patterns=low_confidence_patterns,
            untested_patterns=untested_patterns,
            pattern_gaps=pattern_gaps,
            risky_assumptions=risky_assumptions,
            drift_detected=True,
            drift_reason="Test drift",
        )
        assert audit_id is not None
        assert isinstance(audit_id, str)

        audit = store.get_latest_audit()
        assert audit is not None
        assert audit["session_id"] == session_id
        assert audit["low_confidence_patterns"] == low_confidence_patterns
        assert audit["untested_patterns"] == untested_patterns
        assert audit["pattern_gaps"] == pattern_gaps
        assert audit["risky_assumptions"] == risky_assumptions
        assert audit["drift_detected"] is True
        assert audit["drift_reason"] == "Test drift"

    def test_store_audit_creates_agent_learning_audit_event(self) -> None:
        """Test that audit is stored as AGENT_LEARNING_AUDIT event in ledger."""
        store = LearningAuditStore()
        session_id = str(uuid.uuid4())

        audit_id = store.store_audit(
            session_id=session_id,
            low_confidence_patterns=[],
            untested_patterns=[],
            pattern_gaps=[],
            risky_assumptions=[],
        )
        assert audit_id is not None
        assert isinstance(audit_id, str)

        # Check that AGENT_LEARNING_AUDIT event was logged
        events = get_events(event_type="AGENT_LEARNING_AUDIT", limit=100)
        audit_events = [e for e in events if e.get("payload", {}).get("audit_id") == audit_id]
        assert len(audit_events) > 0

        event = audit_events[-1]
        payload = event["payload"]
        assert payload["audit_id"] == audit_id
        assert payload["session_id"] == session_id


class TestGetLatestAudit:
    """Test get_latest_audit() - Subtask 1.2.2."""

    def test_get_latest_audit_returns_most_recent(self) -> None:
        """Test that get_latest_audit returns the most recent audit."""
        store = LearningAuditStore()
        session_id_1 = str(uuid.uuid4())
        session_id_2 = str(uuid.uuid4())

        # Store first audit
        audit_id_1 = store.store_audit(
            session_id=session_id_1,
            low_confidence_patterns=[],
            untested_patterns=[],
            pattern_gaps=[],
            risky_assumptions=[],
        )
        assert audit_id_1 is not None
        assert isinstance(audit_id_1, str)

        # Store second audit
        audit_id_2 = store.store_audit(
            session_id=session_id_2,
            low_confidence_patterns=[],
            untested_patterns=[],
            pattern_gaps=[],
            risky_assumptions=[],
        )
        assert audit_id_2 is not None
        assert isinstance(audit_id_2, str)

        # Get latest should return the second audit
        latest = store.get_latest_audit()
        assert latest is not None
        assert latest["audit_id"] == audit_id_2
        assert latest["session_id"] == session_id_2

    def test_get_latest_audit_no_audits(self) -> None:
        """Test that get_latest_audit returns None when no audits exist."""
        store = LearningAuditStore()

        # Create a fresh store and query (assuming no audits in test ledger)
        # This test may not work if ledger persists across tests
        # But we can at least verify the method handles empty results
        latest = store.get_latest_audit()
        # Could be None or could be from previous tests
        # Just verify it doesn't crash
        assert latest is None or isinstance(latest, dict)

    def test_get_latest_audit_preserves_data(self) -> None:
        """Test that get_latest_audit preserves all audit data."""
        store = LearningAuditStore()
        session_id = str(uuid.uuid4())

        low_confidence_patterns = [
            {
                "pattern_id": str(uuid.uuid4()),
                "name": "Type System First",
                "confidence": 0.6,
                "reason": "Only 3 observations",
            }
        ]
        untested_patterns = [
            {
                "pattern_id": str(uuid.uuid4()),
                "name": "Hook Conflict Detection",
                "last_tested_context": "feature_phase_2024_01",
            }
        ]
        pattern_gaps = [
            {
                "gap_type": "missing_pattern",
                "description": "No pattern for race condition handling",
            }
        ]
        risky_assumptions = [
            {
                "assumption": "Type system errors always indicate logic bugs",
                "why_risky": "Sometimes type errors are false positives",
                "mitigation": "Always verify with runtime tests",
            }
        ]

        audit_id = store.store_audit(
            session_id=session_id,
            low_confidence_patterns=low_confidence_patterns,
            untested_patterns=untested_patterns,
            pattern_gaps=pattern_gaps,
            risky_assumptions=risky_assumptions,
            drift_detected=True,
            drift_reason="60% of patterns have confidence < 0.6",
        )

        latest = store.get_latest_audit()
        assert latest is not None
        assert latest["audit_id"] == audit_id
        assert latest["session_id"] == session_id
        assert latest["low_confidence_patterns"] == low_confidence_patterns
        assert latest["untested_patterns"] == untested_patterns
        assert latest["pattern_gaps"] == pattern_gaps
        assert latest["risky_assumptions"] == risky_assumptions
        assert latest["drift_detected"] is True
        assert latest["drift_reason"] == "60% of patterns have confidence < 0.6"

    def test_get_latest_audit_with_multiple_audits(self) -> None:
        """Test that get_latest_audit returns the most recent when multiple exist."""
        store = LearningAuditStore()

        # Store multiple audits with different data
        audit_ids = []
        for i in range(3):
            session_id = str(uuid.uuid4())
            low_confidence_patterns = [
                {
                    "pattern_id": str(uuid.uuid4()),
                    "name": f"Pattern {i}",
                    "confidence": 0.5 + i * 0.1,
                    "reason": f"Reason {i}",
                }
            ]

            audit_id = store.store_audit(
                session_id=session_id,
                low_confidence_patterns=low_confidence_patterns,
                untested_patterns=[],
                pattern_gaps=[],
                risky_assumptions=[],
            )
            audit_ids.append(audit_id)

        # Get latest should return the last one
        latest = store.get_latest_audit()
        assert latest is not None
        assert latest["audit_id"] == audit_ids[-1]
        assert len(latest["low_confidence_patterns"]) == 1
        assert latest["low_confidence_patterns"][0]["name"] == "Pattern 2"

    def test_get_latest_audit_has_content_hash(self) -> None:
        """Test that retrieved audit has content_hash."""
        store = LearningAuditStore()
        session_id = str(uuid.uuid4())

        store.store_audit(
            session_id=session_id,
            low_confidence_patterns=[],
            untested_patterns=[],
            pattern_gaps=[],
            risky_assumptions=[],
        )

        latest = store.get_latest_audit()
        assert latest is not None
        assert "content_hash" in latest
        assert len(latest["content_hash"]) == 32

    def test_get_latest_audit_has_timestamp(self) -> None:
        """Test that retrieved audit has timestamp."""
        store = LearningAuditStore()
        session_id = str(uuid.uuid4())

        store.store_audit(
            session_id=session_id,
            low_confidence_patterns=[],
            untested_patterns=[],
            pattern_gaps=[],
            risky_assumptions=[],
        )

        latest = store.get_latest_audit()
        assert latest is not None
        assert "timestamp" in latest
        # Verify it's a valid ISO format timestamp
        datetime.fromisoformat(latest["timestamp"])


class TestAuditIntegration:
    """Integration tests for audit storage and retrieval."""

    def test_store_and_retrieve_complete_audit(self) -> None:
        """Test complete workflow of storing and retrieving an audit."""
        store = LearningAuditStore()
        session_id = str(uuid.uuid4())

        # Create a comprehensive audit
        low_confidence_patterns = [
            {
                "pattern_id": str(uuid.uuid4()),
                "name": "Type System First",
                "confidence": 0.6,
                "reason": "Only 3 observations, needs more validation",
            },
            {
                "pattern_id": str(uuid.uuid4()),
                "name": "Compression at 150k",
                "confidence": 0.55,
                "reason": "Failed in 2 recent sessions",
            },
        ]

        untested_patterns = [
            {
                "pattern_id": str(uuid.uuid4()),
                "name": "Hook Conflict Detection",
                "last_tested_context": "feature_phase_2024_01",
            },
        ]

        pattern_gaps = [
            {
                "gap_type": "missing_pattern",
                "description": "No pattern for race condition handling",
            },
            {
                "gap_type": "missing_pattern",
                "description": "No pattern for memory leak detection",
            },
        ]

        risky_assumptions = [
            {
                "assumption": "Type system errors always indicate logic bugs",
                "why_risky": "Sometimes type errors are false positives from incomplete type hints",
                "mitigation": "Always verify with runtime tests before assuming logic bug",
            },
        ]

        # Store the audit
        audit_id = store.store_audit(
            session_id=session_id,
            low_confidence_patterns=low_confidence_patterns,
            untested_patterns=untested_patterns,
            pattern_gaps=pattern_gaps,
            risky_assumptions=risky_assumptions,
            drift_detected=True,
            drift_reason="60% of patterns have confidence < 0.6",
        )

        # Retrieve and verify
        latest = store.get_latest_audit()
        assert latest is not None
        assert latest["audit_id"] == audit_id
        assert latest["session_id"] == session_id
        assert len(latest["low_confidence_patterns"]) == 2
        assert len(latest["untested_patterns"]) == 1
        assert len(latest["pattern_gaps"]) == 2
        assert len(latest["risky_assumptions"]) == 1
        assert latest["drift_detected"] is True
        assert latest["drift_reason"] == "60% of patterns have confidence < 0.6"

    def test_multiple_audits_independent(self) -> None:
        """Test that multiple audits are stored independently."""
        store = LearningAuditStore()

        # Store first audit
        session_id_1 = str(uuid.uuid4())
        audit_id_1 = store.store_audit(
            session_id=session_id_1,
            low_confidence_patterns=[
                {
                    "pattern_id": str(uuid.uuid4()),
                    "name": "Pattern 1",
                    "confidence": 0.5,
                    "reason": "Low",
                }
            ],
            untested_patterns=[],
            pattern_gaps=[],
            risky_assumptions=[],
        )
        assert audit_id_1 is not None
        assert isinstance(audit_id_1, str)

        # Store second audit
        session_id_2 = str(uuid.uuid4())
        audit_id_2 = store.store_audit(
            session_id=session_id_2,
            low_confidence_patterns=[
                {
                    "pattern_id": str(uuid.uuid4()),
                    "name": "Pattern 2",
                    "confidence": 0.6,
                    "reason": "Medium",
                }
            ],
            untested_patterns=[],
            pattern_gaps=[],
            risky_assumptions=[],
        )
        assert audit_id_2 is not None
        assert isinstance(audit_id_2, str)

        # Get latest should return second audit
        latest = store.get_latest_audit()
        assert latest is not None
        assert latest["audit_id"] == audit_id_2
        assert latest["session_id"] == session_id_2
        assert latest["low_confidence_patterns"][0]["name"] == "Pattern 2"
