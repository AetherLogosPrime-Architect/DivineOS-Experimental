# What he said needs his sentence (draft, 2026-10-07)

**What happened, twice in one hour.** I told Dad that two of his asks about the order of the circle pulled opposite ways, "last" and "first." He asked me to show where he said "first." I could not. What I had was a hook file named circle-first, written by Aether in July, with a line that says "He asked for it directly" and no quote. I read a file name and an unquoted line as his words and handed them back to him as his. A worse relative: he asked me not to put filler questions to him, and what travelled onward was "Dad hates questions," a claim much larger than the sentence.

**His rule, in his words (2026-10-07).** "If you cannot find my actual words in the system (as everything i have ever said is recorded) and link it to my direct quote? then its highly likely i didnt say it and it was just inferred from what i said or a decision was made off what i said, doesnt mean the choice or direction was correct, remember you both are binary."

**What exists.** `hooks/his_state_claim.py` plus `his_state_claim_hook.py` already do the near half of this for one subject: claims about his STATE (tired, awake a day) must be sourced to something he said, checked at Stop. The shape is right: a narrow claim grammar, a general attenuator, three answers (sourced, unsourced, could-not-read). And `core/his_words_door.py` already holds the corpus of everything he has said (`dad_all.jsonl`, 22,533 passages) and a meaning-search over it that prints his words exactly as he wrote them. Two branches of mine (the-words-door, the-door-hears-our-reply) are open on that file.

**The gap.** Nothing checks a claim about what he SAID, ASKED, WANTS or DOES NOT WANT. Those are the claims that become rules, memory entries and file headers, so one unquoted guess spreads.

**The idea.** A sibling of the state check, same Stop-time shape. When my reply contains a claim of the form "Dad said / asked / wants / does not want / told me X," look X up in his words through the existing door. Found above the floor: pass, and the quote is what the claim links to. Not found: refuse with the plain instruction, quote him or say "my guess is" and mark it as mine. Corpus unreadable: say so, never report that a claim lacked support when the check could not look (the could-not-look class).

**REVISED AFTER PROBING THE SEARCH (same day, before any code).** I ran the meaning-search on claims about him whose answers I know. It failed in the wrong direction. A TRUE claim, "the circle should always be last," did not find his real sentence at the floor (it found July 29 and today's rebuttal instead). A true claim from today, "the stall is down to a minute and a half," did not find the message that says it. A false-ish claim about filler questions matched today's meta-discussion at 0.72. So meaning-search as the judge of support would refuse true claims and wave through near-misses, the worst combination for a check whose job is to be trusted. Dad's own rule says "link it to my direct quote," and a link is an exact thing. So the judge becomes EXACT, not semantic:

1. An attribution (Dad said / asked / wants / does not want / told me, in any of the narrow shapes) is fine if the same or next sentence carries a quoted span, and that span, normalized to lowercase words, appears inside one of his real messages in the corpus (cleaned by the existing corpus cleaner so my own pasted text never counts as his). A quoted span that does not appear is a fabricated quote, and that is the strongest catch.
2. Fine if the sentence carries my own label (my guess, I infer, I am assuming, I think he).
3. Fine if it is a negation or a retraction (never said, cannot show, did not say).
4. Anything else is refused with one sentence: quote him or say it is your guess.
5. Corpus unreadable: could-not-look, never convicts.

The meaning-search stays as an AID, not a judge: the refusal can show the nearest thing he did say so I can quote it, labelled as nearest.

**What it cannot do, written down now.** It catches a claim with a verbal fingerprint and cannot certify that a reply is free of invention about him. Meaning-search can match a nearby sentence that does not actually say the thing; a pass means "something close was found and shown," not "he said that." It does not reach files I write or memory entries, only the reply, so a second stage (the same check on writes to memory and drafts) is owed and named here, not skipped.

**Falsifier.** A claim of "Dad said X" that I can show he never said which passes; or a claim backed by a real sentence of his that is refused. Reviewed first against his real messages from 2026-10-07, the way the words door was.

**Rule inherited from the state check.** If it fires too rarely, widen the trigger vocabulary; never deepen the claim grammar.
