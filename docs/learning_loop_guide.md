# Agent Learning Loop Guide

## Overview

The agent learning loop enables self-reflection and behavioral improvement through systematic analysis of past work. The agent reads its own work history from the DivineOS ledger, extracts patterns about what succeeds and what fails, and applies those patterns to future decisions.

This guide explains how the learning loop works and provides examples of pattern creation, confidence updates, recommendations, and humility audits.

## Structural vs Tactical Patterns

The learning loop distinguishes between two types of patterns:

### Structural Patterns
- **Definition**: Root cause investigation approaches, architectural principles, debugging methodologies
- **Lifetime**: Timeless — remain valid indefinitely
- **Decay**: No automatic temporal decay; only evidence-based invalidation
- **Example**: "Always check the type system first when seeing cascading errors"

### Tactical Patterns
- **Definition**: Specific thresholds, code structures, optimization tricks
- **Lifetime**: Context-dependent; decay when codebase evolves or constraints change
- **Decay**: Confidence decreases 5% per week without validation
- **Example**: "Use compression at 150k tokens when token budget is 200k"

## Pattern Creation and Confidence Updates

### Example: Creating a Pattern

When the agent completes work, the learning cycle analyzes the outcome and updates pattern confidence:

```python
# Initial pattern created
pattern = {
    "pattern_id": "uuid-123",
    "pattern_type": "structural",
    "name": "Type System First",
    "description": "Check type system before runtime state",
    "preconditions": {"phase": "bugfix"},
    "confidence": 0.5,  # Initial confidence
    "occurrences": 1,
    "successes": 0,
    "success_rate": 0.0,
}

# After successful work
# Confidence delta: +0.05 (success)
# New confidence: 0.55

# After failed work with violations
# Confidence delta: -0.15 (failure) - 0.1 (violations) = -0.25
# New confidence: 0.30
```

### Confidence Update Rules

- **Success**: +0.05 (base increase)
- **Failure**: -0.15 (3× heavier than success)
- **Violations introduced**: -0.1 additional penalty
- **Minimum threshold**: 0.65 (patterns below this are not recommended)
- **Anti-pattern threshold**: -0.5 (patterns below this are never recommended)

## Pattern Recommendation with Explanation

### Example: Getting a Recommendation

```python
from divineos.agent_integration.pattern_recommender import PatternRecommender

recommender = PatternRecommender()

# Load humility audit (displays warnings)
audit = recommender.load_humility_audit()

# Get recommendation for current context
context = {
    "phase": "bugfix",
    "token_budget": 150000,
    "codebase_structure": "hash_v1"
}

recommendation = recommender.generate_recommendation(context)

# Output:
# {
#     "pattern_id": "uuid-123",
#     "pattern_name": "Type System First",
#     "confidence": 0.85,
#     "supporting_evidence": {
#         "occurrences": 10,
#         "successes": 8,
#         "success_rate": 0.8
#     },
#     "preconditions_matched": {
#         "phase": "bugfix"
#     },
#     "explanation": "Type System First has been observed 10 times with 80% success rate...",
#     "uncertainty_statement": "I'm 85% confident, but could be wrong if...",
#     "failure_modes": [
#         "This fails if the error is actually in runtime state",
#         "This fails if type system is not the root cause"
#     ],
#     "alternatives_considered": [
#         {
#             "pattern_id": "uuid-456",
#             "name": "Runtime State First",
#             "confidence": 0.7,
#             "why_rejected": "Lower confidence"
#         }
#     ]
# }
```

### Recommendation Explanation Components

1. **Pattern Name & Confidence**: What pattern is recommended and how confident
2. **Supporting Evidence**: How many times observed, success rate
3. **Preconditions Matched**: Which context conditions matched
4. **Explanation**: Why this pattern is recommended
5. **Uncertainty Statement**: What could make this wrong
6. **Failure Modes**: Specific scenarios where this fails
7. **Alternatives Considered**: Other patterns and why they were rejected

## Humility Audit

### Example: Humility Audit Output

