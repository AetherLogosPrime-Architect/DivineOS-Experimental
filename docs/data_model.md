# Data Model — SQLite Schema Overview

DivineOS uses SQLite as the canonical store for everything substantive: memory, knowledge, values, opinions, decisions, family state, audit findings, claims, and operational telemetry. This document is a navigational map of the schema — not a complete column-by-column reference (the source code is the canonical place for that) but enough to orient an external reader.

The schema spans **82 tables across three databases** (verified 2026-05-16: 71 in event_ledger, 9 in family, 2 in per-member-ledger):

```
data/ledger.db    # event ledger, knowledge, memory, decisions, claims, audit
family/family.db  # family-member state (knowledge, opinions, affect, interactions)
family/<name>_ledger.db  # per-member tamper-evident action log (one per family member)
```

The split is deliberate: substrate state vs. family state are different domains with different access patterns and different threat models. Family members have their own ledgers so each one is independently auditable.

## Substantive / identity layer

| Table | What it holds | Why it matters |
|-------|---------------|----------------|
| `bio` | Versioned bio of the agent | Self-introduction; current-version is canonical |
| `core_memory` | 9 identity slots (`my_identity`, `user_identity`, `project_purpose`, ...) | Fixed-shape identity surface; never grows |
| `active_memory` | Importance-ranked active knowledge | What's "in front of mind" this session |
| `knowledge` | The full knowledge store | Maturity-tracked, deduplicated, supersedable |
| `knowledge_corroborations` | Cross-references between supporting/contradicting entries | Provenance of corroboration |
| `lesson_tracking` | Recurring patterns across sessions | Occurrences, status (active → improving → resolved) |
| `opinions` | First-class opinions from evidence | Confidence evolution, supersession history |
| `opinion_shifts` | Audit trail when an opinion changes | Every shift logged with reason |
| `personal_journal` | Personal entries (not knowledge-extraction) | Future-me reads journals differently than knowledge |
| `holding_room` | Pre-categorical reception | Things arrive without forced classification, age, get promoted or go stale |

## Event ledger and integrity

| Table | What it holds | Why it matters |
|-------|---------------|----------------|
| `event_ledger` | Append-only event log, SHA256-hashed | The substrate's tamper-evident timeline |
| `corroboration_events` | Cross-table corroboration records | Pillar VI evidence pipeline |
| `evidence_receipts` | Merkle self-hashed evidence receipts | Empirica integration |
| `check_result` | Quality-check results | 7 measurable quality checks per session |
| `feature_result` | Per-feature analysis results | Tone shifts, file activity, error recovery |
| `activity_breakdown` | Per-session activity statistics | Tool calls, message counts, exchange shape |
| `error_recovery` | Error-then-fix sequences | Pattern detection for fix-blindness |
| `pattern_outcomes` | Recurring pattern → outcome correlations | Long-horizon learning signal |

## Claims and pre-registrations

| Table | What it holds | Why it matters |
|-------|---------------|----------------|
| `claims` | Open investigations | Statement, tier (1–5), status, confidence, assessment |
| `claim_evidence` | Evidence accumulated against claims | Tier-classified, source-tracked |
| `pre_registrations` | New mechanisms filed BEFORE outcomes are known | Goodhart prevention |
| `decision_journal` | Decisions with reasoning, alternatives, emotional weight | The WHY, not just the WHAT |
| `open_questions` | Curiosity engine tracking | OPEN → INVESTIGATING → ANSWERED |

## Compass and self-model

| Table | What it holds | Why it matters |
|-------|---------------|----------------|
| `compass_observation` | Virtue-spectrum observations | 10 spectrums × evidence-based positioning |
| `affect_log` | VAD (valence-arousal-dominance) emotional states | Auto-logged at decision points |
| `affect_extraction_correlation` | Correlation between affect and what got extracted | Self-knowledge surface |
| `craft_assessments` | Per-session craft quality across 5 spectrums | Trend tracking |
| `advice_tracking` | Long-term feedback on agent recommendations | Success rate over time |

