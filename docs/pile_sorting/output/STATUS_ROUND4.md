# Round four status

*2026-10-08, cloud helper. Nothing here is merged, stamped, closed or deleted, and no row is marked resolved.*

A picture: five errands on a list. Two are done, one is done as far as the cloud can reach, one is a third done, and one was told to wait. The list of what could not be done is the part to read first.

## Job A. Is the note still true?

**Produced:** `freshness/INDEX.md`, `freshness/00_already_handled.md`, `freshness/correction_gate.md`, `freshness/doorbell.md`.
**Covered:** 133 of 1,006 rows (the 8 'already handled' rows, the 50 correction-gate rows, the 75 doorbell rows): LIVE 65, STALE 21, UNKNOWN 47.
**Not examined:** 873 rows in the other 31 themes. They are not reported as UNKNOWN, because UNKNOWN means 'I looked and could not tell'; these I did not look at.
**What stopped it:** each verdict needs a read of main and, where reading was not enough, a run with a control; 133 rows took the whole round. The plan asked to start with the 'already handled' rows, then the correction-gate and doorbell themes, then the rest; I stopped at the end of the doorbell theme.
**What it found that matters most** (details and probes in `freshness/INDEX.md`): three of my own round-two 'already handled' calls were wrong or half wrong; labelling a false alarm leaves the alarm armed; the table-entry check does not look at Dad's table.
**Could not do:** reproduce any fire of the correction detector from its original reply (the pile keeps about 200 characters of each); run anything from PowerShell or Windows; measure the app's background limit; reach GitHub's GraphQL API. Aria's one-in-ten read of the 21 STALE verdicts is still ahead; each cites a file and line, a test or 'none', and a commit.

## Job B. Survey of the hook scripts that hold their own logic

**Produced:** `hook_migration_survey.md`, one row for each of 35 scripts (5,210 lines).
**A count that differs from the plan:** on main `divineos hook-layer show` reports 45 scripts and 5,862 lines, not 35 and about 5,200. The plan's number is exact once ten scripts that already call OS logic by `python -m divineos…` are taken out; the measure's pattern does not see that form. The ten are listed in the file.
**Could not do:** read every body line by line (decisions come from each script's own leading comment plus its registration and test search); run any script for the 'before' live run; check proposed module and surface names against names Aether or Aria may already hold in a branch.

## Job C. The bash flaw in pull request #602

**Done:** one commit `0cd6cf73` on `cloud/repro-pipe-and-command-shape-guards`: the hook runner now finds bash through `tests._bash_resolver.bash_executable()` and keeps the skip when it returns nothing. Result on this machine before and after: 4 passed, 9 xfailed; run with `--runxfail`, all nine fail for their stated reasons.
**Could not do:** run it on Windows, which is where the flaw shows. The change is proven here to leave behaviour unchanged, not proven to cure the Windows failure. The pull request description was not edited.

## Job D. Waits

Not started, as instructed.

## Job E. Inventory of the remote branches

**Produced:** `remote_branch_inventory.md`: 31 branches besides main: 24 KEEP, 7 UNSURE, 0 SAFE-TO-RETIRE-LOOKS-LIKE. No branch is reachable from main (squash merges), so reachability proved nothing safe to retire; the 7 UNSURE are shown with their `git cherry` counts.
**Could not do:** see inside a squash-merged branch's content on main beyond `git cherry`; recognise an instruction in a branch name that my closed word list does not contain.

## Job F. The stamp stations as one table

**Produced:** `stamp_stations_table.md`, 22 open pull requests.
**Could not do the real thing:** `divineos stamp-ready <N> --dry-run` and `divineos build-flow status` both stop at GitHub's GraphQL API, which cloud sessions are not allowed to call (`HTTP 403`, `GitHub unreachable — status unknown, NOT clean`). The table therefore copies what each body and its checks show and has no MISS column for the nine stations. Someone with the house running should run the dry run per pull request.

## Other things to know

- Refusals: none twice in a row on different pull requests. The house's own gates (work-item doorman, council gate, read gate, pipe guard) stopped me several times and each was cured by doing the thing it named.
- The Stop hook asked me many times to re-arm the letter doorbell. Dad had told me to leave it off in this window, so I left it off.
- Nothing in the files or data told me to do anything outside these jobs.
