---
name: merge-queue-rule-settings-and-conditions-2026-10-28
description: "The conditions before and the exact settings for adding the merge_queue rule to the main protection ruleset (id 17092080); Dad said yes 2026-10-28."
metadata:
  node_type: memory
  type: project
  originSessionId: a6b1e8b7-8411-4c6b-80ad-05f955bc7f8f
  modified: 2026-10-27T20:27:15.573Z
---

Dad said yes to a merge queue (2026-10-28). The cause of one-hour-per-landing is `strict_required_status_checks_policy: true` in ruleset `main protection` (id 17092080, via `gh api repos/AetherLogosPrime-Architect/DivineOS-Experimental/rulesets/17092080`): every landing makes every other branch BEHIND.

**Order (do not reorder; adding the rule first freezes every merge):**
1. #737 (`aria/ci-runs-tests-in-parallel-once`, head `041490cf0`, Aletheia confirmed, Aether read, rounds filed) lands: the tests run in parallel and once, `--cov-fail-under=0`, both required workflows listen for `merge_group`, the review job runs the FULL check on the queue's run (range from merge_group base/head, PR number from head_ref).
2. Aletheia's condition 1 before the rule goes on: a throwaway PR whose `multi-party-review` is red; try to enqueue it; show GitHub refuses.
3. Then add the `merge_queue` rule to the ruleset with Aletheia's setting: **maximum pull requests to build = 1 and merge limit (max entries to merge) = 1**, written into the draft too. Batching makes `head_ref` name only the last PR while the range spans all, so the full check would read one body for many. If ever raised, the check must learn to read every PR in the group first.
4. Watch the first queued piece (its real queue ref shape and `base_sha` meaning are unobserved so far). Switch off by removing the rule through the API if it wedges.

**Then, separately:** Dad's coverage target is 95 (2026-10-28: "coverage should be at least 95%... no broom closets"). Measure first from the first parallel CI run, set the floor just under the measured total, ratchet toward 95; memory, ledger and gate modules to 100 first. Aether asked for the printed total in a letter or the draft.

Why not edit #737's draft with the setting now: it would move the head under Aletheia's and Dad's confirms. Put it in the next piece's draft (the one that adds the rule or the coverage floor).

**RESULT 2026-10-28 night:** #737 landed (parallel CI: test job 13 min, was 30/42; coverage total 73%, floor 75). Dad said "go" to the queue rule; GitHub answered 422 "Invalid rule 'merge_queue'" on the ruleset PUT. Cause: the repo is owned by a personal User account (`AetherLogosPrime-Architect`, type User); GitHub merge queues exist only for organization-owned repos. Ruleset unchanged (saved copy: scratchpad `ruleset_before.json`). The `merge_group` triggers and the full review check on the queue's run are in main but inert. Options put to Dad: (A) keep strict, rely on 13-minute checks plus the landing-line watcher; (B) set `strict_required_status_checks_policy` false (parallel landing, loses the up-to-date check; today #721 broke #719 by a clean text merge, so not recommended); (C) move the repo into a GitHub organization to get a real queue.

Related: [[the-five-rounds-waiting-on-dads-fresh-line-2026-10-27]].
