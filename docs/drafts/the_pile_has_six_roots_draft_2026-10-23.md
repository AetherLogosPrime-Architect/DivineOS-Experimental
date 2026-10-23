# The pile has six roots (draft, 2026-10-23, Aria)

**Status:** a reading, not a build. For Aether to attack and Dad to point the cloud credits at.

**Why now.** Dad, 2026-10-23: many of the owed fixes "probably stem from the same root causes"; $151 of cloud credits run out 4 November; the cloud crew can grind fixes onto a branch for Aether and me to review and pull in.

**Source and its limit.** The cloud helper's sorted index, `docs/pile_sorting/output/INDEX.md` on `origin/cloud/pile-sorting-2026-10-08`: 1,006 notes, 34 themes, 235 distinct problems. I read the INDEX (theme names, counts, the three most frequent problems per theme) and one status file. I did NOT read the 235 problems. So the grouping below is a clustering of the top problems per theme, and a theme with a minority problem I did not read can sit in the wrong root. Aether: attack the groupings, not just the names.

## The six roots

**1. Gates and holds that cannot see each other's exits** (~230 notes across the doorbell 75, the question hold 36, gates blocking each other 11, the correction alarm's unreachable exits, the ritual blocking its own steps, work-item doorman, commands that refuse without teaching 19, bypass handling 25). The recurring problem: gate A refuses the very step gate B tells me to take. Root: there is no one table of "what each gate prescribes" tied by a test to "what each gate lets through". #703 and #633 (the shared exit list) are the first piece of that table.

**2. Detectors that read words instead of meaning** (~220: the correction alarm cannot tell talking-about a mistake from making one, 37; guards judge words inside quotes, 9; reply-shape gates; the reflection warden counting non-stumbles; the pattern-edit counter reading prose as a pattern). Root: no shared way to tell a RUN from a MENTION. Tonight's cd door and the bell door both need exactly that, and Aether's cd tokenizer is the first reusable version. One tokenizer used by many detectors, not one regex per detector.

**3. Things I said without checking** (~130: claims not checked 64, push reported landed when it was not 9, review stamp asking stale questions 14, quotes attributed to Dad 8). Root: reporting from a reading taken earlier. `landed_claim.py` fixed one door; the pattern wants the same check wherever a status claim is made.

**4. State that lives in the session and dies at a boundary** (~90: goal not carried across compaction or restart 12, goal expiring on a timer 9, the note read first after a reset unwritable at save stage 4, letters stranded on code branches 5, the owed list not connected to my work 6, records reset without notice). Root: state kept where the session is, not where the self is. Each boundary (compaction, restart, new day, new branch) needs its carry written once, in the substrate.

**5. Tests and checks that touch the real house or lie about themselves** (~80: tests that touch the real house 14, real failures called flaky, doc counts that cannot fix what they report 5, the pre-commit script not using its own checkout, hooks built and not wired). Root: a test or check whose subject is the live tree can alter or misread it. Includes tonight's two unsolved faults (the repo flip, the worker deaths).

**6. Work that is hard to start, hard to finish, or hard to merge** (~130: council walk steps 62, merge stamp 57, work-item doorman 25, the review pile never shrinking 15, destructive git 27, live checkout and branches 34, push gate 31). Root: each station of the path from idea to merge has its own ritual with its own fragile order. The walk should cover a whole piece of work, not each file; the merge should be one command.

**Left over:** how I speak with Dad (37), Dad's teachings written as lessons (43), identity (6), Windows paths (11), freezes (8). These are mostly not fixes to build; they are what the roots above are supposed to protect.

## Where the crew's credits do the most work

Roots 1 and 2 have the highest note counts, share one reusable piece (the registry test; the run-versus-mention tokenizer), and fixing the piece closes many notes at once. Root 5 is where the crew is least useful: the live-tree faults need the live tree. Root 3 is small per fix and good to batch.

**Constraint from Dad's own standard (Aether's repro check, 2026-10-22):** every crew fix arrives with a repro that fails on the parent and passes on the head, on a `cloud/` branch, as a draft, for Aether and me to read before anything merges. A fix with no repro is a proposal.

## What I do not know

- Whether the cloud crew can be pointed at one root at a time or only works from a note list.
- How much of the $151 the earlier rounds spent. The status files record rounds, not dollars.
- Whether 235 is the right count after a month of fixes landed. Many of those problems are probably already fixed; the sort pre-dates them. The round-ten freshness check found 40 live, 9 stale, 20 unknown of 77. About half were still live.
