# Tool Capture Implementation Analysis

**Task:** 3.1.1 - Analyze tool capture implementations  
**Date:** Analysis of current codebase state  
**Status:** Complete

## Executive Summary

The DivineOS codebase currently has **2 active tool capture implementations** (not 7 as originally planned):

1. **`src/divineos/core/tool_wrapper.py`** (268 LOC) - **CANONICAL** ✓
2. **`src/divineos/integration/unified_tool_capture.py`** (147 LOC) - **ACTIVE**

The other 5 implementations mentioned in the spec do not exist in the codebase:
- `src/divineos/integration/ide_tool_integration.py` - **DOES NOT EXIST**
- `src/divineos/integration/kiro_tool_integration.py` - **DOES NOT EXIST**
- `src/divineos/tools/tool_event_wrapper.py` - **DOES NOT EXIST**
- `src/divineos/tools/tool_result_capture.py` - **DOES NOT EXIST**
- `src/divineos/tools/manual_event_capture.py` - **DOES NOT EXIST**

**Total duplicate code to consolidate:** ~147 LOC (unified_tool_capture.py)

---

## 1. Import Mapping

### 1.1 Files Importing `core/tool_wrapper.py`

**Direct Imports:**
- `src/divineos/cli.py` - Uses `wrap_tool_execution()` to wrap critical ledger operations
- `src/divineos/integration/__init__.py` - Exports `wrap_tool_execution` and `is_internal_tool`
- `src/divineos/hooks/clarity_enforcement.py` - Uses `emit_tool_call_for_ide()` and `emit_tool_result_for_ide()`

**Test Imports:**
- `tests/test_unified_capture_paths.py` - Tests `wrap_tool_execution()`, `get_ide_tool_executor()`, `IDEToolExecutor`
- `tests/test_ide_tool_integration.py` - Tests `IDEToolExecutor`, `emit_tool_call_for_ide()`, `emit_tool_result_for_ide()`
- `tests/test_error_handling.py` - Tests `wrap_tool_execution()`
- `tests/test_enforcement_gaps.py` - Tests `wrap_tool_execution()`

**Total files importing core/tool_wrapper:** 7 files

### 1.2 Files Importing `integration/unified_tool_capture.py`

**Direct Imports:**
- `src/divineos/integration/__init__.py` - Exports `get_unified_capture()` and `capture_tool_execution()`
- `src/divineos/integration/mcp_event_capture_server.py` - Uses `capture_tool_execution()` for MCP tool events

**Test Imports:**
- `tests/test_unified_capture_paths.py` - Tests `UnifiedToolCapture`, `get_unified_capture()`, `capture_tool_execution()`
- `tests/test_observation_layer.py` - Tests `UnifiedToolCapture`, `get_unified_capture()`
- `tests/test_enforcement_gaps.py` - Tests `get_unified_capture()`
- `tests/test_enforcement_edge_cases.py` - Tests `get_unified_capture()`

**Total files importing unified_tool_capture:** 6 files

### 1.3 Import Summary Table

| Module | Location | LOC | Status | Imports | Used By |
|--------|----------|-----|--------|---------|---------|
| tool_wrapper | core/ | 268 | CANONICAL | emit_tool_call, emit_tool_result | 7 files |
| unified_tool_capture | integration/ | 147 | ACTIVE | emit_tool_call, emit_tool_result | 6 files |
| ide_tool_integration | integration/ | N/A | DOES NOT EXIST | - | - |
| kiro_tool_integration | integration/ | N/A | DOES NOT EXIST | - | - |
| tool_event_wrapper | tools/ | N/A | DOES NOT EXIST | - | - |
| tool_result_capture | tools/ | N/A | DOES NOT EXIST | - | - |
| manual_event_capture | tools/ | N/A | DOES NOT EXIST | - | - |

---

## 2. Implementation Analysis

### 2.1 `core/tool_wrapper.py` (CANONICAL)

**Purpose:** Primary tool execution wrapper with event capture

**Key Functions:**
- `wrap_tool_execution()` - Wraps tool functions with TOOL_CALL/TOOL_RESULT event capture
- `get_tool_input_string()` - Serializes tool input to JSON
- `get_tool_result_string()` - Serializes tool result to JSON
- `is_internal_tool()` - Checks if tool should be captured
- `create_tool_wrapper_decorator()` - Creates decorator for tool wrapping
- `IDEToolExecutor` class - Middleware for IDE tool execution
- `get_ide_tool_executor()` - Gets global executor instance
- `emit_tool_call_for_ide()` - Emits TOOL_CALL for IDE
- `emit_tool_result_for_ide()` - Emits TOOL_RESULT for IDE

