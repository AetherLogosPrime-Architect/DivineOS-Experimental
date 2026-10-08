# Retire the routine that rewrites every commit to carry the review stamp

**Draft, 2026-10-07. The idea, not a plan.**

## What he said

Dad, 2026-10-07: "yes retire it", after I told him the routine goes back through every commit on a branch touching the special files, stamps each with a review note, rewrites history and force-sends it, and that his rule now is that only the cover at merge time carries the stamp. The house instruction (Hard Rule 8, his words 2026-08-19, said five times): "commits do not require an external trailer only merging to main." And 2026-08-13: "not every commit just every merge to main, committing is allowed in your own workspace without any audit."

## What exists

`core/push_ready.py` finds guardrail-touching commits on a branch that lack an `External-Review` trailer, opens an audit round, rewrites each commit's message with `git filter-branch`, files an aether self-CONFIRMS, and force-pushes with lease. `cli/push_ready_command.py` is its command. `cli/stamp_ready_command.py` calls it as one stage (lines about 1096 to 1280: a preflight, the amend, a verify-after, then the real work of writing the trailer into the PR body). The routine already has a safety check because rewriting over a newer server copy went wrong twice (2026-09-05).

## Why it is no longer needed, checked and not assumed

The thing that made it needed has moved. The CI check `scripts/ci_check_guardrail_trailer.sh`, run on pull requests, falls back to the pull request body when a commit carries no trailer, and its own comment says a trailer in the PR body "still covers the whole branch" (line 348). Its workflow comment (`integrity-audit.yml`) says the PR-body fallback is what made per-commit trailers unnecessary. The merge itself is checked on the squash-merge message, which GitHub builds from the PR title and body. So the commits can go unstamped and the branch still passes, and rewriting them is cost with no benefit: it changes every commit's hash, invalidates any review that named a hash, and needs a force-push.

## What I confirmed after the council walk, by reading and not assuming

`scripts/ci_check_guardrail_trailer.sh` lines 380 to 387: for each commit that needs review, if its own message has no trailer, the check reads the trailer from the PR body, prints "trailer absent from the commit message; read from the PR body instead", and passes. Lines 457 to 476 pass a PR-body trailer with a note that tree-hash binding does not apply on that path. Lines 340 to 349 say the per-commit trailer requirement "was removed on 2026-08-13 for being unmeetable after a force-push". `one_command_from_confirm_to_main_draft_2026-10-02.md` says the same from the other side: the ruleset's `multi-party-review` "reads per-commit trailers or the PR body". So an unstamped branch with a stamped body clears the check, and the rewrite buys nothing.

Two more things only the reading showed. `_commits_behind_base`, `_worktrees_holding` and `_BASE_BRANCH` in `stamp_ready_command.py` exist only to guard the rewrite ("stamping rewrites history, so an unreadable check is treated as unsafe"); with no rewrite they have no caller, so they go, and so do the two test files that exist only to pin them (`test_stamp_ready_preflight.py`, `test_stamp_ready_measures_the_pr_branch.py`). A side effect to say out loud: the same earlier draft records `stamp-ready` refusing a stamp "because the branch was behind main", which is that check; with it gone, stamping no longer refuses on that, and a branch that is behind main meets GitHub's own rule at merge instead. And `divineos push-ready` is a separate command over the same module, so it goes too.

## The shape

1. `stamp-ready` stops calling the amend. It keeps what it is for: writing the trailer into the PR body, marking the PR ready, and the preflight that checks the round. Only the amend stage and its after-the-fact verify come out.
2. `push_ready.py` and its command are retired: moved to `archive/superseded/` with a row in the ledger saying what it did and why it went, the CLI registration removed. The "why" lives in `docs/retired_rules/` as a new entry, so the guard that stops retired rules being served can name it.
3. Tests that exist only to pin the routine's behaviour (`test_push_ready*.py`, `test_amend_stamps_the_branch_it_was_handed.py`, `test_the_stamp_selection_matches_full_hashes.py`) go with it, archived; `test_stamp_ready_preflight.py` keeps what is about the preflight.
4. Everything that points at the routine is updated or removed: `pr_merge_gate.py` (one mention), `gh-pr-ready-gate.sh`, `guardrail_files.txt` (two lines), `retired_rules_baseline.txt` (two lines, which shrink).

## What it will not see, and what is left for others

The commit-time message printed by `check_multi_party_review.py` ("it requires a multi-party review before it can be recorded") is a separate site and the question is Aria's and mine together; I think it becomes a one-line pointer to the merge. The five wording sites are Aria's. The `pr_gate` "every PR starts as a draft" change is hers and Dad has said yes in plain words.

If anything outside this tree still calls the routine (a script, a hook in another checkout, a branch not yet merged), it breaks when the module goes. A grep of this tree found only the files above; other open branches may carry callers I cannot see, and #585 and Aria's branches touch neighbouring files.

## Cost

Several files touched and a few archived, none rewritten blind. The reason to do it as one piece is that half of it would leave a command with no module behind it, or a module nothing reaches.
