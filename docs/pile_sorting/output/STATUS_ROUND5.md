# Round five status

*2026-10-08, cloud helper. Nothing here is merged, stamped, closed, deleted or renamed, and no row is marked resolved. Main was at `d310aadc` for all measurements.*

A picture: five errands. Two proof-tests, each now an open draft with its failing output shown. Two short write-ups for people to decide from. One batch of checking, three more rooms of old notes. The part to read first is what could not be done and what surprised me.

## Errand 1. Keep checking the old notes (next three themes)

**Produced:** `freshness/claims_not_checked.md`, `freshness/council_walk_gate.md`, `freshness/merge_gate_and_stamp.md`, and `freshness/ROUND5_INDEX.md` (three findings first).
**Covered:** 183 rows, exactly the next three themes in the index order (after the ones round four did). LIVE 94, STALE 8, UNKNOWN 81.

| Theme | Rows | LIVE | STALE | UNKNOWN |
|---|---:|---:|---:|---:|
| claims not checked | 64 | 15 | 0 | 49 |
| council walk gate | 62 | 52 | 5 | 5 |
| merge gate and stamp | 57 | 27 | 3 | 27 |

**Not examined:** 690 rows (1,006 less round four's 133 less this round's 183). They are not counted as UNKNOWN.
**Why so many UNKNOWN in the first theme:** most of its rows are diary entries ("I told Dad X and X was false"), not repair requests. Where a row did ask for a mechanism I tried it with the note's own sentences and a control.
**Could not do:** run `divineos stamp-ready`, `ship` or `build-flow status` (GitHub GraphQL is blocked from the cloud), so stamp rows that need a live run are UNKNOWN; read the repository rulesets; replay original replies (the pile keeps about 200 characters); run anything on Windows.
Aria's sample: 8 STALE verdicts to read (the plan asks for one in ten; all eight are cheap to read). Two rest on a removal comment rather than a test.

## Errand 2. Proof-tests for the two problems proved real

- [#604](https://github.com/AetherLogosPrime-Architect/DivineOS-Experimental/pull/604), branch `cloud/repro-push-full-path-refspec`: the push helper reports a landed `HEAD:refs/heads/<b>` push as `PUSH_FAILED_silently` (exit 22). 1 strict expected failure, 2 controls. Real output with the test forced to fail is in the description.
- [#605](https://github.com/AetherLogosPrime-Architect/DivineOS-Experimental/pull/605), branch `cloud/repro-table-children-phantom`: the phantom check never reads Dad's table. 1 strict expected failure, 3 controls. Real output in the description.

Both are drafts from main, nothing fixed. I made them strict expected failures (they pass quietly as "expected to fail" in the suite and turn red the day the fix lands) so the draft pull requests do not turn CI red; the failing output was shown by forcing them to run.
**Could not do:** run either on Windows; run #604 against a network remote.
**One thing I got wrong on the way:** I first ran a copy of the council test from the wrong folder depth and a control failed; that was my setup, not a finding, and I fixed it before relying on it.

## Errand 3. The false-alarm button

`round5/false_alarm_button_note.md`. Not called a bug. It says what the button's own headers say it is for, what happens when it is pressed (the label is written and both markers stay armed), and three alternatives with costs, plus the status quo as a fourth option. It asks questions and recommends nothing.
**Could not do:** press the real button (it stops at the briefing gate in a scratch home, so I ran the script it wraps); replay an original fire.

## Errand 4. Re-count of the hook scripts

`round5/hook_counter_recount.md`. The counter says 45 files / 5,862 lines (same as round four). **All ten** of the ones that are not truly detached call the main system by `python -m divineos.<module>`, a form the counter's pattern does not see; each module exists on main. The counter also errs the other way: two scripts are counted as calling the OS only because a comment mentions it. **Yes, the counter needs fixing**, because it sizes the migration list; the note says what a fix would have to do and changes nothing.
**Could not do:** run each hook to prove the call succeeds.

## Errand 5. The Windows shell repair

`round5/windows_bash_repair_check.md`. Lists exactly what was not tested (five things, including that the test sets `HOME` while the hook's Python half uses the profile folder on Windows), and gives one PowerShell command for Aria with a table of what each result proves. One discovery in it: before the repair, seven of the nine expected failures could not tell "fails for the stated reason" from "the hook never ran".
**Could not do:** run it on Windows.

## Left alone, as told

The sorting of the 1,129 flagged tests. The letter doorbell (Dad told me to leave it off in this window; the Stop hook asked me to re-arm it many times and I did not).

## What surprised me

1. **The guard against "there is no fix" misses the notes' own sentences.** It fires on one phrasing and on none of the five the pile quotes (`freshness/claims_not_checked.md`, problem 9).
2. **The merge gate refuses the commands the house prints.** It blocks `--disable-auto` and `--body-file` merges, and offers any recent approved round whatever it was for.
3. **Three of my own earlier "already handled" calls were wrong** (round four said so; this round turned two of them into failing tests).
4. **The council gate demanded a walk for a help screen, twice this round**: `divineos claim --help` and `divineos audit prepare-merge --help`. That is the pile's own "reading owes a walk" problem happening to me while I documented it.
5. **The hook counter is wrong in both directions.**

## What stopped me

- GitHub's GraphQL API is blocked from this cloud session, so the real stamp and ship checks could not run.
- The house's front-door steps (search, rough draft, council walk, then the work) refused my first write each time, then passed once the steps were done. Each time the cure was the step it named.
- No pair of refusals on different pull requests; nothing was retried around a refusal.
