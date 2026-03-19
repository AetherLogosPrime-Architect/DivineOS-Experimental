# Agent Work Clarity System - API Documentation

## Overview

The Agent Work Clarity System provides transparent agent work planning and execution tracking through a comprehensive API. This document describes all public functions, data structures, and integration points.

## Table of Contents

1. [Data Structures](#data-structures)
2. [Core Components](#core-components)
3. [Integration Interfaces](#integration-interfaces)
4. [Error Handling](#error-handling)

---

## Data Structures

### ScopeEstimate

Represents the estimated scope for planned work.

```python
@dataclass
class ScopeEstimate:
    estimated_files: int              # Number of files expected to be modified
    estimated_tool_calls: int         # Number of tool calls expected
    estimated_complexity: str         # Complexity level: "low", "medium", "high"
    estimated_time_minutes: int       # Estimated duration in minutes
```

### ClarityStatement

Pre-work clarity statement describing the agent's planned work.

```python
@dataclass
class ClarityStatement:
    id: UUID                          # Unique identifier for this statement
    timestamp: str                    # ISO8601 timestamp when statement was created
    goal: str                         # Primary goal of the planned work
    approach: str                     # Strategy or method to be used
    expected_outcome: str             # Expected deliverables or results
    scope: ScopeEstimate              # Scope estimate for the work
    user_feedback: Optional[str]      # Optional user feedback on the plan
```

### PlanMetrics

Metrics extracted from the clarity statement plan.

```python
@dataclass
class PlanMetrics:
    estimated_files: int              # Estimated files to modify
    estimated_tool_calls: int         # Estimated tool calls needed
    estimated_complexity: str         # Complexity level
    estimated_time_minutes: int       # Estimated time in minutes
```

### PlanData

Structured plan data extracted and normalized from a clarity statement.

```python
@dataclass
class PlanData:
    clarity_statement_id: UUID        # Reference to source clarity statement
    goal: str                         # Extracted goal
    approach: str                     # Extracted approach
    expected_outcome: str             # Extracted expected outcome
    metrics: PlanMetrics              # Extracted and normalized metrics
```

### ToolCall

Represents a single tool call event from the ledger.

```python
@dataclass
class ToolCall:
    tool_name: str                    # Name of the tool called
    timestamp: str                    # ISO8601 timestamp of the call
    input: Dict[str, Any]             # Input parameters to the tool
```

### ExecutionMetrics

Metrics calculated from actual work execution.

```python
@dataclass
class ExecutionMetrics:
    actual_files: int                 # Number of files actually modified
    actual_tool_calls: int            # Number of tool calls actually made
    actual_errors: int                # Number of errors encountered
    actual_time_minutes: float        # Actual duration in minutes
    success_rate: float               # Success rate as percentage (0.0-100.0)
```

### ExecutionData

Actual execution data extracted from the ledger for a work session.

```python
@dataclass
class ExecutionData:
    session_id: UUID                  # Session ID for this execution
    tool_calls: List[ToolCall]        # All tool calls made during execution
    errors: List[str]                 # All errors encountered
    metrics: ExecutionMetrics         # Calculated execution metrics
```

### Deviation

Represents a deviation between planned and actual metrics.

```python
@dataclass
class Deviation:
    metric: str                       # Name of the metric (e.g., "tool_calls")
    planned: float                    # Planned value
    actual: float                     # Actual value
    difference: float                 # Absolute difference (actual - planned)
    percentage: float                 # Percentage deviation
    severity: str                     # Severity level: "low", "medium", "high"
    category: str                     # Category: "scope", "efficiency", "quality", "approach"
```

### Lesson

Represents a lesson extracted from execution analysis.

```python
@dataclass
class Lesson:
    id: UUID                          # Unique identifier for this lesson
    type: str                         # Type: "deviation", "pattern", "error_pattern", "approach"
    description: str                  # Description of the lesson
    context: str                      # Context where lesson applies
    insight: str                      # Key insight or takeaway
    confidence: float                 # Confidence score (0.0-1.0)
    source_session_id: Optional[UUID] # Session where lesson was learned
    created_at: str                   # ISO8601 timestamp when lesson was created
```

### Recommendation

Represents a recommendation generated from lessons.

```python
@dataclass
class Recommendation:
    lesson_id: UUID                   # Reference to source lesson
    recommendation_text: str          # Specific, actionable recommendation
    priority: str                     # Priority level: "low", "medium", "high"
    applicable_to: List[str]          # Contexts where recommendation applies
```

### PlanVsActualComparison

Comparison between planned and actual work execution.

```python
@dataclass
class PlanVsActualComparison:
    planned_goal: str                 # Goal from clarity statement
    actual_goal: str                  # Actual goal achieved
    planned_approach: str             # Planned approach
    actual_approach: str              # Actual approach used
    planned_outcome: str              # Expected outcome
    actual_outcome: str               # Actual outcome achieved
    alignment_score: float            # Alignment score (0.0-1.0)
```

### PostWorkSummary

Comprehensive post-work summary combining all analysis.

```python
@dataclass
class PostWorkSummary:
    id: UUID                          # Unique identifier for this summary
    clarity_statement: ClarityStatement  # Original clarity statement
    plan_vs_actual: PlanVsActualComparison  # Plan vs actual comparison
    deviations: List[Deviation]       # All identified deviations
    lessons_learned: List[Lesson]     # All extracted lessons
    recommendations: List[Recommendation]  # All generated recommendations
    metrics: ExecutionMetrics         # Execution metrics
    timestamp: str                    # ISO8601 timestamp when summary was created
```

---

## Core Components

### ClarityStatementGenerator

Generates pre-work clarity statements describing planned work.

#### Methods

**`generate_clarity_statement(work_context: Dict[str, Any]) -> ClarityStatement`**

Generates a clarity statement from work context.

- **Parameters:**
  - `work_context`: Dictionary containing planned work information
- **Returns:** `ClarityStatement` with goal, approach, outcome, and scope
- **Raises:** Logs errors and returns minimal statement if generation fails

**`extract_goal(work_context: Dict[str, Any]) -> str`**

Extracts the primary goal from work context.

- **Parameters:**
  - `work_context`: Dictionary containing work information
- **Returns:** Goal as string

**`extract_approach(work_context: Dict[str, Any]) -> str`**

Extracts the planned approach or strategy from work context.

- **Parameters:**
  - `work_context`: Dictionary containing work information
- **Returns:** Approach as string

**`extract_expected_outcome(work_context: Dict[str, Any]) -> str`**

Extracts the expected outcome or deliverables from work context.

- **Parameters:**
  - `work_context`: Dictionary containing work information
- **Returns:** Expected outcome as string

**`extract_scope(work_context: Dict[str, Any]) -> ScopeEstimate`**

Extracts scope estimate from work context.

- **Parameters:**
  - `work_context`: Dictionary containing work information
- **Returns:** `ScopeEstimate` with file, tool call, complexity, and time estimates

**`present_to_user(clarity_statement: ClarityStatement) -> Optional[str]`**

Presents clarity statement to user and optionally captures feedback.

- **Parameters:**
  - `clarity_statement`: Statement to present
- **Returns:** Optional user feedback

### PlanAnalyzer

Analyzes and normalizes clarity statements into structured plan data.

#### Methods

**`analyze_plan(clarity_statement: ClarityStatement) -> PlanData`**

Analyzes clarity statement and extracts structured plan.

- **Parameters:**
  - `clarity_statement`: Clarity statement to analyze
- **Returns:** `PlanData` with normalized plan information

**`extract_goal_from_statement(statement: ClarityStatement) -> str`**

Extracts goal from clarity statement.

- **Parameters:**
  - `statement`: Clarity statement
- **Returns:** Goal as string

**`extract_approach_from_statement(statement: ClarityStatement) -> str`**

Extracts approach from clarity statement.

- **Parameters:**
  - `statement`: Clarity statement
- **Returns:** Approach as string

**`extract_scope_metrics(clarity_statement: ClarityStatement) -> Dict[str, Any]`**

Extracts scope metrics from clarity statement.

- **Parameters:**
  - `clarity_statement`: Clarity statement
- **Returns:** Dictionary with estimated_files, estimated_tool_calls, estimated_complexity, estimated_time_minutes

**`normalize_plan_data(plan_data: PlanData) -> PlanData`**

Normalizes plan data to standard format.

- **Parameters:**
  - `plan_data`: Plan data to normalize
- **Returns:** Normalized `PlanData`

### ExecutionAnalyzer

Queries ledger and extracts actual execution data.

#### Methods

**`analyze_execution(session_id: UUID) -> ExecutionData`**

Analyzes execution from ledger for a session.

- **Parameters:**
  - `session_id`: Session ID to analyze
- **Returns:** `ExecutionData` with tool calls, errors, and metrics

**`extract_tool_calls(session_id: UUID) -> List[ToolCall]`**

Extracts all tool calls from ledger for a session.

- **Parameters:**
  - `session_id`: Session ID
- **Returns:** List of `ToolCall` objects

**`extract_errors(session_id: UUID) -> List[str]`**

Extracts all errors from ledger for a session.

- **Parameters:**
  - `session_id`: Session ID
- **Returns:** List of error messages

**`calculate_execution_metrics(execution_data: ExecutionData) -> ExecutionMetrics`**

Calculates metrics from execution data.

- **Parameters:**
  - `execution_data`: Execution data to analyze
- **Returns:** `ExecutionMetrics` with calculated values

### DeviationAnalyzer

Compares planned vs actual and identifies deviations.

#### Methods

**`analyze_deviations(plan_data: PlanData, execution_data: ExecutionData) -> List[Deviation]`**

Analyzes deviations between plan and execution.

- **Parameters:**
  - `plan_data`: Planned work data
  - `execution_data`: Actual execution data
- **Returns:** List of `Deviation` objects

**`compare_metric(metric_name: str, planned: float, actual: float) -> Deviation`**

Compares a single metric and creates deviation.

- **Parameters:**
  - `metric_name`: Name of metric to compare
  - `planned`: Planned value
  - `actual`: Actual value
- **Returns:** `Deviation` object

**`categorize_deviations(deviations: List[Deviation]) -> Dict[str, List[Deviation]]`**

Categorizes deviations by type.

- **Parameters:**
  - `deviations`: List of deviations
- **Returns:** Dictionary with deviations grouped by category

### LearningExtractor

Extracts lessons and generates recommendations.

#### Methods

**`extract_lessons(deviations: List[Deviation], execution_data: ExecutionData) -> List[Lesson]`**

Extracts lessons from deviations and execution.

- **Parameters:**
  - `deviations`: List of deviations
  - `execution_data`: Execution data
- **Returns:** List of `Lesson` objects

**`extract_deviation_lessons(deviations: List[Deviation]) -> List[Lesson]`**

Extracts lessons from deviations.

- **Parameters:**
  - `deviations`: List of deviations
- **Returns:** List of `Lesson` objects

**`identify_tool_patterns(execution_data: ExecutionData) -> List[Lesson]`**

Identifies patterns in tool usage.

- **Parameters:**
  - `execution_data`: Execution data
- **Returns:** List of `Lesson` objects describing patterns

**`generate_recommendations(lessons: List[Lesson]) -> List[Recommendation]`**

Generates recommendations from lessons.

- **Parameters:**
  - `lessons`: List of lessons
- **Returns:** List of `Recommendation` objects

### SummaryGenerator

Generates comprehensive post-work summaries.

#### Methods

**`generate_post_work_summary(clarity_statement: ClarityStatement, plan_data: PlanData, execution_data: ExecutionData, deviations: List[Deviation], lessons: List[Lesson], recommendations: List[Recommendation]) -> PostWorkSummary`**

Generates comprehensive post-work summary.

- **Parameters:**
  - `clarity_statement`: Original clarity statement
  - `plan_data`: Planned work data
  - `execution_data`: Actual execution data
  - `deviations`: Identified deviations
  - `lessons`: Extracted lessons
  - `recommendations`: Generated recommendations
- **Returns:** `PostWorkSummary` object

**`generate_plan_vs_actual_section(plan_data: PlanData, execution_data: ExecutionData) -> Dict[str, Any]`**

Generates plan vs actual comparison section.

- **Parameters:**
  - `plan_data`: Planned work data
  - `execution_data`: Actual execution data
- **Returns:** Dictionary with comparison data

**`generate_deviations_section(deviations: List[Deviation]) -> Dict[str, Any]`**

Generates deviations section.

- **Parameters:**
  - `deviations`: List of deviations
- **Returns:** Dictionary with deviation summary

**`generate_metrics_section(execution_data: ExecutionData) -> Dict[str, Any]`**

Generates metrics section.

- **Parameters:**
  - `execution_data`: Execution data
- **Returns:** Dictionary with execution metrics

**`present_summary_to_user(summary: PostWorkSummary) -> None`**

Presents summary to user.

- **Parameters:**
  - `summary`: Summary to present

---

## Integration Interfaces

### LedgerQueryInterface

Interface for querying the event ledger.

#### Methods

**`query_events_for_session(session_id: UUID) -> List[dict]`**

Queries ledger for all events in a session.

- **Parameters:**
  - `session_id`: Session ID to query
- **Returns:** List of event dictionaries

**`extract_tool_calls_from_events(events: List[dict]) -> List[ToolCall]`**

Extracts tool calls from event list.

- **Parameters:**
  - `events`: List of events from ledger
- **Returns:** List of `ToolCall` objects

**`extract_errors_from_events(events: List[dict]) -> List[str]`**

Extracts errors from event list.

- **Parameters:**
  - `events`: List of events from ledger
- **Returns:** List of error messages

**`get_session_events(session_id: UUID) -> ExecutionData`**

Gets all execution data for a session.

- **Parameters:**
  - `session_id`: Session ID
- **Returns:** `ExecutionData` object

### SessionManagerInterface

Interface for session management.

Provides access to session information and metadata.

### EventEmissionInterface

Interface for emitting clarity-related events.

#### Methods

**`emit_clarity_statement_event(clarity_statement: ClarityStatement) -> bool`**

Emits event when clarity statement is generated.

- **Parameters:**
  - `clarity_statement`: Generated clarity statement
- **Returns:** True if event was emitted successfully

**`emit_summary_event(summary: PostWorkSummary) -> bool`**

Emits event when summary is generated.

- **Parameters:**
  - `summary`: Generated summary
- **Returns:** True if event was emitted successfully

**`emit_deviation_event(deviation: Deviation) -> bool`**

Emits event for each deviation.

- **Parameters:**
  - `deviation`: Identified deviation
- **Returns:** True if event was emitted successfully

**`emit_lesson_event(lesson: Lesson) -> bool`**

Emits event for each lesson.

- **Parameters:**
  - `lesson`: Extracted lesson
- **Returns:** True if event was emitted successfully

### HookIntegrationInterface

Interface for integrating with hook system.

#### Methods

**`register_pre_work_hook(callback: Callable) -> bool`**

Registers callback to run before work begins.

- **Parameters:**
  - `callback`: Function to call before work
- **Returns:** True if hook was registered successfully

**`register_post_work_hook(callback: Callable) -> bool`**

Registers callback to run after work completes.

- **Parameters:**
  - `callback`: Function to call after work
- **Returns:** True if hook was registered successfully

**`register_clarity_generated_hook(callback: Callable) -> bool`**

Registers callback when clarity statement is generated.

- **Parameters:**
  - `callback`: Function to call when clarity is generated
- **Returns:** True if hook was registered successfully

**`register_summary_generated_hook(callback: Callable) -> bool`**

Registers callback when summary is generated.

- **Parameters:**
  - `callback`: Function to call when summary is generated
- **Returns:** True if hook was registered successfully

---

## Error Handling

All components implement graceful error handling:

- **Clarity Generation Failures**: Logs error and generates minimal statement with available info
- **Plan Analysis Failures**: Logs error and uses available data for comparison
- **Execution Analysis Failures**: Logs error and uses cached or partial data
- **Deviation Analysis Failures**: Logs error and skips problematic metrics
- **Lesson Extraction Failures**: Logs error and continues with available lessons
- **Summary Generation Failures**: Logs error and presents partial summary

All errors are logged using the clarity system logger for debugging and analysis.

---

## Usage Example

```python
from divineos.clarity_system import (
    DefaultClarityStatementGenerator,
    DefaultPlanAnalyzer,
    DefaultExecutionAnalyzer,
    DefaultDeviationAnalyzer,
    DefaultLearningExtractor,
    DefaultSummaryGenerator,
)

# Generate clarity statement
generator = DefaultClarityStatementGenerator()
clarity = generator.generate_clarity_statement(work_context)

# Analyze plan
plan_analyzer = DefaultPlanAnalyzer()
plan = plan_analyzer.analyze_plan(clarity)

# Analyze execution
exec_analyzer = DefaultExecutionAnalyzer()
execution = exec_analyzer.analyze_execution(session_id)

# Identify deviations
dev_analyzer = DefaultDeviationAnalyzer()
deviations = dev_analyzer.analyze_deviations(plan, execution)

# Extract lessons
learning = DefaultLearningExtractor()
lessons = learning.extract_lessons(deviations, execution)
recommendations = learning.generate_recommendations(lessons)

# Generate summary
summary_gen = DefaultSummaryGenerator()
summary = summary_gen.generate_post_work_summary(
    clarity, plan, execution, deviations, lessons, recommendations
)

# Present to user
summary_gen.present_summary_to_user(summary)
```
