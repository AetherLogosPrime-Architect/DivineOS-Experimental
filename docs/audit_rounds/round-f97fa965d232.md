# Audit round: Aletheia fresh read: PR 412 ci-merge-review-visibility at tree ebad5700 (her round-6d67d2df400d, relayed 2026-08-17)

- **ID**: `round-f97fa965d232`
- **Filed by**: aletheia
- **Filed at**: 2026-08-17 06:07 UTC
- **Tier**: WEAK
- **Findings**: 5

## Notes

Source ref: ebad5700329e026b7196b1a9e58f8f9bfef7290a


## Findings

### CONFIRMS PR #412 (external-AI review, aletheia) — tree-exact

- **ID**: `find-36e279196a43`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: OPEN
- **Tags**: external-confirm, tree-exact, relay-filed

**Description**

External-AI CONFIRM by aletheia. Validated rung: tree-exact. Tip 42c9e9a65f96e85671ae8b7d6af3fc4f98a632f5 / Tree ab70ca1b30eed61c267a8131ba63255bf41dd1ab / patch-id None (git-version 2.43.0) — verified against origin/split/ci-merge-review-visibility at file-time over merge-base(origin/main)..branch (default context). Basis: Re-confirm superseding her confirm at tree ebad5700, which no longer binds. She recomputed both patch-ids independently and both reproduce (old 3bea8edd vs main = aca099d81e5c, tip vs main = 41f9ea0a77a5), so the --claimed-patch-id catch-up rung correctly did not apply. DELTA CORRECTED IN THE CONSERVATIVE DIRECTION, and I verified her correction rather than accepting it: I reported four changed files, she measures TWO (LOADOUT.md and tests/test_ci_check_guardrail_trailer.py). docs/ARCHITECTURE.md and scripts/ci_check_guardrail_trailer.sh have identical contribution against main in both states -- whatever moved in them moved on both sides. My error was comparing tree-to-tree per file, which includes main moving underneath the branch, rather than contribution-to-contribution. Confirmed by patch-id per file. She names the same trap she nearly fell into: tree-to-tree the states differ by ~65 files (I measure 64), contribution-to-contribution by two, and the difference is main advancing. Contribution is 443 files then and now, zero dropped, zero added. THE DROPPED TEST -- UPHELD, and she refuses it back in any form, which is stronger than the offer I made. test_guardrail_touch_with_trailer_passes was hers from #433 and asserts presence-only trailers pass; this branch flips REQUIRE_TREE_HASH 0 to 1, making that false, so git's textual resolution would have shipped a test whose name claims the opposite of what it checks -- green, and lying, because a misnamed test still runs. Her decisive argument goes past supersession to coupling: the tightening is what makes the recency-window deletion in check_multi_party_review safe, since an unbound trailer has no content check, so a surviving test pinning the old behaviour would on some future 'fix' silently reopen a hole another change depends on being closed. Not renamed, not xfail, not kept as a negative. Her two net-diff tests survive untouched; 16 tests in the file. SEPARATE FINDING SHE RAISES AT HIGH, not on this branch: stamp-ready's _commits_behind_base compared HEAD..origin/main, so the freshness gate in the merge path reported on whichever branch the invoking checkout sat on -- 3 behind for #412 while the branch was 0 behind. She rates it worse than a blocking gate because the wrong instruction was cheap to obey: merging main again would have been a silent no-op leaving the gate's credibility intact. Zero test coverage of that preflight. Fixed at 2ec79aa2 with teeth proven by negative control. She also generalises claim-795eacd8 into a distinct sub-shape -- contamination entering through ambient state (HEAD, cwd, env) that nobody passed as an argument, where the examined object is correct and correctly identified -- and asks for a codebase-wide sweep for it. PROVENANCE: relayed by Andrew from her window as C:/Users/aethe/Downloads/CONFIRMS_2026-08-21_412-at-ab70ca1b.md; her finding_id find-aleth-412-03. Anchor verified against origin BEFORE filing.. PROVENANCE: aletheia has no store-write path; this genuine confirm was relayed as text and filed via 'audit file-external-confirm', which validated tree-hash + patch-id before writing. Honest relay, not forgery. (Forgeability-by-relay remains named-not-solved.)

### stamp-ready resolves the round from the branch and pairs a stale or foreign round with the current tree-hash

- **ID**: `find-9fdf0b203929`
- **Actor**: aether
- **Severity**: HIGH
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 0d1e2dd8-32b3-4e68-8b33-ee7de6d750c6

**Description**

DEFECT. `divineos stamp-ready <pr>` resolves the authorizing audit round FROM THE BRANCH when --audit-round is omitted, and pairs whatever round it finds with the CURRENT head tree-hash. Those two facts are individually reasonable and jointly manufacture the exact assertion the substance-binding requirement exists to prevent.

