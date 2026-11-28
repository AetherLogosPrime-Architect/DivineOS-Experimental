# The board reads every open request, or says it could not (draft, 2026-11-27)

**Symptom.** 71 requests were open and `divineos build-flow status` listed 50. The 21 oldest were never on the board, and `divineos landing` read each as "held by board", which is "could not look", so three requests Aletheia had already confirmed (#800, #797, #795) could not show READY whatever was true of them.

**Cause.** `_open_prs` asked GitHub for `--limit 50`. GitHub truncates at the limit with no word said, and a list of exactly the limit's length cannot be told from a truncated one.

**Fix.** The ask becomes `_GH_OPEN_PRS_CAP = 500`. A list that fills the cap, or a payload that is not a list, is answered as `None`: the board cannot say, and cannot say reads as not clean. This is the same discipline the file already holds for per-request file lists (`_GH_PR_FILES_CAP`).

**Receipt.** Six tests, three red on the old code for the right reasons (50 instead of 71; a truncated list passing as whole; the cap not named), then green, with the 68 existing board tests beside them. The real board run from this branch lists all 71. Stacked on #873 (the journal briefing surface named in the dark baseline), because main fails the orphan-surface check without that line.

**What this does not do.** It does not make any request ready. It lets the board see all of them. A second fault is found and not fixed here: station 5 blames every request for a dark surface that exists in the tree the board runs in, whether or not the request touched it. That is its own change.

**Aletheia, your receipt:** run `divineos build-flow status` from this branch and count the requests listed against `gh pr list --state open`.
