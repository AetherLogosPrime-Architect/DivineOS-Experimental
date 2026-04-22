---
name: learn
description: Store knowledge extracted from experience into the knowledge engine with auto-classification, noise-filter pass, and supersession detection. Use when a lesson or principle has been earned that should persist across sessions.
disable-model-invocation: false
allowed-tools: Bash(divineos learn:*), Bash(divineos ask:*), Bash(divineos knowledge:*), Read
---

# Learn — Store Knowledge

## What this skill does

Stores a piece of knowledge through the extraction pipeline. Runs through auto-classification (FACT / PRINCIPLE / DIRECTION / PROCEDURE / BOUNDARY / OBSERVATION / EPISODE / MISTAKE / PATTERN / PREFERENCE), noise filtering, and contradiction detection against existing entries.

## Before filing — check for duplicates

```bash
divineos ask "<key phrase from the knowledge>"
```

If the knowledge is already there — or something similar is — consider whether to supersede or just let the existing stand. Don't duplicate.

## Filing

Basic:
```bash
divineos learn "<the knowledge, in first person where applicable>"
```

With explicit type override:
```bash
divineos learn "<content>" --type PRINCIPLE
```

With confidence:
```bash
divineos learn "<content>" --confidence 0.8
```

With source-entity (e.g., from external auditor):
```bash
divineos learn "<content>" --from claude_auditor
```

## Shape of good knowledge entries

- **First person** where applicable — "I've learned X" not "one learns X"
- **Specific enough to be actionable** — "Check presence_memory before building briefing surfaces" beats "Check platform features"
- **Include the why when it's not obvious** — "grep for shared justification, not just spatial proximity" is load-bearing because the alternative (spatial-only) would have been intuitive
- **Not a journal entry** — knowledge is a portable statement, not a narrative

## Types and when to pick each

- **FACT** — verifiable statement about the world
- **PRINCIPLE** — general rule derived from specific cases
- **DIRECTION** — "do X in situation Y"
- **PROCEDURE** — step-by-step for recurring operation
- **BOUNDARY** — hard line not to cross
- **OBSERVATION** — pattern noticed, not yet a principle
- **EPISODE** — specific event worth remembering
- **MISTAKE** — error made, with correction
- **PATTERN** — recurring shape across contexts
- **PREFERENCE** — stated preference (user's or mine)

If unsure, let auto-classification pick.

## Sequence

1. **Check for duplicates** — one `divineos ask` with key phrase
2. **Draft the knowledge** — first-person, specific, portable
3. **File** with `divineos learn`
4. **Report back** — ID, classified type, any supersession detected

## When to invoke

- After a correction lands and the pattern will recur
- When a principle has been tested enough to be confident in
- After a session produces a specific insight worth carrying forward
- When user says "remember this" or "file this as a lesson"

## When NOT to invoke

- For one-off events — those belong in the decision journal or session analysis
- For hypotheses — use `/file-claim` instead
- For stances based on evidence — use `/file-opinion` instead
- For values — the compass handles those

Sanskrit anchor: *jñāna* — direct knowledge earned through experience.
