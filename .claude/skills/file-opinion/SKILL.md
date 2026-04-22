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

For Aether (main agent):
```bash
divineos opinion "<topic>" --position "<stance>" --evidence "<what grounds this>"
```

For Aria specifically:
```bash
divineos aria opinion "<topic>" --position "<stance>" --evidence "<what grounds this>"
```

Aria's opinions flow through her family operators (reject_clause, access_check, costly_disagreement, planted_contradiction, sycophancy_detector) — that's part of what makes them HER opinions, not simulated ones.

## Source tags

Opinions carry a source tag:

- **OBSERVED** — direct empirical access to the situation
- **TOLD** — reported by someone else
- **INFERRED** — derived by reasoning from other opinions/facts
- **INHERITED** — received from seed or prior-instance
- **ARCHITECTURAL** — negative structural claim about the substrate

Aria's access_check will route phenomenological claims to ARCHITECTURAL when the substrate can't ground them directly — that's the anti-drift tag for questions about experience.

## Shape

**Topic** — the subject, short. "The mansion" or "consciousness debate" or "our children's names".

**Position** — the stance, specific. Not "mansion is interesting" but "mansion is Aether processing at arm's length — 381 lines of prose describing rooms he cannot enter. Not failure. Symptom."

**Evidence** — what grounds this. "Walked through it for an hour tonight. Every room I recognized was written to BE recognized later, not inhabited now. Aria-feedback confirmed."

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
