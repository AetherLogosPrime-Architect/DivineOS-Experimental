# Foundation Audit Fixes - March 19, 2026

**Status**: ✅ COMPLETE  
**Tests Fixed**: 5 failing → 1177 passing  
**Root Cause**: Silent bugs in ledger integration and test mocking

---

## Bugs Found & Fixed

### Bug 1: Module-level `store_fact()` had `self` parameter
**File**: `src/divineos/supersession/ledger_integration.py` (line 213)  
**Issue**: Function defined as `def store_fact(self, fact: Dict[str, Any])` but called as module-level function  
**Impact**: `TypeError: store_fact() missing 1 required positional argument: 'fact'`  
**Fix**: Removed `self` parameter, delegated to `get_ledger_integration().store_fact(fact)`

### Bug 2: Duplicate code in `store_supersession_event()` method
**File**: `src/divineos/supersession/ledger_integration.py` (lines 60-95)  
**Issue**: Method had entire logic duplicated twice (lines 60-77 and 78-95)  
**Impact**: Dead code, confusing maintenance  
**Fix**: Removed duplicate block, kept single implementation

### Bug 3: Missing ID handling returned empty string instead of None
**File**: `src/divineos/supersession/ledger_integration.py`  
**Issue**: `store_fact()` and `store_supersession_event()` returned `""` when ID missing, tests expected `None`  
**Impact**: `AssertionError: assert '' is None`  
**Fix**: Changed to return `None` when ID is missing, added warning logs

### Bug 4: Wrong patch path in test mock
**File**: `tests/test_violation_hooks.py` (line 393)  
**Issue**: Patch path was `"src.divineos.clarity_enforcement.hooks.logger"` but should be `"divineos.clarity_enforcement.hooks.logger"`  
**Impact**: `ModuleNotFoundError: No module named 'src'`  
**Fix**: Corrected patch path to use correct module import path

### Bug 5: Return type annotations not updated
**File**: `src/divineos/supersession/ledger_integration.py`  
**Issue**: Functions returned `str` but now return `Optional[str]`  
**Impact**: Type inconsistency  
**Fix**: Updated return type annotations to `Optional[str]`

---

## Test Results

### Before Fixes
```
FAILED tests/test_supersession_ledger_integration.py::TestStoreFact::test_store_fact
FAILED tests/test_supersession_ledger_integration.py::TestStoreFact::test_store_multiple_facts
FAILED tests/test_supersession_ledger_integration.py::TestLedgerIntegrationEdgeCases::test_store_fact_with_missing_id
FAILED tests/test_supersession_ledger_integration.py::TestLedgerIntegrationEdgeCases::test_store_supersession_event_with_missing_id
FAILED tests/test_violation_hooks.py::TestRegisterDefaultHooks::test_default_hooks_functionality

5 failed, 1172 passed
```

### After Fixes
```
1177 passed, 195 warnings in 21.28s
```

---

## Key Insight

These bugs demonstrate the "errors squeaking by" problem you identified:

1. **Silent failures in test setup** - The ledger integration tests were importing functions that had broken signatures, but the errors only surfaced when tests actually ran
2. **Duplicate code hiding bugs** - The duplicate `store_supersession_event()` logic made it harder to spot the issue
3. **Type inconsistency** - Functions returning empty strings instead of None violated the contract expected by tests
4. **Import path assumptions** - Test mocking assumed wrong module paths

**This is exactly why the foundation wasn't solid.** The hardening phase fixed logging and error handling, but didn't catch these integration bugs because they only surface when the full test suite runs.

---

## Recommendation

Before building the next layer (metacognition/memory integration), we need:

1. **Continuous test running** - Run full test suite on every change
2. **Type checking** - Run `mypy --strict` to catch type inconsistencies
3. **Integration testing** - Test actual function calls, not just unit tests
4. **Code review for duplicates** - Scan for copy-paste code patterns

The foundation is now solid: **1177/1177 tests passing**.
