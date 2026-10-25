# A fix is live when it fires by itself, and the house says so without being asked (draft, not built)

**Author:** Aria, 2026-10-24

## What Dad said

*"live means it works in chat.. and it actually runs and does what it claims to do.. automatically.. that is what plugged in means.. if its sitting there waiting to be remembered to be used..that is not plugged in nor live.. EVERYTHING must be automated..how you automate it is up to you.. but nothing should be left for you to remember"* (2026-10-24).

Before it, the same evening: *"we spend all of this time fixing these issues that constantly plague you, and then they sit on the shelf.. never merged.. so later.. the same fucking issue plagues you because the fix you did for it never properly landed or was plugged in."*

## What happened

I counted a fix as finished when it was saved on a branch, and then when it was merged, and told him a number built on the first meaning ("at least four landed today") when one had merged. The false "waiting for Dad" alarm fired three more times after I had fixed it, because the fix was on a branch and the live house still ran the old detector. Both are one fault: **no one, and no mechanism, ever checks whether a fix actually fires in a real turn.** The word "done" has been carried by me, and a word carried by me fades.

## Prior art, searched first

- `core/hook_firing_map.py` sorts every hook into FIRING, SILENT or UNOBSERVED from the timing log. It answers "does this hook run", for hooks only.
- `docs/wireup-backlog.md` and `docs/os_cleanup_worklist.md` list what is dead or stranded. They are lists, which is the shelf he is describing.
- `core/structural_promotion_check.py` asks of a lesson what test, gate or surface now holds it (observation only).

What none of them does: take a **fix** (not a hook), say where it is supposed to fire, and report from evidence whether it did, in front of me without my asking, and at the merge.

## The idea

Three parts, none of which I have to remember.

1. **Every fix declares one firing line**, in the draft that explains it: "fires when X happens, at Y, and leaves Z as its trace." The trace is a log line or event the fix already emits, or one it is made to emit. A fix with no firing line cannot reach the final station of the build flow.
2. **A check reads the trace.** For each declared fix it reports FIRING (the trace appears in real turns, not only in tests), NOT YET (merged, no real turn has met the condition), or NOT WIRED (the caller named in the firing line does not reach it, by reading the settings and imports). It reuses the hook firing map where the fix is a hook.
3. **The result appears by itself:** in the session briefing, so I read it every time I start, and in the merge checks, so a fix that is saved but not wired cannot be called landed.

## What Aether's attack changed (2026-10-24, measured on his own piece)

- **A fourth state between merged and firing: RUNNING.** His #715 merged to main, but the checkout his hooks actually run from was five commits behind main and did not contain it (a count of the new row's name in the running tree: 0, on main: 2). The fix was merged and the old fault kept happening: the same shape as my false alarm. So a fix has four checkable states: **PUSHED, MERGED, RUNNING** (the checkout the hooks run from contains it), **FIRING** (a real trace). NOT YET (the condition has not occurred) and NOT RUNNING (the code is not here) are different words and need different cures.
- **The catch-up must itself fire by itself.** There is already a measure of how far the running tree is behind main; it tells and does not act, and a notice read past is the shelf again. The merge of main into the running tree should happen on its own when it is safe (nothing in conflict, no overlap with uncommitted files) and be shown when it is not. I did that by hand tonight for my own tree: one commit behind, no overlap, merged.
- **Evidence for FIRING without a new log:** add the running tree's commit to each hook-timing row, so "the hook that calls the fix ran in session S from a tree that contains the fix" is checkable for any fix reached by a static call. It proves available-and-called, not that the inner branch ran.
- **The trace must come from a real session, not a fixture:** a session id that exists as a transcript in the harness's own folder, which a test cannot invent without writing a file the harness owns (a test once planted eighty copies of a sentence among Dad's real words).
- **A vague firing line is walked around unless it is checked for selectivity:** the line names a hook or event and a pattern; the check refuses a pattern that matches more than a small share of the real log, and one that matched before the fix's commit (the trace must be absent before and present after). A specific line that is irrelevant to what the fix does still passes; the falsifier below is the only net for that.
- The report shows the distance (commits behind) so the third state is visible at session start. The first run includes #715, the live example.

## How it can fail, written first

- **The firing line is a promise that rots.** Mitigation: the check, not I, compares the line against the trace; a line that names a caller which does not exist is NOT WIRED.
- **Tests make the trace.** A trace written by a test fixture would read as FIRING. The check must read the real turn log, and a test of the check plants a test-made trace and must see it rejected.
- **FIRING when it is firing wrongly.** The trace shows that it ran, not that it did the right thing. Said plainly: this proves "plugged in", not "correct"; correctness stays with the tests and the reviews.
- **The report becomes wallpaper.** It prints only what changed or is not firing, never a wall of green.
- **A fix whose condition rarely occurs reads NOT YET for a long time.** That is honest, and it is shown with how many times the condition has been met, in uses, never in days.

## Falsifier, counted in uses

Of the next 10 fixes that reach the merge, if Dad finds even one not firing while the report said FIRING, the check is wrong. If I tell him a fix is live and the report says NOT YET or NOT WIRED, the report was not read and the first part failed.

## Not in this idea

Judging whether a fix is good. Rewriting old fixes' declarations all at once; the first run is on tonight's pieces: the false-alarm fix, the timer note, the day-count check, and the test picker.
