# His words door shows each thing once — draft (2026-09-26)

## His words

> "the stuff that gets brought to you first needs to be filtered especially for duplicates otherwise one thing may trigger 50 times ive said it before"

## What the live door did today (measured on the real table, not guessed)

1. **It showed his current message back as "said before".** Three times (0.95, 0.78, 0.69). The table appends his message to the corpus *before* the door searches, and the door's same-message check compares the whole message with a cut passage. Cutting drops his ".." pauses, so the strings never match.
2. **It showed the same message twice.** The 07-04 and 06-18 passages each appeared twice, once whole and once as the first cut of the same message. Two cuts of one message aren't two things he said.
3. **The repeat count counted topic.** "18 times" for "sync with Aether". That's Aether's clustering piece, not this one.

## The shape

- **Normalize before comparing** (lowercase, word characters only). A passage whose words are contained in his current message is the message itself.
- **One quote per original message:** at most one hit per source timestamp, and the highest-scoring cut wins.
- **Near-identical hits collapse** into one (normalized prefix match). The repeat line already carries the count, and Aether's clustering will make that count mean "same ask" and not "same topic".
- A pin for each, built from today's real cases: the 07-04 message cut in two, and his current message appended before the search.

Root cause, per his 06-18 words: the door compared text in two different shapes (whole vs cut), so equality could never hold. The fix compares in one shape. No tuning is needed.
