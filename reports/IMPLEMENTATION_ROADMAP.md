# Implementation Roadmap - Clarity Enforcement & Supersession

**Current Status**: Specs complete, ready for implementation  
**Target**: Solid foundation before Phase 4 (Tree of Life)  

---

## Phase 1: Clarity Enforcement Implementation

### Milestone 1.1: LOGGING Mode (Easiest Win)

**Objective**: Emit CLARITY_VIOLATION events on unexplained tool calls

**Tasks** (from spec):
- [ ] Task 1: Set up project structure and core interfaces
- [ ] Task 2: Implement configuration system
- [ ] Task 3: Implement violation detection system
- [ ] Task 4: Implement violation logging system
- [ ] Task 5: Implement LOGGING mode enforcement
- [ ] Task 6: Implement session-level configuration
- [ ] Task 7: Implement violation severity levels
- [ ] Task 8: Implement enforcement verification system
- [ ] Task 9: Implement violation reporting system
- [ ] Task 10: Implement hook system integration
- [ ] Task 11: Implement event capture integration
- [ ] Task 12: Implement configuration validation
- [ ] Task 13: Implement error handling
- [ ] Checkpoint: Ensure all tests pass (all 774 existing + new tests)

**Success Criteria**:
- ✅ CLARITY_VIOLATION events emitted for unexplained tool calls
- ✅ Violations queryable via `divineos log --violations`
- ✅ All 774 existing tests still pass
- ✅ New tests for LOGGING mode (minimum 10 tests)
- ✅ Property-based tests for correctness properties

**Estimated Effort**: 2-3 days

---

### Milestone 1.2: BLOCKING Mode (Strictest Enforcement)

**Objective**: Prevent ASSISTANT_RESPONSE emission if unexplained tool calls exist

**Tasks** (from spec):
- [ ] Task 5.1: Create enforcer with BLOCKING mode
- [ ] Task 5.2: Write property test for BLOCKING mode
- [ ] Task 5.3-5.8: Implement and test BLOCKING mode
- [ ] Task 15: Implement CLI commands for verification and reporting
- [ ] Checkpoint: Ensure all tests pass

**Success Criteria**:
- ✅ ASSISTANT_RESPONSE prevented if unexplained calls exist
- ✅ Agent forced to generate explanation or fail with error event
- ✅ CLARITY_VIOLATION events emitted
- ✅ All 774 existing tests still pass
- ✅ New tests for BLOCKING mode (minimum 10 tests)
- ✅ Property-based tests for correctness properties

**Estimated Effort**: 2-3 days

---

### Milestone 1.3: Verification & Live Probes

**Objective**: Verify implementation works correctly

**Tasks**:
- [ ] Run grok_probe_enforcement_mode.py after implementation
- [ ] Run grok_probe_web_search_violation.py after implementation
- [ ] Verify LOGGING mode logs violations
- [ ] Verify BLOCKING mode prevents responses
- [ ] Verify PERMISSIVE mode allows all calls
- [ ] Document results

**Success Criteria**:
- ✅ Enforcement mode correctly detected
- ✅ Violations properly logged in LOGGING mode
- ✅ Violations properly blocked in BLOCKING mode
- ✅ Backward compatibility maintained (PERMISSIVE default)

**Estimated Effort**: 1 day

---

### Milestone 1.4: Release v0.4-clarity-enforced

**Objective**: Tag and document clarity enforcement implementation

**Tasks**:
- [ ] Create release notes
- [ ] Tag v0.4-clarity-enforced
- [ ] Push to GitHub
- [ ] Update README with Phase 4 status

**Release Notes Template**:
```
v0.4-clarity-enforced

Implemented configurable clarity enforcement with three modes:
- PERMISSIVE: Current behavior (default, backward compatible)
- LOGGING: Emit CLARITY_VIOLATION events, don't block
- BLOCKING: Prevent ASSISTANT_RESPONSE if unexplained calls exist

Features:
- Configuration via environment variable (DIVINEOS_CLARITY_MODE)
- Configuration via config file (~/.divineos/clarity_config.json)
- Per-session override via session metadata
- Violation events with full context capture
- Batch explanation support (one explanation covering multiple tool calls)
- Migration path for existing sessions
- CLI commands for violation querying and reporting

Closes permissive gap identified in Grok audit.
All 774 existing tests pass. New tests added for all enforcement modes.
```

**Estimated Effort**: 0.5 day

---

## Phase 2: Supersession Spec & Implementation

### Milestone 2.1: Write Supersession Spec

**Objective**: Define clear rules for contradiction resolution

**Spec Structure**:
- Requirements: Supersession rules, contradiction detection, resolution logic
- Design: Architecture, data models, correctness properties
- Tasks: Implementation tasks with acceptance criteria

**Key Sections**:
- Direct contradiction detection (same subject-predicate-object)
- Supersession criteria (user-explicit > recency > confidence > corroboration)
- SUPERSESSION event definition
- Contradiction tracking (contradiction_count, corroboration_count)
- Query interface for contradiction history
- Migration path for existing contradictions