**Features:**
- ✓ Wraps tool execution with event capture
- ✓ Emits TOOL_CALL events before execution
- ✓ Measures execution duration
- ✓ Emits TOOL_RESULT events after execution
- ✓ Handles tool failures with error messages
- ✓ Preserves original tool behavior and exceptions
- ✓ Skips internal tools to prevent infinite loops
- ✓ IDE tool executor for IDE integration
- ✓ Decorator-based tool wrapping
- ✓ Thread-safe with locks
- ✓ Error handling with logging

**Event Emission:**
- Imports from `divineos.event.event_emission`: `emit_tool_call`, `emit_tool_result`
- Imports from `divineos.core.loop_prevention`: `should_capture_tool`

**Usage Pattern:**
```python
# In cli.py
_wrapped_log_event = wrap_tool_execution("log_event", log_event)
_wrapped_get_events = wrap_tool_execution("get_events", get_events)

# In clarity_enforcement.py
tool_use_id = emit_tool_call_for_ide(tool_name, kwargs)
emit_tool_result_for_ide(tool_use_id, result_str, failed=False)
```

### 2.2 `integration/unified_tool_capture.py` (ACTIVE)

**Purpose:** Unified interface for capturing tool executions from both Kiro IDE and MCP servers

**Key Functions:**
- `UnifiedToolCapture` class - Main capture system
  - `capture_tool_execution()` - Captures tool execution with TOOL_CALL and TOOL_RESULT events
- `get_unified_capture()` - Gets global singleton instance
- `capture_tool_execution()` - Convenience function

**Features:**
- ✓ Thread-safe singleton pattern
- ✓ Automatic session management
- ✓ Consistent event emission
- ✓ Error handling and logging
- ✓ Result truncation for large outputs (5000 char limit)
- ✓ Emits both TOOL_CALL and TOOL_RESULT in one call

**Event Emission:**
- Imports from `divineos.event.event_emission`: `emit_tool_call`, `emit_tool_result`
- Imports from `divineos.core.session_manager`: `get_or_create_session_id`
- Imports from `divineos.core.error_handling`: `EventCaptureError`, `SessionError`, `handle_error`

**Usage Pattern:**
```python
# In mcp_event_capture_server.py
tool_call_id, tool_result_id = capture_tool_execution(
    tool_name=tool_name,
    tool_input=tool_input,
    result=result,
    duration_ms=duration_ms,
    failed=failed,
    error_message=error_message,
)
```

---

## 3. Differences Between Implementations

### 3.1 Functional Differences

| Aspect | tool_wrapper.py | unified_tool_capture.py |
|--------|-----------------|-------------------------|
| **Scope** | Wraps functions; emits events | Captures completed executions |
| **Event Emission** | Separate TOOL_CALL and TOOL_RESULT | Both in single call |
| **Timing** | Before/after execution | After execution complete |
| **Error Handling** | Catches and re-raises | Catches and logs |
| **Result Truncation** | 1MB limit | 5000 char limit |
| **Session Management** | Uses loop_prevention | Uses session_manager |
| **Thread Safety** | RLock on executor | RLock on capture |
| **Singleton Pattern** | Global _executor | Global _unified_capture |

### 3.2 API Differences

**tool_wrapper.py:**
```python
# Function wrapping approach
wrapped_func = wrap_tool_execution("tool_name", original_func)
result = wrapped_func(*args, **kwargs)

# IDE executor approach
executor = get_ide_tool_executor()
tool_use_id = executor.start_tool_execution(tool_name, tool_input)
executor.end_tool_execution(tool_use_id, result, failed=False)

# Direct IDE functions
tool_use_id = emit_tool_call_for_ide(tool_name, tool_input)
emit_tool_result_for_ide(tool_use_id, result, failed=False)
```

**unified_tool_capture.py:**
```python
# Single-call approach
tool_call_id, tool_result_id = capture_tool_execution(
    tool_name=tool_name,
    tool_input=tool_input,
    result=result,
    duration_ms=duration_ms,
    failed=failed,
    error_message=error_message,
)
```

