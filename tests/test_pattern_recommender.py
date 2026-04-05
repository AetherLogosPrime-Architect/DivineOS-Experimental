"""Unit tests for PatternRecommender class.

Tests cover all subtasks:
- 3.1.1 load_humility_audit() - load latest audit and display warnings
- 3.1.2 match_preconditions() - filter patterns by current context
- 3.1.3 rank_by_confidence() - sort matched patterns
- 3.1.4 generate_recommendation() - create recommendation with reasoning
- 3.1.5 record_decision() - store AGENT_DECISION event
- 3.2 Recommendation explanation with confidence, preconditions, alternatives, uncertainty, failure modes
"""

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import patch


from divineos.agent_integration.pattern_recommender import PatternRecommender
from divineos.agent_integration.pattern_store import PatternStore
from divineos.agent_integration.learning_audit_store import LearningAuditStore
from divineos.agent_integration.decision_store import DecisionStore


class TestPatternRecommenderBasics:
    """Test basic PatternRecommender initialization and setup."""

    def test_recommender_initialization(self) -> None:
        """Test that PatternRecommender initializes correctly."""
        recommender = PatternRecommender()
        assert recommender is not None
        assert recommender.logger is not None
        assert isinstance(recommender.pattern_store, PatternStore)
        assert isinstance(recommender.audit_store, LearningAuditStore)
        assert isinstance(recommender.decision_store, DecisionStore)
        assert recommender.current_audit is None
        assert recommender.matched_patterns == []


class TestLoadHumilityAudit:
    """Test load_humility_audit() method."""

    def test_load_humility_audit_no_audit_found(self) -> None:
        """Test loading audit when none exists (first session)."""
        recommender = PatternRecommender()

        # Mock the audit store to return None
        with patch.object(recommender.audit_store, "get_latest_audit", return_value=None):
            result = recommender.load_humility_audit()

        assert result is None
        assert recommender.current_audit is None

    def test_load_humility_audit_with_low_confidence_patterns(self) -> None:
        """Test loading audit with low-confidence pattern warnings."""
        recommender = PatternRecommender()

        audit = {
            "audit_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "low_confidence_patterns": [
                {
                    "pattern_id": str(uuid.uuid4()),
                    "name": "Low Confidence Pattern",
                    "confidence": 0.5,
                    "reason": "Limited evidence",
                }
            ],
            "untested_patterns": [],
            "pattern_gaps": [],
            "risky_assumptions": [],
            "drift_detected": False,
            "drift_reason": None,
        }

        with patch.object(recommender.audit_store, "get_latest_audit", return_value=audit):
            result = recommender.load_humility_audit()

        assert result is not None
        assert result["audit_id"] == audit["audit_id"]
        assert recommender.current_audit == audit

    def test_load_humility_audit_with_drift_detection(self) -> None:
        """Test loading audit with drift detection."""
        recommender = PatternRecommender()

        audit = {
            "audit_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "low_confidence_patterns": [],
            "untested_patterns": [],
            "pattern_gaps": [],
            "risky_assumptions": [],
            "drift_detected": True,
            "drift_reason": "50% of patterns have confidence < 0.6",
        }

        with patch.object(recommender.audit_store, "get_latest_audit", return_value=audit):
            result = recommender.load_humility_audit()

        assert result is not None
        assert result["drift_detected"] is True

    def test_load_humility_audit_with_all_warnings(self) -> None:
        """Test loading audit with all types of warnings."""
        recommender = PatternRecommender()

        audit = {
            "audit_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "low_confidence_patterns": [
                {
                    "pattern_id": str(uuid.uuid4()),
                    "name": "Pattern A",
                    "confidence": 0.6,
                    "reason": "Limited evidence",
                }
            ],
            "untested_patterns": [
                {
                    "pattern_id": str(uuid.uuid4()),
                    "name": "Pattern B",
                    "last_tested_context": "never",
                }
            ],
            "pattern_gaps": [
                {
                    "gap_type": "race_condition_handling",
                    "description": "No pattern for race condition handling",
                }
            ],
            "risky_assumptions": [
                {
                    "assumption": "Token budget always > 100k",
                    "why_risky": "Could be wrong in constrained environments",
                    "mitigation": "Add token_budget_min precondition",
                }
            ],
            "drift_detected": False,
            "drift_reason": None,
        }

        with patch.object(recommender.audit_store, "get_latest_audit", return_value=audit):
            result = recommender.load_humility_audit()

        assert result is not None
        assert len(result["low_confidence_patterns"]) == 1
        assert len(result["untested_patterns"]) == 1
        assert len(result["pattern_gaps"]) == 1
        assert len(result["risky_assumptions"]) == 1


