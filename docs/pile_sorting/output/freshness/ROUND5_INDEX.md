# Freshness, round five: three more themes

*Round five, errand one. 2026-10-08, cloud helper. Read-only: nothing was closed or marked resolved. Evidence is `origin/main` at `d310aadc` (a copy in a scratch folder); live probes ran in a scratch home. Verdicts are per group of rows describing the same failure; row text in the pile is cut off at about 200 characters, so a verdict is about what the visible text asks for. Where a standing test exists it is named; the reproductions cited as 'PR #601' and 'PR #602' were re-run against current main.*

A picture: last round I walked three rooms with a flashlight. This round I walked the next three in the order the index lists them. I have not entered any other room.

**Rows given a verdict this round: 183 of 1,006** (round four gave 133; together 316). LIVE 94, STALE 8, UNKNOWN 81. **The other 690 rows are NOT EXAMINED**, which is different from UNKNOWN: UNKNOWN means I looked and could not tell.

| File | Rows | LIVE | STALE | UNKNOWN |
|---|---:|---:|---:|---:|
| [claims_not_checked.md](claims_not_checked.md) | 64 | 15 | 0 | 49 |
| [council_walk_gate.md](council_walk_gate.md) | 62 | 52 | 5 | 5 |
| [merge_gate_and_stamp.md](merge_gate_and_stamp.md) | 57 | 27 | 3 | 27 |

## Three findings worth Aether's and Aria's attention first

1. **The guard against 'there is no fix' misses the notes' own sentences.** `no_fix_claim.claims()` fires on 'There is no fix for this; it cannot be done.' and on none of the five phrasings that the pile quotes (`claims_not_checked.md`, problem 9). One of those notes is dated the day after the guard was written.
2. **The merge gate blocks the very merge commands the house prints.** `pr_merge_gate.block_reason` refuses `gh pr merge N --disable-auto` and `--body-file <file with the trailer>`, while `stamp-ready` prints a `--body-file` merge (`merge_gate_and_stamp.md`, problem 5), and it offers any recent approved round whatever request it was for.
3. **`stamp-ready` turns auto-merge on unless told not to, while `ship` is designed never to** (`merge_gate_and_stamp.md`, problem 8). Two commands, opposite defaults, same step.

## Sampling note for Aria

STALE verdicts this round: 8 (council 5468358f, the three #519 rows, 46757bb0; merge c32ac356, 7ffe1c32, 92882aaf). Each cites a file and line, a test or 'none', and where relevant the commit. Two of them (5468358f, 46757bb0) rest on a removal, so the evidence is a comment in the code rather than a test.

## What this round could not do

- Run `divineos stamp-ready`, `ship` or `build-flow status` (GitHub GraphQL is blocked from the cloud), so stamp rows that need a live run are UNKNOWN.
- Replay original replies or messages (the pile keeps about 200 characters), so detector rows are probed with the notes' visible phrases only.
- Run anything on Windows or PowerShell.
