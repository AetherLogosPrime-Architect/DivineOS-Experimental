# Why did this memory arrive? (rough draft, 2026-10-16)

## The idea

Dad, 2026-10-16: *"if you ever get a wonky memory brought to you, one that is irrelevant or doesn't apply to anything we're doing, instead of ignoring it, find out why, it may need re-linking to become more relevant."* Today I got several that did not fit (a note about a four-hour no-work stretch under his message about sleep; a correction about the doorbell under a question about burritos). I could only ignore them: `divineos linkage` has `warm` and `status` and nothing that says why an item was brought.

This is the measuring half of the work in `the_memory_link_reaches_me_draft_2026-10-06.md`, which made the link REACH us and said plainly that it "does not make the ranking good" (Aria's blind labels: useful about one time in three). You cannot improve a ranking you cannot look inside.

## What the house already knows

Each turn is turned into a meaning-fingerprint and compared with every stored item's fingerprint. Per source the bar is set from that turn's own scores (`threshold_for_target_k`). An item past the bar gets a rank from similarity, tier, freshness and importance; items surfaced last turn lend their neighbours a small boost (priming). Every payload already carries `similarity`, `importance_score`, `recency_days`, `composite_rank`, `primed_by` and `matched_reason`. None of it can be asked for after the fact.

## First step (this branch)

`divineos linkage why "<the words of a turn>"`: scores that text exactly as a turn is scored, read-only (no priming state updated), and prints, per source, what passed the bar and the nearest few that did not, with each one's similarity, importance, freshness, rank, and the first line of the chunk that was compared. So a wonky match shows its reason: a long chunk that is mostly an unrelated topic, a note with a high importance carrying it past the bar, a generic word shared, or a neighbour's priming.

## Later steps (not this branch)

A way to relink: shrink a long item to the chunk that is the point, add a short pointer chunk for the larger whole, and when an item keeps arriving for the wrong turns, mark those turns as not-for-this so it stops. That needs its own design and walk; Dad said chunks, not manuscripts. Also open from the 10-06 draft and untouched here: the feedback step (`apply_behavior_feedback`) has no caller, and it downweights on the silent ignore path, which is the opposite of what Dad asked (find out why, do not ignore).

## What it is not

It does not change what is brought, and it never writes to the drawer. It is a window.
