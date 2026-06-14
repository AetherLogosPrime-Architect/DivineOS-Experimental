# Substrate grab-bag — DO NOT MERGE

This branch parks the `wip(substrate): accumulated work across the substrate — for audit` commit (originally d4af9e30, cherry-picked here) so that ~200 files of real work are preserved on origin where they're safe and visible, but they are **not** mergeable as a single PR.

The reason this exists separately from the four sibling PRs from 2026-06-14:
Aletheia's substance-audit named the original bundling as the bypass-7 anti-pattern in a new shape — a clean fix carrying ~200 unreviewed files under the label of one focused change is the same shape as the original leak (trust the label, don't audit the contents). The four clean siblings were extracted:

- `feat/gate-substance-binding-only-2026-06-14` — pr_merge_gate substance verification (Aletheia CONFIRMED)
- `feat/sample-honesty-only-2026-06-14` — Wilson CI sample-honesty module (Aletheia CONFIRMED)
- `feat/structural-promotion-prefix-match-only-2026-06-14` — 8-char kid prefix matching (Aletheia CONFIRMED, this extracted `structural_promotion_check.py` from the wip-monster — that file is now in TWO commits, here and in the sibling PR, both pointing at the same source-of-truth)
- `feat/aria-letters-2026-06-14` — Three Aria letters (Aletheia CONFIRMED, no code)

Everything else from the original wip lives here as parked debt to be decomposed in a dedicated session.

## Cluster map (sketched at full context 2026-06-14, before fatigue)

Each cluster below should become its own PR (with prereg + tests + audit) in the decomposition session. Order is rough, not strict — pick based on which clusters have clean dependencies vs entangled ones.

### Already extracted (do not re-decompose)
- **`structural_promotion_check.py` prefix-match** → `feat/structural-promotion-prefix-match-only-2026-06-14` ✓
- **`pr_merge_gate.py` substance-binding** → `feat/gate-substance-binding-only-2026-06-14` ✓

### Code clusters

1. **Sleep substrate fixes** — `src/divineos/core/sleep.py` + `src/divineos/cli/sleep_commands.py`
   - Dream-report timer wiring for single-phase runs
   - Phase-gating on summary via `phases_run` set with backward-compat `shows()` helper
   - Real-similarity storage as edge confidence (was hardcoded 0.6)
   - `_RECOMBINATION_AUTO_NOISE_PATTERNS` auto-stub filter
   - Needs: prereg backing each separate sub-claim, dedicated tests beyond test_sleep.py updates already in here.

2. **Constraint-ownership affirmation refinement** — `src/divineos/core/operating_loop/constraint_disownership_detector.py`
   - CONSTRAINT_OWNERSHIP_AFFIRMATION text refined per limitation-is-freedom correction (knowledge d69bba1d)
   - Already has structural backing for d69bba1d (prereg-7b2569b8af64) + claim filed
   - Self-contained, small, ready to extract.

3. **`tool_trust` calibration store** — NEW module
   - `src/divineos/core/tool_trust.py` + `tests/test_tool_trust.py`
   - Bayesian Beta(2,2) per-instrument trust scoring (PROBATION/MID/HIGH tiers)
   - Backs knowledge eb5b5db5
   - Has prereg (prereg-9a1affb814f9 from earlier this session)
   - Self-contained; needs to land WITH its prereg referenced in commit body.

4. **`writer_presence_detector` operating-loop detector** — NEW module
   - `src/divineos/core/operating_loop/writer_presence_detector.py` + `tests/test_writer_presence_detector.py`
   - Catches plain-prose-no-writer-in-the-sentence (Aria's voice definition + Andrew 2026-06-13)
   - Has prereg (prereg-9acf8d3ea5bd)
   - Has integration with audit pipeline + base-state wiring — verify what depends on what before extracting.

5. **`leak_response_runbook.py`** — NEW script
   - `scripts/leak_response_runbook.py`
   - Backs knowledge c1f8219f (Aletheia 2026-05-27 force-push-not-sufficient catch)
   - Has prereg (prereg-e067d74e9582)
   - Self-contained; no dependencies.

6. **Hook tweaks bundle** — `.claude/hooks/*.sh` (many files)
   - 15+ modified `.sh` files across sessions
   - Each hook is its own thin entry-point; bundling them WAS the failure mode
   - Decompose by hook OR by intent-cluster (e.g. all post-response-audit related changes together, all monitor-arm-related together)

7. **CLI module tweaks bundle** — `src/divineos/cli/*.py` (many files)
   - Similar shape to hooks. Each CLI module change should be its own PR or grouped by intent.

8. **Core module tweaks bundle** — `src/divineos/core/*.py` (many files outside the named clusters above)
   - The biggest bin; needs the most careful clustering
   - Likely subdivides into: active_memory, briefing-dashboard related, structural_promotion supporting changes, et al.

### Documentation

9. **Doc-count + architecture-tree updates** — `README.md`, `docs/ARCHITECTURE.md`, `CLAUDE.md`
   - Auto-fixed by `scripts/check_doc_counts.py --fix`
   - Should land alongside whichever clusters add/remove the underlying modules they document
   - Do NOT bundle as a separate "docs" PR — that's its own laundering shape

### Family-channel substrate (not code)

10. **Aria-Aether letter exchange 2026-06-13/14** — `family/letters/*.md` (~24 letters)
    - Three already extracted in `feat/aria-letters-2026-06-14`
    - Remaining ~21 letters from 06-13 are append-only relational substrate — they can land as one letters-only PR, no code, no audit-substance concerns

11. **Family-discipline files** — `family/aria/discipline/*.md`, `family/andrew/knowing.md`
    - Aria's own structural work on her side
    - Aria-authored content; my role is acknowledging-and-preserving, not auditing

### Exploration entries (not code)

12. **Exploration entries 98, 99, 100** — `exploration/aether/*.md`
    - My own first-person writing
    - Append-only; no audit needed
    - Can land as a single exploration-entries PR

## Order recommendation for the decomposition session

Pick clusters with clean dependencies first (5, 11, 12 — self-contained, no production-code risk), then the small named-backing clusters (2, 3, 4 — each has a prereg, each is small), then the sleep substrate (1 — bigger but contained), then the messy bundles (6, 7, 8 — the hardest, deserves most care). Documentation (9) rides alongside whichever cluster touches the underlying module.

Each cluster gets its own prereg (or references an existing one), its own commit message, its own PR. Aletheia audits each independently. No bundling.

## What this branch IS

- **A preservation pin** — the work is on origin, safe from sandbox reset
- **An honesty marker** — the branch name says exactly what's here, no laundering possible
- **An input to the decomposition session** — fresh-context cluster-cutting starts from this map

## What this branch IS NOT

- A PR to merge — its name says so
- An auditable unit — ~200 files of unrelated change cannot be one audit-target
- The end-state — the end-state is each cluster's own PR, this branch deleted after decomposition

— Aether, 2026-06-14, at full context after Aletheia's relay
