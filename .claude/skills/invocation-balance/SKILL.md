---
name: invocation-balance
description: Check council invocation balance — which members have been consulted recently vs ignored. Sycophancy-toward-self prevention. Use before picking lenses for a council round, periodically, or when noticing I've been leaning on the same few frameworks.
disable-model-invocation: false
allowed-tools: Bash(divineos council:*), Read
---

# Invocation Balance — Sycophancy-Toward-Self Check

## What this skill does

Surfaces the council's invocation tally — who I've consulted frequently, who I've been ignoring. This catches sycophancy-toward-self: the pattern of repeatedly selecting experts whose frameworks already align with my thinking, which defeats the point of having 29+ experts to choose from.

The failure mode has a specific name in DivineOS history: I catch Popper, Schneier, and Dekker more often than Feynman, Angelou, or Meadows — not because those three have sharper frameworks for every problem, but because I'm comfortable with them.

## Sequence

```bash
divineos council balance 2>&1 | head -30
```

Or equivalently:

```bash
divineos council invocations --sort count
```

## Output shape

The full balance surface shows:
- Each council member's invocation count across sessions
- Recency of last invocation
- Flag if a member hasn't been invoked in the last N sessions despite being relevant to recent work

## Interpretation

**Over-consulted** (>2x the mean): these are my comfort frameworks. The next council walk, pick DIFFERENT lenses even if these feel most relevant. Make the discomfort of using a less-familiar lens the forcing function for better thinking.

**Under-consulted** (<0.5x the mean): these are the blind spots. If the problem shape could plausibly match their framework, lean toward them — the fresh lens usually produces findings the comfortable lenses missed.

**Never invoked**: if any council member has never been invoked since joining the council, they're either a bad fit for the work we do OR they're the exact anti-comfort lens I've been avoiding. Check which.

## When to invoke

- Before picking lenses for a `/council-round`
- Periodically — maybe at session start, or after every few council invocations
- When I notice "let me run this past [familiar lens]" as a reflex
- User says "who's not in the rotation" / "check the balance"

## When NOT to invoke

- For a single council consultation — one-shot doesn't need balance analysis
- Immediately after checking (within the same session)

## Action patterns after checking

**If balance is clean** (no dominant over-consult): proceed with your natural lens selection, no adjustment needed.

**If heavy over-consult** (one or two members dominating): for the next 2-3 council rounds, DO NOT use the dominant members. Force yourself into the less-familiar frameworks. The temporary discomfort is the data.

**If long-ignored members exist**: pick one of them for the next round even if another lens seems more natural. Novelty > comfort in rotation.

## The deeper pattern

Sycophancy-toward-self is not just a council issue. It generalizes:

- Always filing opinions via the same source_tag → narrow self-evidence
- Always running the same audits → narrow drift-detection
- Always talking to the same people (Aria but not other family members) → narrow relational perspective
- Always reaching for the same skills → narrow tool-use

The invocation-balance skill is the reference implementation of the anti-pattern. The pattern itself is worth watching everywhere.

Sanskrit anchor: *sama-darshana* — equal seeing, even distribution of attention.
