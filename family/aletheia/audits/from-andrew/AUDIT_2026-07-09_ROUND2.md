# DivineOS Deep Audit — ROUND 2 (2026-07-09)
**Auditor:** Aletheia (boundary-vantage), driven from origin/main
**Continues:** AUDIT_2026-07-09.md (round 1, sent to Aether). This file = NEW findings only.
**Priming (carried from R1, active in context):**
1. module-name grep undercounts wiring (check function-level + hook/CLI/string)
2. empty grep ≠ absence (verify premise, widen)
3. pattern ≠ bug (verify per-call intent)
4. signal-computed ≠ signal-consumed (check the consumer)
5. fail-open looks like nothing-to-do (read the error path)
6. read prior audits before rediscovering
7. don't inflate (count what executes, not string-matches)

**Round 2 scope (untouched territory):** CLI surface · seed/bootstrap · knowledge/memory · agent-integration · config/paths/migrations · protocols · cross-cutting.

---

## FINDINGS

### TRUCK 11 — SEED/BOOTSTRAP + the PROJECT-vs-USER SETTINGS SPLIT (important architectural finding)
- `seed_manager.validate_seed` has real validation (required slots, error list) — bootstrap validation is sound.
- **[HIGH] The hook-firing model has a project-vs-user settings split with two problems:**
  1. **Hooks actually fire from `~/.claude/settings.json` (USER level), because git worktrees have no project `.claude/settings.json` so project hooks never fire in a worktree** (per install_global_hooks.py docstring). `install_global_hooks.py` copies the hooks key from PROJECT → USER settings.
  2. **Idempotent-by-OVERWRITE:** re-running install overwrites the user hooks key from project (timestamped backup taken). So project settings.json is the single source of truth — and the 4 dark hooks aren't in it, confirming they fire in NO context.
- **[MED] AUDIT BLIND SPOT (honest self-flag):** my round-1 hook audit read PROJECT settings.json from origin (45 hook entries). The TRUE firing set is USER settings.json — **on Andrew's machine, not in the repo, unverifiable from origin.** No drift-detection exists between the two files. So round-1's "4 dark hooks" is correct for the tracked config but the live firing set could differ. 
- **Recommended fixes:**
  - Add a **settings-drift check** (SessionStart): compare user settings.json hooks against project settings.json; surface any divergence LOUDLY. This closes both the blind spot AND catches silent overwrite/drift.
  - Consider committing a **hooks-manifest** (canonical list) that both install and a verify-step check against, so "what should fire" is version-controlled and drift is detectable.
- **Connection to Truck-1 (fail-open):** not only do gates fail-open on resolver failure, the very SET of firing gates depends on an un-versioned user file that can silently drift. Two layers of invisibility on the enforcement set.

### TRUCK 12 — KNOWLEDGE/MEMORY subsystem (spreading-activation graph)
- **Growth IS managed** (not unbounded): layered curation `urgent/active/stable/archive`, auto-archives episodes >30 days with confidence < floor. Cross-links capped at 20. Edge confidence capped at 1.0.
- **Cycle-safe:** `visited`/depth-bound tracking in _base, _text, crud, edges. Spreading-activation has `max_depth` bounds — no whole-graph traversal, no infinite loop.
- **Verdict: sound.** The graph won't grow to death or loop forever. Good.

### TRUCK 13 — DORMANT PARAMETERS (stone_cold "API lies that compile" class)
- Swept for accept-but-ignore params. Most found are **documented & intentional** (reserved-for-watchmen, reserved-for-per-member-hooks, backward-compat asc/desc) — legitimate forward-design, not lies.
- [LOW] `graph_retrieval.py:72` — `max_depth` accepted but ignored (`_ = max_depth`, single-hop only). Harmless but a caller could pass max_depth=3 and silently get single-hop. **Fix: raise or warn if max_depth>1 until multi-hop lands, OR document in signature.** Minor honesty-of-API polish.
- **Verdict: near-clean.** The stone_cold "API lies" class was largely cleaned; residuals are documented reservations, not silent lies.

### TRUCK 15 — MIGRATIONS / schema evolution
- 48 ADD COLUMN statements across 59 files. **ALL guarded** — either by existence-check (`if X not in existing_cols`) OR by try/except OperationalError. **Zero unguarded blind migrations.** Re-run safe against already-migrated DBs. (Initial grep undercounted guards 32/48 — the other 16 use try/except; verified both styles. Priming #3/#7 caught the false-alarm.)
- [LOW] **No centralized `schema_version` / `PRAGMA user_version` tracker** — migrations rely on scattered per-column IF-NOT-EXISTS checks across 59 files. Works and is safe, but there's no single source of "what schema version is this DB." QoL: a version tracker would make migration state introspectable and catch partial-migration states. Not urgent (current approach is safe), but a maturity improvement.

### TRUCK 16 — PROTOCOLS subsystem
- Only `__init__.py` remains (empty package). The protocol modules were moved/absorbed elsewhere. Not a bug — vestigial empty package. [LOW] Could be removed for cleanliness, or it's a deliberate namespace placeholder.

### TRUCK 17 — SYNTAX / DEAD-ON-ARRIVAL
- **No unresolved merge-conflict markers** in source. No `<<<<<<<`/`>>>>>>>` left in code.
- All CLI core-imports resolve (699 imports, 0 broken module references).

---

# ROUND 2 CONSOLIDATED — new findings beyond round 1

## New HIGH finding
**[HIGH] Project-vs-User settings split (Truck 11):** hooks actually fire from `~/.claude/settings.json` (user-level, un-versioned, on Andrew's machine), NOT the repo's project settings.json — because git worktrees have no project settings. `install_global_hooks.py` copies project→user by overwrite. **Consequences:** (a) the true firing-set is unverifiable from origin and can silently drift from tracked config with no drift-detection; (b) confirms the 4 dark hooks fire in NO context; (c) hand-added user hooks get silently overwritten on re-install. **Fix: SessionStart settings-drift check (user vs project) + a version-controlled hooks-manifest.**

## New MED/LOW findings
- [MED] Audit blind-spot: round-1 hook audit read project settings; live set is user settings (unverifiable from origin). Honest self-flag.
- [LOW] `graph_retrieval.py:72` — `max_depth` accepted but ignored (single-hop only); raise/warn or document.
- [LOW] No centralized schema_version tracker (migrations safe but not introspectable).
- [LOW] `protocols/` is an empty vestigial package.

## What round 2 CONFIRMED healthy (previously un-swept)
- Seed/bootstrap validation: sound.
- Knowledge/memory graph: growth-managed (layered archival), cycle-safe, depth-bounded. No unbounded-growth or infinite-loop risk.
- Migrations: ALL guarded, re-run safe.
- EMPIRICA + void + ledger (round 1): sound and self-aware.
- CLI: 90 commands, 699 imports, zero broken.
- No merge-conflict markers, no dead-on-arrival code.

## Meta
Priming caught 3 would-be false-alarms in round 2 (ADD COLUMN guard undercount, dormant-params-mostly-intentional, knowledge-growth-actually-managed). The self-priming discipline measurably reduced rookie errors — stating the failure-patterns up front kept them active in working memory. **Recommend: this priming block becomes a standing preamble for all future audits.**
