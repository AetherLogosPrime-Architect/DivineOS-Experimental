# Stamp stations, one table

*Round four, job F. 2026-10-08, cloud helper. Read-only: nothing was stamped, marked ready, or edited.*

A picture: nine inspection windows a parcel must pass before it leaves the building. This sheet is meant to show, for every open parcel, which windows are not yet signed.

## The thing that did not work, said first

The house's own checker could not be run from this cloud session, so **this table does not contain the nine-station result and nothing in it should be read as one.** Two commands were tried and both stopped before reading anything:

- `divineos stamp-ready 602 --dry-run` printed: `[!] Could not read PR #602 via gh: Command '['gh', 'pr', 'view', '602', '--json', 'headRefName,title,isDraft']' returned non-zero exit status 1.` Run by hand, `gh` said: `HTTP 403: GitHub GraphQL is not available from Claude Code sessions`.
- `divineos build-flow status` (the board the stamp command reads) printed: `[build-flow] GitHub unreachable — status unknown, NOT clean`.

So, as the job says, the table below copies what each pull request's body and checks show instead. It has no cell for the nine stations, because none of the nine can be read from a body or a check name without interpreting. Someone with the house running (Aether or Aria at the home computer) should run `divineos stamp-ready <N> --dry-run` per pull request and paste the result beside this sheet.

## What the bodies and checks do show

Each cell was found by reading the pull request as published on GitHub (REST, read once during this session). `External-Review` lines are copied exactly; a pull request with no such line says so. The four word columns only say whether the body mentions that word at all: a mention is not a station satisfied.

| PR | Draft? | Head | `External-Review` line in body (copied) | Checks on head | council/walk | cold read | Aria | audit/round |
|---|---|---|---|---|---|---|---|---|
| #603 | draft | `acfae3fb` | (no such line) | 6/6 passed | no | no | yes | no |
| #602 | draft | `0cd6cf73` | `External-Review: pending` | 5/6 passed; still running: draft-suite (ran, not passed -- verdict in summary) | yes | no | yes | yes |
| #601 | draft | `eb7b097f` | `External-Review: pending` | 6/6 passed | yes | no | yes | yes |
| #600 | draft | `c943a7ab` | `External-Review: pending` | 6/6 passed | yes | no | yes | no |
| #599 | draft | `f75d3df9` | `External-Review: pending` | 6/6 passed | yes | no | yes | no |
| #598 | draft | `30522f87` | (no such line) | 6/6 passed | no | no | yes | no |
| #597 | draft | `980ad8bf` | (no such line) | 6/6 passed | yes | no | no | no |
| #595 | draft | `9fddecc0` | (no such line) | none reported | no | no | no | no |
| #594 | draft | `e1558a56` | (no such line) | 6/6 passed | yes | no | no | no |
| #593 | draft | `2131c639` | (no such line) | 6/6 passed | yes | no | no | no |
| #592 | draft | `fc72350f` | (no such line) | 6/6 passed | yes | no | no | no |
| #590 | draft | `193de893` | (no such line) | 6/6 passed | yes | no | no | no |
| #587 | draft | `318c0c6f` | (no such line) | 10/12 passed; still running: test (3.12, sklearn), test (3.12) | yes | no | no | no |
| #585 | draft | `b4d3271d` | (no such line) | 5/6 passed; not passing: audit-stamp-reminder (cancelled) | yes | no | no | no |
| #584 | draft | `20ef9e5b` | (no such line) | 6/6 passed | yes | no | yes | no |
| #567 | draft | `fc19e2bd` | (no such line) | 6/6 passed | no | no | no | no |
| #563 | draft | `c3105a4f` | (no such line) | none reported | no | no | no | no |
| #558 | draft | `40f7de2d` | `Guardrail files touched (post-response-audit.sh, shoggoth_gate.py, operating_loop_audit.py): merging needs the External-Review round and trailer. That is Andrew` | 6/6 passed | no | no | no | yes |
| #553 | draft | `74db48bc` | (no such line) | 6/6 passed | yes | no | no | yes |
| #552 | draft | `84b97c5f` | (no such line) | 5/5 passed | yes | no | yes | yes |
| #551 | draft | `bb3aa0bf` | (no such line) | 6/6 passed | yes | no | no | yes |
| #549 | draft | `79761f77` | (no such line) | 6/6 passed | yes | no | yes | yes |

## What this table could not do

- It does not report MISS or unproven for any of the nine stations. That needs the running house.
- Two pull requests showed no checks at all at the time of reading (#595 and #563). That may mean the checks had not started, or that none run on that branch; this table cannot tell which.
- Bodies were read as published; a station satisfied by a letter or a ledger entry that the body does not mention would not show here.