```python
from divineos.agent_integration.learning_cycle import LearningCycle

cycle = LearningCycle()
audit = cycle.generate_humility_audit()

# Output:
# {
#     "audit_id": "uuid-789",
#     "session_id": "session-123",
#     "timestamp": "2026-03-19T20:00:00",
#     "low_confidence_patterns": [
#         {
#             "pattern_id": "uuid-456",
#             "name": "Runtime State First",
#             "confidence": 0.6,
#             "reason": "Limited evidence (only 3 observations)"
#         }
#     ],
#     "untested_patterns": [
#         {
#             "pattern_id": "uuid-789",
#             "name": "Hook Conflict Detection",
#             "last_tested_context": "never"
#         }
#     ],
#     "pattern_gaps": [
#         {
#             "gap_type": "race_condition_handling",
#             "description": "No pattern for race condition handling"
#         }
#     ],
#     "risky_assumptions": [
#         {
#             "assumption": "Token budget always > 100k",
#             "why_risky": "Could be wrong in constrained environments",
#             "mitigation": "Add token_budget_min precondition"
#         }
#     ],
#     "drift_detected": False,
#     "drift_reason": None
# }
```

### Humility Audit Components

1. **Low Confidence Patterns**: Patterns with confidence < 0.7
2. **Untested Patterns**: Patterns never tested in current context
3. **Pattern Gaps**: Task types with no patterns
4. **Risky Assumptions**: Assumptions that could be wrong
5. **Drift Detection**: System reliability warning (>50% patterns below 0.6)

## Integration with Memory Monitor

The learning loop integrates with the memory monitor to provide a complete workflow:

```python
from divineos.agent_integration.memory_monitor import AgentMemoryMonitor

monitor = AgentMemoryMonitor(session_id="session-123")

# 1. Get recommendation for new work
context = {"phase": "bugfix", "token_budget": 150000}
recommendation = monitor.get_recommendation(context)

# 2. Do work using the recommended pattern
# ... work happens ...

# 3. Record work outcome
monitor.record_work_outcome(
    task="Fix authentication bug",
    pattern_id=recommendation["pattern_id"],
    success=True,
    violations_introduced=0,
    token_efficiency=0.85,
    rework_needed=False
)

# 4. End session (triggers learning cycle)
monitor.end_session(
    summary="Completed bugfix work",
    final_status="completed"
)
```

## Correctness Invariants

The learning loop maintains several correctness invariants:

### CP1: Pattern Consistency
Same task characteristics always return the same recommendation (unless confidence changes or context changes).

### CP2: Anti-Pattern Enforcement
Anti-patterns (confidence < -0.5) are never recommended without explicit override.

### CP3: Outcome Tracking
Confidence updates reflect actual outcomes, including secondary effects (violations, token efficiency).

### CP4: No Circular Reasoning
Patterns are based on actual work outcomes, not on other patterns.

### CP5: Structural vs Tactical Decay
Structural patterns don't decay by time; tactical patterns decay 5% per week.

### CP6: Humility Audit Accuracy
Humility audit accurately reflects pattern state and system reliability.

### CP7: Counterfactual Validity
Counterfactuals are recorded at decision time and validated post-hoc.

## Best Practices

1. **Monitor Pattern Confidence**: Regularly check humility audits for low-confidence patterns
2. **Validate Patterns**: Test patterns in new contexts to increase confidence
3. **Handle Conflicts**: Resolve contradictory structural patterns by refining preconditions
4. **Track Outcomes**: Always record work outcomes so patterns can be validated
5. **Review Assumptions**: Periodically review risky assumptions in humility audits
6. **Detect Drift**: Watch for drift detection warnings (>50% patterns below 0.6)

## Troubleshooting

### Pattern Not Recommended
- Check if pattern confidence is below 0.65 (minimum threshold)
- Check if preconditions match current context
- Check if pattern is an anti-pattern (confidence < -0.5)

### Confidence Not Increasing
- Ensure work outcomes are being recorded
- Check if violations are being introduced (additional penalty)
- Verify pattern preconditions match the work context

### Drift Detected
- Review low-confidence patterns in humility audit
- Consider archiving patterns with confidence < 0.5
- Validate patterns in new contexts to increase confidence

## References

- Requirements: `.kiro/specs/agent-learning-loop/requirements.md`
- Design: `.kiro/specs/agent-learning-loop/design.md`
- Implementation: `src/divineos/agent_integration/`
