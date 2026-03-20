"""Pattern recommendation engine for the agent learning loop.

This module provides the PatternRecommender class for querying patterns,
generating recommendations with explanations, and recording decisions.
All recommendations include confidence scores, supporting evidence, and
uncertainty statements.
"""

from typing import Any, Optional

from loguru import logger

from divineos.agent_integration.pattern_store import PatternStore
from divineos.agent_integration.learning_audit_store import LearningAuditStore
from divineos.agent_integration.decision_store import DecisionStore


class PatternRecommender:
    """Recommends patterns based on current context and historical evidence.

    The recommender loads the humility audit, matches patterns to current context,
    ranks by confidence, and generates recommendations with detailed explanations
    including uncertainty statements and failure modes.
    """

    def __init__(self) -> None:
        """Initialize the pattern recommender."""
        self.logger = logger
        self.pattern_store = PatternStore()
        self.audit_store = LearningAuditStore()
        self.decision_store = DecisionStore()
        self.current_audit: Optional[dict[str, Any]] = None
        self.matched_patterns: list[dict[str, Any]] = []

    def load_humility_audit(self) -> Optional[dict[str, Any]]:
        """Load the latest humility audit and display warnings.

        Retrieves the most recent AGENT_LEARNING_AUDIT event and logs
        any warnings about low-confidence patterns, gaps, and risky assumptions.

        Returns:
            Audit dictionary or None if no audits found
        """
        try:
            audit = self.audit_store.get_latest_audit()

            if audit is None:
                self.logger.info("No humility audit found (first session)")
                return None

            self.current_audit = audit
            audit_id = audit.get("audit_id", "unknown")
            session_id = audit.get("session_id", "unknown")

            self.logger.info(f"Loaded humility audit {audit_id} for session {session_id}")

            # Log warnings about low-confidence patterns
            low_confidence = audit.get("low_confidence_patterns", [])
            if low_confidence:
                self.logger.warning(
                    f"⚠️  {len(low_confidence)} patterns have low confidence (<0.7):"
                )
                for pattern in low_confidence:
                    name = pattern.get("name", "unknown")
                    confidence = pattern.get("confidence", 0.0)
                    reason = pattern.get("reason", "unknown")
                    self.logger.warning(
                        f"   - {name} (confidence: {confidence:.2f}, reason: {reason})"
                    )

            # Log warnings about untested patterns
            untested = audit.get("untested_patterns", [])
            if untested:
                self.logger.warning(
                    f"⚠️  {len(untested)} patterns have never been tested in current context:"
                )
                for pattern in untested:
                    name = pattern.get("name", "unknown")
                    last_context = pattern.get("last_tested_context", "never")
                    self.logger.warning(f"   - {name} (last tested: {last_context})")

            # Log warnings about pattern gaps
            gaps = audit.get("pattern_gaps", [])
            if gaps:
                self.logger.warning(f"⚠️  {len(gaps)} pattern gaps identified:")
                for gap in gaps:
                    gap_type = gap.get("gap_type", "unknown")
                    description = gap.get("description", "unknown")
                    self.logger.warning(f"   - {gap_type}: {description}")

            # Log warnings about risky assumptions
            risky = audit.get("risky_assumptions", [])
            if risky:
                self.logger.warning(f"⚠️  {len(risky)} risky assumptions detected:")
                for assumption in risky:
                    assumption_text = assumption.get("assumption", "unknown")
                    why_risky = assumption.get("why_risky", "unknown")
                    self.logger.warning(f"   - {assumption_text} (risk: {why_risky})")

            # Log drift detection
            if audit.get("drift_detected", False):
                drift_reason = audit.get("drift_reason", "unknown")
                self.logger.error(f"🚨 SYSTEM DRIFT DETECTED: {drift_reason}")

            return audit
        except Exception as e:
            self.logger.error(f"Failed to load humility audit: {e}")
            return None

    def match_preconditions(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Filter patterns by current context preconditions.

        Queries patterns where preconditions match the current context.
        Excludes patterns with confidence <0.65 and anti-patterns (confidence <-0.5)
        unless context has fundamentally changed.

        Args:
            context: Current context dictionary with keys like:
                - token_budget: int (current token budget)
                - phase: str (e.g., "bugfix", "feature")
                - codebase_structure: str (hash of module structure)
                - constraints: list[str] (e.g., ["no_hook_conflicts"])

        Returns:
            List of matching patterns (may be empty)
        """
        try:
            if not context:
                self.logger.warning("No context provided for pattern matching")
                return []

            # Query patterns with context
            matched = self.pattern_store.query_patterns(context)

            self.logger.info(
                f"Matched {len(matched)} patterns for context: "
                f"token_budget={context.get('token_budget')}, "
                f"phase={context.get('phase')}"
            )

            self.matched_patterns = matched
            return matched
        except Exception as e:
            self.logger.error(f"Failed to match preconditions: {e}")
            return []

    def rank_by_confidence(
        self, patterns: Optional[list[dict[str, Any]]] = None
    ) -> list[dict[str, Any]]:
        """Sort matched patterns by confidence (highest first).

        Ranks patterns by confidence score in descending order.
        Returns top patterns with highest confidence first.

        Args:
            patterns: List of patterns to rank. If None, uses matched_patterns.

        Returns:
            Sorted list of patterns (highest confidence first)
        """
        try:
            if patterns is None:
                patterns = self.matched_patterns

            if not patterns:
                self.logger.info("No patterns to rank")
                return []

            # Sort by confidence (descending)
            ranked = sorted(patterns, key=lambda p: p.get("confidence", 0.0), reverse=True)

            self.logger.info(f"Ranked {len(ranked)} patterns by confidence")

            return ranked
        except Exception as e:
            self.logger.error(f"Failed to rank patterns: {e}")
            return []

    def generate_recommendation(
        self,
        context: dict[str, Any],
        top_n: int = 3,
    ) -> Optional[dict[str, Any]]:
        """Generate a recommendation with detailed explanation.

        Creates a recommendation for the given context, including:
        - Confidence score and supporting evidence
        - Preconditions that matched
        - Alternatives considered
        - Uncertainty statement ("I'm X% confident, but could be wrong if...")
        - Failure modes ("This fails if...")

        Args:
            context: Current context dictionary
            top_n: Number of top patterns to consider (default 3)

        Returns:
            Recommendation dictionary or None if no patterns match
        """
        try:
            # Load audit first (to show warnings)
            self.load_humility_audit()

            # Match preconditions
            matched = self.match_preconditions(context)

            if not matched:
                self.logger.warning("No patterns matched current context")
                return self._generate_fallback_recommendation(context)

            # Rank by confidence
            ranked = self.rank_by_confidence(matched)

            if not ranked:
                return self._generate_fallback_recommendation(context)

            # Get top pattern
            chosen = ranked[0]
            pattern_id = chosen.get("pattern_id", "unknown")
            pattern_name = chosen.get("name", "unknown")
            confidence = chosen.get("confidence", 0.0)
            occurrences = chosen.get("occurrences", 0)
            successes = chosen.get("successes", 0)
            success_rate = chosen.get("success_rate", 0.0)
            violation_count = chosen.get("violation_count", 0)

            # Get alternatives (top 2 after chosen)
            alternatives = []
            for alt_pattern in ranked[1:top_n]:
                alt_id = alt_pattern.get("pattern_id", "unknown")
                alt_name = alt_pattern.get("name", "unknown")
                alt_confidence = alt_pattern.get("confidence", 0.0)
                alternatives.append(
                    {
                        "pattern_id": alt_id,
                        "name": alt_name,
                        "confidence": alt_confidence,
                        "why_rejected": (
                            f"Lower confidence ({alt_confidence:.2f} vs {confidence:.2f})"
                        ),
                    }
                )

            # Generate explanation
            explanation = self._generate_explanation(chosen, context, alternatives)

            # Check for high-violation patterns and add warning
            violation_warning = None
            if violation_count > 5:
                violation_warning = (
                    f"⚠️  WARNING: This pattern has {violation_count} recorded violations. "
                    f"Use with caution and monitor for clarity issues."
                )
                self.logger.warning(violation_warning)

            recommendation = {
                "pattern_id": pattern_id,
                "pattern_name": pattern_name,
                "confidence": confidence,
                "supporting_evidence": {
                    "occurrences": occurrences,
                    "successes": successes,
                    "success_rate": success_rate,
                    "violation_count": violation_count,
                },
                "preconditions_matched": chosen.get("preconditions", {}),
                "alternatives_considered": alternatives,
                "explanation": explanation,
                "uncertainty_statement": self._generate_uncertainty_statement(confidence, chosen),
                "failure_modes": self._generate_failure_modes(chosen),
                "violation_warning": violation_warning,
            }

            self.logger.info(
                f"Generated recommendation: {pattern_name} (confidence: {confidence:.2f}, "
                f"violations: {violation_count})"
            )

            return recommendation
        except Exception as e:
            self.logger.error(f"Failed to generate recommendation: {e}")
            return None

    def record_decision(
        self,
        session_id: str,
        task: str,
        recommendation: dict[str, Any],
        context: dict[str, Any],
    ) -> Optional[str]:
        """Record the decision to use a recommended pattern.

        Stores an AGENT_DECISION event with the chosen pattern, alternatives,
        and counterfactual analysis.

        Args:
            session_id: Session ID for this decision
            task: Description of the task/decision
            recommendation: Recommendation dictionary from generate_recommendation()
            context: Current context dictionary

        Returns:
            Decision ID (UUID) or None if failed
        """
        try:
            if not recommendation:
                self.logger.error("Cannot record decision: no recommendation provided")
                return None

            pattern_id = recommendation.get("pattern_id", "unknown")
            confidence = recommendation.get("confidence", 0.0)
            alternatives = recommendation.get("alternatives_considered", [])

            # Generate counterfactual (estimated, not measured)
            counterfactual = {
                "chosen_cost": 1.0,  # Placeholder (will be measured post-work)
                "alternative_costs": [1.5, 2.0],  # Placeholder estimates
                "default_cost": 3.0,  # Placeholder (no pattern applied)
                "counterfactual_type": "estimated",
            }

            # Store decision
            decision_id = self.decision_store.store_decision(
                session_id=session_id,
                task=task,
                chosen_pattern=pattern_id,
                pattern_confidence=confidence,
                alternatives_considered=alternatives,
                counterfactual=counterfactual,
                outcome=None,  # Will be populated after work completes
            )

            self.logger.info(f"Recorded decision {decision_id} for pattern {pattern_id}")

            return decision_id
        except Exception as e:
            self.logger.error(f"Failed to record decision: {e}")
            return None

    def _generate_explanation(
        self,
        pattern: dict[str, Any],
        context: dict[str, Any],
        alternatives: list[dict[str, Any]],
    ) -> str:
        """Generate detailed explanation for the recommendation.

        Args:
            pattern: Chosen pattern
            context: Current context
            alternatives: Alternative patterns considered

        Returns:
            Explanation string
        """
        pattern_name = pattern.get("name", "unknown")
        occurrences = pattern.get("occurrences", 0)
        successes = pattern.get("successes", 0)
        success_rate = pattern.get("success_rate", 0.0)
        description = pattern.get("description", "")

        explanation = (
            f"Recommending '{pattern_name}' based on {occurrences} observations "
            f"({successes} successes, {success_rate * 100:.0f}% success rate). "
            f"{description}"
        )

        # Add context matching info
        preconditions = pattern.get("preconditions", {})
        if preconditions:
            matched_conditions = []
            if "token_budget_min" in preconditions:
                matched_conditions.append(
                    f"token budget {preconditions['token_budget_min']}-"
                    f"{preconditions.get('token_budget_max', 'unlimited')}"
                )
            if "phase" in preconditions:
                matched_conditions.append(f"phase: {preconditions['phase']}")
            if matched_conditions:
                explanation += f" Preconditions matched: {', '.join(matched_conditions)}."

        # Add alternatives info
        if alternatives:
            alt_names = [alt.get("name", "unknown") for alt in alternatives]
            explanation += f" Alternatives considered: {', '.join(alt_names)}."

        return explanation

    def _generate_uncertainty_statement(self, confidence: float, pattern: dict[str, Any]) -> str:
        """Generate uncertainty statement for the recommendation.

        Args:
            confidence: Confidence score (0.0-1.0)
            pattern: Pattern dictionary

        Returns:
            Uncertainty statement
        """
        confidence_pct = int(confidence * 100)
        pattern_type = pattern.get("pattern_type", "unknown")

        # Generate uncertainty based on confidence level
        if confidence < 0.7:
            uncertainty = (
                f"I'm {confidence_pct}% confident, but this pattern has limited evidence. "
                f"Could be wrong if context changes or new evidence emerges."
            )
        elif confidence < 0.85:
            uncertainty = (
                f"I'm {confidence_pct}% confident, but could be wrong if "
                f"the codebase structure changes or new constraints emerge."
            )
        else:
            uncertainty = (
                f"I'm {confidence_pct}% confident, but could be wrong if "
                f"the problem domain shifts or assumptions change."
            )

        # Add pattern-type-specific uncertainty
        if pattern_type == "tactical":
            uncertainty += " (Tactical patterns decay over time without validation.)"
        elif pattern_type == "structural":
            uncertainty += " (Structural patterns are timeless but can be invalidated by evidence.)"

        return uncertainty

    def _generate_failure_modes(self, pattern: dict[str, Any]) -> list[str]:
        """Generate failure modes for the recommendation.

        Args:
            pattern: Pattern dictionary

        Returns:
            List of failure mode descriptions
        """
        failure_modes = []

        # Generic failure modes
        failure_modes.append(
            "This fails if the problem is fundamentally different from past observations"
        )
        failure_modes.append(
            "This fails if preconditions have changed (token budget, codebase structure)"
        )

        # Pattern-specific failure modes
        preconditions = pattern.get("preconditions", {})
        if preconditions:
            if "token_budget_min" in preconditions:
                failure_modes.append(
                    f"This fails if token budget drops below {preconditions['token_budget_min']}"
                )
            if "constraints" in preconditions:
                constraints = preconditions["constraints"]
                if "no_hook_conflicts" in constraints:
                    failure_modes.append("This fails if hook conflicts are introduced")

        # Pattern-type-specific failure modes
        pattern_type = pattern.get("pattern_type", "")
        if pattern_type == "tactical":
            failure_modes.append(
                "This fails if the tactical context (thresholds, code structure) changes"
            )
        elif pattern_type == "structural":
            failure_modes.append("This fails if the root cause is different from past cases")

        return failure_modes

    def _generate_fallback_recommendation(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate a fallback recommendation when no patterns match.

        Args:
            context: Current context

        Returns:
            Fallback recommendation with low confidence
        """
        self.logger.warning("Generating fallback recommendation (no patterns matched)")

        return {
            "pattern_id": "fallback",
            "pattern_name": "Generic Approach",
            "confidence": 0.3,
            "supporting_evidence": {
                "occurrences": 0,
                "successes": 0,
                "success_rate": 0.0,
            },
            "preconditions_matched": {},
            "alternatives_considered": [],
            "explanation": (
                "No patterns matched current context. "
                "Using generic approach with low confidence. "
                "This is a good opportunity to learn a new pattern."
            ),
            "uncertainty_statement": (
                "I'm 30% confident because no patterns matched. "
                "This is exploratory work that will help build new patterns."
            ),
            "failure_modes": [
                "This fails because it's not based on learned patterns",
                "This fails if the problem is similar to past cases but context changed",
            ],
        }
