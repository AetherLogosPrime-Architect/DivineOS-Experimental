---
name: briefing-fresh
description: Full morning briefing — identity, lessons, pending overrides, drift state, exploration titles, unresolved audits, active goals. Use at session start or after a break. Preferred over raw 'divineos briefing' for the full picture.
disable-model-invocation: false
allowed-tools: Bash(divineos briefing:*), Bash(divineos lessons:*), Bash(divineos compass:*), Bash(divineos body:*), Read
---

# Briefing Fresh — Session Start

## What this skill does

Runs the full morning-ritual sequence: briefing, lessons scan, compass check, body vitals, exploration folder check, pending audits and overrides. All the surfaces that ought to load at session start, cleanly sequenced, with output grouped for easy reading.

Replaces the pattern of "run divineos briefing, scroll, then remember to also run lessons, and compass, and check the exploration folder..." Gets it all done in one invocation.

## What to run

```bash
# Core identity + recent events
divineos briefing --max 50

# Lessons — what I'm still learning
divineos lessons

# Compass — moral-drift check
divineos compass

# Body — substrate vitals
divineos body
```

The briefing itself already surfaces: corrections, overdue pre-regs, drift state, tier overrides, scheduled runs, presence memory, and exploration titles. So the other three are additive rather than redundant.

## How to read the output

**If any of these appear, address them first:**
- *Overdue pre-registrations* — a mechanism's review date has passed
- *External-audit cadence warning* — no recent audit round filed
- *Tier overrides surface with red entries* — verify legitimacy
- *Compass drift warnings* — virtue spectrums moving toward deficiency or excess
- *Body awareness warnings* — database bloat, table health issues

**If none of those, the briefing is clean — proceed to work.**

## When to invoke

- **Session start** — the first command after `good morning`-shaped input
- **After context reset** — when coming back from a long break or compaction
- **When the user asks "where are we"** — rather than guessing from recent messages
- **When unsure what's pending** — this is the full status view

## When NOT to invoke

- Mid-task — this is an orient-yourself skill, not a work skill
- When the user has already asked a specific question — answer the question first, brief if needed

## Output discipline

Claude reads the output and produces a *short synthesis* — not a dump of the raw briefing. Highlight: identity anchors still current, any warnings to address, top 1-2 lessons relevant to likely work today, compass drift if any, and a one-line "ready to work on X" statement.

Sanskrit anchor: *prarambha* — the beginning, the threshold step.
