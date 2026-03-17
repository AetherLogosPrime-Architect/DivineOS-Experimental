# Session Isolation Bug Fix - Summary

## Status: IN PROGRESS - Critical Issues Remain

### What Was Fixed

1. **Removed Premature Session End** - emit_session_end() was calling end_session() which cleared the session ID before querying
2. **Fixed CLI Parameter Handling** - All emit commands now properly convert empty strings to None
3. **Added Session ID Persistence** - Implemented file-based persistence at `~/.divineos/current_session.txt`
4. **Fixed Event Ordering** - SESSION_END now reverses event list to get most recent first

### Critical Issues Remaining

#### Issue #1: Session Tracker is Process-Local
- **Problem**: Each CLI command is a separate Python process
- **Impact**: Session tracker singleton doesn't persist between commands
- **Evidence**: USER_INPUT gets session_id `81832c5a...` but SESSION_END gets `20b02a34...`
- **Root Cause**: `get_session_tracker().get_current_session_id()` creates new ID in each process

#### Issue #2: SESSION_END Reports All Zeros
- **Problem**: SESSION_END reports `message_count: 0, tool_call_count: 0, tool_result_count: 0`
- **Evidence**: Database has 2 events with session_id `81832c5a...` but SESSION_END reports 0
- **Root Cause**: Unknown - persistent file approach should work but doesn't

#### Issue #3: Persistent File Not Being Read
- **Problem**: File exists at `~/.divineos/current_session.txt` with correct session_id
- **Evidence**: File contains `81832c5a...` but SESSION_END reports different session_id `20b02a34...`
- **Root Cause**: Code path not being executed or file reading failing silently

### Files Modified

1. `src/divineos/event_emission.py`
   - emit_user_input() - Added session_id persistence
   - emit_tool_call() - Added session_id persistence
   - emit_tool_result() - Added session_id persistence
   - emit_session_end() - Multiple fixes for session_id handling

2. `src/divineos/cli.py`
   - emit_cmd() - Fixed all 4 branches to use `session_id or None`

### Database Evidence

Most recent events show session_ids:
```
SESSION_END     | 81832c5a-fb4d-4d30-a328-67a0dcf0ab50
USER_INPUT      | 81832c5a-fb4d-4d30-a328-67a0dcf0ab50
SESSION_END     | 2615590e-bd8d-4a8a-b3da-78413d80ba5b
USER_INPUT      | 40e0d25b-cf14-4187-b14e-6ad266eeab49
```

The most recent SESSION_END and USER_INPUT have matching session_ids, but SESSION_END still reports 0 events.

### Next Steps Required

1. **Debug why persistent file isn't being read**
   - Add print statements to verify file reading code path
   - Check if Path.home() is working correctly
   - Verify file permissions

2. **Alternative approach: Use environment variable**
   - Store session_id in environment variable instead of file
   - Pass between CLI processes via environment

3. **Alternative approach: Query database for most recent session**
   - Instead of relying on session tracker or file
   - Query for the most recent USER_INPUT/TOOL_CALL event
   - Use that session_id for SESSION_END

4. **Root cause analysis**
   - Why is SESSION_END getting a different session_id?
   - Is the fallback code being executed instead of file reading?
   - Is there a bug in the Path.home() or file reading logic?

### Test Commands

```bash
# Emit USER_INPUT (saves session_id to file)
divineos emit USER_INPUT --content "test"

# Check persistent file
cat ~/.divineos/current_session.txt

# Emit SESSION_END (should read from file)
divineos emit SESSION_END

# Check database
python debug_query.py
```

### Conclusion

The session isolation issue is more complex than initially thought. The persistent file approach should work but isn't. Further investigation needed to identify why the file isn't being read or why SESSION_END is getting a different session_id.

The core problem is that each CLI command is a separate Python process, so the session tracker singleton doesn't persist. A more robust solution is needed that doesn't rely on in-memory state.
