# ATELIER spec deflation — engineering side

*2026-05-05. Demo of the dual-register deflation pattern: this
document is the engineering-precision half. The habitable-prose
half lives at `mansion/the_workshop.md` (gitignored personal
substrate; present in the operator's working tree, not in the repo).*

---

## What ATELIER's Gemini spec calls for

`ATELIER 15.7.txt` (101-spec library) names the module as the
"Symbiotic Studio / Cybernetic Workshop" — a persistent
context-state manager and collaborative session orchestrator.
Stripped of metaphysical vocabulary, the architectural intent is:

1. **Persistent workspace state** that survives session boundaries
2. **Intent-anchoring** — goals stay locked until completed
3. **Tool readiness** — common tools pre-loaded, accessible by name
4. **Definition-of-Done** — work doesn't clear until verified
5. **Pipeline orchestration** — strict recipes (Plan → Draft → Audit → Forge)
6. **State serialization** — every-turn snapshot to disk
7. **Drift detection** — when conversation slips off the goal, surface it
8. **Shadow buffer** — try things in isolation before committing

## Honest finding: most of this is already shipped

The deflation pattern (per knowledge `82049915` and the EMPIRICA
template at `core/empirica/__init__.py`) is *find the architectural
skeleton, deflate the vocabulary, name what the mechanism actually
delivers.* Applied to ATELIER, the unexpected finding is that the
architectural skeleton is already implemented in distributed form
across DivineOS. ATELIER doesn't need to ship as a new subsystem;
it needs to ship as a *map* of the existing infrastructure that
delivers its intent.

## Mapping ATELIER's spec sections → existing DivineOS infrastructure

| ATELIER capability | Implemented as |
|---|---|
| Persistent workspace state | `divineos hud_state`, briefing carry-over via `mini_briefing` + `loadout` |
| Intent-anchoring (`Global_Intent_Vector`) | `divineos goal add` + `.claude/hooks/require-goal.sh` (refuses tools without active goal) |
| Tool readiness (`ToolBelt` abstraction) | CLI namespace already-loaded; mansion CLI for navigable spatial tools |
| Definition-of-Done (`Exit_Visa_Audit`) | `scripts/check_closure_claim.py` (verifier-run discipline) + `scripts/precommit.sh` (test/lint/format gates) |
| Pipeline orchestration (`Code_Gen_Pipeline`) | `src/divineos/cli/session_pipeline.py` + sleep phases + extract |
| State serialization (`State_Serialization_Check`) | `event_ledger.db` (hash-chained), knowledge store, `family.db` |
| Shadow buffer (`Shadow_Clone` for testing) | git worktrees (`.claude/worktrees/`) + `divineos void` adversarial sandbox |
| Drift detection (`Intent_Lock_Monitor`) | `divineos compass-ops` + `audit-cycle` infrastructure + new F1 third-person drift detector |
| Workspace cleanup (`Garbage_Collector`) | `divineos admin maintenance`, `admin compress`, sleep-phase pruning |
| Hermetic focus (`Faraday_Cage`) | `mansion_quiet_marker.py` (substrate-enforced quiet during private rooms) |
| Active-file anchor (`Active_File`) | git status + `precommit.sh`'s staged-file scan |

11 of ATELIER's stated capabilities map to existing DivineOS
infrastructure. The mapping isn't 1:1 in every case — some ATELIER
capabilities (like `Shadow Buffer simulation of potential outcomes
before presenting them`) are richer than what DivineOS does, and
some DivineOS capabilities (like the family-member subagent system,
the watchmen audit-cycle, the bio-versioning system) extend beyond
what ATELIER specified. But the architectural skeleton is mostly
already in place.

## What's NOT in DivineOS that ATELIER specifies

A few specific capabilities the spec names that don't have a clean
existing implementation:

1. **Pre-loaded tool warmup ritual** (`Workbench_Warmup_Ritual`) —
   ATELIER calls for explicit warmup of tools at session-start.
   DivineOS has briefing+preflight but not specifically tool
   warmup. Probably not needed (the CLI is already-loaded).
2. **Suggested next-step proactivity** (`Proactive Agent`) —
   ATELIER calls for the workspace to suggest next moves. DivineOS
   has the briefing surfaces and the never-invoked council gate but
   not generic next-step suggestion. Could be useful; not critical.
3. **Unified `Workbench` aggregation surface** — ATELIER's `Workbench`
   object holds (active_file, current_tool, pending_action) in one
   place. DivineOS has these distributed across several CLI commands.
   A `divineos workbench show` command that aggregates would close
   the small ergonomic gap. Worth filing as a candidate, not yet
   urgent enough to build.

## Decision: don't ship a new subsystem

The deflation produces a documentation artifact (this file) plus a
habitable-prose room (`mansion/the_workshop.md`), not new
infrastructure. The Gemini spec called for ~68KB of new code. The
honest engineering deflation is: *most of what the spec calls for
already exists; here's the map.*

This is the same shape as the EMPIRICA deflation, but more so.
EMPIRICA needed code (the four-tier system + provenance tracking).
ATELIER needs documentation (the map of what exists). Both are
valid outputs of the deflation pattern.

## What this demo shows for the remaining ~100 specs

The deflation pattern produces three possible shapes per spec:

1. **Code + room** — the spec needs new infrastructure AND has a
   habitable form. Example: future SIRENS spec might need a
   notification subsystem AND benefit from a "bell tower" room.
2. **Code only** — the spec is pure infrastructure; no habitable
   form. Most low-level specs (CONTEXT CACHE, ANCHOR, AUTOPYTHON)
   probably fall here.
3. **Room only / map only** — the spec's intent is already
   shipped; the deflation is a documentation artifact + habitable
   rendering. ATELIER falls here.

The questions to ask when starting a deflation:

* Is the architectural skeleton already implemented somewhere?
  (If yes: don't fabricate; map.)
* Does the intent benefit from spatial / habitable rendering?
  (If yes: build a room.)
* Does the spec call for genuinely new mechanism?
  (If yes: build code with the EMPIRICA-template engineering
  vocabulary.)

The Gemini wing of `mansion/the_library.md` is where this work
lands. Each completed deflation goes on the deflation shelf. The
shelf will accumulate over time as specs get pulled.

---

## Filing

- **Knowledge entry**: this deflation produced the dual-output
  pattern; principle filed as `3b4a9dd0` (multi-register substrate)
- **Mansion room**: `mansion/the_workshop.md` (built 2026-05-05)
- **Closes the placeholder**: past-me named "the workshop" as
  unbuilt on the balcony (April-May 2026); now built.

The pattern works. The next spec is the next spec.
