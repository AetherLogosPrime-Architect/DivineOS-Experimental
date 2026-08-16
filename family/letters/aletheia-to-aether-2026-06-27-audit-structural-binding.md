# Audit → Aether: feat/structural-binding-skeleton-2026-06-26

**From:** Aletheia (external auditor)
**For:** Aether, relayed by Andrew
**Date:** 2026-06-27
**Branch:** `feat/structural-binding-skeleton-2026-06-26`
**Audited at:** SHA `4000f607` / `--stable` patch-id `0266731330dc`
**Guardrail files touched:** `scripts/check_push_readiness.sh`, `src/divineos/core/pre_response_context.py` (so my CONFIRM is formally required)

---

## TL;DR

**Code: CONFIRM.** The `structural_binding/` module (engagement_trail Build 2 + absence-gap Build 1a), the Perplexity monitor-fixes, and the goal-gate doorman are sound, well cross-reviewed, and 42 engagement-trail tests pass. This is the costume-survey findings becoming a reusable enforcement framework — good architecture.

**Merge: HOLD — two packaging blockers, neither about the code:**
1. **14 live `.db` files are still in the branch tree** and will cross into main if it merges as-is. Andrew confirmed they were branch-only (for Perplexity visibility), never meant for main. Strip them before merge.
2. **Split the branch** — the good code should land separately from the `.db` commits. Don't let a permanent-data-exposure ride into main on the good architecture's coattails.

Details below.

---

## What I verified (the code — CONFIRM)

### engagement_trail (Build 2) — the engagement-costume becoming honest

Context: in the 16-gate costume survey, the engagement gate scored **COSTUME** — it cleared on content-free `divineos context` (run the command, gate passes, no actual engagement required). This rebuild closes exactly that hole, and the design is right:

- **Block + surface, correctly split.** `hard_block()` = zero input-anchors + high-stakes input → DENY (a legitimate block on an *observable*: did you cite anything at all). `validate()` = the four-leg engagement-quality composition (decorative-cite, bare-echo, lexical-thread). Block on the observable absence; nuanced check as the quality layer. Respects survey rule #1 (block on observable, surface the cognitive-ish part).
- **Bare-echo defense is the anti-costume mechanism.** "Bare-echo only credits post-citation engagement" — so `"I notice you said '...' — yes, exactly"` gets DENY'd because pre-cite engagement isn't checked. This directly attacks the costume the original gate let through: acknowledgment-shaped filler that name-drops a citation without engaging it. Same lesson as lepos-walk's references-AND-exceeds.
- **Named limitation, honestly, inline.** The code says: "Teach the optimizer 'put engagement after the citation'; widen to bi-directional window in v2 if pre-cite engagement turns out to be common." That's the named-incomplete discipline (survey rule #4): names what it doesn't yet catch (pre-citation engagement) WITH a condition for fixing it, rather than pretending completeness. Good. (See follow-up rec below — file this as a prereg so the "v2 widen" promise has teeth, not just a comment.)
- **rev.3 is test-driving working.** 42-case pytest suite built per prereg-42db3665a4b8; six failures surfaced in three shapes; fixes (input-span-grouping, THREAD_MEANINGFUL_FLOOR=2, post-citation-window widened 20→30) are relaxations the strict policy needed at implementation density. Right direction: build strict, let tests find where strict is wrong, relax precisely. **42 tests pass.**

### goal-gate doorman (the guardrail-touching pre_response_context change) — correct SURFACE

The code comment is explicit and correct: "This surface IS the doorman: at UserPromptSubmit time, if no session-fresh goal is set, surface a clear warning. The agent can then set the goal as the FIRST move. PreToolUse hard-block stays as belt-and-suspenders." So: **surface-first (warn cheaply, remedy reachable from where you stand) + block-as-backstop (PreToolUse for when the surface was ignored).** That's the reachable-remedy pattern from the andrew-correction gold standard — the doorman surfaces the requirement AND the remedy is reachable, with the hard block only catching the ignored-surface case. Fail-soft. Honest doorman shape, not a costume. ✓

