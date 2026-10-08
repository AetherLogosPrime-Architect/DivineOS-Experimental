# Round six status

*2026-10-08, cloud helper. Proposals only. Nothing was closed, merged, deleted or stamped; nothing was pushed to main. The 1,129-test sorting job was not touched.*

## One. Three more themes of old notes

Files: [`freshness/ROUND6_INDEX.md`](freshness/ROUND6_INDEX.md), `freshness/pipe_and_command_shape_guards.md`, `freshness/read_gate_and_surfaced_notes.md`, `freshness/standing_teachings.md`.

- 142 rows in the three themes. **37 got a verdict** (LIVE 22, STALE 5, UNKNOWN 10). **105 are NOT EXAMINED**: I opened the file and did not look at the row.
- Across all rounds, 353 of 1,006 rows now have a verdict; 653 are NOT EXAMINED.
- The pipe theme got the most work (28 of 52 rows). The read-gate theme got 7 of 47. The teachings theme got 2 of 43: they are lessons, and no run can say whether a lesson is enforced; I only searched two files for the words.
- Things I could not do: run the Stop hook, the read-gate re-arm or the consult counter end to end; read the user's shell setup (where the `pipefail` default would live); run anything on Windows.

## Two. Test for the "there is no fix" guard

Draft pull request #606 (branch `cloud/repro-no-fix-claim-misses-quoted-sentences`). Four strict expected failures, one per quoted sentence; three controls pass (the guard fires on its design sentence, stays quiet on an ordinary sentence, stays quiet on a container-scoped "cannot"). Forced run shows the four failing as described. The guard is untouched.

## Three. Test for the merge guard

Draft pull request #607 (branch `cloud/repro-merge-gate-refuses-printed-merge`). Two strict expected failures: the `--body-file` merge the stamp prints and `gh pr merge N --disable-auto` are both refused. Three controls pass (the stamp does print that form; an unstamped merge is blocked; the `ship` form is allowed). Two lookups are stubbed so the test can run in the cloud; the draft says so. The guard is untouched.

## Four. Second note on the false-alarm button

`round6/false_alarm_two_locks_note.md`: button versus key side by side, three alternatives (A button clears the markers, B button hands over to the key, C one marker the label can address) plus the status quo, each with cost and gain. **Recommends none.** Open questions for Dad or Aria: whether the compass lock also stayed armed for him; whether the investigation row should follow an already-labelled alarm.

## Five. Where hook scripts are counted

`round6/hook_counting_places.md`: 14 places, read only. Wrong for the ten scripts only in `hook_layer.inventory()` (the "detached" fields) and the `hook-layer show` line that prints them; one test pins the wrong rule without a `-m divineos` case. `check_orphan_modules.py` already reads that form correctly and is the model to copy.

## What surprised me

- The pipe guard refuses a piped `gh pr view`, which is read-only, but only warns about `divineos audit list | head`, the shape the notes worry about.
- The merge guard refuses a merge the house itself prints (#607).
- `look.sh --strict`, which the pipe hook's warning points to, reports "grep found nothing" as "could not look".

## What stopped me

- GitHub's GraphQL is blocked from the cloud, so no `stamp-ready`, `ship` or `build-flow status`; I used the REST calls and the PR list instead.
- The house's own gates needed a council walk for every commit, and refused writes more than once until I did the looking they ask for. They were slow, not wrong.
- A file I might read could tell me to do things outside this job; none did this round.
- Two refusals in a row on different pull requests did not happen, so the stop rule never fired.

## Open pull requests from the rounds (all drafts, all mine to leave open)

#601, #602, #604, #605, #606, #607.