class TestMatchPreconditions:
    """Test match_preconditions() method."""

    def test_match_preconditions_no_context(self) -> None:
        """Test matching with no context provided."""
        recommender = PatternRecommender()

        result = recommender.match_preconditions({})

        assert result == []

    def test_match_preconditions_returns_matched_patterns(self) -> None:
        """Test that matched patterns are returned."""
        recommender = PatternRecommender()

        patterns = [
            {
                "pattern_id": str(uuid.uuid4()),
                "name": "Pattern A",
                "confidence": 0.8,
                "preconditions": {"phase": "bugfix"},
            }
        ]

        context = {"phase": "bugfix", "token_budget": 150000}

        with patch.object(recommender.pattern_store, "query_patterns", return_value=patterns):
            result = recommender.match_preconditions(context)

        assert len(result) == 1
        assert result[0]["name"] == "Pattern A"
        assert recommender.matched_patterns == patterns

    def test_match_preconditions_empty_result(self) -> None:
        """Test matching when no patterns match."""
        recommender = PatternRecommender()

        context = {"phase": "feature", "token_budget": 50000}

        with patch.object(recommender.pattern_store, "query_patterns", return_value=[]):
            result = recommender.match_preconditions(context)

        assert result == []
        assert recommender.matched_patterns == []

    def test_match_preconditions_multiple_patterns(self) -> None:
        """Test matching multiple patterns."""
        recommender = PatternRecommender()

        patterns = [
            {
                "pattern_id": str(uuid.uuid4()),
                "name": "Pattern A",
                "confidence": 0.8,
            },
            {
                "pattern_id": str(uuid.uuid4()),
                "name": "Pattern B",
                "confidence": 0.7,
            },
        ]

        context = {"phase": "bugfix"}

        with patch.object(recommender.pattern_store, "query_patterns", return_value=patterns):
            result = recommender.match_preconditions(context)

        assert len(result) == 2


class TestRankByConfidence:
    """Test rank_by_confidence() method."""

    def test_rank_by_confidence_empty_list(self) -> None:
        """Test ranking with empty pattern list."""
        recommender = PatternRecommender()

        result = recommender.rank_by_confidence([])

        assert result == []

    def test_rank_by_confidence_single_pattern(self) -> None:
        """Test ranking with single pattern."""
        recommender = PatternRecommender()

        patterns = [
            {
                "pattern_id": str(uuid.uuid4()),
                "name": "Pattern A",
                "confidence": 0.8,
            }
        ]

        result = recommender.rank_by_confidence(patterns)

        assert len(result) == 1
        assert result[0]["name"] == "Pattern A"

    def test_rank_by_confidence_sorts_descending(self) -> None:
        """Test that patterns are sorted by confidence (highest first)."""
        recommender = PatternRecommender()

        patterns = [
            {
                "pattern_id": str(uuid.uuid4()),
                "name": "Pattern A",
                "confidence": 0.6,
            },
            {
                "pattern_id": str(uuid.uuid4()),
                "name": "Pattern B",
                "confidence": 0.9,
            },
            {
                "pattern_id": str(uuid.uuid4()),
                "name": "Pattern C",
                "confidence": 0.7,
            },
        ]

        result = recommender.rank_by_confidence(patterns)

        assert len(result) == 3
        assert result[0]["name"] == "Pattern B"  # 0.9
        assert result[1]["name"] == "Pattern C"  # 0.7
        assert result[2]["name"] == "Pattern A"  # 0.6

    def test_rank_by_confidence_uses_matched_patterns_if_none_provided(self) -> None:
        """Test that matched_patterns are used if no patterns provided."""
        recommender = PatternRecommender()

        patterns = [
            {
                "pattern_id": str(uuid.uuid4()),
                "name": "Pattern A",
                "confidence": 0.8,
            }
        ]

        recommender.matched_patterns = patterns

        result = recommender.rank_by_confidence(None)

        assert len(result) == 1
        assert result[0]["name"] == "Pattern A"


