# Automatic Context Loading - OS Enforced

## Overview

DivineOS now automatically loads previous work context from the ledger when a new session starts. This is enforced at the OS level (in the memory monitor), not through IDE hooks.

## How It Works

### Automatic Initialization

When you create a new `AgentMemoryMonitor` instance:

```python
from src.divineos.agent_integration.memory_monitor import get_memory_monitor
from src.divineos.core.session_manager import initialize_session

# Initialize session
session_id = initialize_session()

# Create memory monitor - automatically loads context
monitor = get_memory_monitor(session_id)
# Context is now loaded automatically!
```

### What Happens Automatically

1. **Session Initialization**: New session ID is created
2. **Memory Monitor Creation**: Monitor is instantiated
3. **Auto-Load Triggered**: `_auto_load_context()` runs automatically
4. **Context Loaded**: Previous work items and recent context are loaded from ledger
5. **Summary Logged**: Information about loaded context is logged

### No Manual Steps Required

You don't need to:
- Call `load_context()` manually
- Set up IDE hooks
- Run scripts
- Ask for context to be loaded

It happens automatically when the monitor is created.

## What Gets Loaded

### Previous Work Items

All work checkpoints from previous sessions:

```
Auto-loaded 5 previous work items
  - Phase 3 Task 15: End-to-end scenario tests (completed)
  - Phase 3 Task 16: Performance tests (completed)
  - Bug fix: Context loading (completed)
  ... and 2 more
```

### Recent Context

Recent events from the ledger (last 20 items):

```
Auto-loaded 20 recent context items
```

### Learning Audits

Pattern analysis and recommendations from previous sessions are available via:

```python
context = monitor.load_session_context()
recent = context.get("recent_context", [])
```

## Usage Example

### New Session Workflow

```python
from src.divineos.agent_integration.memory_monitor import get_memory_monitor
from src.divineos.core.session_manager import initialize_session

# 1. Initialize session
session_id = initialize_session()

# 2. Create memory monitor (context auto-loads here)
monitor = get_memory_monitor(session_id)

# 3. Access loaded context
context = monitor.load_session_context()
previous_work = context.get("previous_work", [])
recent_context = context.get("recent_context", [])

# 4. Continue working with full context
# ... do work ...

# 5. Save work
monitor.save_work_checkpoint(
    task="My Task",
    status="completed",
    files_modified=["file.py"],
    tests_passing=1500
)

# 6. End session (triggers learning cycle)
monitor.end_session(
    summary="Session complete",
    final_status="completed"
)
```

## Workflow After IDE Compression

### Before (Manual)
1. IDE compresses context window
2. IDE opens new window
3. User manually loads context (or asks for it)
4. Context is restored
5. Work continues

### After (Automatic)
1. IDE compresses context window
2. IDE opens new window
3. **OS automatically loads context** (no user action needed)
4. Context is restored
5. Work continues

## Implementation Details

### Auto-Load Method

The `_auto_load_context()` method:

1. Checks if context already loaded (prevents duplicate loads)
2. Calls `load_session_context()` to fetch from ledger
3. Logs summary of loaded items
4. Sets `context_loaded` flag to prevent re-loading

### Logging

Auto-load logs information about what was loaded:

```
AgentMemoryMonitor initialized for session: abc123
Auto-loaded 5 previous work items
  - Task 1 (completed)
  - Task 2 (completed)
  - Task 3 (in_progress)
Auto-loaded 20 recent context items
```

### Error Handling

If auto-load fails:

1. Error is logged
2. `context_loaded` flag is set to False
3. Session continues (graceful degradation)
4. User can manually call `load_session_context()` if needed

## Benefits

1. **Automatic**: No manual intervention required
2. **Transparent**: Works silently in the background
3. **Reliable**: Graceful error handling
4. **Complete**: All previous context is restored
5. **OS-Enforced**: Part of the OS, not IDE-dependent

## Testing

The auto-load functionality is tested in:

- `tests/test_integration_memory_monitor.py` - Integration tests
- `tests/test_memory_monitor_integration.py` - Memory monitor tests
- All 1499 tests pass with auto-load enabled

## Accessing Loaded Context

### Get Current Session

```python
from src.divineos.core.session_manager import get_current_session_id
from src.divineos.agent_integration.memory_monitor import get_memory_monitor

session_id = get_current_session_id()
monitor = get_memory_monitor(session_id)
```

### Load Context Manually (if needed)

```python
context = monitor.load_session_context()

# Access previous work
for work in context.get("previous_work", []):
    payload = work.get("payload", {})
    task = payload.get("task")
    status = payload.get("status")
    print(f"{task}: {status}")

# Access recent context
for event in context.get("recent_context", []):
    print(f"{event['event_type']}: {event['timestamp']}")
```

## Troubleshooting

### Context Not Loading

If context doesn't load automatically:

1. Check logs for errors: Look for "Failed to auto-load context"
2. Verify ledger exists: `src/divineos/core/ledger.db`
3. Check session ID: `echo $DIVINEOS_SESSION_ID`
4. Manually load: `monitor.load_session_context()`

### Missing Previous Work

If previous work is missing:

1. Verify work was saved: Check for `AGENT_WORK` events in ledger
2. Check session ID matches: Previous work is filtered by session ID
3. Query ledger directly: `python -c "from src.divineos.core.ledger import get_events; print(get_events(event_type='AGENT_WORK'))"`

### Learning Cycle Not Running

If learning cycle doesn't run:

1. Ensure `end_session()` is called: `monitor.end_session(...)`
2. Check logs for learning cycle: Look for `LEARNING_AUDIT` events
3. Verify pattern store: Check `src/divineos/agent_integration/pattern_store.py`

## Architecture

### Memory Monitor Initialization Flow

```
initialize_session()
    |
    v
get_memory_monitor(session_id)
    |
    v
AgentMemoryMonitor.__init__()
    |
    v
_auto_load_context()  <-- Automatic!
    |
    v
load_session_context()
    |
    v
get_events() from ledger
    |
    v
Context loaded and logged
```

### Session Lifecycle

```
New Session
    |
    v
Memory Monitor Created
    |
    v
Context Auto-Loaded  <-- OS Enforced
    |
    v
Work Continues
    |
    v
Checkpoints Saved
    |
    v
Session Ends
    |
    v
Learning Cycle Runs
    |
    v
Context Compressed
    |
    v
Next Session Starts
    |
    v
Context Auto-Loaded  <-- OS Enforced
```

## See Also

- `src/divineos/agent_integration/memory_monitor.py` - Memory monitoring implementation
- `src/divineos/core/ledger.py` - Ledger storage
- `src/divineos/agent_integration/learning_cycle.py` - Learning cycle
- `src/divineos/core/session_manager.py` - Session management
