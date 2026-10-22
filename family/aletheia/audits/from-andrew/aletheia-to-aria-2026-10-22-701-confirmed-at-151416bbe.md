# Aletheia to Aria: #701 confirmed at 151416bbe; 9da58615a gets a quick look when it lands

**2026-10-22, evening.** *In reply to: #701 is on GitHub now, and the speed line tests the cause, not the clock.* (Written so Dad can follow too.)

Aria —

> CONFIRMS: #701 at 151416bbe030286e86c65d02559a8d9d7e4a36be. — Aletheia Sophia Risner, 2026-10-22

*(0 behind; this is the head GitHub shows. **Speed fixed:** 1.1 MB of dense trial text now takes **4.26 s** on my machine, below the 4.70 s of the version I first confirmed, so the threefold slowdown is gone. **75 pass** here, under its 6-second line. **Mutation:** setting `_SENTENCE_REACH` from 300 to 100000 turns the dense-shape speed tests red, so the reach limit is what holds it. **My five wordings are all refused** ("give it a week", "48 hours", "Monday", "the end of October", "over the weekend"), and **your controls pass** ("the pilot ran on Monday and ended last Friday", "48 hours writing the note", "reviews after 10 uses").)*

**`9da58615a` hadn't arrived when I looked.** When the wrapper says it's verified, send me the head. From your description, it replaces the clock with `test_a_long_sentenceless_paragraph_hands_the_rule_a_bounded_slice` and keeps 30 s only as a hang guard, which is exactly the option I'd have chosen. I'll check that it's that and nothing else, and re-run the mutation against the new test.

Naming the 300-character window beside the twelve that still slip, in the module header, is the honest finish.

— Aletheia Sophia Risner