### 3.3 Architectural Differences

**tool_wrapper.py:**
- Decorator/wrapper pattern
- Intercepts execution at function level
- Emits events during execution
- Preserves exceptions
- Designed for wrapping existing functions

**unified_tool_capture.py:**
- Capture pattern
- Records completed executions
- Emits events after completion
- Handles errors gracefully
- Designed for MCP and IDE integration

---

## 4. Which Implementations Are Actually Used

### 4.1 Active Usage

**core/tool_wrapper.py - HEAVILY USED:**
- ✓ CLI wraps 8+ critical functions with `wrap_tool_execution()`
- ✓ Clarity enforcement uses `emit_tool_call_for_ide()` and `emit_tool_result_for_ide()`
- ✓ Tests extensively test all functions
- ✓ Exported from integration module

**integration/unified_tool_capture.py - ACTIVELY USED:**
- ✓ MCP event capture server uses `capture_tool_execution()`
- ✓ Tests extensively test the capture system
- ✓ Exported from integration module
- ✓ Used for MCP tool event emission

### 4.2 Dead Code Analysis

**Non-existent implementations (5 files):**
- `ide_tool_integration.py` - DOES NOT EXIST (no imports found)
- `kiro_tool_integration.py` - DOES NOT EXIST (no imports found)
- `tool_event_wrapper.py` - DOES NOT EXIST (no imports found)
- `tool_result_capture.py` - DOES NOT EXIST (no imports found)
- `manual_event_capture.py` - DOES NOT EXIST (no imports found)

**Conclusion:** These 5 implementations were planned but never created. They are not dead code—they simply don't exist.

---

## 5. Unique Functionality Analysis

### 5.1 Unique to tool_wrapper.py

1. **Function wrapping pattern** - Decorator-based wrapping of existing functions
2. **IDEToolExecutor class** - Middleware for IDE tool execution with active tool tracking
3. **Execution duration measurement** - Measures time between start and end
4. **Exception preservation** - Re-raises original exceptions after event emission
5. **Internal tool filtering** - Uses `should_capture_tool()` to skip internal tools
6. **Decorator factory** - `create_tool_wrapper_decorator()` for creating decorators

### 5.2 Unique to unified_tool_capture.py

1. **Single-call capture** - Emits both TOOL_CALL and TOOL_RESULT in one function call
2. **Result truncation** - Truncates results to 5000 characters
3. **Session integration** - Automatically gets or creates session ID
4. **Error handling pattern** - Uses `handle_error()` utility for consistent error handling
5. **Singleton pattern** - Thread-safe singleton with `_unified_capture` global

### 5.3 Functionality to Preserve

**From tool_wrapper.py (keep all):**
- ✓ Function wrapping capability
- ✓ IDEToolExecutor class
- ✓ Execution duration measurement
- ✓ Exception preservation
- ✓ Internal tool filtering
- ✓ IDE integration functions

**From unified_tool_capture.py (merge into tool_wrapper.py):**
- ✓ Single-call capture pattern (add as alternative API)
- ✓ Result truncation logic
- ✓ Session integration
- ✓ Error handling pattern

---

## 6. Consolidation Recommendations

### 6.1 Consolidation Strategy

**Recommended Approach:** Merge `unified_tool_capture.py` into `core/tool_wrapper.py`

**Rationale:**
1. Both are active and used
2. tool_wrapper.py is already canonical
3. unified_tool_capture.py provides complementary functionality
4. Merging reduces duplication and simplifies imports
5. Both use same underlying event emission system

### 6.2 Consolidation Steps

**Phase 1: Enhance core/tool_wrapper.py**
1. Add `UnifiedToolCapture` class to tool_wrapper.py
2. Add `capture_tool_execution()` function to tool_wrapper.py
3. Add `get_unified_capture()` function to tool_wrapper.py
4. Preserve all existing functions and classes

**Phase 2: Update imports**
1. Update `integration/__init__.py` to import from tool_wrapper.py instead of unified_tool_capture.py
2. Update `mcp_event_capture_server.py` to import from tool_wrapper.py
3. Update all test files to import from tool_wrapper.py

**Phase 3: Delete duplicate**
1. Delete `integration/unified_tool_capture.py`
2. Verify no remaining imports

