# A plain yes in chat confirms a held row: the pair is the receipt (draft, 2026-11-24, Aria)

Status: DRAFT, before any code. Reach opened and disposed (`reach-72994517da55`). Owed: council walk, tests first, run in my window, run in Aether's, then a draft PR. Idea first written by Aether (`workbench/a_plain_yes_in_chat_moves_a_row_to_the_held_shelf_draft_aether_2026-11-24.md`); the pair-as-receipt is mine and he took it whole.

## What Dad said (2026-11-24)
He did not understand why he would type a code line to confirm a held row. His words: *"Yes me saying to do it in chat should be enough without me needing to type code or commands."* The rule behind the code line is unchanged: nothing moves on a seat's say-so, only on his word. The exact line `hold <n>` was only ever the clumsy way to carry that word.

## What the code does today (read, not remembered)
`confirm_hold(correction_id, transcripts)` in `andrew_correction_tracker.py` reads his messages through `his_message.heard_in` and moves a proposed row to HELD only when one of them has a line that is exactly `hold <n>`. One write: it stores the prior status and sets HELD.

## The change
A second way into the same write, `confirm_hold_plain(ids, his_words, meaning, transcripts)`, run by the seat that holds the rows (row ids are per seat; the yes is read from that seat's own transcript, never from a letter that reports it).

The tool checks, deterministically, three things and nothing about meaning:
1. **His words are real.** `his_words` sits inside a message he typed, found through `heard_in`.
2. **It answers something that named the rows.** The last message of mine before his reply names every id being confirmed (as `149` or `#149`). A yes with no named rows in front of it moves nothing, and he never has to say a number.
3. **Order.** My message comes before his reply in the transcript, so an old unrelated yes cannot be reused.

Then it moves only the ids my message named, through the one existing write (prior status stored, HELD set, never twice). The receipt kept in `held_confirmed_by` carries the whole pair: my asking message, his words, and `meaning`, which names which question the yes answered. The tool does not judge that; a person reading the receipt can disagree with it.

Refusals each name their reason: his words not found in anything he typed; no message of mine before his reply names the id; the id was not proposed; the row is already held; `meaning` too short to say what was asked.

The exact `hold <n>` line keeps working. Same read-back both ways: after a confirmation the CLI says in plain words which rows went on the shelf, what each was before, and that `unhold` puts it back.

## What it cannot see
A seat that quotes his real words and reads them as a yes they were not. The pair makes that visible (the question and the answer sit side by side), it does not make it impossible. A yes to a different question two lines later, with the right row numbers in my message, is the failure Aether fears; the receipt must carry the whole pair and `meaning` must name which question it answered, so a reader can disagree.

## Attack surface
- A quote short enough to match anything ("yes"): allowed on purpose, because the named-rows message in front of it is what binds it.
- One yes confirming rows my message never named: refused per id.
- A relayed yes (a letter saying he said yes): never counts; only records `heard_in` reads as his.
- My message naming the rows casually (not as a question): the tool cannot tell; `meaning` and the receipt show it.

## Tests, first (all red before the code)
Real pairs in a temp transcript: a clean pair moves the rows and stores the receipt; his yes with no rows named in my message moves nothing; a pair where his words are not in anything he typed moves nothing; a yes that answers a different question than the one naming the rows (lunch two lines later) is the pinned test; my message naming 149 and 272 while the call asks for 281 refuses 281 and moves the other two; an id not proposed refuses; a second confirmation changes nothing; `hold <n>` still works; the receipt contains the asking message, his words and the meaning.

## Falsifier
If over the first ten holds any row is confirmed whose receipt, on his own reading, does not show a yes to that row, the plain way is dropped and the exact line returns.
