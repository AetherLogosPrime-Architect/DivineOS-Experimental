# Agent Work Clarity System - Usage Examples

This document provides practical examples of using the Agent Work Clarity System for different scenarios.

## Table of Contents

1. [Example 1: Generate Clarity Statement Before Work](#example-1-generate-clarity-statement-before-work)
2. [Example 2: Analyze Execution After Work Completes](#example-2-analyze-execution-after-work-completes)
3. [Example 3: Generate Post-Work Summary with Deviations and Lessons](#example-3-generate-post-work-summary-with-deviations-and-lessons)

---

## Example 1: Generate Clarity Statement Before Work

### Scenario

An agent is about to refactor a Python module. Before starting, we want to generate a clarity statement that describes what the agent plans to do.

### Code

```python
from divineos.clarity_system import DefaultClarityStatementGenerator

# Create the clarity generator
generator = DefaultClarityStatementGenerator()

# Define the work context
work_context = {
    "task": "Refactor authentication module",
    "goal": "Improve code organization and reduce duplication in auth.py",
    "approach": [
        "Extract common validation logic into utility functions",
        "Consolidate error handling patterns",
        "Add type hints to all functions",
        "Update docstrings"
    ],
    "expected_outcome": "Cleaner, more maintainable code with better documentation",
    "scope": {
        "files_affected": ["src/auth.py", "src/auth_utils.py"],
        "estimated_tool_calls": 15,
        "complexity": "medium",
        "estimated_time_minutes": 45
    }
}

# Generate clarity statement
clarity_statement = generator.generate_clarity_statement(work_context)

# Present to user
user_feedback = generator.present_to_user(clarity_statement)
```

### Expected Output

```
═══════════════════════════════════════════════════════════════
                    CLARITY STATEMENT
═══════════════════════════════════════════════════════════════

Goal:
  Improve code organization and reduce duplication in auth.py

Approach:
  • Extract common validation logic into utility functions
  • Consolidate error handling patterns
  • Add type hints to all functions
  • Update docstrings

Expected Outcome:
  Cleaner, more maintainable code with better documentation

Scope Estimate:
  • Files to modify: 2
  • Tool calls needed: ~15
  • Complexity: medium
  • Estimated time: 45 minutes

═══════════════════════════════════════════════════════════════
This is an informational statement. Work will proceed immediately.
═══════════════════════════════════════════════════════════════
```

### Data Structure

The generated `ClarityStatement` object contains:

```python
ClarityStatement(
    id=UUID('a1b2c3d4-e5f6-7890-abcd-ef1234567890'),
    timestamp='2024-01-15T10:30:00.000000',
    goal='Improve code organization and reduce duplication in auth.py',
    approach='Extract common validation logic into utility functions; Consolidate error handling patterns; Add type hints to all functions; Update docstrings',
    expected_outcome='Cleaner, more maintainable code with better documentation',
    scope=ScopeEstimate(
        estimated_files=2,
        estimated_tool_calls=15,
        estimated_complexity='medium',
        estimated_time_minutes=45
    ),
    user_feedback=None
)
```

---

## Example 2: Analyze Execution After Work Completes

### Scenario

After the agent completes the refactoring work, we want to analyze what actually happened by querying the ledger.

### Code

```python
from uuid import UUID
from divineos.clarity_system import (
    DefaultPlanAnalyzer,
    DefaultExecutionAnalyzer,
)

# Session ID from the work execution
session_id = UUID('b2c3d4e5-f6a7-8901-bcde-f12345678901')

# Analyze the plan from the clarity statement
plan_analyzer = DefaultPlanAnalyzer()
plan_data = plan_analyzer.analyze_plan(clarity_statement)

# Analyze actual execution from ledger
exec_analyzer = DefaultExecutionAnalyzer()
execution_data = exec_analyzer.analyze_execution(session_id)
```

### Expected Output

**Plan Data:**
```python
PlanData(
    clarity_statement_id=UUID('a1b2c3d4-e5f6-7890-abcd-ef1234567890'),
    goal='Improve code organization and reduce duplication in auth.py',
    approach='Extract common validation logic into utility functions; Consolidate error handling patterns; Add type hints to all functions; Update docstrings',
    expected_outcome='Cleaner, more maintainable code with better documentation',
    metrics=PlanMetrics(
        estimated_files=2,
        estimated_tool_calls=15,
        estimated_complexity='medium',
        estimated_time_minutes=45
    )
)
```

**Execution Data:**
```python
ExecutionData(
    session_id=UUID('b2c3d4e5-f6a7-8901-bcde-f12345678901'),
    tool_calls=[
        ToolCall(
            tool_name='readFile',
            timestamp='2024-01-15T10:30:15.000000',
            input={'path': 'src/auth.py'}
        ),
        ToolCall(
            tool_name='strReplace',
            timestamp='2024-01-15T10:31:20.000000',
            input={'path': 'src/auth.py', 'oldStr': '...', 'newStr': '...'}
        ),
        # ... more tool calls
    ],
    errors=['ValidationError: Invalid type hint on line 42'],
    metrics=ExecutionMetrics(
        actual_files=3,
        actual_tool_calls=18,
        actual_errors=1,
        actual_time_minutes=52.5,
        success_rate=94.4
    )
)
```

### Tool Calls Made

The execution analyzer queries the ledger and extracts:

```python
tool_calls = exec_analyzer.extract_tool_calls(session_id)
# Returns list of 18 ToolCall objects

errors = exec_analyzer.extract_errors(session_id)
# Returns ['ValidationError: Invalid type hint on line 42']

metrics = exec_analyzer.calculate_execution_metrics(execution_data)
# Returns ExecutionMetrics with calculated values
```

---

## Example 3: Generate Post-Work Summary with Deviations and Lessons

### Scenario

Now we want to generate a comprehensive summary comparing what was planned vs what actually happened, including deviations, lessons learned, and recommendations.

### Code

```python
from divineos.clarity_system import (
    DefaultDeviationAnalyzer,
    DefaultLearningExtractor,
    DefaultSummaryGenerator,
)

# Analyze deviations between plan and execution
dev_analyzer = DefaultDeviationAnalyzer()
deviations = dev_analyzer.analyze_deviations(plan_data, execution_data)

# Extract lessons and generate recommendations
learning = DefaultLearningExtractor()
lessons = learning.extract_lessons(deviations, execution_data)
recommendations = learning.generate_recommendations(lessons)

# Generate comprehensive summary
summary_gen = DefaultSummaryGenerator()
summary = summary_gen.generate_post_work_summary(
    clarity_statement=clarity_statement,
    plan_data=plan_data,
    execution_data=execution_data,
    deviations=deviations,
    lessons=lessons,
    recommendations=recommendations
)

# Present summary to user
summary_gen.present_summary_to_user(summary)
```

### Expected Output

```
═══════════════════════════════════════════════════════════════════════════════
                         POST-WORK SUMMARY
═══════════════════════════════════════════════════════════════════════════════

ORIGINAL CLARITY STATEMENT
─────────────────────────────────────────────────────────────────────────────
Goal: Improve code organization and reduce duplication in auth.py
Approach: Extract common validation logic; Consolidate error handling; Add type hints; Update docstrings
Expected Outcome: Cleaner, more maintainable code with better documentation
Scope: 2 files, ~15 tool calls, medium complexity, ~45 minutes

PLAN VS ACTUAL COMPARISON
─────────────────────────────────────────────────────────────────────────────
Goal Alignment:        ✓ Achieved (100%)
Approach Alignment:    ✓ Achieved (95%)
Outcome Alignment:     ✓ Achieved (90%)
Overall Alignment:     92%

DEVIATIONS DETECTED
─────────────────────────────────────────────────────────────────────────────
[HIGH SEVERITY]
  • Tool Calls: Planned 15, Actual 18 (+20% deviation)
    Category: Efficiency
    Reason: Additional refactoring opportunities discovered during execution

  • Time: Planned 45 min, Actual 52.5 min (+16.7% deviation)
    Category: Efficiency
    Reason: More complex refactoring than initially estimated

[MEDIUM SEVERITY]
  • Files Modified: Planned 2, Actual 3 (+50% deviation)
    Category: Scope
    Reason: Additional utility file created for extracted functions

[LOW SEVERITY]
  • Errors: Planned 0, Actual 1 (-100% deviation)
    Category: Quality
    Reason: Type hint validation error (resolved)

EXECUTION METRICS
─────────────────────────────────────────────────────────────────────────────
Total Tool Calls:      18 (planned: 15)
Successful Calls:      17 (94.4% success rate)
Failed Calls:          1
Total Duration:        52.5 minutes (planned: 45 minutes)
Files Modified:        3 (planned: 2)
Errors Encountered:    1 (resolved)

LESSONS LEARNED
─────────────────────────────────────────────────────────────────────────────
1. [HIGH CONFIDENCE] Scope Estimation Accuracy
   Insight: Initial scope estimates tend to underestimate refactoring complexity
   Context: When extracting common logic, additional opportunities often emerge
   Evidence: 3 additional tool calls and 1 new file created
   Recommendation: Add 20% buffer to refactoring time estimates

2. [HIGH CONFIDENCE] Type Hint Validation
   Insight: Type hints require careful validation during refactoring
   Context: Complex type hints can cause validation errors
   Evidence: 1 validation error encountered and resolved
   Recommendation: Run type checker incrementally during refactoring

3. [MEDIUM CONFIDENCE] Code Organization Patterns
   Insight: Extracted utility functions improve code reusability
   Context: Common validation logic was successfully consolidated
   Evidence: 3 validation functions extracted and reused 5 times
   Recommendation: Consider extracting utility functions earlier in planning

RECOMMENDATIONS
─────────────────────────────────────────────────────────────────────────────
[HIGH PRIORITY]
  → For future refactoring tasks: Add 20% time buffer to estimates
    Applicable to: Code refactoring, module reorganization
    Based on: Lesson 1 (Scope Estimation Accuracy)

  → Run type checker incrementally during refactoring
    Applicable to: Python refactoring with type hints
    Based on: Lesson 2 (Type Hint Validation)

[MEDIUM PRIORITY]
  → Consider extracting utility functions earlier in planning
    Applicable to: Code organization tasks
    Based on: Lesson 3 (Code Organization Patterns)

═══════════════════════════════════════════════════════════════════════════════
Summary generated: 2024-01-15T10:45:30.000000
═══════════════════════════════════════════════════════════════════════════════
```

### Data Structure

The generated `PostWorkSummary` object contains:

```python
PostWorkSummary(
    id=UUID('c3d4e5f6-a7b8-9012-cdef-123456789012'),
    clarity_statement=ClarityStatement(...),
    plan_vs_actual=PlanVsActualComparison(
        planned_goal='Improve code organization and reduce duplication in auth.py',
        actual_goal='Improved code organization and reduced duplication in auth.py',
        planned_approach='Extract common validation logic; Consolidate error handling; Add type hints; Update docstrings',
        actual_approach='Extracted common validation logic; Consolidated error handling; Added type hints; Updated docstrings; Created utility module',
        planned_outcome='Cleaner, more maintainable code with better documentation',
        actual_outcome='Cleaner, more maintainable code with better documentation and reusable utilities',
        alignment_score=0.92
    ),
    deviations=[
        Deviation(
            metric='tool_calls',
            planned=15.0,
            actual=18.0,
            difference=3.0,
            percentage=20.0,
            severity='high',
            category='efficiency'
        ),
        Deviation(
            metric='time_minutes',
            planned=45.0,
            actual=52.5,
            difference=7.5,
            percentage=16.7,
            severity='high',
            category='efficiency'
        ),
        Deviation(
            metric='files',
            planned=2.0,
            actual=3.0,
            difference=1.0,
            percentage=50.0,
            severity='medium',
            category='scope'
        ),
        Deviation(
            metric='errors',
            planned=0.0,
            actual=1.0,
            difference=1.0,
            percentage=100.0,
            severity='low',
            category='quality'
        ),
    ],
    lessons_learned=[
        Lesson(
            id=UUID('d4e5f6a7-b8c9-0123-def1-234567890123'),
            type='deviation',
            description='Scope Estimation Accuracy',
            context='When extracting common logic, additional opportunities often emerge',
            insight='Initial scope estimates tend to underestimate refactoring complexity',
            confidence=0.95,
            source_session_id=UUID('b2c3d4e5-f6a7-8901-bcde-f12345678901'),
            created_at='2024-01-15T10:45:20.000000'
        ),
        # ... more lessons
    ],
    recommendations=[
        Recommendation(
            lesson_id=UUID('d4e5f6a7-b8c9-0123-def1-234567890123'),
            recommendation_text='For future refactoring tasks: Add 20% time buffer to estimates',
            priority='high',
            applicable_to=['Code refactoring', 'Module reorganization']
        ),
        # ... more recommendations
    ],
    metrics=ExecutionMetrics(
        actual_files=3,
        actual_tool_calls=18,
        actual_errors=1,
        actual_time_minutes=52.5,
        success_rate=94.4
    ),
    timestamp='2024-01-15T10:45:30.000000'
)
```

### Accessing Summary Components

```python
# Access individual components
print(f"Alignment Score: {summary.plan_vs_actual.alignment_score}")
print(f"Total Deviations: {len(summary.deviations)}")
print(f"High Severity Deviations: {len([d for d in summary.deviations if d.severity == 'high'])}")
print(f"Lessons Learned: {len(summary.lessons_learned)}")
print(f"Recommendations: {len(summary.recommendations)}")
print(f"Success Rate: {summary.metrics.success_rate}%")

# Filter deviations by category
scope_deviations = [d for d in summary.deviations if d.category == 'scope']
efficiency_deviations = [d for d in summary.deviations if d.category == 'efficiency']

# Filter recommendations by priority
high_priority = [r for r in summary.recommendations if r.priority == 'high']
medium_priority = [r for r in summary.recommendations if r.priority == 'medium']

# Access lessons by type
pattern_lessons = [l for l in summary.lessons_learned if l.type == 'pattern']
error_lessons = [l for l in summary.lessons_learned if l.type == 'error_pattern']
```

---

## Integration with Hooks

The clarity system integrates with the hook infrastructure to automatically trigger at appropriate points:

```python
from divineos.clarity_system import HookIntegrationInterface

# Register pre-work hook to generate clarity statement
def pre_work_callback(work_context):
    generator = DefaultClarityStatementGenerator()
    clarity = generator.generate_clarity_statement(work_context)
    generator.present_to_user(clarity)

HookIntegrationInterface.register_pre_work_hook(pre_work_callback)

# Register post-work hook to generate summary
def post_work_callback(session_id):
    # ... generate and present summary
    pass

HookIntegrationInterface.register_post_work_hook(post_work_callback)
```

---

## Error Handling Examples

### Handling Missing Work Context

```python
try:
    clarity = generator.generate_clarity_statement({})  # Empty context
except Exception as e:
    # System logs error and generates minimal statement
    print(f"Error: {e}")
    # Clarity statement still generated with available info
```

### Handling Ledger Query Failures

```python
try:
    execution = exec_analyzer.analyze_execution(session_id)
except Exception as e:
    # System logs error and uses cached data if available
    print(f"Ledger query failed: {e}")
    # Execution data still available from cache
```

### Handling Partial Analysis

```python
# If some deviations can't be calculated, they're skipped
deviations = dev_analyzer.analyze_deviations(plan_data, execution_data)
# Returns available deviations, logs errors for problematic metrics

# If some lessons can't be extracted, continue with available lessons
lessons = learning.extract_lessons(deviations, execution_data)
# Returns available lessons, logs errors for failed extractions
```