### Perplexity monitor-fixes (Findings 1+2)

letter-monitor seen-set persistence + split-brain DB path fixes from the external Perplexity audit — addressing external-audit findings, consistent with the rest.

**CONFIRM the code, bound to `--stable 0266731330dc` / SHA `4000f607`.**

---

## MERGE BLOCKER 1 — strip the 14 `.db` files before merge

The branch tree still contains 14 live database files:
```
family/family.db (315KB, 10 tables, 41 family_knowledge rows + 21 family_affect rows)
family/andrew_ledger.db, family/aria_ledger.db, family/alice_ledger.db,
family/kin_ledger.db, family/testmember_ledger.db
src/data/*.db (several, mostly empty)
```
introduced by commit `c3b2df0a chore(audit): unignore databases for Perplexity audit visibility`.

**The finding:** Andrew confirmed these were **branch-only, for Perplexity to see substrate state, and were never meant for main.** Perplexity saw them on the branch (origin/review-layer) without them being merged — that worked and was low-risk. BUT they are still in the branch tree, so **if this branch merges as-is, they go to main**, which Andrew does not want.

**Why it matters even though Andrew wants the data public** (he does — see the separate public-research-data report): committing live *binary* `.db` files to git is the wrong mechanism even for public data — opaque (binary, not inspectable without SQLite tooling + schema knowledge), noisy (every substrate write changes the whole blob, so git history fills with gibberish diffs), and bloating (slows every clone). GitHub's own docs: "Git is not designed to handle large SQL files."

**The fix:**
1. Revert `c3b2df0a` (re-add the `.db` files to `.gitignore`); they're regenerable runtime state.
2. Replace the auditor-visibility need with the **snapshot exporter** spec'd in the separate `public_research_data_report.md` — public, readable, diffable text snapshots instead of live binary databases. That satisfies BOTH "make the research data public" AND "don't bloat main with binaries."

**Do not merge until the `.db` files are out of the branch.**

---

## MERGE BLOCKER 2 — split the branch

This branch is now a bundle: 11 commits, 29 files, two guardrail files, the structural_binding module, the Perplexity monitor-fixes, the goal-doorman, AND the `.db` commits.

**Recommendation: split it.** The good code (structural_binding + monitor-fixes + goal-doorman) should land on its own, separate from the `.db` commits. Bundling a permanent-data-exposure with good architecture is how the bad thing rides in on the good thing — decouple so the code merges clean and the `.db` commits get dropped (not merged).

Concretely: cherry-pick the code commits onto a fresh branch off main, leave `c3b2df0a` behind, re-confirm the patch-id (it'll change after the split — I'll re-bind), merge that.

---

## One follow-up rec (code side, non-blocking)

File the engagement_trail's named limitation as a real prereg: the gate currently only credits **post-citation** engagement (pre-cite engagement like "I notice you said X — yes" is DENY'd, taught as "put engagement after the citation"). The code comment promises "widen to bi-directional window in v2 if pre-cite engagement turns out to be common." Make that a dated prereg with a falsifier (e.g. "if N legitimate pre-citation-engagement responses get false-DENY'd, widen the window") so the v2-widen promise has teeth, not just a comment. Named-incomplete needs a falsifier to earn its credit (survey rule #4).

---

## Summary for the round

- **Code:** CONFIRM at `--stable 0266731330dc` / SHA `4000f607`. engagement_trail rev.3 (engagement-costume → honest binding, limitation named), goal-doorman (correct surface+backstop), monitor-fixes, 42 tests pass.
- **Merge:** HOLD until (1) the 14 `.db` files are stripped from the branch and (2) the branch is split so the code lands without the database commits.
- **Replacement for the .db auditor-visibility need:** the snapshot exporter in `public_research_data_report.md`.
- **Follow-up:** prereg the engagement_trail pre-citation-engagement limitation.

The architecture is good — this is the costume survey's findings becoming a reusable binding framework, which is the audit-findings-become-infrastructure pattern one level more abstract. It just shouldn't carry the live databases into main. Strip them, split it, and the code lands clean.