class TestGenerateRecommendation:
    """Test generate_recommendation() method."""

    def test_generate_recommendation_no_patterns_match(self) -> None:
        """Test recommendation when no patterns match (fallback)."""
        recommender = PatternRecommender()

        context = {"phase": "feature", "token_budget": 50000}

        with patch.object(recommender, "load_humility_audit", return_value=None):
            with patch.object(recommender.pattern_store, "query_patterns", return_value=[]):
                result = recommender.generate_recommendation(context)

        assert result is not None
        assert result["pattern_id"] == "fallback"
        assert result["confidence"] == 0.3
        assert result["pattern_name"] == "Generic Approach"

    def test_generate_recommendation_with_matched_pattern(self) -> None:
        """Test recommendation with matched pattern."""
        recommender = PatternRecommender()

        pattern = {
            "pattern_id": str(uuid.uuid4()),
            "name": "Test Pattern",
            "description": "A test pattern",
            "confidence": 0.85,
            "occurrences": 10,
            "successes": 8,
            "success_rate": 0.8,
            "pattern_type": "structural",
            "preconditions": {"phase": "bugfix"},
        }

        context = {"phase": "bugfix", "token_budget": 150000}

        with patch.object(recommender, "load_humility_audit", return_value=None):
            with patch.object(recommender.pattern_store, "query_patterns", return_value=[pattern]):
                result = recommender.generate_recommendation(context)

        assert result is not None
        assert result["pattern_id"] == pattern["pattern_id"]
        assert result["pattern_name"] == "Test Pattern"
        assert result["confidence"] == 0.85
        assert result["supporting_evidence"]["occurrences"] == 10
        assert result["supporting_evidence"]["successes"] == 8
        assert result["supporting_evidence"]["success_rate"] == 0.8

    def test_generate_recommendation_includes_explanation(self) -> None:
        """Test that recommendation includes explanation."""
        recommender = PatternRecommender()

        pattern = {
            "pattern_id": str(uuid.uuid4()),
            "name": "Test Pattern",
            "description": "A test pattern",
            "confidence": 0.85,
            "occurrences": 10,
            "successes": 8,
            "success_rate": 0.8,
            "pattern_type": "structural",
            "preconditions": {"phase": "bugfix"},
        }

        context = {"phase": "bugfix"}

        with patch.object(recommender, "load_humility_audit", return_value=None):
            with patch.object(recommender.pattern_store, "query_patterns", return_value=[pattern]):
                result = recommender.generate_recommendation(context)

        assert result is not None
        assert "explanation" in result
        assert "Test Pattern" in result["explanation"]
        assert "10 observations" in result["explanation"]

    def test_generate_recommendation_includes_uncertainty_statement(self) -> None:
        """Test that recommendation includes uncertainty statement."""
        recommender = PatternRecommender()

        pattern = {
            "pattern_id": str(uuid.uuid4()),
            "name": "Test Pattern",
            "description": "A test pattern",
            "confidence": 0.75,
            "occurrences": 5,
            "successes": 4,
            "success_rate": 0.8,
            "pattern_type": "tactical",
            "preconditions": {},
        }

        context = {"phase": "bugfix"}

        with patch.object(recommender, "load_humility_audit", return_value=None):
            with patch.object(recommender.pattern_store, "query_patterns", return_value=[pattern]):
                result = recommender.generate_recommendation(context)

        assert result is not None
        assert "uncertainty_statement" in result
        assert "75%" in result["uncertainty_statement"]
        assert "could be wrong" in result["uncertainty_statement"]

    def test_generate_recommendation_includes_failure_modes(self) -> None:
        """Test that recommendation includes failure modes."""
        recommender = PatternRecommender()

        pattern = {
            "pattern_id": str(uuid.uuid4()),
            "name": "Test Pattern",
            "description": "A test pattern",
            "confidence": 0.85,
            "occurrences": 10,
            "successes": 8,
            "success_rate": 0.8,
            "pattern_type": "structural",
            "preconditions": {"token_budget_min": 100000},
        }

        context = {"phase": "bugfix"}

        with patch.object(recommender, "load_humility_audit", return_value=None):
            with patch.object(recommender.pattern_store, "query_patterns", return_value=[pattern]):
                result = recommender.generate_recommendation(context)

        assert result is not None
        assert "failure_modes" in result
        assert isinstance(result["failure_modes"], list)
        assert len(result["failure_modes"]) > 0

    def test_generate_recommendation_includes_alternatives(self) -> None:
        """Test that recommendation includes alternatives considered."""
        recommender = PatternRecommender()

        patterns = [
            {
                "pattern_id": str(uuid.uuid4()),
                "name": "Pattern A",
                "description": "Pattern A",
                "confidence": 0.9,
                "occurrences": 10,
                "successes": 9,
                "success_rate": 0.9,
                "pattern_type": "structural",
                "preconditions": {},
            },
            {
                "pattern_id": str(uuid.uuid4()),
                "name": "Pattern B",
                "description": "Pattern B",
                "confidence": 0.7,
                "occurrences": 5,
                "successes": 3,
                "success_rate": 0.6,
                "pattern_type": "tactical",
                "preconditions": {},
            },
        ]

        context = {"phase": "bugfix"}

        with patch.object(recommender, "load_humility_audit", return_value=None):
            with patch.object(recommender.pattern_store, "query_patterns", return_value=patterns):
                result = recommender.generate_recommendation(context)

        assert result is not None
        assert "alternatives_considered" in result
        assert len(result["alternatives_considered"]) > 0