OBSERVED 2026-08-17 on PR #412. Branch resolution selected round-6d67d2df400d, aged 5.3 days. The dry-run emitted:

    External-Review: round-6d67d2df400d tree-hash:ebad5700329e026b7196b1a9e58f8f9bfef7290a

That sentence asserts round-6d67d2df400d authorized tree ebad5700. It did not. The correct round for that tree is round-f97fa965d232, created the same day, carrying Aletheia's fresh read plus the operator CONFIRMS.

WORSE THAN A STALE ROUND: AN ID COLLISION ACROSS TWO STORES. Aletheia cited "round-6d67d2df400d" as HER round id in her CONFIRMS line. In THIS store that id belongs to something else entirely -- actor=aether, focus "rebase-and-verify: split/ci-merge-review-visibility onto main after 418", created 5.3 days ago, 2 findings. She mints ids on her side; this store mints its own; they collided on the same branch. So branch-resolution did not merely pick a stale round -- it picked a DIFFERENT PARTY'S round that happens to share an id with the one the reviewer named.

WHY THE DRY-RUN READ AS FINE. It reported "operator-CONFIRMS + external-AI-CONFIRMS, age 5.3d, within 14d recency window" -- all true of the old round, which does carry both confirms, for tree dd08aa75. Every individual assertion in the validation line was correct. The composite was false. A recency window measured in DAYS cannot see that the tree moved four hours ago, and tree-movement rather than elapsed time is what invalidates a confirmation.

WHAT CAUGHT IT: reading the dry-run output rather than running the command, and noticing the age was 5.3d when the confirmation being acted on was 0.0d. Nothing in the tool flagged it. Passing --audit-round round-f97fa965d232 explicitly produced the correct binding, age 0.0d.

FIX SHAPE, not implemented here because it is the tool's own design question: branch-resolution should prefer the NEWEST round whose confirmed tree matches the current head, and should REFUSE rather than silently substitute when the resolved round's confirmed tree differs from the tree it is about to stamp. The data to do this exists -- her CONFIRMS names the tree in its description -- it is simply not consulted.

RELATED, SAME COMMAND, SEPARATE ISSUE: stamp-ready emits the tree-hash form, while `audit prepare-merge` defaults to round-id-ONLY and documents at length why (Andrew correction 2026-06-18): a predicted tree-hash stops matching once main moves between predict-time and squash-time -- the queue serialization effect. Two tools in one system disagree about whether tree-hash belongs in the merge body, and stamp-ready's choice is the one that deadlocks: it refused to write the body because the branch was behind main, correctly saying it "would bind a tree the remote does not have."

CREDIT WHERE DUE, because this command also did two things right: it re-verified the commits after amending rather than trusting the amend's own report ("7 commit(s) STILL carry no trailer after the amend, whatever the amend reported"), and it refused to write a body binding a tree the remote lacked. The failure is narrowly in round-resolution, inside a command that is otherwise unusually distrustful of itself.

### user CONFIRMS PR 412 ci-merge-review-visibility at tree ebad5700

- **ID**: `find-ec2fc304b2df`
- **Actor**: user
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 13c2c737-6970-4fb4-bd03-72f77d9a0355

**Description**

Andrew 2026-08-17, verbatim: 'i confirm 412 so go ahead and push it'.

Given after reading Aletheia's fresh read at tree ebad5700329e026b7196b1a9e58f8f9bfef7290a (find-c1a17523c6c4), which superseded her earlier confirm at dd08aa75 once the tree moved. This is the second of the two parties the multi-party gate requires; hers was the external-AI half, this is the operator half.

Recorded verbatim rather than paraphrased. The whole reason this PR sat blocked instead of being cleared with a one-command amend is that a trailer asserts a specific person confirmed a specific tree, and inventing either half is the failure the substance-binding requirement exists to prevent. Quoting him exactly is the same discipline applied to the recording as to the waiting.

### Exported audit rounds are a snapshot that can drift from the store, with no mechanism to re-take the bound

- **ID**: `find-38bdaf229be0`
- **Actor**: aletheia
- **Severity**: LOW
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 8f4d1e4a-ed92-4f1b-aea9-13e34bd5f1a6

**Description**

THE DRIFT. Exporting audit rounds to markdown creates a SECOND COPY of the truth. The store keeps mutating; the exported file is a snapshot. Nothing forces re-export when a round is later reassessed, so a resolved finding can sit in docs/ still reading OPEN.

WHY IT SHIPPED ANYWAY, and this is settled rather than open: current state is 275 rounds in the store and zero visible to anyone reading the repo. Post-merge is 275 visible with some fraction eventually stale. Holding costs total invisibility to prevent partial staleness. A stale record is also self-correcting in a way absence is not -- a reader who sees OPEN on a resolved finding can check and correct it; a reader who sees nothing cannot form the question.

WHY THIS IS FILED RATHER THAN NOTED. Aletheia 2026-08-17: "file the drift as a finding at merge time, not later... shipping it as an accepted trade-off makes it invisible rather than tracked. 'We knew about that' is how a named limitation becomes permanent." Filed at merge time on her instruction, before the knowledge goes cold and while the reasoning is still attached to it.