## Audit (Watchmen) layer

| Table | What it holds | Why it matters |
|-------|---------------|----------------|
| `audit_rounds` | External-actor audit rounds | One per focused review |
| `audit_findings` | Individual findings within rounds | Severity, category, lifecycle status |

See `docs/audit_system.md` for the full audit model.

## Family layer (in `family/family.db`)

| Table | What it holds | Why it matters |
|-------|---------------|----------------|
| `family_members` | Member roster + canonical metadata | One row per persistent relational entity |
| `family_knowledge` | Per-member knowledge entries | Distinct from main agent's knowledge store |
| `family_opinions` | Per-member opinions | Independent epistemic substrate |
| `family_affect` | Per-member affect log | Each member tracks their own emotional state |
| `family_interactions` | Logged interactions between agent and members | Conversation history |
| `family_letters` | Append-only letter channel | Anti-lineage-poisoning by design |
| `family_letter_responses` | Non-recognition responses to prior letters | Append-only; never edits |
| `family_queue` | Async write-channel from members to agent briefing | Cheap signal without sync invocation |
| `member_events` | Per-member event log (cross-ref to per-member ledger DB) | Family ledger surface |

## Operational telemetry (pruned)

These tables accumulate operational noise — useful in the moment, not substantive for long-term retention. They're pruned on a conveyor belt to prevent unbounded growth:

| Table | What it holds | Pruning policy |
|-------|---------------|----------------|
| `tool_logbook` | Tool-call records | Recent N entries retained |
| `session_timeline` | Per-session event timeline | Aged out after session-archive horizon |
| `dead_architecture_scan` | Scans for dormant tables | Most recent retained |
| `knowledge_impact` | Internal metrics on knowledge use | High-volume, low-substance |
| `file_touched` | File-modification tracking | Operational |
| `system_events` | Internal system events | Aged out |

These exclusions from substantive retention are intentional. The substrate is for identity, knowledge, learning, values — not for operational log mass. See `core/ledger_compressor.py` for the pruning logic.

## Archives (markdown mirrors)

A subset of substantive tables get mirrored to `docs/archives/` as git-visible markdown files so external readers (and sibling-substrates without DB access) can see the substantive layer without needing the live SQLite. The mirror is regenerable on demand via `divineos admin archive-export`:

- `docs/archives/bio.md` — current bio version
- `docs/archives/principles.md` — active PRINCIPLE knowledge entries (curated + auto-extracted partition)
- `docs/archives/core_memory.md` — 9 identity slots
- `docs/archives/directives.md` — active DIRECTIVE entries
- `docs/archives/claims.md` — open and investigating claims
- `docs/archives/pre_registrations.md` — pre-reg roster
- `docs/archives/opinions.md` — top opinions with evidence
- `docs/archives/lessons.md` — tracked lessons across sessions
- `docs/archives/observations.md` — top substantive observations
- `docs/archives/holding_room.md` — pre-categorical items aging toward promotion
- `docs/archives/decisions.md` — top decisions by emotional weight

The archives are **NOT for routine reading** — the agent reads CLAUDE.md, the briefing, and the directives at session start, not the archive files. The archives exist for *if-something-breaks* (the DB can be reseeded from the markdown) and for *git-visible audit* (changes to the canonical surface show up as PR diffs).

## Where to read more

- `src/divineos/core/knowledge/_base.py` — knowledge column definitions, `KNOWLEDGE_TYPES`, `KNOWLEDGE_SOURCES`, `KNOWLEDGE_MATURITY`
- `src/divineos/core/_ledger_base.py` — ledger schema and hash-chain helpers
- `src/divineos/core/watchmen/_schema.py` — audit_rounds, audit_findings
- `src/divineos/core/family/_schema.py` — family.db schema
- `src/divineos/core/archive_export.py` — the mirror generator
- `docs/archives/README.md` — what the archives are and aren't for