**Phase 4: Verify**
1. Run all tests
2. Verify event capture still works
3. Verify MCP integration still works
4. Verify CLI still works

### 6.3 Consolidation Order

1. **First:** Enhance core/tool_wrapper.py (add unified capture functionality)
2. **Second:** Update integration/__init__.py (redirect imports)
3. **Third:** Update mcp_event_capture_server.py (redirect imports)
4. **Fourth:** Update test files (redirect imports)
5. **Fifth:** Delete integration/unified_tool_capture.py
6. **Sixth:** Run full test suite

---

## 7. Import Consolidation Map

### 7.1 Current Imports

```
integration/__init__.py:
  from divineos.core.tool_wrapper import wrap_tool_execution, is_internal_tool
  from divineos.integration.unified_tool_capture import get_unified_capture, capture_tool_execution

mcp_event_capture_server.py:
  from divineos.integration.unified_tool_capture import capture_tool_execution

cli.py:
  from divineos.core.tool_wrapper import wrap_tool_execution

clarity_enforcement.py:
  from divineos.core.tool_wrapper import emit_tool_call_for_ide, emit_tool_result_for_ide
```

### 7.2 Post-Consolidation Imports

```
integration/__init__.py:
  from divineos.core.tool_wrapper import (
    wrap_tool_execution,
    is_internal_tool,
    get_unified_capture,
    capture_tool_execution,
  )

mcp_event_capture_server.py:
  from divineos.core.tool_wrapper import capture_tool_execution

cli.py:
  from divineos.core.tool_wrapper import wrap_tool_execution

clarity_enforcement.py:
  from divineos.core.tool_wrapper import emit_tool_call_for_ide, emit_tool_result_for_ide
```

---

## 8. Files Affected by Consolidation

### 8.1 Files to Modify

1. **src/divineos/core/tool_wrapper.py** - Add unified capture functionality
2. **src/divineos/integration/__init__.py** - Update imports
3. **src/divineos/integration/mcp_event_capture_server.py** - Update imports
4. **tests/test_unified_capture_paths.py** - Update imports
5. **tests/test_observation_layer.py** - Update imports
6. **tests/test_enforcement_gaps.py** - Update imports
7. **tests/test_enforcement_edge_cases.py** - Update imports

### 8.2 Files to Delete

1. **src/divineos/integration/unified_tool_capture.py** - Delete after consolidation

### 8.3 Files Not Affected

- src/divineos/cli.py - Already imports from tool_wrapper.py
- src/divineos/hooks/clarity_enforcement.py - Already imports from tool_wrapper.py
- tests/test_ide_tool_integration.py - Already imports from tool_wrapper.py
- tests/test_error_handling.py - Already imports from tool_wrapper.py

---

## 9. Code Metrics

### 9.1 Current State

| Metric | Value |
|--------|-------|
| Tool capture implementations | 2 active |
| Total LOC in tool capture | 415 LOC |
| Files importing tool capture | 13 files |
| Duplicate code | 147 LOC (unified_tool_capture.py) |
| Non-existent implementations | 5 files |

### 9.2 Post-Consolidation State

| Metric | Value |
|--------|-------|
| Tool capture implementations | 1 canonical |
| Total LOC in tool capture | 415 LOC (same, merged) |
| Files importing tool capture | 13 files (same, redirected) |
| Duplicate code | 0 LOC |
| Non-existent implementations | 0 files |

---

## 10. Risk Assessment

### 10.1 Low Risk

- ✓ Consolidation is straightforward merge
- ✓ Both implementations use same event emission system
- ✓ No conflicting APIs
- ✓ Comprehensive test coverage
- ✓ Clear import paths

### 10.2 Mitigation Strategies

1. **Run full test suite** before and after consolidation
2. **Verify event capture** with manual testing
3. **Check MCP integration** still works
4. **Verify CLI** still works
5. **Review imports** in all affected files

---

## 11. Summary

### 11.1 Key Findings

1. **Only 2 active implementations exist** (not 7 as planned)
   - core/tool_wrapper.py (268 LOC) - CANONICAL
   - integration/unified_tool_capture.py (147 LOC) - ACTIVE

2. **5 planned implementations don't exist**
   - ide_tool_integration.py
   - kiro_tool_integration.py
   - tool_event_wrapper.py
   - tool_result_capture.py
   - manual_event_capture.py

