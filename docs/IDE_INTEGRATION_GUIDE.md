# IDE Tool Integration Guide

## Overview

The DivineOS system now provides a complete infrastructure for capturing tool execution events. The IDE needs to integrate with this infrastructure to emit TOOL_CALL and TOOL_RESULT events when tools are executed.

## Integration Points

### 1. When a Tool is About to Execute

Call `emit_tool_call_for_ide()` before executing a tool:

```python
from divineos.integration.ide_tool_integration import emit_tool_call_for_ide

# Before tool execution
tool_use_id = emit_tool_call_for_ide(
    tool_name="readFile",
    tool_input={"path": "src/main.py"}
)
```

This will:
- Emit a TOOL_CALL event to the ledger
- Return a `tool_use_id` that must be used later

### 2. When a Tool Completes Successfully

Call `emit_tool_result_for_ide()` after the tool completes:

```python
from divineos.integration.ide_tool_integration import emit_tool_result_for_ide

# After tool execution
result = "file content here"
emit_tool_result_for_ide(
    tool_use_id=tool_use_id,
    result=result,
    failed=False
)
```

### 3. When a Tool Fails

Call `emit_tool_result_for_ide()` with failure information:

```python
from divineos.integration.ide_tool_integration import emit_tool_result_for_ide

# After tool execution fails
error_msg = "File not found"
emit_tool_result_for_ide(
    tool_use_id=tool_use_id,
    result=error_msg,
    failed=True,
    error_message=error_msg
)
```

## Complete Example

```python
from divineos.integration.ide_tool_integration import (
    emit_tool_call_for_ide,
    emit_tool_result_for_ide
)

def execute_tool_with_capture(tool_name, tool_input, tool_function):
    """Execute a tool and capture TOOL_CALL and TOOL_RESULT events."""
    
    # 1. Emit TOOL_CALL event
    tool_use_id = emit_tool_call_for_ide(tool_name, tool_input)
    
    try:
        # 2. Execute the tool
        result = tool_function(**tool_input)
        result_str = str(result) if not isinstance(result, str) else result
        
        # 3. Emit TOOL_RESULT event (success)
        emit_tool_result_for_ide(
            tool_use_id=tool_use_id,
            result=result_str,
            failed=False
        )
        
        return result
    
    except Exception as e:
        # 3. Emit TOOL_RESULT event (failure)
        error_msg = str(e)
        emit_tool_result_for_ide(
            tool_use_id=tool_use_id,
            result=error_msg,
            failed=True,
            error_message=error_msg
        )
        raise
```

## Using IDEToolExecutor Class

For more advanced use cases, use the `IDEToolExecutor` class directly:

```python
from divineos.integration.ide_tool_integration import get_ide_tool_executor

executor = get_ide_tool_executor()

# Execute a tool with automatic event capture
result = executor.execute_tool(
    tool_name="readFile",
    tool_input={"path": "src/main.py"},
    tool_function=my_read_file_function
)
```

## Tool Names

Use the actual tool name as it appears in the IDE:
- `readFile`
- `readCode`
- `strReplace`
- `fsWrite`
- `executePwsh`
- `createHook`
- `grepSearch`
- etc.

## Tool Input Format

The `tool_input` should be a dictionary containing all parameters for the tool:

```python
tool_input = {
    "path": "src/main.py",
    "explanation": "Reading the main file"
}
```

## Result Format

The `result` should be a string containing the complete output from the tool:

```python
result = "def main():\n    print('Hello')\n"
```

For large results, include the full output (not truncated).

## Error Handling

Always emit TOOL_RESULT events, even when tools fail:

```python
try:
    result = tool_function(**tool_input)
    emit_tool_result_for_ide(tool_use_id, str(result), failed=False)
except Exception as e:
    emit_tool_result_for_ide(
        tool_use_id,
        str(e),
        failed=True,
        error_message=str(e)
    )
    raise
```

## Session Tracking

All TOOL_CALL and TOOL_RESULT events are automatically associated with the current session. The session ID is managed by DivineOS and doesn't need to be specified.

## Testing

The integration is fully tested. Run the tests with:

```bash
pytest tests/test_ide_tool_integration.py -v
```

## Benefits

Once integrated, the IDE will:
- ✅ Capture all tool execution in the ledger
- ✅ Enable accurate session tracking
- ✅ Provide complete session analysis
- ✅ Track tool execution duration
- ✅ Record tool failures with error messages
- ✅ Enable audit trails and compliance tracking
