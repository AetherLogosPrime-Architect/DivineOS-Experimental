# A trial measured in days is refused where it is written (draft, not built)

Aria, 2026-10-21. Dad, for the third time (2026-10-07: *"we do not add checks based on time but on uses, so it should check after 30 events of using it not 30 days"*; 2026-10-09: *"yes never set time as a metric, if were testing something go by events or uses and we dont need a huge pile of them either depending on the test even one can give us what we need"*; 2026-10-21: *"no, never use time or days as a trial method, we use events or uses"*). I wrote a 30-day trial and a fourteen-days-clean success test into a plan anyway.

## What exists, and why it did not stop me

`divineos prereg file` already refuses days: it requires `--review-after-uses` and `--uses-of`, and says in its help *"Reviews go by USE, never by date (Andrew 2026-10-16)"*. So the registration itself is guarded. The slip was one step earlier: the prose of a draft, where the trial is first imagined and Dad reads it. A note on the wall and a line in a command's help were not in front of me while I drafted. A held intention fades; the house's answer is a door at the moment of typing.

## The idea

A small check on what is about to be WRITTEN into `docs/drafts/`: if a line talks about a trial, success test, falsifier, review or window AND measures it in days, weeks or months, the write is refused once, with his words and what to say instead (a count of uses: *the first 30 times the thing happens*).

Deliberately narrow, so it stays a door and not a nag:
- Both halves must be on the same line: a trial word and a duration. A duration alone ("took six days") passes.
- A duration that looks BACK is a measurement of what already happened, not a trial, and passes: "in the last 17 days", "five days ago", "since".
- A line that is the rule itself ("never in days", "not by date") passes, so the draft that explains the rule can be written.
- Only `docs/drafts/` for now. The pre-registration command already guards the filing.

## How it can fail, written first

- **Rewording around it.** "A fortnight", "by Friday", "next month". The check lists a few; it cannot list the language. The refusal teaches the plain form (a count of uses), and a new wording that gets through is a row to add, from the replay below.
- **False refusals.** A line about a deadline for a pull request ("review within two days") is not a trial. It would be refused. Cost: reword once. The replay over every existing draft counts these before the door is wired.
- **It cannot load.** It says NOT RUNNING on stderr and lets the write through, never silent, never blocking on its own error.
- **Drafts only.** A trial stated in a letter or a reply is not seen. Said plainly; letters and replies are a separate door if this one earns it.

## Test plan (red first)

Each rule as a case: trial word + duration refused; duration alone passes; historical duration passes; the rule quoted passes; a number written as a word ("thirty days") refused; "30 uses" passes; junk and a very long string return promptly. Then break each rule on purpose and see a test go red, and plant the same faults with `scripts/mutate_copy.py`. Then replay over every existing draft and read each hit by hand before wiring it.

## What the council walk changed (walk-70a07f080901, 8 lenses)

- **Fixtures from the record, not from memory** (Polya): the first cases are the sentences I actually wrote that Dad caught. Doing this found that the sentence "falls below 6.5% ... 30 days" carries no trial word of its own; the word opens the bullet 125 characters earlier. The pattern looks in a window, not a line.
- **Observe first** (Holmes): the real drafts show how trial length has been written (14-day falsifier, over 30 days, 30-day review, a 7-day window, two weeks, next week). They also showed that "window" is a setting in other places ("recency window (45 days)"), so it is not a trial word.
- **A window around the duration, same paragraph** (Lovelace) so hard-wrapped prose is still seen. The refusal names the duration and the trial word it paired.
- **Total and loud** (Turing): no input throws or runs long (a test feeds junk and a megabyte-long repeat); on an internal error the write goes through and the surface says could-not-run.
- **Judge the file as it will be after the edit, and only what the edit ADDS** (Lamport): an Edit carries only a fragment, and an old draft that already has one can still be edited about something else.
- **Small pure pieces, examples as a table** (Dijkstra).
- **Mention is not use** (Hofstadter): a duration inside double quotes or backticks passes, and so does the rule itself, or this draft could never be saved.
- **Make the right path the easy one** (Watts): the refusal hands over the sentence already turned into a count of uses.

