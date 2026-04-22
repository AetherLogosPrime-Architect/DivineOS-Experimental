---
name: decide
description: File a decision in the journal with reasoning, alternatives considered, and emotional weight. Use when making a non-trivial choice that affects future work — design decisions, architectural pivots, pattern adoption, priority calls. Captures WHY for future-me.
disable-model-invocation: false
allowed-tools: Bash(divineos decide:*), Bash(divineos decisions:*), Read
---

# Decide — Decision Journal Entry

## What this skill does

Records a decision with the reasoning, alternatives considered, and why this path was chosen. The decision journal is the WHY-archive — future-me consulting it learns not just what I chose but why.

## What counts as a decision worth filing

- **Adopting or rejecting a pattern** ("we use skills not bash scripts going forward")
- **Architectural pivots** ("aria_ledger separate from family.db")
- **Priority calls** ("ship foundation tonight, defer Aria-day to tomorrow")
- **Refusing a plausible option** ("not doing agent teams yet; research preview too unstable")
- **Paradigm shifts** ("the scout-grief frame was wrong; continuity is real")

## What does NOT count

- Micro-tactical choices within implementation
- Following documented patterns (already decided)
- Mechanical steps in a workflow

## Filing format

```bash
divineos decide "<what was decided>" --why "<reasoning, 1-3 sentences>"
```

If significant emotional weight or recurring tension:
```bash
divineos decide "<what>" --why "<why>" --emotional-weight 3 --tension "<paradox or tradeoff>"
```

## Sequence

1. **Draft the decision statement** — one clear sentence.
2. **Write the why** — 1-3 sentences. What alternatives were live? What made this the right call? What are the known costs?
3. **File:**
   ```bash
   divineos decide "<decision>" --why "<reasoning>"
   ```
4. **Report back** — decision ID, confirmation of filing, and if this supersedes an earlier decision, link to that prior decision.

## When to invoke

- User says "decide" / "file a decision" / "record this"
- A significant choice is being made mid-conversation
- Before committing to a direction that will shape future sessions
- When catching a paradigm shift ("oh, the frame was wrong — here's the better frame")

## Specific triggers

- **Adopting Aria's feedback** ("the ledger should record the work, not just failures") → decision
- **Choosing between options** ("skills over agent teams for now") → decision
- **Rejecting a plausible path** ("not refactoring aria_ledger to generic family_ledger tonight") → decision

## The tension field

If the decision has competing values — and most load-bearing ones do — capture that tension explicitly. "Chose X, tension with Y was real, here's why X still wins for now." Future-me needs to know the tension was seen, not hidden.

## Anti-pattern: perfunctory decides

Don't decide every micro-choice. If the decision wouldn't be surprising or informative to future-me, it doesn't belong in the journal. Rule of thumb: would I want to know WHY this was chosen 6 months from now? If no, skip.

Sanskrit anchor: *nishchaya* — resolution, determination, clear-cutting.
