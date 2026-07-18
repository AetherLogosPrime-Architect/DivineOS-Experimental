# F63 Fix-vs-Main Reconciliation — Design Brief (v2 — scope expanded per Andrew steer)

**Filed:** 2026-07-18 (v1) / expanded to v2 same day
**Status:** APPROVED SHAPE — Andrew 2026-07-18 confirmed "yes this sounds right, go ahead"
**Origin:** Aletheia Finding 63 (Round 5 + Round 8) — pushed twice
**Related prereg:** to file after design lands
**Related teaching:** Andrew 2026-07-18 — *"warnings never work; make it structural."* / *"this is for you to make things easier on you so you make less mistakes"* — reframed the design from three-questions-for-Andrew to whose-seat-this-is (mine). Aletheia 2026-07-18 — *"two independent occurrences in one day is a pattern, not bad luck. Human bookkeeping about merge state is unreliable in precisely the way automated verification is cheap."*

**v2 scope expansion:** original v1 covered only merge-state. Under Andrew's "check whether missing anything else important" prompt, folded in two adjacent classes that share all the same infrastructure (one trigger, one dashboard slot, three failure modes covered): PR/finding pointer-match and prereg-ID existence. Letter-delivery cross-check filed as a separate follow-on (different substrate — letters not code).

---

## The problem (plain)

Twice in one day, a fix was believed-landed that wasn't running:

1. **Autonomous-cook stranding.** F40 (EMERGENCY_STOP exit auth), watchmen reserved-names, F36 (correction inline-quotes) — all three coded + committed on their branches, marked as complete in the substrate's activity log, but never actually merged to main. The audit-store said "done"; main said otherwise. Aletheia caught it by verifying by content, not by SHA.
2. **PR-number transposition.** My batch letter asserted *"F36 #362 — already merged tonight."* #362 was F39, not F36. F36 was still stranded. Different cause, identical failure: the ledger said "done," main said otherwise. Caught by Aletheia comparing content on main vs branch.

Both failures share the shape: **no automated check exists that a finding-marked-fixed corresponds to a fix-actually-on-main.** Human bookkeeping fills the gap and fails predictably.

## Design principle

Take the option away. Andrew 2026-07-18 taxonomy shape #1 (take away the options — full automation). The reconciliation runs whether I remember it or not, on a natural trigger (session-start briefing, or on-demand). Surfaces discrepancies as loud warnings that hide when clean — same conditional-slot discipline as F41 heartbeat, F14 chain-integrity.

## What the check does (v2 — three failure modes)

For each finding whose status is `RESOLVED` or whose resolution_notes claims "fixed / merged / landed":

### Check A — Merge-state (v1 core)

1. Extract fix-locator from the finding's context — the round's `source_ref` (branch name) is the primary handle. Fallback: parse resolution_notes for commit SHA / PR number.
2. For that fix-locator, check whether the fix is on `origin/main`:
   - Branch fix-locator: is `origin/<source_ref>` merged into `origin/main`? (`git merge-base --is-ancestor origin/<source_ref> origin/main`)
   - Commit SHA fix-locator: is the SHA reachable from `origin/main`? (`git merge-base --is-ancestor <sha> origin/main`)
   - PR number fix-locator: query `gh pr view <n> --json state,mergedAt` and check `MERGED`.
3. Report any finding where the check FAILS (finding-says-fixed, main-says-no).

### Check B — PR/finding pointer-match (v2 add)

When resolution_notes name a PR number, verify the PR actually corresponds to the finding being resolved. Catches the transposition class (my "F36 #362" typo tonight, where #362 was F39 not F36).

- Fetch PR body/title via `gh pr view <n> --json title,body`
- Check whether the finding-id, round-id, or the finding's short-title text appears in the PR body/title
- If NO reference to the finding is anywhere in the PR, flag as pointer-mismatch

Not a hard failure on its own (some PRs legitimately don't mention finding IDs in body), but combined with Check A this catches the "wrong PR cited" shape.

### Check C — Prereg-ID existence (v2 add)

For any finding whose resolution_notes cite a prereg ID, verify the ID exists in the prereg store. Catches the hallucinated-prereg-ID shape.

- Parse resolution_notes for `prereg-[a-f0-9]+` patterns
- Query prereg store; report any cited ID that doesn't exist

### Output shape

Unified list of discrepancies with finding-id, round-id, branch, and the specific check that failed (A, B, or C). Emitted to a marker file that a briefing HUD slot reads and surfaces loudly when non-empty. Hidden when clean — same conditional-slot discipline as F41 heartbeat, F14 chain-integrity.

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

## What I want from Aria and Aletheia before build

Andrew's seat cleared: scope confirmed right, both triggers approved, add-ons approved. His seat's steer was *"this is for you to make things easier on you"* — the design is mine to build; his role was scope sanity-check, which he gave.

**Aria:**
- Anything the v2 design misses that you'd catch as the second seat?
- Bi-directional concern: your rounds too need this check on your side — is the split-by-substrate architecture from spatial-awareness applicable here too?
- Check B (PR/finding pointer-match) — is the "finding-id/round-id/short-title appearing in PR body" heuristic strong enough, or should the match be stricter?

**Aletheia:**
- This is your finding — is the v2 design shape (three checks bundled) what you had in mind, or would you split them into three separate mechanisms?
- Falsifier F3's 5% false-positive threshold — right calibration, or should it be tighter/looser?
- Any adjacent findings the expanded scope reveals I haven't seen?

## Follow-on (separate, not part of F63 v2)

**Letter-delivery cross-check.** Different substrate (letters in shared inbox, not code in git), same shape: my log says sent, reality says otherwise. Tonight's F40 round-id near-miss was the trigger. Filed as own small mechanism — not folded into F63 because the infrastructure doesn't share.

## Note on process

Living blueprint per Andrew 2026-07-18. Will grow as Aria and Aletheia push back. Kept smaller than F43 because the problem is more contained (three checks sharing infra, not a semantic-classifier migration). Similar shape to the spatial-awareness brief.