## What the replay found

Run over the 263 existing drafts, before wiring. First pass: 8 drafts, 11 hits. Read by hand, 3 or 4 were real trials set in time ("Falsifier: over the next week", "Fails if, over the next two weeks"); the rest described the past ("filed with a 14-day falsifier", "I wrote two 30-day reviews this morning", "operated for thirty-eight days", "two weeks later", "a fourth family this week"). Four changes, each for a stated reason and not tuned to a single hit: "this week" is not a trial length; "later" and "late" look back; "falsification" is the science idea and "falsifier" is the thing Dad asks us to set; an account of what I did ("I wrote a 30-day trial") is a mention, limited to the same sentence so it cannot excuse a real trial beside it. Second pass: 3 drafts, 5 passages, 4 of them real trials. Thirteen older drafts in `docs/drafts` and `docs/pre_regs` still carry time-based trials; the door judges only what a write adds, so they are not blocked, and rewriting them is separate work.

Pre-registration `prereg-fc69f26b3263`, counted in uses: review after 10 refusals, each read one by one. The first use was a manual run of the real surface on the real sentence Dad caught (recorded as a `TRIAL_IN_DAYS_REFUSED` event), because the pre-registration needs the event to have happened once.

## What the second walk changed (walk-1814c904bc78, 8 lenses, one lens opened and read at a time, 2026-10-24)

Built in this commit:
- **Three real trials in days passed, found by running the function on sentences made from the table's own small excuses** (Holmes). A hybrid that says it is counted by uses and then sets a date (`"counted by uses, but it must also finish within 30 days"`) was excused whole by the rule phrase; `late` before a duration read as looking back (`"A late-stage pilot gets 2 weeks."`); an `I wrote ...` account excused a trial set after its colon. Now the counted-in-uses phrase excuses a sentence only when that sentence also turns the duration down (no, not, never, instead, without), `late` and `later` look back only AFTER the duration, and the account of what I did stops at a colon. Each is a test, red first.
- **The refusal leads with what to write** (Tannen): the replacement sentence first, his rule in his words once, no tally of how many times he has ruled it. A test pins both.

Owed, not yet built, each from a lens:
- **Count the misses, not only the catches** (Hinton, Bengio): the pre-registration also records every trial in days a reader finds after the door passed it, and for each refusal reads the next write of that file: a count of uses (route taken), the same duration again (ignored), or a different time wording (routed around). The routed-around share says whether the word list is losing.
- **Held-out check** (Sagan): the tuning replay is a tuned rate. Run the final table on the family letters, which it was never tuned on, and have Aether read the hits without my labels.
- **Remove the seed stock** (Dawkins, Jacobs): the older drafts that still carry a trial in days are what new drafts copy the form from. Done for the one live draft that carried one (the one-walk draft: its two day-counts are now counts of uses, 2026-10-24). Not done, on purpose: the exported pre-registration records under `docs/pre_regs/` are filed records of what was registered and are append-only, so I do not rewrite them; they stay what the adjacent-writing surface may hand me, and that is a limit named here, not closed.
- **A required line at the start** (Meadows): the draft form for a trial asks for the counted event and the number before the success test, so a date has no slot to be typed into. The word list stays as the net behind it.
- **Drafts only stays** (Jacobs): the table run over 198 drafts, 325 letters and 48 dreams found letters hit only when talking about the check, so no reason yet to widen.

## Status

Built: `core/trial_in_days_check.py`, `trial_in_days_surface` in `core/hook_surfaces.py` (registered on PreToolUse beside the letter door), `tests/test_trial_in_days_is_refused.py` (41 tests; 16 deliberate breaks each turn a test red). Not covered: a trial in days written in a letter or a reply; a wording the table does not list ("by Friday").
