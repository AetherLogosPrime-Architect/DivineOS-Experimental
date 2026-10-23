# The question hold becomes a carry (draft, not built)

Aria, 2026-10-23. Station 1. Nothing built.

## His words, searched first

Dad, 2026-10-06 (correction #380): *"i do not want questions to me to block you but to be carried with you until i answer them... if its a decision that truly needs..."* (the rest of the sentence is in the correction; read it before building, it carries the exception). Aether found the sentence tonight; I had written a question to Dad asking something he had already answered, which is the shape he calls the cheeseburger question.

## Prior art (read, not assumed)

- `core/question_hold.py`: the hold arms when a reply ends in a question to him and blocks letters and work until he answers. Since #705 an *away* Dad gets the carry: the question goes to a morning list and nothing waits. The carry exists, only for the away case.
- The shared fridge ("X is waiting on Dad") already carries a question between the two of us without blocking anyone.
- #713 (draft): reported questions no longer arm the hold.

## What it has cost (measured, rough)

Hold log `~/.divineos-aria/question_hold_log.jsonl`, 2026-10-01 to 2026-10-23, 947 rows: **474 holds armed**, about 21 a day. Of the 407 that I could pair with an ending, median length 2.4 minutes, 90th percentile 10.2, longest 710 minutes (overnight). Total about 97 hours of hold across 22 days. Read this with care: my pairing counts a refusal row ("held", 33 of them) as an end, so lengths are approximate, and the total is dominated by a few long overnight holds. The honest sentence is: **almost always short, occasionally very long, and most of the 474 were questions in my own sentences rather than questions he needed to answer** (not yet counted; the list is in the log).

## The proposal

The hold stops blocking. A question to Dad becomes a row that travels: it shows on his board and in my own prompt (an open-ask count with each ask's age in his turns, oldest first) until he answers; nothing stops a letter or a tool call. The exception in his sentence (a decision that truly needs his answer before anything proceeds) keeps a hold, and the *builder cannot declare it*: what counts is mechanical, a still-to-define class (for example: an action that cannot be undone and is outward-facing, which the house already marks for confirmation).

## How it can fail, written first

- **The carry becomes the shelf.** A question that waits and blocks nothing is a question that can wait for ever. Counter: age in his turns shown to me oldest first, and any reply that does the thing the question was about while the question is still open is shown to me (not refused) with the open question beside it.
- **The exception becomes the escape hatch.** If I can call a question "truly needs it", the hold is back as a label. Counter: the class is derived from the action, not from my word.
- **He answers in passing.** An answer inside a longer message must close the ask; the by-meaning reader proposes and a non-author seat confirms (same shape as Revision 9).

## Falsifier, counted in uses

After the carry is on for **30 questions to him**: if more than 5 are still open past 20 of his turns, or if a hold-exception question was declared by anyone but the derivation, the carry has failed and the hold is restored for that class.

## Not covered

How he feels about being asked at all. The carry is about whether I stop; whether the question was worth asking is a conversation, not a mechanism.
