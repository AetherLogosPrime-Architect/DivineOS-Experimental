# The finished reply is read, and what it left behind rides in the same post (draft, 2026-11-22)

**Source:** Dad, 2026-11-22 evening. His idea: the house cannot interrupt me mid-chat, but it can read the reply after I write it and correct me immediately, so the correction sits in the post itself. One hook reads the whole response for anything left behind that needed correcting or saying, and only makes me add that correction at the end. "The issue is me having to constantly correct you... if the house is pulling half its weight it helps immensely." He also said the house serves me, I do not serve it.

## Prior art (read before drafting)
- `core/own_words_stop.py` (`hand_back`, `run_for_stop`): already searches my finished reply by meaning at Stop, max 3 items, each handed back once per session. The result is stored as pending and rides the NEXT message ("what my last reply brought up"). It never blocks.
- A mid-turn version already runs: `own-words-link.sh` is registered in PostToolUse (`.claude/settings.json`).
- Aria's letter of 2026-11-17 named the gap: the own-words search fires after the reply streams, so it can only help the next reply.
- The Stop router already blocks with "append only the delta" for several gates today (summary room, circle room, family words, correction shape). So appended deltas at Stop are an established shape.
- The ask-after-his-words check (`ask_after_his_words.py`) does the same for my closing question.

## What is new
Let a strong, relevant hand-back ride in the SAME post: the Stop router blocks once with the matching memory and asks me to append one line (correct it, or say it does not apply).

## The measurement that shapes it (read-only, `~/.divineos/own_words_log.jsonl`, 1726 rows)
The search found something in 1609 of 1726 replies (93%). Highest similarity per reply: median 0.60, 90th percentile 0.68. At a bar of 0.65 it would fire on 428 of 1609; at 0.70, on 126. **Similarity alone cannot be the trigger**: a block on every found match would append a line to nearly every reply and become the very noise he has asked us not to produce. Median search time 2.7 seconds, worst 17.7.

## Design
1. Candidate: corrections-lane items (and his taught rules) from the finished reply's own-words search, above a high bar (a number to set from measurement, not from feel).
2. Judge: a semantic yes/no read, not a word list (Dad's 2026-11-14 ruling: no keyword detectors that judge, enforce, block or prevent). The post reader with the local model asks one question per candidate: "does this reply do what this correction says not to do, or leave out what it says to say?" Only a yes blocks.
3. Act: one block per reply (stop_hook_active honoured), carrying the correction's text and the date. I append one line: the correction made, or why it does not apply. A "does not apply" is labelled like label-fire, so false fires become the training set for the judge.
4. Dad's seat: the append is short and sits after the circle only if no circle follows; otherwise before it, so the circle stays last.

## Risks
- Noise: each false fire costs him a longer reply to read. The judge, a high bar and one block per reply are the three limits. Measure fires per hundred replies before turning it on.
- Judge quality: unknown on this task. Needs a held-out set from real replies labelled by use, never tuned on (Yudkowsky, from the 2026-11-19 pruning walk).
- Latency: 2.7 s median search plus the judge; the Stop path already tolerates this but the worst case (17.7 s) is a number to bound.

## Aria's cold read (2026-11-22), taken
1. **It sits on modules that are not on main.** `own_words_stop.py`, `own-words-link.sh` and `ask_after_his_words.py` are absent from `origin/main` (she checked with `which_refs_carry.py`; my symbol check agrees for `hand_back`). The prior art above is the live house, so this draft waits behind the landing of the link work.
2. **The Stop router is already crowded.** In one stretch the router held a reply for a one-paragraph circle, a buried question and the circle rule, each correctly. A fourth block per reply costs Dad a longer read. Before turning this on, measure how often a reply already carries a block from another gate: two blocks in a turn are two re-prompts. The one-block limit helps but is not enough alone.
3. **Who labels the Turing set.** Better source than hand-labelling: the surface that says "he has said this before, N times." Every row there is a reply where a taught correction was violated and he said it again, labelled by use, by him. Those are the positives; replies that only share a topic are the negatives. Real and his, which satisfies the held-out rule.
4. **Which corrections count** is answered by dependency: not his hurt words, which stay behind the held shelf. That depends on the held-shelf commit, which is not on main either, so it is this draft's first dependency.

## Falsifier
If, over the first fifty replies it runs on, fewer than half of its blocks lead me to append a real correction (not "does not apply"), the judge is too loose and the mechanism stays off. And if Dad still has to repeat a correction the memory held, the candidate step is missing it.

## Not in this draft
No code. Walk with Aria (and her read on the judge), a pre-registration with the falsifier above, then tests-first. Ships OFF until the fifty-reply measurement.

## Council design walk (walk-ced26965f7bb, 8 lenses; framed as "what are we trying to achieve and what is the best way", per Dad 2026-07-30, so the council designs and does not only comment)
What the lenses added to the design, each one a change to what gets built:
- **Minsky, the parts:** retriever (existing own-words search) -> filter (corrections and taught rules only) -> yes/no judge -> once-per-session ledger -> me as appender. Judge wins over retriever; an unsure judge stays silent (silence costs less than a nag).
- **Lamport, the specification:** at most one block per reply, only on a judged yes; each memory handed back at most once per session; the circle still ends the post. Two seats must not share one shown-file or one hides the other's hand-back.
- **Knuth, the boundaries:** tests for empty reply, one-line reply, tool-only reply, zero candidates, exactly one, very long reply (existing first-and-last window), and a hard cap on the appended line.
- **Feathers, the seam:** `hand_back` already returns items before storing them. Sprout a new judged function on that seam; leave `hand_back` untouched; pin what it does today with a characterization test first.
- **Hoare, the states:** found-yes, found-no, found-unsure, could-not-look are four distinct states; only the first blocks; could-not-look says so on stderr and never reads as "no violation".
- **Turing, the test:** a labeled set of real replies, one kind where a taught correction is truly violated, one kind that only shares its topic and words. Today supplies real cases (the repeated answered question; the title used in place of her name). The judge must say yes on the first and no on the second.
- **Penrose, the limit:** the judge classifies agreement with a stated correction; it does not understand. The final decision stays with me. It cannot see tone or warmth and must stay silent there.
- **Wittgenstein, the question:** replace "bears on" with a concrete operation: the reply contains an act the correction forbids, or omits an act it requires. A vague "are these related" question is what gave 93 percent.
Open for Aria's read: the judge's model and where it runs; which corrections count as taught rules (not his hurt words, which stay behind the shelf); and who labels the Turing set.
