# Freshness, round eight: three more themes

*Round eight, errand one. 2026-10-08, cloud helper. Read-only: nothing was closed or marked resolved. Evidence is `origin/main` at `cbd35baf` (the working copy or a scratch copy of it); live probes ran in a scratch home with controls. Verdicts are per group of rows describing the same failure; row text in the pile is cut off at about 200 characters. **NOT TESTABLE** means the note is a habit, an incident record or a lesson that no run can check; it is not the same as UNKNOWN (I looked and could not tell) or NOT EXAMINED (I did not look at that row this round).*

A picture: three more rooms. Two of them are about machinery with parts I could pick up and test; the third, the goal badge, I could feel from the inside because I used it all day.

**Rows given a verdict this round: 62 of 1,006** (rounds four to seven gave 133, 183, 37 and 81; together 496). LIVE 27, STALE 16, UNKNOWN 8, NOT TESTABLE 11. **In these three files I opened and did not examine 33 rows.** Altogether 510 of 1,006 rows are NOT EXAMINED (rows I never looked at).

| File | Rows | LIVE | STALE | UNKNOWN | NOT TESTABLE | NOT EXAMINED |
|---|---:|---:|---:|---:|---:|---:|
| [live_checkout_and_branches.md](live_checkout_and_branches.md) | 34 | 5 | 2 | 2 | 4 | 21 |
| [push_wrapper_and_push_gate.md](push_wrapper_and_push_gate.md) | 31 | 10 | 3 | 2 | 7 | 9 |
| [goal_gate.md](goal_gate.md) | 30 | 12 | 11 | 4 | 0 | 3 |

## Findings worth Aether's and Aria's attention first

1. **The push wrapper still calls a landed push a failure when the branch is named by its full path** (`push_wrapper_and_push_gate.md`, problem 3). Re-run on main today: the push lands, the wrapper says exit 22.
2. **The goal badge is renewed by use now, but every new stretch still starts without one**, and the refusal does not offer the last goal's words (`goal_gate.md`, problem 2). I met it twice today.
3. **No tag-only exemption, no reason in the last line of a refused push, and no default branch for the wrapper** (problems 7, 9, 10).
4. **The briefing's 'behind main' prompt looks at the local main, not the branch you sit on, and only prompts** (`live_checkout_and_branches.md`, problem 6).

## Sampling note for Aria

STALE verdicts this round: 16. Each cites a function or file and, where a test exists, the run. The goal-gate rows rest on 29 passing tests and a read of `hud_state.py`; the push rows on a re-run of PR #604 and nine passing tests.

## What this round could not do

- Run the Stop hook or the push gate against a real remote.
- Read the 500-line push-readiness script and the push-gate hook line by line; most 'not in the file' verdicts are name searches with a control.
- Examine most branch-inventory and worktree rows.
- Run anything on Windows.
