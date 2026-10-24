# A pasted line cannot become his yes (draft, 2026-10-17)

## What was wrong

`his_words_were_typed` (the landing clerk, #660) accepts a quote if it is a stretch of any stored message of his, compared in lower case with spaces collapsed. A message in which he PASTED a letter is stored whole, with the pasted text inside `<pasted_content id="..."> ... </pasted_content id="...">`. So a line of that letter, "yes, land it" or "CONFIRMS: #594", counted as words he typed, got the paste's time, and passed both the typed check and the time check as his yes. Nobody has to intend it. Found by Aletheia on 2026-10-17 reading Aria's #594, which had cut the paste in the words door only. Measured: the corpus holds 62 such messages, so the shape is real and the probe can find it.

## What this changes

1. `his_message.py` gets `typed_part(text)`: the message's own part (`his_part`) with any pasted block cut out, in one home beside `his_part`. The closing tag carries the opening tag's id, so a pattern wanting a bare closing tag never finds the close; an unclosed block runs to the end of the message.
2. `his_words_were_typed` matches against `typed_part`, so only what he typed counts.
3. Pins: a yes-shaped line that exists only inside a pasted block is refused, and the same words typed outside a paste pass (the control). An unclosed paste hides nothing he typed before it. A closing tag with the id still closes, so his own words after a paste count.

## What it does not do

It does not change the words door (Aria's #594 has its own copy of the same regex; the plan is that she imports `typed_part` and deletes hers once either lands). An uppercase `<PASTED_CONTENT>` leaks, since the harness writes lower case (Aria's named boundary). Text he copies in WITHOUT the harness tag, for example by typing it out, is his by definition.

## Falsifier

If a quote that appears only inside a pasted block is ever accepted as his words, or his own sentences typed around a paste are ever lost, the change is wrong.

## Who reads it

Aria cold, Aletheia, Dad's yes. It rides on #660's branch because the function it fixes exists only there.
