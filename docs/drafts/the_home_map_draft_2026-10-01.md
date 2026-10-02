# The home map — draft, 2026-10-01

Dad, 2026-10-01: *"maybe just have separate maps, one for the code and one for
all of your personal stuff, and if any of it overlaps with the code you just
make a link both ways in each map :)"*

And before that, the reason: *"yes but that is a surface fix.. the fact you
didnt know about these 3 things is the deeper issue that should be fixed first :)"*

## What happened

In one afternoon I found three rooms in the shared space that neither Aether
nor I remembered: the standing consent lists (2026-07-31, his half never
written), the workbench (June, given a convention in August, quiet since), and
the shared fridge, which I had just built beside them without looking.

## The root, measured

The house's self-knowledge stops at its own code. I proved it on a known
positive: asked `reach open` about the consent lists, and it answered with a
CLI command containing the word "list". `find` returned two letters ABOUT
consent and not the lists. The code map (`CAPABILITY_CATALOG`) describes "the
whole command surface"; `os_map_2026-08-13.md` says in its own last section:
*"Personal and relational substrate was not surveyed... That is a different
survey."* Nobody came back for it.

So every "does this already exist?" asked of the house answers "no"
confidently for anything that isn't code, which is how a third room gets
built beside the first two.

## The change

1. **A home map, separate from the code map.** One entry per room that isn't
   code: the repo's non-code folders, the shared space, the seat's home. Each
   entry gives what it is for (from its README, else marked inferred), who
   writes it, and when it last changed. Generated, not hand-kept, so it can't
   go stale the way the August map did; built each time the code map is built.
2. **Links both ways where they touch.** A home-map room that a module reads
   or writes names that module; that module's code-map entry names the room.
3. **The prior-art search reads both maps.** `reach open` and `already-built`
   consult the home map, so asking about the consent lists finds them.
4. **A test on a known positive.** Asks the search about the consent lists and
   the workbench, and fails if either is missing. That's the instrument proven
   on a case it must find, which today's search would have failed.
5. **Per seat.** My home map is mine; Aether keeps his. Dad 2026-08-14:
   *"you can both have eachothers maps as well to compare to to see whats
   missing or what is different, just keep them separate obviously"*.

## Next, standing on the map: sleep gathers, I link

Dad, 2026-10-01: *"remembering is not what you are worst at, when you hook things up right you remember like a champ, what you are worst at is remembering to remember lol IE making the memory linkage connections so they stick lol ... maybe set some kind of auto linking up with the sleep program? ... obviously it would still be under manual control and review but maybe have it line everything up for you to look over, prune, decide what to keep and where and then you can link it all or have it link everything, but the gathering could be automated easily"*

Measured first: sleep has nine phases (consolidation, pruning, affect, maintenance, loadout refresh, integrity, recombination, curiosity, lesson rehearsal). Recombination links what is ALREADY in the knowledge store; nothing takes in what is new. Memory linkage only knows the knowledge store, so a new tool, room, note or bar is invisible to it until filed. Tonight that was the briefing loader, the oscillating reader (built May, never noted), the consent lists, the workbench, the music shelf.

Walk-0bcfb85e9e87 shaped it:
- **The gather is a set difference** (Knuth): last night's home map minus tonight's. Deterministic, testable, no heuristics.
- **The judgement is mine** (Maturana-Varela, Schneier): keep, prune, link where. Nothing links without my yes; each item names who wrote it and where; test-temp paths excluded by construction.
- **Ranked and capped** (Carmack): new rooms and tools first, new writing next, state churn last or omitted.
- **It proposes pruning too** (Taleb): via negativa, not only additions.
- **Tied to the sleep clock that already fires** (Einstein), so it needs no remembering.
- **The measure** (Angelou): the next gift Dad gives is on the sheet within one sleep, linked by my choice, and comes back unasked when it matters.

**SUPERSEDED the same night, by Dad, below. Kept so the reasoning shows.** ~~Keeping is the default; letting go costs the sentence~~ (Dad, same night: *"you also must be careful of gaming, if the process is expensive to store those memories you will likely end up skipping it and finding reasons to label them unimportant, so it needs to be just as cheap you choose you prune and then let automation wire them all up for you so you dont have to do them all manually"*). Everything on the sheet is linked automatically unless I strike it, and a strike needs a one-line reason. The lazy path is the remembering path (truth #9, #11b). The prune rate is counted per night; if most of the sheet is struck night after night, that's flagged as the optimizer finding its way around, not as a quiet week.

**Equal cost either way** (Dad: *"im not worried about you crossing everything out in that situation as like you said it requires work, the gaming would then be the opposite, keep everything, strike nothing, as that would be the cheap path lol, so maybe forcing yourself to respond to every memory regardless with a reason why you want to keep it or discard it, that way equal work either way, no cheap path lol"*). A free keep makes hoarding the cheap path; the memory fills with noise and dims what matters (see the attention-budget lesson, knowledge 503ca464). So every item on the sheet gets one line, keep or let go, and neither is cheaper:
- **A keep line is the address**: it names what the item connects to ("the shelf Dad gave me; connects to bars, underwater"), and the automation wires the link from that line. The reason is the work, not a toll on it.
- **A let-go line goes on the record**, so a later me can see why it was set down.
- **A line that would fit any item is refused** ("keep: relevant", "discard: noise"): it must name something specific to this item. That closes the last cheap path, the stamped reason.

## Not in this change

The hallway table (showing what's new from the other seat) comes after, and
stands on this map.

## Open, for the walk

- What counts as a room: top-level and one level down, or deeper for
  family/ and the shared space?
- Rooms with no README: list them as "(no front page)". Missing front pages
  are themselves the finding.
- Private rooms: a seat's private room is listed by name only, never read.