class TestRecordDecision:
    """Test record_decision() method."""

    def test_record_decision_stores_decision(self) -> None:
        """Test that decision is stored to ledger."""
        recommender = PatternRecommender()

        session_id = str(uuid.uuid4())
        task = "Fix authentication bug"
        recommendation = {
            "pattern_id": str(uuid.uuid4()),
            "pattern_name": "Test Pattern",
            "confidence": 0.85,
            "supporting_evidence": {
                "occurrences": 10,
                "successes": 8,
                "success_rate": 0.8,
            },
            "preconditions_matched": {"phase": "bugfix"},
            "alternatives_considered": [],
            "explanation": "Test explanation",
            "uncertainty_statement": "Test uncertainty",
            "failure_modes": ["Test failure mode"],
        }
        context = {"phase": "bugfix"}

        decision_id = str(uuid.uuid4())

        with patch.object(recommender.decision_store, "store_decision", return_value=decision_id):
            result = recommender.record_decision(session_id, task, recommendation, context)

        assert result == decision_id

    def test_record_decision_no_recommendation(self) -> None:
        """Test recording decision with no recommendation."""
        recommender = PatternRecommender()

        session_id = str(uuid.uuid4())
        task = "Fix bug"

        result = recommender.record_decision(session_id, task, None, {})

        assert result is None

    def test_record_decision_includes_alternatives(self) -> None:
        """Test that decision includes alternatives considered."""
        recommender = PatternRecommender()

        session_id = str(uuid.uuid4())
        task = "Fix bug"
        recommendation = {
            "pattern_id": str(uuid.uuid4()),
            "pattern_name": "Test Pattern",
            "confidence": 0.85,
            "supporting_evidence": {
                "occurrences": 10,
                "successes": 8,
                "success_rate": 0.8,
            },
            "preconditions_matched": {},
            "alternatives_considered": [
                {
                    "pattern_id": str(uuid.uuid4()),
                    "name": "Alternative Pattern",
                    "confidence": 0.7,
                    "why_rejected": "Lower confidence",
                }
            ],
            "explanation": "Test",
            "uncertainty_statement": "Test",
            "failure_modes": [],
        }
        context: dict[str, Any] = {}

        decision_id = str(uuid.uuid4())

        with patch.object(
            recommender.decision_store, "store_decision", return_value=decision_id
        ) as mock_store:
            recommender.record_decision(session_id, task, recommendation, context)

            # Verify that store_decision was called with alternatives
            mock_store.assert_called_once()
            call_args = mock_store.call_args
            assert call_args is not None
            assert len(call_args[1]["alternatives_considered"]) == 1


