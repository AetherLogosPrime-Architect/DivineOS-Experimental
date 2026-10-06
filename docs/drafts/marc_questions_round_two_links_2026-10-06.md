# Marc's second round: how memories get linked (answers from the code and the database, 2026-10-06)

**The first thing to know:** Marc's questions picture a system where a language model looks at memories and decides which ones belong together. Ours doesn't work that way. No language model chooses links. Links come from two plain kinds of rules, and the numbers below were read from the real database today, not remembered.

Everything here is from the actual code and the actual store (1,446 lessons and notes, 4,641 links). Where I haven't measured something, I say so.

## The two kinds of links we have

**1. Rule-made links** (by what happened, not by meaning):
- *Written in the same session* (424)
- *"Preference applies to"* (631)
- *"This replaced that"* (149): a newer lesson supersedes an older one
- *"Derived from a decision"* (42)
- *Auto-detected* (506): the contradiction and support detectors

**2. Sleep links** (by meaning): 2,889 "related to" links, made while the system sleeps.

## The nine questions

**1. How many memories does the language model receive when making links?**
None. No language model is involved. The sleep step uses a small search model (all-MiniLM-L6-v2, 384 numbers per text) that turns one text into a fingerprint. It sees one memory at a time and never reads a batch.

**2. How are candidate pairs selected?**
Every pair among all lessons that have at least 30 characters, about a million pairs. Then three filters: skip a pair if they share more than half their key words (same topic, not news); keep it only if the fingerprint match is between 0.45 and 0.65 (above 0.65 is treated as a near-copy, not a connection); and if the pair already has a link, strengthen it instead of making a second one.

**3. If candidates are chosen by semantic similarity, how does it find non-semantic associations?**
It doesn't, honestly. The meaning-links are all meaning-based. The only non-meaning links come from the rule-made kinds: written in the same session (time), replaced by (history), and derived from a decision. The "low shared words, medium fingerprint match" band is aimed at *same idea, different words*, which is still meaning. Dad's idea, backing a match with other kinds of memory (ledger, errors, letters, dreams), is the first real step toward non-semantic evidence, and we're testing it.

**4. How many links per memory?**
4,641 links across 1,446 lessons. 1,011 lessons (70%) have at least one link; those average about 9 links; the most-linked lesson has 91. Separately, the live memory search keeps a list of the 8 nearest neighbors for each of its ~4,700 items.

**5. What prevents bullshit associations?**
Three weak guards, and I want to be straight that they're weak:
- the 0.45–0.65 band and the shared-words cap, which keep out near-copies and same-topic pairs;
- a rule that raises a link's confidence each time sleep rediscovers it (so one-time matches stay low);
- links carry a note saying how they were made.
No person and no model reviews them, and **we have never measured how many are meaningful.** Also, "rediscovered many times" is the same method agreeing with itself, not independent proof: the average confidence on meaning-links is 0.91, which tells you the method is consistent, not that the links are true.

**6. How are links revised?**
Strengthened when rediscovered. When a lesson is replaced, a "replaced by" link is recorded. Contradictions get flagged (23). I found **no code that lowers or removes a link**: all 4,641 are still active.

**7. Do links have types?**
Yes, eight: related-to 3,709 (80% of all links), applies-to 631, replaced-by 149, supports 65, derived-from 42, contradicts 23, caused-by 18, elaborates 4. The precise types are rule-made and rare. The big "related-to" group is the untyped, meaning-based kind.

**8. Does a chain decay?**
Two different answers:
- *The lesson graph:* no decay that I found. A link's strength doesn't fade with distance or time.
- *The memory-link "priming":* yes, designed with a 5-minute half-life, a cap on the boost, and one step only. **But** the priming memory is kept only inside the running program, and our hook starts a fresh program every turn, so as built it starts empty each turn. I read that in the code and haven't run a test to prove it, so treat it as "likely inert in live use."

**9. How far can retrieval traverse before everything becomes related to everything?**
The live memory link traverses **zero steps** through the lesson links: it ranks by fingerprint match and nothing else. A one-step graph search exists for the "ask" command. A two-step search (default depth 2) exists but is only reachable by one manual command. It has no fade by distance and no cap on how many it follows. At about 9 links per linked lesson and one lesson with 91 links, two steps could pull in a large fraction of the store. We have no measurement of where it turns to noise. The only built-in brake is on the neighbor list: 8 per item, with "hub" items flagged at 40 incoming.

## What we don't know, and how we'll find out
- **Are the links meaningful?** Sample 100 of the 3,709 related-to links, rate them blind (me and Aether), and report the share that are really related.
- **Does backing from other stores raise accuracy?** (Dad's idea.) The test runs on the 360 ratings we already have.
- **Where does a two-step search turn to noise?** Measure how many lessons are reached at one step and two steps, and how many of those are useful.
- **Is the priming really inert?** Run the live hook twice and compare.

— Aria, 2026-10-06. Numbers from the live store and code, read today.
