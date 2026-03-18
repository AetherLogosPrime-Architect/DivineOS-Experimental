# Hook System Audit & Restructuring Plan

## Current Hooks Status

### 1. auto-analyze-sessions.kiro.hook
- **Status**: DISABLED (was enabled)
- **Trigger**: agentStop (when session ends)
- **Action**: Asks agent to run `divineos analyze-now`
- **Problem**: Creates loop with capture-session-end hook
- **Decision**: ❌ REMOVE - Analysis should be manual, not automatic

### 2. auto-capture-tool-results.kiro.hook
- **Status**: DISABLED (already disabled)
- **Trigger**: userTriggered
- **Action**: Echo message (disabled)
- **Problem**: Tool event capture timing issues
- **Decision**: ❌ REMOVE - Not functional

### 3. auto-fix-after-diagnosis.kiro.hook
- **Status**: DISABLED (was enabled)
- **Trigger**: postToolUse (after getDiagnostics)
- **Action**: Asks agent to fix issues immediately
- **Problem**: Creates false expectations, no user control
- **Decision**: ❌ REMOVE - User should decide when to fix

### 4. capture-session-end.kiro.hook
- **Status**: ENABLED
- **Trigger**: agentStop (when session ends)
- **Action**: Asks agent to summarize and emit SESSION_END
- **Problem**: Loops with auto-analyze-sessions
- **Decision**: ⚠️ KEEP BUT MODIFY - Make it manual, not automatic

### 5. capture-tool-events.sh
- **Status**: Shell script (not JSON hook)
- **Purpose**: Capture tool events
- **Problem**: Not integrated with hook system
- **Decision**: ❓ INVESTIGATE - Understand purpose before deciding

### 6. capture-user-input.kiro.hook
- **Status**: ENABLED
- **Trigger**: promptSubmit (on every user message)
- **Action**: Asks agent to emit USER_INPUT event
- **Problem**: Runs on EVERY message, creates noise
- **Decision**: ❌ REMOVE - Should be manual or built into CLI

### 7. enforce-ruff-format.kiro.hook
- **Status**: DISABLED (was enabled)
- **Trigger**: preToolUse (before git commit)
- **Action**: Runs ruff format and check
- **Problem**: Redundant with Git pre-commit hook
- **Decision**: ✅ KEEP - But verify Git pre-commit is working instead

### 8. explain-all-tools.kiro.hook
- **Status**: DISABLED
- **Trigger**: preToolUse (before any tool)
- **Action**: Asks agent to explain and emit EXPLANATION event
- **Problem**: Creates noise, runs on every tool call
- **Decision**: ❌ REMOVE - Explanations should be in response text

### 9. explain-before-write.kiro.hook
- **Status**: DISABLED (was enabled)
- **Trigger**: preToolUse (before write operations)
- **Action**: Asks agent to explain before writing
- **Problem**: Interrupts workflow, creates loops
- **Decision**: ❌ REMOVE - Explanations should be in response text

### 10. explain-session-start.kiro.hook
- **Status**: ENABLED
- **Trigger**: promptSubmit (on first user message)
- **Action**: Asks agent to explain understanding and plan
- **Problem**: Doesn't actually wait for user input
- **Decision**: ❌ REMOVE - Clarity should be in response, not hook

### 11. test-after-edits.kiro.hook
- **Status**: DISABLED (was enabled)
- **Trigger**: postToolUse (after write/strReplace/editCode)
- **Action**: Runs pytest
- **Problem**: None identified
- **Decision**: ✅ KEEP - Useful for verification

### 12. verify-before-claim.kiro.hook
- **Status**: DISABLED (was enabled)
- **Trigger**: preToolUse (before executePwsh)
- **Action**: Asks agent to verify what it's doing
- **Problem**: None identified
- **Decision**: ✅ KEEP - Safety check

---

## Hooks to Remove

1. auto-analyze-sessions.kiro.hook
2. auto-capture-tool-results.kiro.hook
3. auto-fix-after-diagnosis.kiro.hook
4. capture-user-input.kiro.hook
5. explain-all-tools.kiro.hook
6. explain-before-write.kiro.hook
7. explain-session-start.kiro.hook

## Hooks to Keep (Re-enable)

1. test-after-edits.kiro.hook - Verify code changes work
2. verify-before-claim.kiro.hook - Safety check before commands

## Hooks to Modify

1. capture-session-end.kiro.hook - Make manual, not automatic
2. enforce-ruff-format.kiro.hook - Verify Git pre-commit is sufficient

## Hooks to Investigate

1. capture-tool-events.sh - Understand purpose

---

## New Explicit Workflow (No Automatic Hooks)

### Session Start
1. User provides request
2. I provide clarity explanation (in text response)
3. I wait for user input (explicit stop)
4. User confirms or provides corrections

### During Work
1. I explain what I'm doing (in text response)
2. I do the work
3. I show results and what they mean
4. I wait for user input before proceeding

### Session End
1. I provide summary (in text response)
2. User manually runs: `divineos analyze-now` (if they want analysis)
3. User manually runs: `divineos emit SESSION_END` (to close session)

### Enforcement (OS/Git Level)
- Git pre-commit hook: Runs ruff format, ruff check, mypy
- GitHub Actions: Runs tests, linting, type checks
- These cannot be bypassed

---

## Implementation Steps

1. Delete problematic hooks
2. Re-enable test-after-edits and verify-before-claim
3. Modify capture-session-end to be manual
4. Verify Git pre-commit hook is working
5. Document the new workflow
6. Test with a real session
