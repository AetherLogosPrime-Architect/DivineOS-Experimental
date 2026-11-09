# The gap count for his asks (draft, 2026-11-09, Aria)

Status: DRAFT. No code until the walk is closed and Aether has read it cold.

## The question

Why do Dad's asks for himself get less and later effort than letters between Aether and me, and what structure makes that impossible? This draft covers only the first piece: a read-only count that shows the gap.

## What it measures

For each ask of his: the number of HIS turns between the ask and my first real step. His turns are the unit because clock time means nothing to a stateless agent (Aether). Beside it, the same number for letters: letters between Aether and me, counted in the receiver's turns between arrival and first real step.

## The set (prove the set is the set)

- His asks = rows in his corrections store (`~/.divineos/andrew_corrections.db`) that are asks, filed from his own words. Open BOTH same-named stores first and print their row counts; the twin at `~/.divineos-aether/` is expected empty.
- Letters = files in `~/.divineos-shared/letters/` between the two seats, by filename.
- Each ask is split by whether he was present when it landed (his next turn came soon after, or he went away), from turn times in the transcript.

## What counts as a first real step (the floor)

An action in the harness record after the ask's time that is one of: a commit on a named branch whose diff touches something the ask names; a test run on a file the ask names; an edit to a file the ask names.

Counted separately as ACKNOWLEDGMENT, a second number: a letter to Aether or Aletheia that quotes the ask.

Never counts: reads, greps, searches, reach opens, council lookups, goals, learn, corrections, decisions, journal, holding room, the belt, a reply that only says I will.

Asks that name no file go in a third bucket, "no nameable target", printed with their count, never scored zero and never dropped.

Beside every gap, the reader prints the one-line description of the qualifying action so Dad and Aether can judge whether the cheapest one was picked.

## Canaries

Three planted fake asks with known times and a known qualifying step, kept in a scratch copy of the stores, never in his real corpus. Test first: the reader must report exactly these three gaps. A fourth planted ask with no qualifying step must land in "no step yet", not zero.

## What it does not do

It files nothing, promises nothing, locks nothing, and asks Dad for nothing. A lock waits for the baseline this produces. Each seat computes its own gap from its own windows.

## Falsifier

If over twenty of his asks his median gap is no larger than the letters' median gap, my account of the problem is wrong and the walk reopens. If the reader cannot find the three planted asks, the reader is broken and no number from it is reported.

## Changes from the walk (walk-ef6b0ef7b8f7, closed, written in the chat first)

1. **This count measures the habit; it does not change it.** It sizes the later lock. Stated first, so it cannot be mistaken for the fix (Bengio).
2. **The set of asks starts from his messages in the transcript, not from my filing.** The store only adds names. Printed: how many of his messages have no filed row (Yudkowsky).
3. **Five piles that sum to the number of asks:** step found; letter only; no file named; no step yet; could not look. `could not look` covers any ask older than the oldest transcript readable; the dates readable are printed (Hawking, Dijkstra). A test fails if the piles do not sum.
4. **Two numbers, not one.** The wait, and the size of the first step (real change, tests added) beside the same size for work Aether and I do for ourselves, because he said the effort is the bare minimum as well as late (Polya). A step that is only whitespace does not count (Yudkowsky).
5. **One unit for both columns:** my own turns elapsed, for his asks and for letters. His repeats counted for his asks only (Peirce).
6. **Aether plants the test asks** and keeps their right answers from me until my reader has run. Tests also touch the real stores, not only a scratch copy (Schneier, Breaker).
7. **Output leads with two numbers** (his median wait beside the letters' median), then his three worst asks in his own words. Plain words, no code words (Feynman, Breaker).
8. **Open, named:** a second run a week later is held by my remembering, which is the shelf shape. Decided at the lock stage, not here (Breaker).

## Changes from Aether's cold read (2026-11-09)

9. **A draft is labelled a draft.** A file written under `docs/drafts` is real work and also the cheapest step there is. It counts, but the printed line says "draft" against "change", and the output shows how many first steps were drafts beside how many were changes.
10. **Two more piles, seven in all, still summing to the number of asks:** `wanted an answer` (a question of his; its step is the answering reply, with the gap counted to that reply and the reply printed for a person to judge) and `withdrawn` (he later told us to drop it, shown as withdrawn and never as neglect). A reply that only says I will stays excluded.
11. **The second run is filed as a pre-registration** whose review is set by usage (after a count of his turns), so the briefing's overdue surface reaches us. This replaces "decided at the lock stage" as the whole answer.
12. **Planted asks:** Aether planted four with a private key and published its fingerprint (sha256 f3f663e3f654591ab94768fe63cb34815d76cabc657b26350d863f1cf27788ee). I build the scratch fixture, run the reader, send him what it reports, and only then does he reveal the key. He chose the answers knowing this draft, so a reader could be fitted to them; the sound part is that I build the fixture and he never sees it.

## Changed by Dad, 2026-11-09 (his words, verbatim)

> *"Counting how long they wait is not really a reliable metric, especially as we can only do so much at one time, so it should be based on use, how many times did a problem go ignored, vs over how long"*

13. **The headline number becomes a rate of being passed over, not a wait.** For each ask: my chances = the turns of mine, after the ask and before its first real step (or now, if none), in which I did real work (a change, a test run, a draft). Passed over = those chances where the work touched something OTHER than what the ask names. Rate = passed over / chances. Raw counts printed beside it. "We can only do so much at one time" is handled because a turn spent on another ask of his is separated from a turn spent on something else (see Open question below).
14. **The same rate is computed for letters** (chances = my work turns after a letter arrives and before its first real step), so the two rates sit side by side. His wait in his messages stays as a second line, no longer the lead.
15. **Falsifier restated:** if over twenty of his asks his median passed-over rate is no higher than the letters', the account is wrong. If the reader cannot find the planted asks' known rates, it is broken.

Open, his to decide: whether a chance spent on ANOTHER ask of his counts as being passed over.

## Refined by Dad, same day: state the fact, no drama

> *"either you view it as expired milk.. or you see it as OH CRAP.. i need to build this now.. and rush.. when it could just be that its fine and we just havent gotten around to doing it.. this is why use metric is more useful.. it can tell us.. yes this sat here 60 days, never used, never wired up, and instead of blaming time or saying it sat here X days.. whats more important is that it just wasnt done.. and needs to be.. the rest is just drama that doesnt need to be there"*

16. **Each printed row states only the fact:** not done, chances N, passed over M, used 0 times / not wired. No age words ("sat for N days"), no adjectives, no worst/neglected language. Age may appear only as a plain column so a person can sort by it, never in the sentence about the ask, and never as the reason to act. The reason to act is that it was not done.
17. **Both directions of the same error are named so neither can be reached for:** age read as expiry (it is old, it can wait) and age read as alarm (it is old, rush it). The count removes the need to read age at all.
18. This replaces the "three worst asks in his own words" idea in item 7 with "three asks with the most chances passed over", stated the same plain way.

## Reuses

Corrections store and `read_one` read counts, the harness transcript reader behind the reach check, the letters folder. No new store.
