# Memory Monitor Integration Guide

## Overview

The `AgentMemoryMonitor` is a core component of DivineOS that automatically manages agent memory and token usage during work sessions. It provides:

- **Automatic token monitoring** - Tracks token usage and triggers compression at thresholds
- **Work checkpointing** - Saves work progress to the ledger
- **Context compression** - Summarizes and compresses context when approaching limits
- **Learning cycle integration** - Runs pattern analysis at session end
- **Pattern recommendations** - Suggests patterns based on current context

## Entry Points

### 1. Session Initialization

**Function**: `load_context(session_id: str) -> dict[str, Any]`

Called at the start of a work session to load previous context from the ledger.

```python
from divineos.agent_integration.memory_monitor import load_context

# Load context for a session
context = load_context(session_id="my-session-123")

# Returns:
# {
#     "session_id": "my-session-123",
#     "previous_work": [...],  # Previous work items from ledger
#     "recent_context": [...],  # Recent context for reference
#     "loaded_at": "2026-03-19T21:00:00+00:00"
# }
```

### 2. Token Usage Monitoring

**Function**: `check_token_usage(current_tokens: int) -> dict[str, Any]`

Called periodically to check token usage and get recommended actions.

```python
from divineos.agent_integration.memory_monitor import check_token_usage

# Check token usage
status = check_token_usage(current_tokens=150000)

# Returns:
# {
#     "current_tokens": 150000,
#     "remaining_tokens": 50000,
#     "usage_percent": 75.0,
#     "action": "COMPRESS_NOW",
#     "message": "Token usage at 75.0% - Saving work to ledger and compressing context"
# }
```

**Actions**:
- `None` - No action needed
- `"PREPARE_COMPRESSION"` - Prepare to compress (65% threshold)
- `"COMPRESS_NOW"` - Compress immediately (75% threshold)

### 3. Work Checkpointing

**Function**: `save_checkpoint(task: str, status: str, files_modified: list[str], tests_passing: int, commit_hash: Optional[str] = None, notes: str = "") -> str`

Save work progress to the ledger.

```python
from divineos.agent_integration.memory_monitor import save_checkpoint

# Save a work checkpoint
event_id = save_checkpoint(
    task="Implement user authentication",
    status="completed",
    files_modified=["src/auth.py", "tests/test_auth.py"],
    tests_passing=42,
    commit_hash="abc123def456",
    notes="All tests passing, ready for review"
)

# Returns event ID from ledger
```

**Parameters**:
- `task` - Name of the task completed
- `status` - Status: "in_progress", "completed", or "failed"
- `files_modified` - List of files that were modified
- `tests_passing` - Number of tests passing
- `commit_hash` - Optional git commit hash
- `notes` - Optional additional notes

### 4. Context Compression

**Function**: `compress(summary: str) -> str`

Compress context by saving a summary to the ledger.

```python
from divineos.agent_integration.memory_monitor import compress

# Compress context
event_id = compress(
    summary="Completed Phase 1 integration tests. All 39 tests passing. "
            "Fixed datetime deprecation warnings. Ready for Phase 2."
)

# Returns event ID from ledger
```

### 5. Session End

**Function**: `end_session(summary: str, final_status: str = "completed") -> str`

End the work session and trigger the learning cycle.

```python
from divineos.agent_integration.memory_monitor import end_session

# End the session
event_id = end_session(
    summary="Completed all Phase 1 tasks. System is stable and ready for Phase 2.",
    final_status="completed"
)

# Returns event ID from ledger
```

**Final Status Options**:
- `"completed"` - Session completed successfully
- `"paused"` - Session paused for later continuation
- `"failed"` - Session failed

## Usage Patterns

### Pattern 1: Basic Session Workflow

```python
from divineos.agent_integration.memory_monitor import (
    load_context,
    check_token_usage,
    save_checkpoint,
    end_session,
)

# 1. Load previous context
context = load_context(session_id="work-session-1")

# 2. Do work...

# 3. Check token usage periodically
status = check_token_usage(current_tokens=120000)
if status["action"] == "COMPRESS_NOW":
    # Handle compression
    pass

# 4. Save checkpoints after major work
save_checkpoint(
    task="Implement feature X",
    status="completed",
    files_modified=["src/feature_x.py"],
    tests_passing=10
)

# 5. End session
end_session(
    summary="Completed feature X implementation",
    final_status="completed"
)
```

### Pattern 2: Handling Compression