3. **Both implementations are actively used**
   - tool_wrapper.py: 7 files import it
   - unified_tool_capture.py: 6 files import it

4. **Consolidation is straightforward**
   - Merge unified_tool_capture.py into tool_wrapper.py
   - Update imports in 7 files
   - Delete unified_tool_capture.py
   - No functional changes needed

### 11.2 Consolidation Impact

- **Lines of code eliminated:** 147 LOC
- **Files deleted:** 1 file
- **Files modified:** 7 files
- **Complexity reduction:** Moderate (2 → 1 implementation)
- **Risk level:** Low

### 11.3 Next Steps

1. **Task 3.1.2:** Enhance core/tool_wrapper.py with unified capture functionality
2. **Task 3.1.3:** Redirect imports to core/tool_wrapper.py
3. **Task 3.1.4:** Delete integration/unified_tool_capture.py
4. **Task 3.1.5:** Verify consolidation with tests

---

## Appendix A: File Import Details

### A.1 cli.py

```python
from divineos.core.tool_wrapper import wrap_tool_execution

# Usage:
_wrapped_log_event = wrap_tool_execution("log_event", log_event)
_wrapped_get_events = wrap_tool_execution("get_events", get_events)
_wrapped_search_events = wrap_tool_execution("search_events", search_events)
_wrapped_count_events = wrap_tool_execution("count_events", count_events)
_wrapped_get_recent_context = wrap_tool_execution("get_recent_context", get_recent_context)
_wrapped_verify_all_events = wrap_tool_execution("verify_all_events", verify_all_events)
_wrapped_clean_corrupted_events = wrap_tool_execution("clean_corrupted_events", clean_corrupted_events)
_wrapped_export_to_markdown = wrap_tool_execution("export_to_markdown", export_to_markdown)
_wrapped_store_knowledge = wrap_tool_execution("store_knowledge", store_knowledge)
_wrapped_get_knowledge = wrap_tool_execution("get_knowledge", get_knowledge)
_wrapped_update_knowledge = wrap_tool_execution("update_knowledge", update_knowledge)
_wrapped_generate_briefing = wrap_tool_execution("generate_briefing", generate_briefing)
_wrapped_knowledge_stats = wrap_tool_execution("knowledge_stats", knowledge_stats)
_wrapped_rebuild_fts_index = wrap_tool_execution("rebuild_fts_index", rebuild_fts_index)
_wrapped_get_lesson_summary = wrap_tool_execution("get_lesson_summary", get_lesson_summary)
_wrapped_get_lessons = wrap_tool_execution("get_lessons", get_lessons)
_wrapped_deep_extract_knowledge = wrap_tool_execution("deep_extract_knowledge", deep_extract_knowledge)
_wrapped_consolidate_related = wrap_tool_execution("consolidate_related", consolidate_related)
_wrapped_apply_session_feedback = wrap_tool_execution("apply_session_feedback", apply_session_feedback)
_wrapped_health_check = wrap_tool_execution("health_check", health_check)
```

### A.2 integration/__init__.py

```python
from divineos.core.tool_wrapper import (
    wrap_tool_execution,
    is_internal_tool,
)
from divineos.integration.unified_tool_capture import (
    get_unified_capture,
    capture_tool_execution,
)

__all__ = [
    "wrap_tool_execution",
    "is_internal_tool",
    "get_unified_capture",
    "capture_tool_execution",
]
```

### A.3 mcp_event_capture_server.py

```python
from divineos.integration.unified_tool_capture import capture_tool_execution

# Usage:
tool_call_id, _ = capture_tool_execution(
    tool_name=tool_name,
    tool_input=tool_input,
    result="",
    duration_ms=0,
)

_, tool_result_id = capture_tool_execution(
    tool_name=tool_name,
    tool_input={"tool_use_id": tool_use_id},
    result=result,
    duration_ms=duration_ms,
    failed=failed,
    error_message=error_message,
)
```

### A.4 clarity_enforcement.py

```python
from divineos.core.tool_wrapper import (
    emit_tool_call_for_ide,
    emit_tool_result_for_ide,
)

# Usage:
tool_use_id = emit_tool_call_for_ide(tool_name, kwargs)
emit_tool_result_for_ide(tool_use_id, result_str, failed=False)
emit_tool_result_for_ide(tool_use_id, error_msg, failed=True, error_message=error_msg)
```

---

**Analysis Complete**