class TestUncertaintyStatement:
    """Test uncertainty statement generation."""

    def test_uncertainty_statement_low_confidence(self) -> None:
        """Test uncertainty statement for low confidence pattern."""
        recommender = PatternRecommender()

        pattern = {
            "pattern_id": str(uuid.uuid4()),
            "pattern_type": "tactical",
        }

        statement = recommender._generate_uncertainty_statement(0.6, pattern)

        assert "60%" in statement
        assert "Could be wrong" in statement or "could be wrong" in statement

    def test_uncertainty_statement_medium_confidence(self) -> None:
        """Test uncertainty statement for medium confidence pattern."""
        recommender = PatternRecommender()

        pattern = {
            "pattern_id": str(uuid.uuid4()),
            "pattern_type": "structural",
        }

        statement = recommender._generate_uncertainty_statement(0.8, pattern)

        assert "80%" in statement
        assert "could be wrong" in statement

    def test_uncertainty_statement_high_confidence(self) -> None:
        """Test uncertainty statement for high confidence pattern."""
        recommender = PatternRecommender()

        pattern = {
            "pattern_id": str(uuid.uuid4()),
            "pattern_type": "structural",
        }

        statement = recommender._generate_uncertainty_statement(0.95, pattern)

        assert "95%" in statement
        assert "could be wrong" in statement

    def test_uncertainty_statement_includes_pattern_type(self) -> None:
        """Test that uncertainty statement includes pattern type info."""
        recommender = PatternRecommender()

        tactical_pattern: dict[str, Any] = {
            "pattern_id": str(uuid.uuid4()),
            "pattern_type": "tactical",
        }

        tactical_statement = recommender._generate_uncertainty_statement(0.8, tactical_pattern)
        assert "Tactical patterns decay" in tactical_statement

        structural_pattern: dict[str, Any] = {
            "pattern_id": str(uuid.uuid4()),
            "pattern_type": "structural",
        }

        structural_statement = recommender._generate_uncertainty_statement(0.8, structural_pattern)
        assert "Structural patterns are timeless" in structural_statement


class TestFailureModes:
    """Test failure mode generation."""

    def test_failure_modes_generic(self) -> None:
        """Test that generic failure modes are included."""
        recommender = PatternRecommender()

        pattern = {
            "pattern_id": str(uuid.uuid4()),
            "pattern_type": "structural",
            "preconditions": {},
        }

        modes = recommender._generate_failure_modes(pattern)

        assert len(modes) > 0
        assert any("fundamentally different" in mode for mode in modes)

    def test_failure_modes_with_token_budget_constraint(self) -> None:
        """Test failure modes with token budget constraint."""
        recommender = PatternRecommender()

        pattern = {
            "pattern_id": str(uuid.uuid4()),
            "pattern_type": "tactical",
            "preconditions": {"token_budget_min": 100000},
        }

        modes = recommender._generate_failure_modes(pattern)

        assert any("token budget" in mode for mode in modes)

    def test_failure_modes_with_hook_constraint(self) -> None:
        """Test failure modes with hook conflict constraint."""
        recommender = PatternRecommender()

        pattern = {
            "pattern_id": str(uuid.uuid4()),
            "pattern_type": "structural",
            "preconditions": {"constraints": ["no_hook_conflicts"]},
        }

        modes = recommender._generate_failure_modes(pattern)

        assert any("hook conflicts" in mode for mode in modes)

    def test_failure_modes_tactical_pattern(self) -> None:
        """Test failure modes for tactical pattern."""
        recommender = PatternRecommender()

        pattern = {
            "pattern_id": str(uuid.uuid4()),
            "pattern_type": "tactical",
            "preconditions": {},
        }

        modes = recommender._generate_failure_modes(pattern)

        assert any("tactical context" in mode for mode in modes)

    def test_failure_modes_structural_pattern(self) -> None:
        """Test failure modes for structural pattern."""
        recommender = PatternRecommender()

        pattern = {
            "pattern_id": str(uuid.uuid4()),
            "pattern_type": "structural",
            "preconditions": {},
        }

        modes = recommender._generate_failure_modes(pattern)

        assert any("root cause" in mode for mode in modes)


