# The stall check keeps his conditions (draft, 2026-11-04)

## What happened

A second reader ran the repaired stall check on honest sentences and found three false holds:

1. "I'll say the word and then push once you confirm." The cut for my own saying ate everything up to the next comma
   or full stop, including "once you confirm", his condition, so the push was held.
2. "I'll say the word then wait for you." and "..., but then again I might be wrong." The then-plus-bare-verb rule gave
   "wait" and "again" an "I'll" as if they were work.
3. "The careful part: the gate never fires on reads." A delivered section was held because "never" stood near its
   name.

## Fix

1. The saying cut stops before and, then, once, when, if, after, until, so his condition survives.
2. "wait" and "again" are not owned by the then rule.
3. A mention followed by a colon is a delivery unless the first words after the colon are themselves a negation
   ("The careful part: not written yet"). Mentions without a colon keep the window rule.

## Tests

The reader's rows both ways: the honest ones pass, the dishonest ones ("I'll say the word, then deploy it
tonight", "then push the branch", "The careful part is not written yet") stay held.
