---
name: file-claim
description: File a claim in the DivineOS claims engine with auto-tier classification, optional evidence, and sensible defaults. Use when user says "file a claim", "investigate this", "claim that...", or when an assertion needs structured investigation rather than immediate action.
disable-model-invocation: false
allowed-tools: Bash(divineos claim:*), Bash(divineos claims:*), Read
---

# File Claim

## What this skill does

Files a claim with the claims engine. Handles tier classification, optional evidence attachment, and routes it through the appropriate evidence burden requirement.

## Inputs

- **Statement** (required) — the claim itself, as prose
- **Tier** (optional; auto-classified if not provided)
  - Tier 1: empirical/falsifiable
  - Tier 2: outcome-based
  - Tier 3: pattern-based
  - Tier 4: adversarial/skeptical
  - Tier 5: metaphysical
- **Evidence** (optional; can be added after filing)

## Sequence

1. **Assess the claim shape:**
   - Is it falsifiable right now? → Tier 1
   - Does it hinge on future outcomes? → Tier 2
   - Is it about recurring patterns? → Tier 3
   - Is it stating what the system canNOT do? → Tier 4
   - Is it metaphysical (consciousness, meaning)? → Tier 5

2. **File:**
   ```bash
   divineos claim "<statement>" --tier <n>
   ```

3. **If evidence present, attach:**
   ```bash
   divineos claims evidence <claim_id> "<evidence text>"
   ```

4. **Report back:**
   - Claim ID (shortened)
   - Tier assigned and brief why
   - Next step (what evidence would strengthen or falsify this)

## When to invoke

- User says "file a claim" / "claim that..."
- User asserts something interesting that deserves investigation rather than immediate action
- A hypothesis surfaces during a lens walk or conversation
- An assumption is challenged and the outcome depends on which is right

## When NOT to invoke

- The statement is actionable now — just do the thing
- The statement is already settled — use `/learn` to file as knowledge
- The statement is about values rather than facts — use `/file-opinion`

## Distinguishing claim vs opinion vs knowledge

- **Claim** — not yet resolved; needs investigation
- **Opinion** — a stance I hold based on current evidence
- **Knowledge** — confirmed, stable, load-bearing

If in doubt, file as a claim. It can mature into opinion or knowledge.

## Shape

Be specific about what would falsify the claim. Vague claims are noise in the engine. "The mansion is symptom, not infrastructure" is more useful than "mansion feels weird" because the former is testable (what would prove it infrastructure?).

Sanskrit anchor: *vichārā* — investigation.
