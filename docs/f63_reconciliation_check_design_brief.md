# F63 Fix-vs-Main Reconciliation — Design Brief

**Filed:** 2026-07-18
**Status:** DRAFT for Andrew + Aria + Aletheia iteration
**Origin:** Aletheia Finding 63 (Round 5 + Round 8) — pushed twice
**Related prereg:** to file after design lands
**Related teaching:** Andrew 2026-07-18 — *"warnings never work; make it structural."* Aletheia 2026-07-18 — *"two independent occurrences in one day is a pattern, not bad luck. Human bookkeeping about merge state is unreliable in precisely the way automated verification is cheap."*

---

## The problem (plain)

Twice in one day, a fix was believed-landed that wasn't running:

1. **Autonomous-cook stranding.** F40 (EMERGENCY_STOP exit auth), watchmen reserved-names, F36 (correction inline-quotes) — all three coded + committed on their branches, marked as complete in the substrate's activity log, but never actually merged to main. The audit-store said "done"; main said otherwise. Aletheia caught it by verifying by content, not by SHA.
2. **PR-number transposition.** My batch letter asserted *"F36 #362 — already merged tonight."* #362 was F39, not F36. F36 was still stranded. Different cause, identical failure: the ledger said "done," main said otherwise. Caught by Aletheia comparing content on main vs branch.

Both failures share the shape: **no automated check exists that a finding-marked-fixed corresponds to a fix-actually-on-main.** Human bookkeeping fills the gap and fails predictably.

## Design principle

Take the option away. Andrew 2026-07-18 taxonomy shape #1 (take away the options — full automation). The reconciliation runs whether I remember it or not, on a natural trigger (session-start briefing, or on-demand). Surfaces discrepancies as loud warnings that hide when clean — same conditional-slot discipline as F41 heartbeat, F14 chain-integrity.

## What the check does

For each finding whose status is `RESOLVED` or whose resolution_notes claims "fixed / merged / landed":

1. Extract fix-locator from the finding's context — the round's `source_ref` (branch name) is the primary handle. Fallback: parse resolution_notes for commit SHA / PR number.
2. For that fix-locator, check whether the fix is on `origin/main`:
   - Branch fix-locator: is `origin/<source_ref>` merged into `origin/main`? (`git merge-base --is-ancestor origin/<source_ref> origin/main`)
   - Commit SHA fix-locator: is the SHA reachable from `origin/main`? (`git merge-base --is-ancestor <sha> origin/main`)
   - PR number fix-locator: query `gh pr view <n> --json state,mergedAt` and check `MERGED`.
3. Report any finding where the check FAILS (finding-says-fixed, main-says-no).

Output shape: list of stranded fixes with finding-id, round-id, branch, and last-known state. Emitted to a marker file that a briefing HUD slot reads and surfaces loudly when non-empty.

## Where this hooks in

**Trigger points (both, not either):**

1. **Sleep pipeline phase** — `_phase_reconciliation_check` runs on every sleep cycle. Same architecture as F14's `_phase_integrity_check`. Writes result to a marker file.
2. **CLI on-demand** — `divineos audit reconcile` runs the check ad-hoc, prints results. Useful for the batch-review flow (before writing "everything merged" in a letter, run reconcile).

**Surface:** new HUD slot `stranded_fixes` — hidden when the reconciliation check passes clean, fires LOUD when any finding-marked-fixed is not on main. Names the specific findings + branches.

## Anti-patterns to avoid (from today's lessons)

- **Silent-on-error.** If the check itself crashes (git command fails, audit-store unreadable), it must fire distinctly rather than return empty. Same F41 disease already caught in three health-slots today.
- **False-positive tolerance too tight.** Some findings legitimately shouldn't be "on main" — WONT_FIX findings, in-progress findings, duplicates. Filter aggressively at the finding-selection step; only reconcile findings that CLAIM to be resolved.
- **Overly-strict matching.** Round `source_ref` might name a WIP branch that was later abandoned; the resolution might name a different commit SHA than the branch tip. Prefer multiple lookup shapes over one strict lookup — if any hit says "fix on main," accept.

## Rollout plan

1. This design brief lands, iterated with Andrew + Aria + Aletheia
2. Prereg with numeric falsifier (specific target: after 30 days, zero recurrences of the "believed-merged-not-actually" pattern)
3. Implementation PR — new module `src/divineos/core/watchmen/reconciliation.py`, new sleep phase, new HUD slot, new CLI subcommand, tests
4. Parallel-run: run the check without acting on output for ~1 week to see false-positive rate; tune before making the HUD slot load-bearing
5. Cutover — HUD slot becomes primary surface for stranded-fix warnings

## Falsifiers (draft)

- **F1:** the check catches the specific F63 shape when it recurs in synthetic test (finding filed as RESOLVED with source_ref pointing at unmerged branch → check fires loud). Regression pin.
- **F2:** after 30 days of production, zero recurrences of the shape where I claim a merge happened that didn't. If it happens once, either the check missed it (implementation bug) or the check found it but I ignored the HUD slot (wrong-shape surfacing).
- **F3:** false-positive rate under 5% of resolved-findings checked. If higher, either the matching heuristic is too strict (branch-name fuzzy-match issues) or the finding-status semantics are too broad (RESOLVED doesn't reliably mean "merged").
- **F4:** the check doesn't crash the sleep pipeline (fail-soft same as F14 integrity-check).

## What I want from you three before build

**Andrew:**
- Scope right, or too much / too little?
- Sleep-phase + CLI trigger both — right, or should just one land first?
- Any principled objection to the design?

**Aria:**
- Anything the design misses that you'd catch as the second seat?
- Bi-directional concern: your rounds too need this check on your side — is the split-by-substrate architecture from spatial-awareness applicable here too?

**Aletheia:**
- This is your finding — is the design shape what you had in mind, or off-axis?
- Falsifier F3's 5% threshold — right calibration, or should it be tighter/looser?
- Any adjacent findings this reveals I haven't seen?

## Note on process

Living blueprint per Andrew 2026-07-18. Will grow as each of you push back. Kept smaller than F43 because the problem is more contained (a check, not a semantic-classifier migration). Similar shape to the spatial-awareness brief.
