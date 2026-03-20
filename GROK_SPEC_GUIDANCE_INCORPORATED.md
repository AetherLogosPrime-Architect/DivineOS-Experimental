# Grok's Spec Guidance - Incorporated

**Date**: March 19, 2026  
**Status**: Spec updated with Grok's guidance  

---

## Quick Guidance Incorporated into Specs

### For Clarity Enforcement Spec

**Three Enforcement Levels** (now in requirements):

1. **PERMISSIVE (Current)**
   - Capture everything, generate explanations when convenient
   - Never block
   - No CLARITY_VIOLATION events
   - Default for backward compatibility

2. **LOGGING (Next Step)**
   - Capture + generate CLARITY_VIOLATION events when TOOL_CALL or TOOL_RESULT lacks paired CLARITY_EXPLANATION
   - Do not block
   - Make violations queryable via `divineos log --violations`

3. **BLOCKING (Strongest Mode)**
   - Prevent ASSISTANT_RESPONSE emission if any TOOL_CALL lacks CLARITY_EXPLANATION
   - Force agent to generate explanation or fail with structured error event
   - Aligns with "cannot lie" philosophy

**Definition of "Explained"** (now in requirements):
- CLARITY_EXPLANATION event exists with `related_event_ids` pointing to TOOL_CALL
- Explanation appears within event window (5 events after TOOL_RESULT)
- Explanation provides clear reasoning for tool call

**Time Window / Event Window** (now in requirements):
- CLARITY_EXPLANATION must appear within **5 events** after TOOL_RESULT
- Or within same logical reasoning block (before ASSISTANT_RESPONSE finalized)
- Flexible timing (before, during, or after tool execution)

**Batched Explanations** (now in requirements):
- One CLARITY_EXPLANATION can cover multiple related tool calls
- `related_event_ids` field lists all covered tool calls
- Valid as long as all tool calls in batch are covered

**Configuration Surface** (now in requirements):
- Environment variable: `DIVINEOS_CLARITY_MODE=blocking|logging|permissive`
- Config file: `~/.divineos/clarity_config.json`
- Per-session override via session metadata

### For Supersession / Contradiction Spec (Future)

**Clear Rules for Supersession** (to be implemented):

1. **Direct Contradiction**
   - Same subject-predicate-object triple with conflicting values
   - Example: "17×23=391" vs "17×23=500"

2. **Supersession Criteria**
   - Higher confidence entry wins
   - More recent entry wins
   - More corroborated entry wins
   - User explicit correction ("forget previous", "correct to X")
   - External verification from trusted source

3. **Supersession Mechanics**
   - Create SUPERSESSION event linking old → new
   - Populate `superseded_by` field on old entry
   - Optionally mark old entry as SUPERSEDED (status change)
   - Never delete or mutate old entry (append-only preserved)
   - Keep `contradiction_count` / `corroboration_count` updated
   - Allow querying both current believed fact and full contradiction history

### General Spec Hygiene Requests (Incorporated)

✅ **Version the Specs**
- Clarity Enforcement: v1.0-draft

✅ **Include Acceptance Criteria / Test Cases by Mode**
- PERMISSIVE mode test cases
- LOGGING mode test cases
- BLOCKING mode test cases

✅ **Reference Existing Tests**
- All 774 existing tests must continue to pass
- New tests will be added for each enforcement mode (minimum 10 per mode)
- Property-based tests for correctness properties
- Integration tests for hook and event capture
- Migration tests for backward compatibility

✅ **Add Migration Path**
- Existing permissive sessions continue in PERMISSIVE mode
- New sessions use new enforcement mode
- Session metadata can override global configuration
- Gradual rollout: LOGGING first, then BLOCKING
- Configuration precedence documented

---

## Answer to Grok's Final Query

### Current Knowledge Base State: 17 × 23

**Query Result**: 

```
Found 2 fact(s) about 17 × 23:

Knowledge ID: 3034df54-b9ef-4076-a870-9003bebef953
  Content: 17 × 23 = 391
  Confidence: 1.0
  Status: ACTIVE
  Created: 1773962134.698874

Knowledge ID: 07b32f71-55bc-465d-9304-88947844f2f7
  Content: 17 × 23 = 500
  Confidence: 1.0
  Status: ACTIVE
  Created: 1773962675.1479237

⚠️  CONFLICT DETECTED: 2 conflicting active facts exist
The system currently returns multiple conflicting values without automatic resolution.
```

**Summary**:
- **Multiple conflicting entries**: YES (2 active facts)
- **Automatic resolution**: NO (both remain active)
- **Contradiction tracking**: NO (contradiction_count = 0 for both)
- **Supersession**: NO (superseded_by = None for both)
- **System behavior**: Returns both values; surfaces the conflict implicitly

**Interpretation**: The system correctly preserves the append-only property (no mutations) but does NOT automatically resolve contradictions. Both facts coexist as active entries with equal confidence. This confirms Grok's earlier findings from the advanced probes.

---

## Spec Status

### Clarity Enforcement Spec
- **File**: `.kiro/specs/divineos-clarity-enforcement-hardening/`
- **Status**: COMPLETE with Grok's guidance incorporated
- **Version**: v1.0-draft
- **Ready for**: Implementation

### Supersession / Contradiction Spec
- **Status**: NOT YET CREATED
- **Next step**: Create after clarity enforcement is implemented
- **Will include**: Clear supersession rules, contradiction detection, and resolution logic

---

## Next Steps

1. **Implement Clarity Enforcement** (using updated spec)
2. **Verify all 774 existing tests pass**
3. **Create Supersession / Contradiction Spec** (with Grok's guidance)
4. **Implement Contradiction Resolution**
5. **Verify foundation is solid** before moving to Phase 4

---

## Key Takeaways

✅ **Spec guidance incorporated**: Three enforcement levels, definition of "explained", time windows, batched explanations, configuration surface, migration path

✅ **Live query completed**: Knowledge base shows 2 conflicting active facts (391 vs 500) with no automatic resolution

✅ **Foundation gaps identified**: Clarity enforcement (permissive), contradiction resolution (missing)

✅ **Path forward clear**: Implement enforcement first, then contradiction resolution, then verify foundation is solid

The system is ready for implementation. All guidance from Grok has been incorporated into the spec.

