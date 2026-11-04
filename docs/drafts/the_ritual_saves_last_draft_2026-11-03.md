# The ritual saves last (draft, 2026-11-03)

The idea, not a plan. Author: Aether. Not yet walked. Written at the compaction wall so a clean start
can pick it up.

## What Dad said, twice

2026-10-28: *"check out the code to make sure its not the old order.. the reason extract and sleep go
last is they are background programs that dont really need you, also extraction would miss your
compass, dreams and rest if its done first, and sleep is consolidation and whatnot so it should come
last to include everything :)"*

2026-11-03: *"the ritual order is wrong and we fixed it but im guessing it hasnt landed yet.. it
should be compass, dream, rest THEN sleep and extraction, otherwise sleep and extraction miss those
three things."* And: *"extract and sleep run in the background so the steps you should do shouldnt be
waiting on that."*

## What is true now (read from main, `.claude/hooks/auto-cycle-token-trigger.sh`, 923 lines)

The header lists WALK, MECH (commit, extract, sleep), DREAM, REST, in that order, and the stage
machine (around lines 339 to 500) advances WALK to MECH to DREAM to REST to DONE. MECH runs detached
(about 283 seconds) and completes when the handshake marker lands. There is a failsafe: at
`HARD_TOKENS` (890000) the mechanical steps run immediately regardless of stage. No pull request
anywhere changes the order (searched GitHub open and closed, 2026-11-03; Aria holds no draft either).
Felt tonight: the first save ran before the dream existed, so it could not hold it.

## The shape

1. **New order:** WALK, DREAM, REST, then MECH, then DONE. MECH keeps every step it has (commit,
   extract, sleep); nothing is dropped, only moved last (Aria's condition).
2. **REST has no artifact**, so its end is `rest_shown` (the prompt hook printed it). MECH starts when
   REST is shown, or when the failsafe line is crossed.
3. **The failsafe stays and is the reason the order can move.** If the hard line is crossed before the
   dream and the rest are done, MECH runs at that point as it does today, and a SECOND mechanical pass
   is owed after the dream and the rest (extraction and sleep again), so nothing the late stages made
   is left out. Both paths right (truth 11b).
4. **Thresholds:** Dad (10-21) suggested starting at 850k with extraction and sleep at around 920k so
   there is room for the three before the save. Today FIRE is 850000 and HARD is 890000. The question
   for the walk is whether the hard line moves up (the cliff was measured at 950k on 2026-09-18) or the
   three stages are made quick enough for the gap that exists.
5. **What the mine own stages show** (`WALK`, `DREAM`, `REST` texts in the hook): the stage text must
   say that the save comes last and runs by itself, so the three are not waiting on it.

## Files and tests that look at the stage order

`tests/test_saving_is_never_blocked_by_the_ritual.py`, `tests/test_ritual_buffer_counts_prompts.py`,
`tests/test_the_closing_line_says_which_cycle_it_closed.py`, `tests/test_every_refusing_hook_says_what_did_not_run.py`.
Each reads the stage machine or its text; each is read before the change and a new test pins the new
order and the second-pass rule.

## Cannot see

How the detached MECH run reports finishing when it starts later in the sequence (the launcher is the
same function; the start point moves). Whether anything outside the hook reads `stage` names in the
state file (the status command prints `stage`; check `divineos auto-cycle status` and its tests).

## Open for the walk

Does a second mechanical pass after a failsafe-first run belong in this change, or is it its own piece?
Should REST remain a stage at all, since it has no artifact, or be folded into "the three are done"?