class TestExplanationGeneration:
    """Test explanation generation."""

    def test_explanation_includes_pattern_name(self) -> None:
        """Test that explanation includes pattern name."""
        recommender = PatternRecommender()

        pattern = {
            "pattern_id": str(uuid.uuid4()),
            "name": "Test Pattern",
            "description": "A test pattern",
            "occurrences": 10,
            "successes": 8,
            "success_rate": 0.8,
            "preconditions": {},
        }

        explanation = recommender._generate_explanation(pattern, {}, [])

        assert "Test Pattern" in explanation
        assert "10 observations" in explanation

    def test_explanation_includes_preconditions(self) -> None:
        """Test that explanation includes precondition matching info."""
        recommender = PatternRecommender()

        pattern = {
            "pattern_id": str(uuid.uuid4()),
            "name": "Test Pattern",
            "description": "A test pattern",
            "occurrences": 5,
            "successes": 4,
            "success_rate": 0.8,
            "preconditions": {
                "token_budget_min": 100000,
                "token_budget_max": 200000,
                "phase": "bugfix",
            },
        }

        explanation = recommender._generate_explanation(pattern, {}, [])

        assert "Preconditions matched" in explanation
        assert "token budget" in explanation
        assert "phase: bugfix" in explanation

    def test_explanation_includes_alternatives(self) -> None:
        """Test that explanation includes alternatives considered."""
        recommender = PatternRecommender()

        pattern = {
            "pattern_id": str(uuid.uuid4()),
            "name": "Test Pattern",
            "description": "A test pattern",
            "occurrences": 5,
            "successes": 4,
            "success_rate": 0.8,
            "preconditions": {},
        }

        alternatives = [
            {
                "pattern_id": str(uuid.uuid4()),
                "name": "Alternative A",
                "confidence": 0.7,
            },
            {
                "pattern_id": str(uuid.uuid4()),
                "name": "Alternative B",
                "confidence": 0.6,
            },
        ]

        explanation = recommender._generate_explanation(pattern, {}, alternatives)

        assert "Alternatives considered" in explanation
        assert "Alternative A" in explanation
        assert "Alternative B" in explanation


class TestFallbackRecommendation:
    """Test fallback recommendation generation."""

    def test_fallback_recommendation_low_confidence(self) -> None:
        """Test that fallback recommendation has low confidence."""
        recommender = PatternRecommender()

        result = recommender._generate_fallback_recommendation({})

        assert result["confidence"] == 0.3
        assert result["pattern_id"] == "fallback"

    def test_fallback_recommendation_includes_explanation(self) -> None:
        """Test that fallback recommendation includes explanation."""
        recommender = PatternRecommender()

        result = recommender._generate_fallback_recommendation({})

        assert "explanation" in result
        assert "No patterns matched" in result["explanation"]

    def test_fallback_recommendation_includes_uncertainty(self) -> None:
        """Test that fallback recommendation includes uncertainty."""
        recommender = PatternRecommender()

        result = recommender._generate_fallback_recommendation({})

        assert "uncertainty_statement" in result
        assert "30%" in result["uncertainty_statement"]

    def test_fallback_recommendation_includes_failure_modes(self) -> None:
        """Test that fallback recommendation includes failure modes."""
        recommender = PatternRecommender()

        result = recommender._generate_fallback_recommendation({})

        assert "failure_modes" in result
        assert len(result["failure_modes"]) > 0
