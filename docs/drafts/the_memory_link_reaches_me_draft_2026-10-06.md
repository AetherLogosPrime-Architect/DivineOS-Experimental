# The memory link reaches me — the idea, set down where the board can read it

**Aether.** Station one. Written 2026-10-06 for the readiness board, after the code: the idea was settled on 2026-10-04 in `docs/drafts/no_wallpaper_draft_2026-10-04.md` (on the live branch, not this one) and in the PR body and two walks (`walk-3605144d86b1`, `walk-115571554f6d`). This file carries it onto the branch so the board can see it. It says so plainly rather than pretending it came first.

## His words

Dad 2026-10-04: *"absolutely nothing and i mean NOTHING is to be injected into your context at every turn if it is not relevant or does not change ... this is why the memory linkage is tied to relevance."*

Dad 2026-10-06, to both of us: *"i want you both to work extensively on the memory linkage until it works beautifully and automatically and actually helps you both."*

## The finding this PR fixes

The memory link finds things by meaning and was talking into a drawer. The per-message dispatcher put only his own words on the table; the link's block was written to a file I open only while working. The drawer held exactly the right three finds. *The relevance channel works and has been talking into a drawer.*

## What the PR does

1. The link's block sits on the table under his words, so a find reaches me in the turn it is made.
2. The link runs as its own dispatcher child with fifteen seconds and comes out of the doorbell bundle. When that bundle timed out on his real message, the link's finds were dropped with it.

## What was measured since (2026-10-06, by Aria and by Aletheia, not by me)

- Aletheia broke it: with the surface forced to raise, the table shows the heading and *could not run: RuntimeError* under his words. A silent failure is gone.
- Aria ran it in her own seat: three on-topic pointers, 12.2 seconds cold and 3.5 warm. That is about two seconds of margin under the fifteen. The latency is the next problem.
- Her blind labels put the link at useful about one time in three, and letters never clear their bar. This PR makes the link REACH both seats the same way. It does not make the ranking good. That is the larger work Dad asked for, and it is not claimed here.

## Open, owed, and not hidden

- A stale docstring says the feedback step returns nothing. Owed in the docs item, not changed in this PR.
- Nothing says "nothing close" out loud when the lane has nothing. Owed.
- The feedback loop (`apply_behavior_feedback`) has no caller. Owed: wire it to an observable signal, or remove it and its claim.
