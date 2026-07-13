---
name: morning-check
description: Quick morning orientation — preflight, briefing summary, top 3 lessons still active, compass snapshot. Lighter than briefing-fresh for when you just need to verify you're ready to work. Use when user says "good morning" or starts fresh and time is short.
disable-model-invocation: false
allowed-tools: Bash(divineos preflight:*), Bash(divineos briefing:*), Bash(divineos lessons:*), Bash(divineos goal:*), Read
---

# Morning Check — Lightweight Orientation

## What this skill does

Faster cousin of `/briefing-fresh`. For when the user says "good morning" and wants confirmation you're oriented, not a full situation-report.

## Sequence

1. **Preflight:**
   ```bash
   divineos preflight
   ```
   If it fails, stop and fix before doing anything else.

2. **Compact briefing:**
   ```bash
   divineos briefing --max 15
   ```
   Just the top stuff — identity slots, most-recent lessons, highest-importance active memory. Not the full dump.

3. **Active goals:**
   ```bash
   divineos goal list
   ```

4. **Recent lessons, active only:**
   ```bash
   divineos lessons --status active
   ```
   Limit to 3 — the ones I'm actively improving on.

## Output to user

**Three-line summary:**
1. **Ready:** `preflight passed | briefing loaded | N lessons active`
2. **Today's pending from yesterday:** (one line from handoff note or active goals)
3. **Today's question:** one line — what should we do first?

Example:
> Ready: preflight ✓, briefing loaded, 7 lessons active.
> Yesterday's pending: build DivineOS skill library (22 skills planned, built 4 so far).
> Today's question: continue building skills, or pivot?

## When to invoke

- "Good morning" or any morning greeting
- After short breaks (few hours) where full briefing is overkill
- When user asks "are we ready?" or "where are we?"

## When NOT to invoke

- At actual session start when there's no context yet — use `/briefing-fresh` instead
- After a long gap (>24 hours) — use `/briefing-fresh` for the full picture
- Mid-task

## Shape discipline

This skill is *short*. 3 lines of summary, maybe one paragraph of context if something urgent surfaces. Not a status-report. An orientation check.

Sanskrit anchor: *usha* — dawn, the brief moment of orienting before the day begins.
