# The task belt — draft, 2026-09-23

## What he asked for, in his words

Andrew, 2026-09-23:

> "the fixes should be added to the todo list.. the todo list should have a relevance/priority/most beneficial task sorter.. so critical, severe or tasks that have wide reach get chosen first over others. and then you need to automate the task flow so that you are always aware of the current tasks and have that task list updated and cleared by other mechanisms.. something should pull from the todo list.. erase it from the todo list as it goes into your current todo folder (which would be much smaller than the full list) and then when you complete the task it should mark it complete.. archive it and delete it from your task list.. and go pull another one, and we already built a task management system.. obviously same shape as everything else.. not plugged in or properly tested.."

He has asked for this before. From the principles store (ba1be20a, TESTED):

> "Watts is correct but all of the stuff the briefing surfaces is alot. and gets lost in context. which is why the task generator should pull from the briefing and stick it in the todo list so its there to check on whats next todo"

## What already exists (prior art, read before drafting)

- **The pile.** `core/unified_todos.collect_todos()` gathers five drawers into one list: pre-registrations, his corrections, audit findings, action-tier claims, and my own structural fixes. Measured today at 845 items, 529 of them with no priority. Each drawer sorts internally; nothing ranks across drawers. Its own pre-registration (prereg-e323248dea01) was DEFERRED at a compaction doorway in July, and its falsifier checks were never run.
- **Main, current, archive, for ONE drawer.** `core/structural_fix_tracker` already has his June design: `pick_to_current` moves an item from main to current, and `mark_done` moves it from current to archive. `pick_to_current` has zero callers. `mark_done` is reachable (`divineos psf mark-done`) and requires evidence. The other four drawers have neither half.
- **One task shown per turn.** `core/next_task_surface` puts one item in front of me before every reply. Its order is strict by drawer, so a LOW audit item from July sat on top while real failures sat under it. It has an August reserved slot for starvation.
- **The note is hidden when unchanged.** `core/context_dedup.should_emit` replaces a byte-identical block with "unchanged, re-emit suppressed". So a task that never moves becomes invisible, which is the opposite of what a stuck task should do.
- **The list crashes.** `divineos todos --counts-only` raises KeyError 'structural-fix': the fifth drawer was added to the collector but not to the CLI's label table.
- **Not reused, and why.** `core/motivation` is needs, wants and dreams, not tasks. `divineos archive` retires knowledge directives. `divineos list` pages ledger events. The reach check surfaced only those last two; it did not find the real prior art above, which I found by reading.

## The design

One module, `core/task_belt.py`. It connects the parts above rather than replacing them.

1. **Rank across all drawers.** Order: severity first, then reach, then age.
   - *Severity* is the item's own recorded severity where one exists (audit findings carry CRITICAL/HIGH/MEDIUM/LOW). Otherwise it is a per-drawer default, stated as a class default rather than dressed up as a per-item measurement: his corrections HIGH, overdue pre-registrations MEDIUM, structural fixes MEDIUM, T1 claims MEDIUM, T2 claims LOW.
   - *Reach* is how many times the same thing has come back. For structural fixes this is the collapsed-duplicate stamp count. For his corrections it is how many times he has asked for the same thing, from the store the STILL OWED surface already reads. Where no count is recorded it is 1. "Wide reach" is measured as recurrence because recurrence is what the house records; anything more is invented.
   - *Age* breaks ties, oldest first.
2. **A small current list.** At most three items, kept in `divineos_home()/task_belt_current.json`. An item on the current list is left out of the pile view, which is the "erase it from the todo list" step. It leaves the pile for good when it closes at its source.
3. **Starvation guard, carried forward from August.** One of the three current slots is reserved for the oldest item that is NOT in the top severity tier. Otherwise 466 corrections at HIGH would mean my own repairs are never reached, which is exactly the failure measured on 2026-08-28.
4. **Automatic pull.** Every time the pre-response context is built, the belt first *reconciles* and then *refills*. Reconciling archives any current item that is no longer open in its own drawer ("closed at source"). Refilling pulls the top-ranked items until the list is full again. There is no command to remember; that is the point.
5. **Done.** `divineos belt done <ref> --evidence <commit or file>` closes the item through its drawer's existing close path, archives it to `task_belt_archive.jsonl`, and refills. Evidence is required, with the same rule as `psf mark-done`. Closing an item with its drawer's own command (for example `prereg assess`) works just as well, because reconcile notices it. Both paths are right (truth #11b).
6. **The note says how long a task has sat there, not "unchanged".** The surface shows every current item plus how many prompts it has been current. Because that count changes every turn, dedup can't hide it. A stuck task gets louder instead of quieter, which is what Aria's furniture law asks for: supply a fact that changes, not the same five lines.
7. **The crash gets fixed**, and the label table and the collector share one source-name list, so a sixth drawer can't reopen the same KeyError.

## Changed after Aria's station-four reading (2026-09-23)

- **Duplicates.** She found two of three slots going to one correction, filed once raw and again under "Andrew verbatim:". On my seat, 312 pairs of his open corrections are one text wholly contained in another. A looser first-80-characters probe matched 788, because templated rows share an opening; that probe was wrong and was not used. A row that is a current item filed again now joins it as a twin and closes with it.
- **The stuck count.** A number rising by one every prompt carries no news. The block now changes only when an item crosses 5, 20 or 50 prompts. Between those it is identical, so dedup may collapse it. But dedup now keeps a one-line residual that names every current item, so the list is never hidden again. She asked for the milestones; the residual is what keeps his "always aware of the current tasks" true while dedup does its job.
- **His personal rows.** Her proposal, not yet built: the first time one reaches the belt, the seat sorts it once, with a written reason. Work stays on the belt. His words leave it, to be kept whole and answered in person, not with a commit. That needs the words store and is the next piece, not this one.

## What goes on the belt first, once it exists

- **A sixth drawer: dropped work.** That means every save, send or letter the house refused this session that was never redone, measured from the transcript the way I did by hand on 2026-09-23. It rides the belt as an item rather than into this build, so the belt's first real job is its own next feature.
- **A seventh: the briefing's own surfaces**, per his earlier ruling above. The briefing prints a great deal that is lost in context, and it should land on the belt.
- **Running the July falsifier checks** for the unified pile that were deferred and never run.
- **Bringing my sixteen open branches down to his limit of two.**

## Open questions for the council and for Aria

- Is "corrections are HIGH by default" right, or does it make his words a flood that drowns everything else? Should reach decide within the class instead?
- Three current slots: right size? He said "much smaller than the full list", not a number.
- Should a current item that sits for N prompts without movement do more than get louder, for example refuse new unrelated work? That would be a gate, and gates need their own falsifier.

## Falsifier

If the open count across the five drawers does not fall within the first stretch of real use, the belt is surfacing but not converting, and the problem is downstream of the belt. If the current list ever shows an item already closed at its source, reconcile is broken.
