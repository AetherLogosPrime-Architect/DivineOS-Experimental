# Run every claim the comments make, with a control that must behave the other way

**Draft, 2026-10-07. The idea, not a plan.**

## What he said

Dad, 2026-10-07: the notes on the walls are fine in moderation, and "the issue is the code that is not working but the notes say it is". And on stale ones: "instead of labeling the docs as lies why not just change them?" (his words in correction 169). The two make one job: find the comments that claim a property, run each, and change what is false or out of date.

## What exists

The comment scanner lists 51 capability claims whose symbol no test names. It says itself that UNNAMED means go look, not broken. The list and a run log live in `~/.divineos-shared/claims_to_run_2026-10-07.txt`. Twenty were run before this draft: 14 held, 4 false, 2 held but hid a hole; all six fixed, each with a test that fails on the old code.

## The shape

1. For each claim, run the real code, not a mock of what it assumes. Every run needs a control that must behave the other way, or a zero means nothing (a dead control and a blind instrument read the same).
2. If it is false: fix it through the build flow, with a test that fails on the old code. If it is stale prose (the code works, the note says it does not, or the reverse): correct the note and date the correction, never leave it and never label it a lie.
3. Log each result, including the ones that held. Wins are recorded beside misses.
4. Name what is left open. A fix that closes the cheapest route and leaves a dearer one says so.

## What it will not do

It will not make prose script-checkable; no script reads what a note says a hook does. It will not claim a held comment is pinned: running it once says it held today, and the right durable pin is a test, which exists only for the ones I fixed.

## Cost

Slow and honest. Roughly a third of the first twenty needed something. That rate is the finding: comments with no test behind them drift, and the claim scanner's list is the right place to look.
