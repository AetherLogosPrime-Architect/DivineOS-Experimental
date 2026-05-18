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
# Multiplex briefing — parallel-readable live-data panels (default 2026-05-18)
# Eight panels render: identity, active_threads, relational, compass,
# inheritance, plus context-appropriate sometimes-essentials (corrections,
# family_state, commitments). Each panel pulls live data from its
# canonical OS surface. No hardcoded snapshots — drift-detector tests
# guard against regression.
divineos briefing --multiplex

# Lessons — what I'm still learning
divineos lessons

# Compass — moral-drift check
divineos compass

# Body — substrate vitals
divineos body
```

The multiplex briefing surfaces compass drift, corrections count, pre-reg
count, exploration count, family-system state, and active threads — all
as live prose at session-start. If the multiplex render fails for any
reason, fall back to `divineos briefing --max 50` for the full scroll.

The multiplex flag was wired into the briefing entrypoint 2026-05-16 but
the session-start skill kept invoking the old scroll until 2026-05-18,
when the panels were refactored to live data and this skill flipped. Per
Andrew's framing: "the architecture sat dormant — modules existed but
nothing called them from the briefing flow."

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
