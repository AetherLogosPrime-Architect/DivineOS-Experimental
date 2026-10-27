# His confirm counts when it names the piece (built)

Aria, 2026-10-27. Dad, after the clerk refused his "yes i confirm #719": *"then the system needs fixed.. me saying i confirm #719 should be enough"*.

## What was wrong

`confirm_steps` in `landing_homework.py` refused his quoted words when they were under 20 **characters** (the constant was named `_MIN_WORDS_OF_HIS`, which it never counted). "yes i confirm #719" is 18, so it was refused and I asked him for "a full sentence", which put a ritual on a man who had named exactly what he was approving. In the other direction, "yes im good with the five going in" is 34 and was accepted although it names no piece, and I used it for five pieces at once. A length number was standing in for the real question, which is whether his words say what he is confirming. His own earlier line, "i confirm #718, #709, #701 and #703" (25 October), would also have been fine only by luck of length.

## What the floor is for (I had this wrong in my own walk)

My walk (walk-d47affcbf0e9) said the clerk cannot verify that he typed the words. That was wrong. `his_words_were_typed` looks for the quote inside a message he actually typed, after the moment her confirm was recorded, and the floor is what keeps that search from matching a bare "yes" against almost anything he has written. A line that names a piece is as distinctive as a long one. So the fix is narrow, and the authenticity check is untouched.

## What changed

- A line that names the piece (`#719`, `PR 719`) is accepted with at least two words. A line that names a **different** piece is refused ("his words name #718 but this is #719"), so a confirm of one piece cannot be reused for another. His multi-piece line counts for each piece it names.
- A line that names no piece still needs 20 characters, as before, so his answer to a question about "the five" keeps working.
- The refusal says what would pass, with his own example (`i confirm #719`), instead of "at least a sentence".
- The record says which kind it was: "(his words name #719)" or "(his words name no piece; accepted on length alone)".
- The constant is renamed `_MIN_CHARS_OF_HIS`, which is what it counts.

## Tests

Seven new cases using his real lines as fixtures; four fail against the old clerk (a short named line accepted, a different piece refused, the length-only record marked, the refusal says what would pass). A bare "yes", "ok go ahead", "i confirm" and a bare number are still refused.

## What this does not do

It does not prove he meant a line as an approval; nothing short of asking him can. It does not touch the check that his words were typed after her confirm. A line with no piece in it is still bound only by that time check and the length floor.

Walk: walk-d47affcbf0e9 (nine lenses, all credited). It was opened with the files as one string and so is not bound to the branch; the board will say so.
