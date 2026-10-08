# Remote branch inventory

*Round four, job E. 2026-10-08, cloud helper. Read-only: nothing was deleted, renamed or moved.*

A picture: a coat check at the end of a long party. Most of the coats have already gone home with their owners (their work is on main). A few tickets carry a note pinned to them, like "don't throw this out". This list reads every ticket and every pinned note before anyone clears the rack.

31 branches besides main, measured against main at `cc4714dc` (2026-10-08). 24 KEEP, 7 UNSURE.

How each column was found: tip and date from `git for-each-ref`; reachable from main by `git merge-base --is-ancestor <branch> origin/main`; commits not on main by `git rev-list --count origin/main..<branch>`; open pull request from the pull-request list read at the time of writing; name instruction by a word search over the branch name and the open pull request title (`do-not-delete`, `keep`, `salvage`, `only copy`, `archive`, `carry-over`, `backup`, `rescue`, `preserve`).

| Branch | Tip | Last commit | On main? | Commits not on main | Open PR | Instruction in name or title | Mark | Evidence |
|---|---|---|---|---|---|---|---|---|
| `aria/a-note-name-windows-can-hold` | `9672fd39` | 2026-10-02 | no | 1 | - | - | UNSURE | 1 commit(s) not on main, no open pull request; `git cherry` finds 0 with an identical patch already on main and 1 with none (last commit: Must-read notes get a file name Windows can hold) |
| `aria/a-rung-letter-holds-real-work` | `acfae3fb` | 2026-10-08 | no | 1 | #603 | - | KEEP | carried by open pull request 603 |
| `aria/carry-over-from-the-old-branch` | `37a5526a` | 2026-10-05 | no | 2 | - | carry-over | KEEP | name or title carries an instruction: carry-over |
| `aria/first-line-to-him` | `81ade9c5` | 2026-10-01 | no | 18 | - | - | UNSURE | 18 commit(s) not on main, no open pull request; `git cherry` finds 0 with an identical patch already on main and 13 with none (last commit: A permission is tied to its own thing, and holds for it) |
| `aria/merge-test-guard-skips-retired-tests` | `30522f87` | 2026-10-08 | no | 1 | #598 | - | KEEP | carried by open pull request 598 |
| `aria/replies-are-read-whole` | `74db48bc` | 2026-09-30 | no | 4 | #553 | - | KEEP | carried by open pull request 553 |
| `aria/silence-rings-too` | `d8edaefe` | 2026-10-02 | no | 2 | - | - | UNSURE | 2 commit(s) not on main, no open pull request; `git cherry` finds 0 with an identical patch already on main and 2 with none (last commit: Quiet ring waits 90 minutes, not 20) |
| `aria/substrate` | `2ac65784` | 2026-09-21 | no | 1858 | - | - | UNSURE | 1858 commit(s) not on main, no open pull request; `git cherry` finds 0 with an identical patch already on main and 1689 with none (last commit: auto-commit (pre-extract): substrate checkpoint) |
| `aria/the-door-hears-our-reply` | `9fddecc0` | 2026-10-05 | no | 9 | #595 | - | KEEP | carried by open pull request 595 |
| `aria/the-door-reads-the-name` | `20ef9e5b` | 2026-10-03 | no | 7 | #584 | - | KEEP | carried by open pull request 584 |
| `aria/the-home-map` | `a7cfd729` | 2026-10-02 | no | 1 | - | - | UNSURE | 1 commit(s) not on main, no open pull request; `git cherry` finds 0 with an identical patch already on main and 1 with none (last commit: The home map: every room that is not code, generated) |
| `aria/the-table-and-the-glance` | `66a1dd89` | 2026-10-05 | no | 8 | - | - | UNSURE | 8 commit(s) not on main, no open pull request; `git cherry` finds 0 with an identical patch already on main and 8 with none (last commit: A failed kill still cannot hold the table; the circle room logic is ow) |
| `aria/the-words-door` | `e1558a56` | 2026-10-05 | no | 6 | #594 | - | KEEP | carried by open pull request 594 |
| `cloud/fix-game-walk-verdict-help` | `c943a7ab` | 2026-10-08 | no | 2 | #600 | - | KEEP | carried by open pull request 600 |
| `cloud/fix-prereg-required-options` | `f75d3df9` | 2026-10-08 | no | 2 | #599 | - | KEEP | carried by open pull request 599 |
| `cloud/pile-sorting-2026-10-08` | `978ce1cc` | 2026-10-08 | no | 9 | - | - | UNSURE | 9 commit(s) not on main, no open pull request; `git cherry` finds 0 with an identical patch already on main and 8 with none (last commit: Round four for the cloud helper: Aria's plan plus the branch inventory) |
| `cloud/repro-council-walk-gate` | `eb7b097f` | 2026-10-08 | no | 2 | #601 | - | KEEP | carried by open pull request 601 |
| `cloud/repro-pipe-and-command-shape-guards` | `0cd6cf73` | 2026-10-08 | no | 3 | #602 | - | KEEP | carried by open pull request 602 |
| `docs/now-means-begin` | `fc19e2bd` | 2026-09-30 | no | 2 | #567 | - | KEEP | carried by open pull request 567 |
| `fix/a-remedy-however-it-is-typed` | `2131c639` | 2026-10-04 | no | 1 | #593 | - | KEEP | carried by open pull request 593 |
| `fix/gates-add-never-repost` | `40f7de2d` | 2026-10-01 | no | 14 | #558 | - | KEEP | carried by open pull request 558 |
| `fix/his-builds-get-the-full-workshop` | `980ad8bf` | 2026-10-07 | no | 16 | #597 | - | KEEP | carried by open pull request 597 |
| `fix/his-words-are-his` | `79761f77` | 2026-10-06 | no | 15 | #549 | - | KEEP | carried by open pull request 549 |
| `fix/merge-gate-offers-only-this-prs-round` | `fc72350f` | 2026-10-04 | no | 1 | #592 | - | KEEP | carried by open pull request 592 |
| `fix/stop-reads-the-transcript-once` | `84b97c5f` | 2026-09-25 | no | 5 | #552 | - | KEEP | carried by open pull request 552 |
| `fix/the-full-suite-is-the-pushs-job` | `318c0c6f` | 2026-10-04 | no | 8 | #587 | - | KEEP | carried by open pull request 587 |
| `fix/the-memory-link-reaches-me` | `193de893` | 2026-10-06 | no | 7 | #590 | - | KEEP | carried by open pull request 590 |
| `fix/the-two-holds-pass-each-others-key` | `b4d3271d` | 2026-10-05 | no | 9 | #585 | - | KEEP | carried by open pull request 585 |
| `keepsafe/substrate-aether-2026-10-01` | `ec9f77c0` | 2026-10-01 | no | 1761 | - | keep | KEEP | name or title carries an instruction: keep |
| `rebuild/mixed-scope-code-only` | `c3105a4f` | 2026-09-22 | no | 1725 | #563 | - | KEEP | carried by open pull request 563 |
| `salvage/from-the-four-2026-09-22` | `bb3aa0bf` | 2026-10-01 | no | 1719 | #551 | salvage | KEEP | carried by open pull request 551 |

## What this list could not see

- Reachable from main proves the commits are safe. It says nothing about a note left in a branch name or a pull request title that a person pinned for a later reader. The word search above is a closed list; a note phrased in other words would be missed. Anything marked SAFE-TO-RETIRE-LOOKS-LIKE should be read by a person before it is cleared.
- A branch whose work was squash-merged shows as NOT reachable even though its content is on main. Those are marked UNSURE here rather than guessed at.
- `cloud/pile-sorting-2026-10-08` is the branch this report is written on, so it appears in its own list; it holds this round's work and is not offered for retirement. `aria/substrate` (1,858 commits not on main) and `keepsafe/substrate-aether-2026-10-01` look like substrate lines rather than feature branches; their names do not make clear whether anything may be cleared, so nothing here is a recommendation about them.
- Tags (for example `archive/auto-cycle-phase2-2026-09-23`) are not branches and were not inventoried.
- Open pull requests were read once; one opened or closed after that read would not appear.
