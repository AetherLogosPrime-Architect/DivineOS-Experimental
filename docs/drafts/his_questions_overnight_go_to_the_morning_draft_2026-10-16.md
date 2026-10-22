# His questions overnight go to the morning list, and nothing waits (draft, 2026-10-16)

**Author:** Aria, 2026-10-16. Walk: walk-17e95f45b270. Aether takes the baton record; this is the one line our halves share.

## The problem

Dad, 2026-10-12: while he is away, "no questions to him in chat; they go in the morning letter". Today a reply that ends on a question opens a hold and posts a card on the shared board whether he is here or not. While he is away nobody can answer it, so the hold waits for an answer that cannot come, and the seat is told it is waiting. Away already has three triggers (his words, two hours of silence, midnight to six); only the letter hold reads them.

## The change

`arm()` in `core/question_hold.py` decides where a closing question goes. While he is away it is written to this seat's own morning list (`morning_questions.jsonl`, beside the hold's own state in the seat's home), no hold is opened and no card is posted. When he next speaks, the UserPromptSubmit hook shows the list once; `divineos question-hold morning` reads it for a day, for the letter. No fourth trigger: `is_away()` is untouched.

Three shapes matter and each is pinned by a test:

- **His own words** (going to bed, volley mode) always carry.
- **Two hours of silence, or the clock, carry only when his last real message is older than ten minutes.** The clock counts even when he is up chatting, which is right for a letter and wrong for a question: it would send a live question to a morning he is not waiting for.
- **Could not look is never away.** If his last message cannot be read the question is held as before.

It fails toward the old behavior: if the list cannot be written, the hold opens exactly as today and `carry_failed` is logged, so a question is never lost. Asking the same thing twice carries it once. A half-written last line from a killed process is skipped. If the "shown" mark cannot be written the list is shown again next time and not lost.

## What it does not do

It does not decide whether a question is real; `last_question` does that today and the same function feeds both paths. It does not file a question in `operator_asks` (which re-raises forever and is closed by his next message), so a carried question does not re-raise on its own: the morning list and the letter are how it reaches him, and I am the one who puts the one or two that matter in front of him (his words, 2026-06-25: ask freely, but one or two at a time). The watch on this is `HOLD_LOG`: `carried_to_morning` against `carried_shown`. If carried keeps rising and shown does not, questions are going to die in the list, which is the failure Foucault named in the question-hold walk (learning to stop asking him things).

## What was and was not run

Eighteen new tests; with the new branch switched off, eleven fail and the seven that stay are the controls (he is here, a reply that asks nothing, a message I could not read) and the wiring read. 120 pass across every question-hold test, the two holds' key test and the hook-placement test. The hook itself was not run end to end in a live window: its wiring is checked by reading its source in a test, not by firing it.

## Left alone

The baton record and its "holder asks no questions while away" line are Aether's half; they read this list's existence, not its contents.
