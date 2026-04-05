---
name: Documentation
description: Generate documentation for a component, module, or file.
---

ultrathink Generate documentation for the specified target.

**MANDATORY READS FIRST:**
1. Read `teamsop.md` - understand verification requirements
2. Read `CLAUDE.md` - understand project context and forbidden things

**Target**: $ARGUMENTS (if empty, ask what to document)

**POLYGLOT SYSTEM REMINDER:**
- **Python**: Full support
- **Node.js/TypeScript**: Full support
- **Rust**: Basic support

When documenting, CHECK:
1. Does this component have Python + Node versions?
2. Document BOTH if they exist - don't leave Node docs orphaned.
3. Is there an orchestrator? Document how it coordinates languages.

---

**Process:**

1. **Gather Context** (DO NOT SKIP):
   ```bash
   aud explain <target>           # Get symbols, callers, callees, hooks
   aud query --symbol <name> --show-callers --show-code  # Deeper trace if needed
   ```

2. **Verify Understanding**:
   - List hypotheses about what this component does
   - Confirm or deny each by reading actual code
   - Document discrepancies between assumptions and reality

3. **Generate Documentation** covering:
   - **Purpose**: What problem does this solve? Why does it exist?
   - **Interface**: Public API, parameters, return values
   - **Dependencies**: What does it import/require?
   - **Callers**: What calls this? (from aud output)
   - **Callees**: What does this call? (from aud output)
   - **Edge Cases**: Known limitations, gotchas
   - **Examples**: Usage examples if applicable

4. **Write to Root**:
   - Filename: `DOC_<component_name>.md`
   - Location: Project root (NOT nested in docs/)

**Output Format:**

```markdown
# [Component Name] Documentation

**Location**: `path/to/file.py:line`
**Type**: [Function/Class/Module]
**Generated**: [Date]

## Purpose
[Why this exists, what problem it solves]

## Interface

### Parameters
| Name | Type | Description |
|------|------|-------------|
| param1 | str | Description |

### Returns
[Return type and description]

## Dependencies
- `module.function` - [Why needed]

## Called By
[List from aud explain output]

## Calls
[List from aud explain output]

## Edge Cases
- [Edge case 1]
- [Edge case 2]

## Example Usage
```python
[Code example]
```

## Notes
[Any gotchas, limitations, or context]
```

**Rules:**
- NO documentation without reading the actual code first
- ALWAYS include file:line references
- ALWAYS run aud explain before documenting
- Write to root, single file per component
- Be concise - document what isn't obvious from code
