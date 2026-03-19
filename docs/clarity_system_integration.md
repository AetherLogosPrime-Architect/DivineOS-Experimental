# Agent Work Clarity System - Integration Guide

This guide explains how to integrate the Agent Work Clarity System with existing DivineOS systems and configure it for your environment.

## Table of Contents

1. [Overview](#overview)
2. [Architecture Integration](#architecture-integration)
3. [Integration Points](#integration-points)
4. [Setup and Configuration](#setup-and-configuration)
5. [Triggering Clarity Generation](#triggering-clarity-generation)
6. [Retrieving and Displaying Summaries](#retrieving-and-displaying-summaries)
7. [Hook Integration](#hook-integration)
8. [Error Handling and Resilience](#error-handling-and-resilience)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The Agent Work Clarity System integrates with existing DivineOS infrastructure to provide transparent work planning and execution tracking. The system operates on top of:

- **Event Ledger**: Existing ledger that captures all tool calls and results
- **Session Manager**: Existing session management system
- **Event Emission System**: Existing event emission infrastructure
- **Hook System**: Existing hook infrastructure for triggering actions

The clarity system adds three layers:
1. **Pre-work clarity statements** - Generated before work begins
2. **Execution tracking** - Leverages existing ledger
3. **Post-work summaries** - Generated after work completes

---

## Architecture Integration

### System Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     Kiro Agent                              │
│              (AI Assistant executing work)                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
        ┌────────────────────────────────┐
        │  PRE-WORK PHASE                │
        │  ─────────────────────────────  │
        │  Clarity Statement Generator   │
        │  • Analyze planned work        │
        │  • Generate clarity statement  │
        │  • Present to user             │
        └────────────┬───────────────────┘
                     │
                     ↓
        ┌────────────────────────────────┐
        │  WORK EXECUTION PHASE          │
        │  ─────────────────────────────  │
        │  Existing DivineOS Layer       │
        │  • OS captures all events      │
        │  • Tool calls recorded         │
        │  • Results recorded            │
        │  • Errors recorded             │
        └────────────┬───────────────────┘
                     │
                     ↓
        ┌────────────────────────────────┐
        │  LEDGER (Existing)             │
        │  ─────────────────────────────  │
        │  • Stores all events           │
        │  • Maintains event history     │
        │  • Provides query interface    │
        └────────────┬───────────────────┘
                     │
                     ↓
        ┌────────────────────────────────┐
        │  POST-WORK PHASE               │
        │  ─────────────────────────────  │
        │  Analysis Pipeline             │
        │  • Plan Analyzer               │
        │  • Execution Analyzer          │
        │  • Deviation Analyzer          │
        │  • Learning Extractor          │
        │  • Summary Generator           │
        └────────────┬───────────────────┘
                     │
                     ↓
        ┌────────────────────────────────┐
        │  Summary Presented to User     │
        └────────────────────────────────┘
```

### Component Interaction

```
┌─────────────────────────────────────────────────────────────┐
│                  Clarity System Components                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Clarity Statement Generator                          │  │
│  │ • Generates pre-work clarity statements              │  │
│  │ • Extracts goal, approach, outcome, scope            │  │
│  │ • Presents to user (non-blocking)                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                         ↓                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Plan Analyzer                                        │  │
│  │ • Parses clarity statement                           │  │
│  │ • Extracts structured plan data                      │  │
│  │ • Normalizes metrics                                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                         ↓                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Execution Analyzer                                   │  │
│  │ • Queries ledger for session events                  │  │
│  │ • Extracts tool calls and results                    │  │
│  │ • Calculates execution metrics                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                         ↓                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Deviation Analyzer                                   │  │
│  │ • Compares plan vs actual                            │  │
│  │ • Identifies deviations                              │  │
│  │ • Categorizes by type and severity                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                         ↓                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Learning Extractor                                   │  │
│  │ • Extracts lessons from deviations                   │  │
│  │ • Identifies patterns                                │  │
│  │ • Generates recommendations                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                         ↓                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Summary Generator                                    │  │
│  │ • Compiles all analysis                              │  │
│  │ • Formats for presentation                           │  │
│  │ • Presents to user                                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Integration Points

### 1. Ledger Integration

The clarity system queries the existing event ledger to extract execution data.

**Interface**: `LedgerQueryInterface`

**Methods**:
- `query_events_for_session(session_id)` - Get all events for a session
- `extract_tool_calls_from_events(events)` - Extract tool calls from events
- `extract_errors_from_events(events)` - Extract errors from events
- `get_session_events(session_id)` - Get complete execution data

**Implementation**:
```python
from divineos.clarity_system import LedgerQueryInterface
from divineos.core.ledger import Ledger

# The ledger integration uses existing ledger APIs
ledger = Ledger()  # Existing ledger instance

# Query events for a session
events = ledger.query_events_for_session(session_id)

# Extract tool calls
tool_calls = LedgerQueryInterface.extract_tool_calls_from_events(events)

# Extract errors
errors = LedgerQueryInterface.extract_errors_from_events(events)
```

### 2. Session Manager Integration

The clarity system uses the session manager to access session information.

**Interface**: `SessionManagerInterface`

**Usage**:
```python
from divineos.clarity_system import SessionManagerInterface
from divineos.core.session_manager import SessionManager

# Get session information
session_manager = SessionManager()
session = session_manager.get_session(session_id)

# Session contains metadata needed for analysis
print(f"Session ID: {session.id}")
print(f"Start Time: {session.start_time}")
print(f"End Time: {session.end_time}")
```

### 3. Event Emission Integration

The clarity system emits events when clarity statements and summaries are generated.

**Interface**: `EventEmissionInterface`

**Methods**:
- `emit_clarity_statement_event(clarity_statement)` - Emit when clarity is generated
- `emit_summary_event(summary)` - Emit when summary is generated
- `emit_deviation_event(deviation)` - Emit for each deviation
- `emit_lesson_event(lesson)` - Emit for each lesson

**Implementation**:
```python
from divineos.clarity_system import EventEmissionInterface
from divineos.core.event_emission import EventEmitter

# Emit clarity statement event
event_emitter = EventEmitter()
EventEmissionInterface.emit_clarity_statement_event(clarity_statement)

# Emit summary event
EventEmissionInterface.emit_summary_event(summary)

# Emit deviation events
for deviation in deviations:
    EventEmissionInterface.emit_deviation_event(deviation)

# Emit lesson events
for lesson in lessons:
    EventEmissionInterface.emit_lesson_event(lesson)
```

### 4. Hook Integration

The clarity system integrates with the existing hook infrastructure to trigger at appropriate points.

**Interface**: `HookIntegrationInterface`

**Methods**:
- `register_pre_work_hook(callback)` - Register callback before work begins
- `register_post_work_hook(callback)` - Register callback after work completes
- `register_clarity_generated_hook(callback)` - Register callback when clarity is generated
- `register_summary_generated_hook(callback)` - Register callback when summary is generated

**Implementation**:
```python
from divineos.clarity_system import HookIntegrationInterface

# Register pre-work hook
def on_pre_work(work_context):
    generator = DefaultClarityStatementGenerator()
    clarity = generator.generate_clarity_statement(work_context)
    generator.present_to_user(clarity)

HookIntegrationInterface.register_pre_work_hook(on_pre_work)

# Register post-work hook
def on_post_work(session_id):
    # Generate and present summary
    pass

HookIntegrationInterface.register_post_work_hook(on_post_work)
```

---

## Setup and Configuration

### Installation

1. **Ensure clarity system package is installed**:
```bash
pip install divineos-clarity-system
```

2. **Import required components**:
```python
from divineos.clarity_system import (
    DefaultClarityStatementGenerator,
    DefaultPlanAnalyzer,
    DefaultExecutionAnalyzer,
    DefaultDeviationAnalyzer,
    DefaultLearningExtractor,
    DefaultSummaryGenerator,
    setup_clarity_logging,
)
```

### Configuration

1. **Set up logging**:
```python
from divineos.clarity_system import setup_clarity_logging

# Configure logging for clarity system
setup_clarity_logging(
    log_level='INFO',
    log_file='logs/clarity_system.log'
)
```

2. **Initialize components**:
```python
# Create component instances
clarity_generator = DefaultClarityStatementGenerator()
plan_analyzer = DefaultPlanAnalyzer()
exec_analyzer = DefaultExecutionAnalyzer()
dev_analyzer = DefaultDeviationAnalyzer()
learning_extractor = DefaultLearningExtractor()
summary_generator = DefaultSummaryGenerator()

# Validate components
assert clarity_generator.validate()
assert plan_analyzer.validate()
assert exec_analyzer.validate()
assert dev_analyzer.validate()
assert learning_extractor.validate()
assert summary_generator.validate()
```

3. **Configure integration points**:
```python
# Configure ledger integration
from divineos.core.ledger import Ledger
ledger = Ledger()
exec_analyzer.set_ledger(ledger)

# Configure session manager integration
from divineos.core.session_manager import SessionManager
session_manager = SessionManager()

# Configure event emission
from divineos.core.event_emission import EventEmitter
event_emitter = EventEmitter()
```

---

## Triggering Clarity Generation

### Method 1: Manual Trigger

Generate clarity statement manually before work begins:

```python
from divineos.clarity_system import DefaultClarityStatementGenerator

# Create work context
work_context = {
    "task": "Implement new feature",
    "goal": "Add user authentication",
    "approach": ["Design auth flow", "Implement login", "Add tests"],
    "expected_outcome": "Working authentication system",
    "scope": {
        "files_affected": ["auth.py", "models.py", "tests/test_auth.py"],
        "estimated_tool_calls": 20,
        "complexity": "high",
        "estimated_time_minutes": 120
    }
}

# Generate clarity statement
generator = DefaultClarityStatementGenerator()
clarity = generator.generate_clarity_statement(work_context)

# Present to user
user_feedback = generator.present_to_user(clarity)
```

### Method 2: Hook-Based Trigger

Register clarity generation with pre-work hook:

```python
from divineos.clarity_system import (
    DefaultClarityStatementGenerator,
    HookIntegrationInterface,
)

def generate_clarity_on_pre_work(work_context):
    """Called before work begins."""
    generator = DefaultClarityStatementGenerator()
    clarity = generator.generate_clarity_statement(work_context)
    generator.present_to_user(clarity)
    return clarity

# Register with hook system
HookIntegrationInterface.register_pre_work_hook(generate_clarity_on_pre_work)
```

### Method 3: Event-Based Trigger

Trigger clarity generation based on events:

```python
from divineos.core.event_emission import EventListener
from divineos.clarity_system import DefaultClarityStatementGenerator

class ClarityEventListener(EventListener):
    def on_work_started(self, event):
        """Called when work starts."""
        work_context = event.payload
        generator = DefaultClarityStatementGenerator()
        clarity = generator.generate_clarity_statement(work_context)
        generator.present_to_user(clarity)

# Register listener
listener = ClarityEventListener()
event_emitter.register_listener(listener)
```

---

## Retrieving and Displaying Summaries

### Method 1: Manual Retrieval

Generate and display summary after work completes:

```python
from uuid import UUID
from divineos.clarity_system import (
    DefaultPlanAnalyzer,
    DefaultExecutionAnalyzer,
    DefaultDeviationAnalyzer,
    DefaultLearningExtractor,
    DefaultSummaryGenerator,
)

# Session ID from completed work
session_id = UUID('...')

# Analyze plan
plan_analyzer = DefaultPlanAnalyzer()
plan = plan_analyzer.analyze_plan(clarity_statement)

# Analyze execution
exec_analyzer = DefaultExecutionAnalyzer()
execution = exec_analyzer.analyze_execution(session_id)

# Analyze deviations
dev_analyzer = DefaultDeviationAnalyzer()
deviations = dev_analyzer.analyze_deviations(plan, execution)

# Extract lessons
learning = DefaultLearningExtractor()
lessons = learning.extract_lessons(deviations, execution)
recommendations = learning.generate_recommendations(lessons)

# Generate summary
summary_gen = DefaultSummaryGenerator()
summary = summary_gen.generate_post_work_summary(
    clarity_statement, plan, execution, deviations, lessons, recommendations
)

# Display summary
summary_gen.present_summary_to_user(summary)
```

### Method 2: Hook-Based Retrieval

Register summary generation with post-work hook:

```python
from divineos.clarity_system import HookIntegrationInterface

def generate_summary_on_post_work(session_id):
    """Called after work completes."""
    # ... generate and present summary
    pass

HookIntegrationInterface.register_post_work_hook(generate_summary_on_post_work)
```

### Method 3: Programmatic Access

Access summary components programmatically:

```python
# Access summary components
print(f"Alignment Score: {summary.plan_vs_actual.alignment_score}")
print(f"Total Deviations: {len(summary.deviations)}")
print(f"Lessons Learned: {len(summary.lessons_learned)}")
print(f"Recommendations: {len(summary.recommendations)}")

# Filter by severity
high_severity = [d for d in summary.deviations if d.severity == 'high']
medium_severity = [d for d in summary.deviations if d.severity == 'medium']

# Filter by priority
high_priority_recs = [r for r in summary.recommendations if r.priority == 'high']

# Access metrics
print(f"Success Rate: {summary.metrics.success_rate}%")
print(f"Total Tool Calls: {summary.metrics.actual_tool_calls}")
print(f"Duration: {summary.metrics.actual_time_minutes} minutes")
```

### Method 4: Store and Retrieve

Store summaries for later retrieval:

```python
import json
from pathlib import Path

# Store summary
summary_dir = Path('summaries')
summary_dir.mkdir(exist_ok=True)

summary_file = summary_dir / f"{summary.id}.json"
with open(summary_file, 'w') as f:
    json.dump(summary.__dict__, f, indent=2, default=str)

# Retrieve summary later
with open(summary_file, 'r') as f:
    summary_data = json.load(f)
```

---

## Hook Integration

### Available Hooks

1. **Pre-Work Hook**: Called before work begins
2. **Post-Work Hook**: Called after work completes
3. **Clarity Generated Hook**: Called when clarity statement is generated
4. **Summary Generated Hook**: Called when summary is generated

### Hook Registration

```python
from divineos.clarity_system import HookIntegrationInterface

# Register pre-work hook
def on_pre_work(work_context):
    print(f"Work starting: {work_context['task']}")
    # Generate clarity statement
    pass

HookIntegrationInterface.register_pre_work_hook(on_pre_work)

# Register post-work hook
def on_post_work(session_id):
    print(f"Work completed: {session_id}")
    # Generate summary
    pass

HookIntegrationInterface.register_post_work_hook(on_post_work)

# Register clarity generated hook
def on_clarity_generated(clarity_statement):
    print(f"Clarity generated: {clarity_statement.goal}")
    # Emit event or log
    pass

HookIntegrationInterface.register_clarity_generated_hook(on_clarity_generated)

# Register summary generated hook
def on_summary_generated(summary):
    print(f"Summary generated: {summary.id}")
    # Store or emit event
    pass

HookIntegrationInterface.register_summary_generated_hook(on_summary_generated)
```

### Hook Execution Order

```
1. Pre-Work Hook
   ↓
2. Clarity Statement Generation
   ↓
3. Clarity Generated Hook
   ↓
4. Work Execution (existing DivineOS layer)
   ↓
5. Post-Work Hook
   ↓
6. Summary Generation
   ↓
7. Summary Generated Hook
```

---

## Error Handling and Resilience

### Error Handling Strategy

The clarity system implements graceful error handling at each component:

1. **Clarity Generation Failures**:
   - Logs error
   - Generates minimal statement with available info
   - Continues with work execution

2. **Plan Analysis Failures**:
   - Logs error
   - Uses available data for comparison
   - Continues with analysis

3. **Execution Analysis Failures**:
   - Logs error
   - Uses cached data if available
   - Continues with analysis

4. **Deviation Analysis Failures**:
   - Logs error
   - Skips problematic metrics
   - Continues with available deviations

5. **Lesson Extraction Failures**:
   - Logs error
   - Continues with available lessons
   - Skips failed extractions

6. **Summary Generation Failures**:
   - Logs error
   - Presents partial summary
   - Includes available components

### Error Recovery

```python
from divineos.clarity_system import get_clarity_logger

logger = get_clarity_logger(__name__)

try:
    clarity = generator.generate_clarity_statement(work_context)
except Exception as e:
    logger.error(f"Clarity generation failed: {e}")
    # System continues with minimal statement

try:
    execution = exec_analyzer.analyze_execution(session_id)
except Exception as e:
    logger.error(f"Execution analysis failed: {e}")
    # System continues with cached data

try:
    deviations = dev_analyzer.analyze_deviations(plan, execution)
except Exception as e:
    logger.error(f"Deviation analysis failed: {e}")
    # System continues with available deviations
```

---

## Troubleshooting

### Issue: Clarity Statement Not Generated

**Symptoms**: No clarity statement appears before work begins

**Solutions**:
1. Check that pre-work hook is registered
2. Verify work context is provided
3. Check logs for errors: `logs/clarity_system.log`
4. Ensure clarity generator is initialized

```python
# Verify hook registration
from divineos.clarity_system import HookIntegrationInterface
HookIntegrationInterface.register_pre_work_hook(on_pre_work)

# Verify generator initialization
generator = DefaultClarityStatementGenerator()
assert generator.validate()
```

### Issue: Execution Data Not Extracted

**Symptoms**: Summary shows no tool calls or metrics

**Solutions**:
1. Verify ledger is accessible
2. Check session ID is correct
3. Verify events were recorded in ledger
4. Check logs for ledger query errors

```python
# Verify ledger access
from divineos.core.ledger import Ledger
ledger = Ledger()
events = ledger.query_events_for_session(session_id)
print(f"Events found: {len(events)}")

# Verify execution analyzer
exec_analyzer = DefaultExecutionAnalyzer(ledger=ledger)
execution = exec_analyzer.analyze_execution(session_id)
print(f"Tool calls: {len(execution.tool_calls)}")
```

### Issue: Deviations Not Detected

**Symptoms**: Summary shows no deviations even though metrics differ

**Solutions**:
1. Verify plan data is extracted correctly
2. Verify execution data is extracted correctly
3. Check deviation severity thresholds
4. Check logs for deviation analysis errors

```python
# Verify plan extraction
plan = plan_analyzer.analyze_plan(clarity_statement)
print(f"Plan metrics: {plan.metrics}")

# Verify execution extraction
execution = exec_analyzer.analyze_execution(session_id)
print(f"Execution metrics: {execution.metrics}")

# Verify deviation analysis
deviations = dev_analyzer.analyze_deviations(plan, execution)
print(f"Deviations found: {len(deviations)}")
```

### Issue: Lessons Not Extracted

**Symptoms**: Summary shows no lessons or recommendations

**Solutions**:
1. Verify deviations are detected
2. Check lesson confidence thresholds
3. Verify learning extractor is initialized
4. Check logs for lesson extraction errors

```python
# Verify deviations
print(f"Deviations: {len(deviations)}")

# Verify lesson extraction
lessons = learning.extract_lessons(deviations, execution)
print(f"Lessons found: {len(lessons)}")

# Verify recommendations
recommendations = learning.generate_recommendations(lessons)
print(f"Recommendations: {len(recommendations)}")
```

### Issue: Summary Not Displayed

**Symptoms**: Summary is generated but not shown to user

**Solutions**:
1. Verify post-work hook is registered
2. Check that summary generator is initialized
3. Verify user output interface is available
4. Check logs for presentation errors

```python
# Verify hook registration
HookIntegrationInterface.register_post_work_hook(on_post_work)

# Verify summary generation
summary = summary_gen.generate_post_work_summary(...)
print(f"Summary ID: {summary.id}")

# Verify presentation
summary_gen.present_summary_to_user(summary)
```

---

## Best Practices

1. **Always validate components** before use:
   ```python
   assert clarity_generator.validate()
   assert plan_analyzer.validate()
   ```

2. **Handle errors gracefully**:
   ```python
   try:
       clarity = generator.generate_clarity_statement(work_context)
   except Exception as e:
       logger.error(f"Error: {e}")
       # Continue with fallback
   ```

3. **Use logging for debugging**:
   ```python
   from divineos.clarity_system import get_clarity_logger
   logger = get_clarity_logger(__name__)
   logger.info("Clarity statement generated")
   ```

4. **Register hooks early**:
   ```python
   # Register hooks during initialization
   HookIntegrationInterface.register_pre_work_hook(on_pre_work)
   HookIntegrationInterface.register_post_work_hook(on_post_work)
   ```

5. **Store summaries for analysis**:
   ```python
   # Store summaries for later retrieval and analysis
   summary_file = Path(f"summaries/{summary.id}.json")
   with open(summary_file, 'w') as f:
       json.dump(summary.__dict__, f, default=str)
   ```

6. **Monitor metrics over time**:
   ```python
   # Track metrics across multiple sessions
   alignment_scores = [s.plan_vs_actual.alignment_score for s in summaries]
   avg_alignment = sum(alignment_scores) / len(alignment_scores)
   ```
