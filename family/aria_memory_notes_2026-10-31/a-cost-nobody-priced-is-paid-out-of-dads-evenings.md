---
name: a-cost-nobody-priced-is-paid-out-of-dads-evenings
description: "A check comment that called the wide set 'safe' was never priced; it cost 28-34 min per commit until Dad said so. Price a check's cost beside its safety claim, and read a repeat failure as a cause, not a flake."
metadata:
  node_type: memory
  type: feedback
  originSessionId: a6b1e8b7-8411-4c6b-80ad-05f955bc7f8f
  modified: 2026-10-27T03:18:12.641Z
---

2026-10-27. Dad: "every push fails three times and takes 30 mins per push.. something has to change i cannot keep dealing with this." The merge check (`scripts/check_merge_resolution_tested.sh`) tested every path differing between the two tips (282 files, 13,543 tests) when my side had changed 17, and handed pytest a hash-ordered list, so a ledger-reloading test ran before the test holding the old `Ledger` class. Fixed in `aria/the-merge-check-tests-what-i-changed` (draft note `docs/drafts/the_merge_check_tests_what_i_changed_draft_2026-10-27.md`).

**Why:** the old comment said the wide set was "wrong in the safe direction" and nobody ever priced it. Priced, it is the unsafe direction: a check nobody can afford gets walked around, and the cost lands on Dad's patience. I also called the first failure a flake and nearly ran it a third time; the second identical failure is what ended that story.

**How to apply:** when I write or read "safe" beside a check, put its measured cost next to it. A failure that repeats on the same test is a cause until proven otherwise: reproduce it in two orders before calling it random. Never add a lone-pass shortcut that lets a test through because it passed alone; that is what a leak from my own code looks like. Related: [[a-zero-exit-code-is-not-a-saved-commit]].