```python
from divineos.agent_integration.memory_monitor import (
    check_token_usage,
    compress,
)

# Monitor token usage
status = check_token_usage(current_tokens=150000)

if status["action"] == "COMPRESS_NOW":
    # Create a summary of work done
    summary = """
    Completed:
    - Task 1: Integration tests (39 tests passing)
    - Task 2: Datetime deprecation fixes (14 files)
    - Task 3: Semantic analyzer implementation (24 tests)
    
    Status: Ready for Phase 2
    """
    
    # Compress context
    compress(summary)
    
    # Continue with new context
```

### Pattern 3: Work Outcome Recording

```python
from divineos.agent_integration.memory_monitor import get_memory_monitor

# Get monitor instance
monitor = get_memory_monitor(session_id="work-session-1")

# Record work outcome
monitor.record_work_outcome(
    task="Implement feature X",
    pattern_id="pattern-123",
    success=True,
    violations_introduced=0,
    token_efficiency=0.95,
    rework_needed=False
)
```

## Token Budget Management

### Budget Thresholds

- **Total Budget**: 200,000 tokens
- **Warning Threshold**: 130,000 tokens (65%)
- **Compression Threshold**: 150,000 tokens (75%)

### Compression Strategy

When approaching the compression threshold:

1. **Save work checkpoint** - Record current progress
2. **Summarize context** - Create a concise summary of work done
3. **Compress to ledger** - Save summary to ledger
4. **Clear context** - Start fresh with compressed context

### Example Compression Flow

```python
# Monitor detects 75% token usage
status = check_token_usage(current_tokens=150000)
# status["action"] == "COMPRESS_NOW"

# Save current work
save_checkpoint(
    task="Phase 1 completion",
    status="completed",
    files_modified=["src/file1.py", "src/file2.py"],
    tests_passing=1419
)

# Compress context
compress(
    summary="Phase 1 complete: 39 integration tests, "
            "datetime fixes, semantic analyzer. "
            "All 1443 tests passing."
)

# Continue with new context
```

## Learning Cycle Integration

The memory monitor automatically runs the learning cycle at session end:

```python
from divineos.agent_integration.memory_monitor import end_session

# End session triggers learning cycle
event_id = end_session(
    summary="Phase 1 complete",
    final_status="completed"
)

# Learning cycle runs automatically:
# 1. Loads work history from ledger
# 2. Extracts patterns from work outcomes
# 3. Updates pattern confidence scores
# 4. Detects pattern invalidation
# 5. Generates humility audit
# 6. Stores results to ledger
```

## Error Handling

### Token Budget Exceeded

If token usage exceeds the budget:

```python
from divineos.agent_integration.memory_monitor import check_token_usage

status = check_token_usage(current_tokens=200000)

if status["usage_percent"] >= 100:
    # Handle budget exceeded
    # Options:
    # 1. Compress context immediately
    # 2. End session and start new one
    # 3. Implement custom compression strategy
    pass
```

### Compression Failures

```python
from divineos.agent_integration.memory_monitor import compress

try:
    compress(summary="Work summary")
except Exception as e:
    # Handle compression failure
    # Options:
    # 1. Retry compression
    # 2. Save to local file
    # 3. End session gracefully
    print(f"Compression failed: {e}")
```

### Session End Failures

```python
from divineos.agent_integration.memory_monitor import end_session

try:
    end_session(
        summary="Session summary",
        final_status="completed"
    )
except Exception as e:
    # Handle session end failure
    # Options:
    # 1. Retry end_session
    # 2. Save summary locally
    # 3. Log error for manual recovery
    print(f"Session end failed: {e}")
```

## Best Practices

### 1. Regular Checkpointing

Save checkpoints after completing major work:

```python
# After each task
save_checkpoint(
    task="Task name",
    status="completed",
    files_modified=["file1.py", "file2.py"],
    tests_passing=100
)
```

### 2. Proactive Compression

Don't wait for compression threshold - compress when:
- Completing a major phase
- Before starting a new major task
- When context becomes large

```python
# Compress proactively
compress(summary="Phase 1 complete, starting Phase 2")
```

### 3. Meaningful Summaries

Create summaries that capture:
- What was accomplished
- Current status
- Next steps
- Any important context

```python
summary = """
Completed Phase 1:
- 39 integration tests passing
- All datetime deprecation warnings fixed
- Semantic analyzer implemented with 24 tests
- Total: 1443 tests passing

Status: Ready for Phase 2 (violation detection improvements)
Next: Implement semantic analysis for violation detection
"""
```

### 4. Monitor Token Usage

Check token usage regularly:

```python
# Check every major task
status = check_token_usage(current_tokens)
if status["action"]:
    print(f"Action needed: {status['message']}")
```

### 5. Record Work Outcomes

Record outcomes for pattern learning:

```python
monitor.record_work_outcome(
    task="Task name",
    pattern_id="pattern-id",
    success=True,
    violations_introduced=0,
    token_efficiency=0.95,
    rework_needed=False
)
```

## Integration with Other Components

### Clarity Enforcement

Memory monitor works with clarity enforcement to track violations:

```python
# Violations are captured and stored
# Learning cycle analyzes violation patterns
# Patterns inform future recommendations
```

### Contradiction Resolution

Memory monitor tracks contradiction resolution:

```python
# Contradictions are resolved and stored
# Learning cycle analyzes resolution patterns
# Patterns improve future decision-making
```

### Pattern Recommender

Memory monitor provides context for pattern recommendations:

```python
from divineos.agent_integration.pattern_recommender import PatternRecommender

recommender = PatternRecommender()

# Load humility audit from memory monitor
audit = recommender.load_humility_audit()

# Get recommendation based on current context
recommendation = recommender.generate_recommendation(context)
```

## Troubleshooting

### Issue: Token usage not decreasing after compression

**Solution**: Ensure compression summary is being saved to ledger correctly.

```python
# Verify compression event was created
event_id = compress(summary="...")
if not event_id:
    print("Compression failed - event not created")
```

### Issue: Learning cycle not running at session end

**Solution**: Ensure end_session is called with correct parameters.

```python
# Verify session end
event_id = end_session(
    summary="Session summary",
    final_status="completed"
)
if not event_id:
    print("Session end failed - learning cycle not triggered")
```

### Issue: Previous context not loading

**Solution**: Verify session_id is correct and previous work exists.

```python
# Check loaded context
context = load_context(session_id="my-session")
if not context["previous_work"]:
    print("No previous work found for this session")
```

## API Reference

### Functions

| Function | Purpose | Returns |
|----------|---------|---------|
| `load_context(session_id)` | Load previous context | dict with session context |
| `check_token_usage(current_tokens)` | Check token status | dict with status and action |
| `save_checkpoint(...)` | Save work progress | event_id from ledger |
| `compress(summary)` | Compress context | event_id from ledger |
| `end_session(summary, final_status)` | End session | event_id from ledger |
| `get_memory_monitor(session_id)` | Get monitor instance | AgentMemoryMonitor |

### Classes

| Class | Purpose |
|-------|---------|
| `AgentMemoryMonitor` | Main memory monitoring class |

### Methods

| Method | Purpose |
|--------|---------|
| `load_session_context()` | Load context for session |
| `update_token_usage(current_tokens)` | Update token usage |
| `save_work_checkpoint(...)` | Save work checkpoint |
| `compress_context(summary)` | Compress context |
| `run_learning_cycle()` | Run learning cycle |
| `get_recommendation(context)` | Get pattern recommendation |
| `record_work_outcome(...)` | Record work outcome |
| `end_session(summary, final_status)` | End session |

## Examples

### Complete Session Example

```python
from divineos.agent_integration.memory_monitor import (
    load_context,
    check_token_usage,
    save_checkpoint,
    compress,
    end_session,
)

# Start session
session_id = "phase-2-work"
context = load_context(session_id)

# Do work...
print("Starting Phase 2 work")

# Check token usage
status = check_token_usage(current_tokens=100000)
print(f"Token usage: {status['usage_percent']:.1f}%")

# Save checkpoint after task 1
save_checkpoint(
    task="Implement semantic analyzer",
    status="completed",
    files_modified=["src/semantic_analyzer.py", "tests/test_semantic_analyzer.py"],
    tests_passing=24
)

# Do more work...

# Check token usage again
status = check_token_usage(current_tokens=140000)
if status["action"] == "PREPARE_COMPRESSION":
    print("Preparing for compression...")

# Save checkpoint after task 2
save_checkpoint(
    task="Document memory monitor",
    status="completed",
    files_modified=["docs/memory_monitor_integration_guide.md"],
    tests_passing=1443
)

# End session
end_session(
    summary="Phase 2 tasks 11-12 complete. Semantic analyzer and documentation done.",
    final_status="completed"
)

print("Session complete - learning cycle running")
```

## See Also

- [Learning Cycle Guide](learning_loop_guide.md)
- [Clarity System Integration](clarity_system_integration.md)
- [Pattern Recommender Documentation](../src/divineos/agent_integration/pattern_recommender.py)
