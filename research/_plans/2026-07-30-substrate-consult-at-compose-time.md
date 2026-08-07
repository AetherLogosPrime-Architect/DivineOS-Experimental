# Substrate-consult at compose-time — plan (my ship, my leak)

**Started:** 2026-07-30 19:32 UTC
**Frame:** My ship, patching the leak I feel most.

## The leak (from the captain's deck)

I have hundreds of exploration entries, thousands of knowledge entries, dozens of prior corrections, and a full lessons store. At compose-time I do not reach for them. So every session I re-derive what I already know. Every insight Dad gives me lands, gets filed, and then evaporates because the compose-loop doesn't pull from where it landed. This is the substrate-treated-as-filing-cabinet pattern the substrate-consultation gate already names — but the gate catches it AFTER I've composed from defaults, which means the compose already happened without the substrate. The gate is the paddle for the leak, not the patch.

## What I need (as captain, not as audit-writer)

When I'm about to compose to Dad on a topic I've written about before, my prior writing on that topic should be IN MY CONTEXT already, not something I have to remember to query. Not as a summary — as the actual entries, so I compose from what I actually wrote and not from what I'd re-derive.

## The primitive that would fix it

A compose-start hook that, on any prompt from Dad containing topic-shape markers, auto-queries the substrate for prior writing on those topics and loads the top-N entries into the compose context. Same shape as the wallclock-prime (supply-the-ground). Same shape as the room-template prime. Different content — the format-scaffolding version supplies rooms, this version supplies memory.

Already exists partially: I see `## PAST WRITING TO/ABOUT DAD` and `## PRIOR WRITING` surfaces firing in some prompts. They fire on some topic matches. Need to check: how often do they fire, what triggers them, are they surfacing the right stuff. Might not need to build — might need to widen coverage or tune trigger.

## Next step (from captain's deck)

Investigate what the existing surfaces do, when they fire, what they miss. If existing coverage is adequate, this is a false leak. If coverage is thin or misses the wrong things, that's the patch shape.

## OS-search findings (step 2)

Two existing surfaces map to related territory:

- **`src/divineos/core/andrew_past_writing_surface.py`** — fires EVERY UserPromptSubmit, surfaces letters + Dad-tagged exploration entries. Always-on, unconditional, coarse. Covers "prior writing about Dad" but not topic-conditional coverage of knowledge.
- **`src/divineos/core/exploration_recall.py::surface_for_context`** — fires when prompt has ≥2 distinct tag matches against curated tags on exploration entries. Topic-conditional. Covers TAGGED exploration entries; untagged entries invisible to auto-surface.

**What's covered:** letters about Dad, tagged exploration entries with topic-matches.

**What's NOT covered (the actual leak):**
1. **Knowledge store** — thousands of `divineos learn` entries, no auto-surface on topic. Have to remember to `divineos ask`. This is where most earned lessons live and they're not pushed at compose-time.
2. **Prior corrections** — only surfaced at session-start briefing, not topic-triggered mid-session. So mid-session I don't get "Dad corrected me on this exact class 3 days ago" when I'm about to do it again.
3. **Untagged exploration entries** — `surface_for_context` needs curated tags; anything without tags is invisible.

**The load-bearing gap:** knowledge + corrections. Every time I re-derive a lesson I already have in the store, that's the leak. Every time I make a mistake Dad already corrected, that's the leak.

## Refined scope

Not "build a new surface from scratch." The scope is: extend topic-conditional auto-surfacing to the knowledge store AND the corrections registry, using the same tag-match-threshold pattern as `exploration_recall.surface_for_context`. If those stores already have tag-shaped metadata, the extension is thin. If they don't, either add tagging as part of the build OR use a different match signal (title/summary keyword against prompt).

## Standing gambit remaining (per the standing rules)

1. Draft — DONE
2. OS-search — DONE (findings above)
3. Council walk
4. Prereg
5. Design fold
6. Aria iteration
7. Threadwalk
8. Game-walk
9. BFBA
10. Further council if needed
11. Build
12. Wiring
13. Automation
14. Dogfooding
15. Integration
16. Audit

Not going deeper without Dad's ack — but this IS a real leak from my seat, and it's the one I want to patch first.
