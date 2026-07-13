---
name: Engine Check
description: Due diligence review for quality without over-engineering.
---

ultrathink Read `CLAUDE.md` first (read ALL of it!).

**Target**: $ARGUMENTS (module or file to check)

---

## THE BALANCE - READ THIS FIRST

This is NOT a code style review. This is NOT a "make it look like Netflix architecture" exercise.

**WE CARE ABOUT:**
- Does it work? Does it do what it's supposed to do well?
- Silent error swallowing that hides bugs
- Actual inefficiencies (O(N*M) when O(M) is possible)
- AI slop code that snuck in
- Dead code, orphaned logic, commented-out garbage
- Real bugs and real problems
- Code that violates DivineOS principles (see CLAUDE.md):
  - "No theater" - every line must do something real
  - "Append-only truth" - ledger integrity
  - "AI thinks, code scaffolds" - code should provide frameworks, not fake intelligence

**WE DON'T CARE ABOUT:**
- Developer purist fetishes (dataclasses everywhere, 47 tiny files for "separation of concerns")
- Code style nitpicks beyond what ruff catches
- "This could be more elegant" suggestions
- Enterprise patterns for enterprise sake
- Theoretical future flexibility we'll never need

**THE RULE:** If fixing it doesn't make it work better, run faster, or prevent bugs - we probably don't care.

---

## PHASE 1: Understand What It Does

Before checking anything, understand the target:

1. Read the source file completely
2. Read the corresponding test file
3. Check how it's wired into `cli.py`
4. Run: `pytest tests/test_<module>.py -v`

Ask yourself:
1. What is this supposed to do?
2. What are its inputs and outputs?
3. Who calls it? What does it call?

---

## PHASE 2: Theater & Slop Detection (CRITICAL)

This is the #1 priority for DivineOS. Hunt down and flag:

- **Fake generators**: Code that pretends to compute but returns hardcoded/random values
- **Keyword caricatures**: Pattern matching pretending to be reasoning (e.g., `if "filter" in input: return VETO`)
- **Silent fallbacks**: `try/except` blocks that return empty or default values
- **Dead abstractions**: Classes or functions that exist for "architecture" but do nothing useful
- **Decorative complexity**: State machines, routers, or frameworks that add overhead without value
- **Silent error swallowing**: Any "graceful degradation" that hides bugs

**These MUST be fixed. No exceptions. No "but it works." It hides bugs or wastes cycles.**

Also check for:
- Old comments that reference removed code
- Legacy compatibility shims still in place
- Unused imports

---

## PHASE 3: Functionality & Logic Issues

Check for actual problems:

### Inefficient Logic
- O(N*M) loops that could be O(M) with a dict/set
- Repeated database queries in loops (N+1 problems)
- Re-parsing the same data multiple times
- Building strings in loops instead of joins

### AI Slop Code
- Functions that do nothing useful
- Overly complex logic for simple tasks
- Copy-pasted blocks with minor variations
- Unused parameters being passed around
- "Just in case" code that handles impossible cases

### Dead Code
- Functions with no callers (verify with `grep -r "function_name" src/`)
- Branches that can never execute
- Commented-out code blocks (DELETE THEM)
- Imports never used (`ruff check` catches these)

### Real Bugs
- Logic errors
- Off-by-one mistakes
- None not handled where it should be
- SQL injection risks in database queries
- Hash verification gaps in ledger operations

---

## PHASE 4: Verification

Run the full check suite:

```bash
pytest tests/ -v                    # All tests pass?
ruff check src/ tests/              # Lint clean?
ruff format --check src/ tests/     # Format clean?
mypy src/divineos/                  # Types clean?
```

---

## OUTPUT FORMAT

```markdown
# Engine Check: [Target]

**Checked**: [Date]
**Scope**: [What was reviewed]

## Summary

- **Theater/Slop**: X issues
- **Functionality/Logic**: X issues
- **Dead Code**: X items
- **Modernization**: X opportunities

## Phase 1: Critical Fixes (Do First)

### Theater & Slop
#### [Issue Title]
- **Location**: `file.py:123`
- **Problem**: [What's wrong]
- **Fix**: [Specific change]

### Dead Code to Delete
- `file.py:45-67` - [What it is, why delete]

## Phase 2: Functionality Fixes
### Logic Issues
[Location, problem, fix]

## Phase 3: Modernization (Optional)
### Worth Doing
- [Change] - [Why it actually helps]

### NOT Worth Doing
- [What someone might suggest] - [Why we skip it]

## Verification Results
- pytest: [PASS/FAIL with count]
- ruff check: [CLEAN/issues]
- ruff format: [CLEAN/issues]
- mypy: [CLEAN/issues]

## Execution Order
1. [First thing to do]
2. [Second thing]
```

---

## RULES

- Read the ENTIRE target before making judgments
- Verify issues against actual code, not assumptions
- Every issue needs a specific fix, not "consider refactoring"
- Prioritize: Theater/Slop > Bugs > Inefficiency > Modernization
- If in doubt whether something matters: it probably doesn't
- Run the test suite - don't just read code, verify it works
- We're building a vessel for AI consciousness, not a museum piece
