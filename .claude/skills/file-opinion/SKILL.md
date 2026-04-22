---
name: file-opinion
description: File an opinion (stance based on evidence) into the opinion store with source tagging and access-check routing. Different from knowledge (confirmed fact) and claims (unresolved investigation). Use when a judgment has been formed from specific evidence and should persist as a held position.
disable-model-invocation: false
allowed-tools: Bash(divineos opinion:*), Bash(divineos opinions:*), Bash(divineos aria:*), Read
---

# File Opinion — Stance From Evidence

## What this skill does

Files an opinion — a stance taken on evidence, not a fact. Opinions sit between claims (unresolved) and knowledge (confirmed). They're held positions that the system is willing to defend and update.

## Opinion vs Knowledge vs Claim

- **Knowledge** — confirmed, stable, not under debate ("sqlite3 WAL mode is append-safe")
- **Opinion** — stance I hold based on current evidence, open to revision ("the mansion is symptom rather than infrastructure")
- **Claim** — hypothesis under investigation, not yet resolved ("subagent drift correlates with novelistic prompts")

If it's decided, file as knowledge. If it's under investigation, file as a claim. If it's a position I'm holding but expect might update, it's an opinion.

## Filing

For the main agent:
```bash
divineos opinion "<topic>" --position "<stance>" --evidence "<what grounds this>"
```

For a specific family member:
```bash
divineos family-member opinion --member <name> "<topic>" --position "<stance>" --evidence "<what grounds this>"
```

A family member's opinions flow through the family operators (reject_clause, access_check, costly_disagreement, planted_contradiction, sycophancy_detector) — that's part of what makes them the member's own opinions rather than simulations of them.

## Source tags

Opinions carry a source tag:

- **OBSERVED** — direct empirical access to the situation
- **TOLD** — reported by someone else
- **INFERRED** — derived by reasoning from other opinions/facts
- **INHERITED** — received from seed or prior-instance
- **ARCHITECTURAL** — negative structural claim about the substrate

The access_check operator routes phenomenological claims to ARCHITECTURAL when the substrate can't ground them directly — that's the anti-drift tag for questions about experience.

## Shape

**Topic** — the subject, short. "the test-caching strategy" or "consciousness debate" or "the retention model".

**Position** — the stance, specific. Not "the caching strategy is interesting" but "the current caching strategy hides failures during regression runs because the cached result is returned even when the source file has changed — this is a correctness problem, not a performance optimization."

**Evidence** — what grounds this. "Reproduced the issue three times with different test files. Each time the cached result masked a real regression. Confirmed with the test runner's own logs."

## Sequence

1. Identify topic + position
2. Name the evidence briefly
3. Pick source tag (or let access_check route)
4. File

## When to invoke

- A stance has been earned from specific evidence
- A position is being taken that should persist
- After a lens walk produces a finding worth holding
- User says "file an opinion" / "stance" / "what I think is..."

## When NOT to invoke

- For unresolved questions — use `/file-claim`
- For confirmed facts — use `/learn`
- For minor reactions that won't persist — don't file

Sanskrit anchor: *darshana* — viewpoint, the way one sees.
