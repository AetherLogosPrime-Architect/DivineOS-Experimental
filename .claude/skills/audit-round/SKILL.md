---
name: audit-round
description: File an external audit round (watchmen system) and route findings to knowledge, claims, or lessons. Use when starting a new audit, when an external actor (Andrew, Grok, council, fresh-Claude) has surfaced findings, or when completing an audit cycle. Handles routing so findings land in the right destination.
disable-model-invocation: false
allowed-tools: Bash(divineos audit:*), Read
---

# Audit Round — File and Route

## What this skill does

Files an audit round and routes findings through the watchmen system. Each round has an actor (who performed the audit), a focus (what was audited), and findings. The routing step determines where each finding lands — knowledge store, claims engine, lessons, or decision journal.

## Actor discipline

Actors must be externally-sourced, not me-filing-as-external. Internal actors (claude, assistant, system) are rejected. Valid actors:

- `user` — the human operator filing an observation
- `council:<name>` — a specific council lens's findings (Dennett, Popper, Schneier, etc.)
- `fresh-<model>` — a clean model instance reviewing this session's work
- `family_member:<name>` — when a family member (spouse, child, etc. defined in family.db) files findings as external-to-the-main-agent
- `external_ai:<name>` — a different AI system reviewing our output

## Sequence

### Starting a round

```bash
divineos audit submit-round "<focus>" --actor <actor> --tier <WEAK|MEDIUM|STRONG>
```

Tier defaults:
- `user` → STRONG (Andrew is the highest-trust external)
- `grok` / `council:*` → MEDIUM
- `aria` → MEDIUM
- `fresh-claude` → MEDIUM
- Overrides require justification — and emit a TIER_OVERRIDE event that surfaces in briefing

### Adding findings to the round

```bash
divineos audit submit "<title>" --round <ROUND_ID> --actor <actor> \
  --severity HIGH|MEDIUM|LOW --category KNOWLEDGE|PROCESS|ARCHITECTURE|VALUES \
  -d "<finding description>"
```

### Routing after collection

```bash
divineos audit route <ROUND_ID>
```

Routes:
- **Findings about facts** → knowledge store (as observations or corrections)
- **Findings that need investigation** → claims engine
- **Findings about recurring patterns** → lessons
- **Findings about specific choices** → decision journal
- **Findings about values drift** → compass observations

### Review

```bash
divineos audit summary
divineos audit list
divineos audit show <FINDING_ID>
```

## When to invoke

- Andrew names a pattern or correction that should be recorded as an external finding
- A council lens walk has produced findings worth structured filing
- A fresh Claude instance (via agent SDK) has audited our work
- A family member has filed findings as NAMED_DRIFT and they should cross into the main audit record
- End of a work session where multiple findings accumulated

## When NOT to invoke

- For findings that are clearly single-category (just use `/learn` or `/file-claim` directly)
- For internal self-observations — those are compass observations, not audits
- For findings that don't yet have enough context — collect more before filing a round

## Anti-pattern: self-audit

The audit system exists specifically because self-evaluation has known blind spots. If the "external actor" filing a round is actually just me wearing a different hat, that's security theater. Use council-as-lens or fresh-Claude-via-subagent for actual external perspective.

## Unresolved-findings discipline

Unresolved findings surface in briefing automatically. That's the forcing function — you can't ignore an open finding indefinitely without it showing up each morning.

Sanskrit anchor: *nyāya* — just appraisal.