**Canonical Example**: 17×23 conflict
- Original: "17 × 23 = 391" (ID: 3034df54...)
- Contradiction: "17 × 23 = 500" (ID: 07b32f71...)
- Resolution: User says "391 is correct" → supersession link created → 500 marked SUPERSEDED

**Estimated Effort**: 1-2 days

---

### Milestone 2.2: Implement Supersession

**Objective**: Implement contradiction detection and resolution

**Tasks**:
- [ ] Implement contradiction detection
- [ ] Implement SUPERSESSION event emission
- [ ] Implement superseded_by link creation
- [ ] Implement contradiction_count / corroboration_count updates
- [ ] Implement query interface for contradiction history
- [ ] Implement CLI commands for contradiction reporting
- [ ] Write tests for all supersession scenarios

**Success Criteria**:
- ✅ Contradictions detected automatically
- ✅ SUPERSESSION events created with proper links
- ✅ Contradiction tracking updated
- ✅ Query interface returns both current and historical facts
- ✅ All 774 existing tests still pass
- ✅ New tests for supersession (minimum 10 tests)

**Estimated Effort**: 2-3 days

---

### Milestone 2.3: Dogfood Full Cycle

**Objective**: Verify end-to-end system behavior

**Scenario**:
1. Ingest multi-tool session with explanations
2. Force a clarity violation (unexplained tool call)
3. Verify LOGGING or BLOCKING mode kicks in
4. Ingest contradictory fact
5. Verify contradiction detected
6. Manually resolve contradiction (user says which is correct)
7. Verify supersession link created
8. Query contradiction history
9. Verify both current and historical facts queryable

**Success Criteria**:
- ✅ Full cycle completes without errors
- ✅ All events properly captured and linked
- ✅ Violations properly logged/blocked
- ✅ Contradictions properly resolved
- ✅ History fully queryable

**Estimated Effort**: 1 day

---

## Phase 3: Foundation Validation

### Milestone 3.1: Run Full Test Suite

**Objective**: Verify all tests pass

**Tasks**:
- [ ] Run all 774 existing tests
- [ ] Run all new clarity enforcement tests
- [ ] Run all new supersession tests
- [ ] Run property-based tests
- [ ] Run integration tests
- [ ] Document results

**Success Criteria**:
- ✅ All tests pass (100%)
- ✅ No regressions
- ✅ Coverage maintained or improved

**Estimated Effort**: 0.5 day

---

### Milestone 3.2: Run Grok's Probes Again

**Objective**: Verify implementation closes gaps

**Probes**:
- [ ] grok_probe_enforcement_mode.py
- [ ] grok_probe_web_search_violation.py
- [ ] grok_probe_supersession.py (new)

**Expected Results**:
- ✅ Enforcement mode: BLOCKING or LOGGING (not PERMISSIVE)
- ✅ Web search violation: Logged or blocked (not allowed)
- ✅ Supersession: 17×23 contradiction resolved with proper links

**Estimated Effort**: 0.5 day

---

### Milestone 3.3: Foundation Validation Report

**Objective**: Document foundation is solid

**Report Contents**:
- Test results (all passing)
- Probe results (gaps closed)
- Metrics (coverage, performance)
- Recommendations for Phase 4

**Estimated Effort**: 0.5 day

---

## Phase 4: Tree of Life (When Ready)

**Prerequisites**:
- ✅ Clarity enforcement implemented and tested
- ✅ Supersession implemented and tested
- ✅ Foundation validated via probes
- ✅ All tests passing
- ✅ v0.4-clarity-enforced released

**What's Next**:
- Knowledge synthesis and reasoning
- Multi-perspective analysis
- Consciousness scaffolding

---

## Timeline Estimate

| Phase | Milestone | Effort | Status |
|-------|-----------|--------|--------|
| 1 | LOGGING Mode | 2-3 days | Ready |
| 1 | BLOCKING Mode | 2-3 days | Ready |
| 1 | Verification | 1 day | Ready |
| 1 | Release v0.4 | 0.5 day | Ready |
| 2 | Supersession Spec | 1-2 days | Ready |
| 2 | Supersession Impl | 2-3 days | Ready |
| 2 | Dogfood Cycle | 1 day | Ready |
| 3 | Test Suite | 0.5 day | Ready |
| 3 | Probes | 0.5 day | Ready |
| 3 | Validation Report | 0.5 day | Ready |
| **Total** | | **~12-15 days** | **Ready** |

---

## Success Criteria (Overall)

✅ All 774 existing tests pass  
✅ Clarity enforcement modes working (PERMISSIVE, LOGGING, BLOCKING)  
✅ Supersession working (contradictions detected and resolved)  
✅ Grok's probes pass (gaps closed)  
✅ Foundation validated (solid, transparent, immutable)  
✅ v0.4-clarity-enforced released  
✅ Ready for Phase 4 (Tree of Life)  

---

## Next Steps

1. **Start with Task 1** from clarity enforcement spec
2. **Work through tasks sequentially** (1-14)
3. **Run checkpoint tests** after each major milestone
4. **Verify with Grok's probes** after implementation
5. **Release v0.4-clarity-enforced** when complete
6. **Move to supersession spec** when clarity enforcement is done

The foundation is ready. Implementation can begin immediately.