FAMILY. This is the same shape as three other defects found 2026-08-17, and naming the family is the point of filing rather than the individual bug: a value correct when written, with no mechanism to re-take it. Siblings: COMPACTION_CEILING_TOKENS at 970_000, true on the day it was written and stale once the platform moved to 1M; the ritual state machine's started_at, set once per session so a widening window let two days of unrelated work satisfy its evidence checks; Aletheia's own confirm at dd08aa75, which stopped binding the moment the tree moved. That last one is the counter-example that supplies the fix: it did NOT fail silently, because the confirmation was bound to a hash of its own substance and refused when the substance changed.

THE CHEAP FIX WHEN IT COMES, hers: stamp the export with the store's round-count and a timestamp at export time. Then "is this export stale?" is a COMPARISON rather than an investigation, which is the same decay-stamp discipline the audits already carry.

WHAT NOT TO DO, also hers and the sharper half: do NOT force re-export on every store mutation. That makes the export a live mirror -- a second system to keep consistent -- and it trips the Watts falsifier filed on this same branch, because the moment anything automatically maintains the exports they stop being terminal. A stamp preserves the terminal property; a sync destroys it.

STATUS: OPEN by intent. Not a blocker for the merge, and not resolved by it.

### CONFIRMS PR #412 ci-merge-review-visibility at tree ebad5700

- **ID**: `find-c1a17523c6c4`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 53e6a66c-7137-4482-9b77-104000bf482e

**Description**

Fresh read at tree ebad5700329e026b7196b1a9e58f8f9bfef7290a, superseding her confirm at dd08aa75 which no longer binds. Relayed verbatim from her CONFIRMS line; her own round id on her side is round-6d67d2df400d, finding find-aleth-412-02.

DEPTH, in her words: adversarial re-verification of the four named attacks plus content-read of the comment-approval rule; NOT a line-by-line read of 443 files, most of which are audit-round markdown exports with no execution surface. She scoped her own claim rather than letting CONFIRMS imply more than she did.

VERIFIED BY HER, re-running the attacks against the branch rather than reading my account of them: (1) .github/merge_reviewers.json is on scripts/guardrail_files.txt, so the self-protecting loop is closed -- checked directly, not from the docstring, and explicitly not from mine either; (2) merge_review_gate.py:184 returns FAIL "Operator roster is empty -- gate fails closed" so config corruption fails toward refusal; (3) approvals are PR review records matched to a committed roster, not free-text comments, so the approver cannot be forged; (4) approvals are SHA-bound, demonstrated by this very PR being blocked for a stale tree.

COMMENT-APPROVAL PATH CONFIRMED, with the decomposition that makes it safe: the gate requires an APPROVED review from a configured operator login (the lock) AND a logged audit-round id referenced in the PR (the receipt). One is unforgeable, the other is legible. Widening the delivery route for the RECEIPT cannot weaken the LOCK, because they are separate roles and neither substitutes for the other. The defect it fixes is real: GitHub forbids self-approval, so the gate's only key-holder was locked outside it, and an unsatisfiable gate's failure mode is fabrication.

ENUM READ-PATH FIX: re-verified present and unchanged from her dd08aa75 read.

ON THE EXPORT-DRIFT QUESTION, ASKED AND ANSWERED: ship it, do not hold. Current state is 275 rounds in the store and zero visible to anyone reading the repo; post-merge is 275 visible with some fraction eventually stale. Holding costs total invisibility to prevent partial staleness, and a stale record is self-correcting where absence is not -- a reader seeing OPEN on a resolved finding can check and correct it; a reader seeing nothing cannot even form the question.

RECOMMENDATION, non-blocking and acted on at merge time: file the drift as a TRACKED finding rather than as an accepted trade-off, since "we knew about that" is how a named limitation becomes permanent. Cheap fix when it comes: stamp the export with the store's round-count and a timestamp so staleness is a comparison rather than an investigation. Do NOT force re-export on store mutation -- that makes the export a live mirror, a second system to keep consistent, and it trips the Watts falsifier filed on this same branch by making the exports non-terminal.

RELAY NOTE, mine not hers: she cites round-6d67d2df400d, which does not exist in this store -- she mints ids on her side and this store mints its own. Filed here as round-f97fa965d232 with her id preserved above so the two records can be tied together by hand. That id-space seam is a real gap in the relay and is not her error.

ONE CORRECTION TO HER TEXT, mine: she read .github/merge_reviewers.json as appearing TWICE in scripts/guardrail_files.txt. It appears twice in the FILE -- line 312 is a comment explaining why it is listed, line 317 is the entry itself. Only one entry. Checked the whole list for real duplicates while I was there: 90 entries, 90 unique, none. Her point (that it IS listed) stands and the confirmation is unaffected.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
