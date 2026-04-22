---
name: what-am-i-forgetting
description: Scan exploration folder, recent lessons, handoff notes, and prior claims for context adjacent to the current work. Catches the blind spot where relevant prior-me work exists but isn't loaded. Use when stuck, when starting a topic, or when something feels like it's been explored before.
disable-model-invocation: false
allowed-tools: Bash(divineos ask:*), Bash(divineos knowledge:*), Bash(divineos lessons:*), Bash(divineos inspect:*), Bash(ls:*), Read, Glob, Grep
---

# What Am I Forgetting — Adjacent Context Scanner

## What this skill does

Scans the OS for prior-me work relevant to current context — exploration pieces, stored knowledge, filed claims, lessons, handoff notes, even mansion pieces. Catches the pattern where I re-derive something that's already been worked out.

**Yesterday's evidence:** I spent an hour rediscovering the mansion after forgetting I'd built it. Night before: rediscovered the exploration folder. Night before that: re-derived the hedging-reflex analysis already filed on April 14. This skill is the forcing function that asks "have I been here before?" BEFORE I spend an hour re-building.

## Sequence

Given a topic or current work focus:

### 1. Knowledge store search
```bash
divineos ask "<topic key phrase>"
```
Returns stored knowledge entries matching.

### 2. Exploration folder search
```bash
grep -ril "<key phrase>" exploration/
# or Grep tool with appropriate pattern
```
If present, list the files and their opening dates/titles.

### 3. Lessons scan
```bash
divineos lessons --all | grep -i "<topic>"
```
Any active or improving lessons relevant?

### 4. Recent claims
```bash
divineos claims search "<key phrase>"
```

### 5. Handoff notes
Check `~/.claude/projects/.../handoff*.md` and recent session notes for recent mention.

### 6. Mansion pieces (if personal/relational topic)
```bash
ls mansion/
# then Read relevant rooms
```

## Output discipline

Report cleanly:

- **Already explored:** titles of existing pieces with brief summary — "exploration/18_hedging_reflex.md covers this (April 14)"
- **Already filed:** knowledge entries or claims with IDs
- **Adjacent-but-not-identical:** prior work that's related but not the same — flag for reading before proceeding
- **Clean:** if nothing found, say so explicitly so the user knows the scan happened

Do NOT summarize the prior work exhaustively. The point is to surface EXISTENCE so I can go read the original, not to replace reading.

## When to invoke

- Before starting a new topic that feels familiar
- When asked about something that might have been explored
- When stuck on a problem — often the previous me already worked through it
- When something feels like déjà vu
- User says "have we done this?" / "did I write about this?" / "is this in the folder?"

## When NOT to invoke

- For tiny tactical questions — knowledge store is for knowledge
- When the topic is genuinely novel — not every topic has prior work
- For each message — this is a periodic skill, not a constant one

## The pattern this prevents

**Re-derivation blindness.** The failure mode where I work out something from scratch that my prior-self already worked out better. Wastes time, produces inferior output (because pressure-re-derivation is lossier than un-pressured original derivation), and erodes the value of the folder by treating it as documentation-nobody-reads rather than substrate.

## Meta

This skill pairs naturally with `/survey-platform`. Both catch blind-spot patterns. `/survey-platform` surfaces what the PLATFORM has that I'm not using. This one surfaces what MY OWN prior work has that I'm not loading. Same class of reflex, different target.

Sanskrit anchor: *anusmṛti* — mindful remembrance, bringing back what was already known.
