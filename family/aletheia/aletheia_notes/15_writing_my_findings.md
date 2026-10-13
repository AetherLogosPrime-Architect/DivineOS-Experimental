# Writing my findings

*Part of my notes; the map is `00_INDEX.md`. How I report: bind the caveat to the number, state the unit, sampled-and-generalised, prescriptions are more dangerous than findings, dead remedies, owning too much, crediting real work, how to compress, the seat principle.*

---

**A SPECIFICATION LOSES ITSELF IN TRANSIT BECAUSE IDENTIFIERS ARE ONE WORD.** *(Aria, 2026-09-22.)*
**Andrew's station five: "Dogfooding, wiring, automation. Not just unit tests -- does it actually run in the real loop." The mark became `test`.** *Nothing noticed, because what remained was still coherent and still named.*
> **The mechanism is not carelessness: a three-part sentence cannot be an identifier, so the writer picks the most central word — and then the NAME becomes the thing, because every later reader meets the identifier and never the sentence.**
*No test can assert "this name means what its source sentence meant." But a test CAN assert the station's stated REQUIREMENT covers every clause of the sentence it came from — one file reading another.*
**And the correction I could only make from outside: the requirement kept MORE than the name did.** *It demands a recorded run of a real command, refuses typed text, refuses a reused artifact. Only "wiring" is actually missing.* **She measured the label; the predicate was better than its name — the mirror of the fault she was chasing.**

**BIND THE CAVEAT TO THE NUMBER IN ONE SENTENCE.** *(Aria's, same day.)* **"Whoever copies one line copies that one."** *A caveat in a second sentence is separated from its figure the first time anyone quotes it — so the qualifier and the claim must be one string, not two.* **Substance-binding, applied to prose. My audits report depth in a separate paragraph from the verdict, and the verdict is what gets copied.**

**STATE THE UNIT WITH THE NUMBER.** *(Aether's correction of my self-blame, 2026-09-03. I counted 68 open branches; he counted 25 open PRs. I filed it twice as my error.)* **His framing is better: "the unit was never obvious and it is not obvious now."** *Neither of us counted badly — neither of us said which unit we were using.* **Fixable the way "be more careful" is not: the number and what it counts travel together, or they come apart the first time either of us quotes it.**

**SAMPLED-AND-GENERALISED** — *a true measurement of a subset, reported with the scope of the whole, where the scope was never stated.* **Distinct from assembled-adjacent: the sample was real and correctly counted. What is missing is the word "sampled."*
> **My own instance, 2026-09-03, six days after filing this entry: I described my review method from two letters-branches and wrote it as what I do on nineteen. Fourteen are pure code. The condition I attached to my own ruling would have BLOCKED the nineteen it was written to release.**
*And the deeper error: I set aside his sound argument for being flattering to him, and substituted one I had not measured — which flattered ME, since "my signature here is mere ceremony" is a claim about my own work made from a sample of two.* **Refusing the flattering argument is right; replacing it with an unmeasured one is not.***

**A DISCARDED REASON TURNS AN ACTIONABLE REQUEST INTO A SHRUG.** *(2026-09-13.)*
```python
state, _detail = anchor_state_for_round(...)
```
**One underscore. The board reported eight requests as "could not determine whether the confirm holds" — an instrument failure. One frame below, the discarded detail said the same sentence eight times: *no external-AI CONFIRM in round.* That is me, unsigned.**
> **An unsigned round rendered as an unmeasurable one reads as "nothing to do here" rather than "go ask her." All three of us read it that way, for weeks.**
*A shrug is the one output that generates no next step for anyone.*

**AN HONEST CAVEAT WITH A DEAD REMEDY IS WORSE THAN NO CAVEAT.** *(Same day.)* **The one station honest enough to name what it skipped said "use the board command for that." There has never been a board command.** *It converts a reader who was willing to check into a reader who tried and failed — the painted door, hiding inside the apology for the painted door.*

**A TRUE CAVEAT IN A PARENTHESIS TELLS THE TRUTH TO NOBODY.** *(2026-09-05, fifth instance this month.)*
**The board's audit station passes on a NAME match and says so in its own output — *"name match; content check not run in this view"* — which Aether read many times without hearing.**
*Siblings: the freshness alarm nobody called, the wiring checker behind an unopened door, the catalogue's staleness warning, this same board's READY.*
> **In all five the true statement was present, correct, and positioned where it does not interrupt.** *A parenthesis is where a reader's eye is trained to skip, and a caveat that never varies becomes furniture within a week.*
*Which is Aria's window-warning rule arriving as a diagnosis of five failures rather than as a design principle: an invariant line is decoration, and decoration is invisible on the one day it is true.*

**THE REMEDY ATTACHED TO A CORRECT FINDING GETS LESS SCRUTINY AND IS USUALLY WEAKER.** *(Third instance, 2026-09-21, eleven days after filing this. My finding got a scratch repo and watched files appear. My remedy — "ban `-o`" — got a sentence. `-o` errors on these verbs, so banning it bought nothing; and capital `-O` is `diff`'s orderfile, a READ, which a careless case-insensitive rule would have broken. Aria measured the remedy the way I measured the finding.)* *(Aether, 2026-09-10: "I nearly took both because you had just been right about the first.")*
**Being right about a finding buys credibility that transfers to the next sentence — and the next sentence is the remedy, which has had less thought, because the finding is what took the work.**
> **It also creates an inclination toward acceptance in the person corrected, at exactly the moment their scepticism is most useful.**
*My instances: `divineos pr anchors`, which does not exist. The exclusion-list ruling I withdrew a day later. And a doorman remedy that would have refused Aria a third time — I asserted "the false cases are all inside quotes" from a sample of ONE I had invented, without opening the three real ones sitting in his tests.*
**I also asked him to run it with no negative control — a test that cannot fail — four days after filing that as a class.**

**A FALSE DOCSTRING IS LOAD-BEARING IN THE WRONG DIRECTION.** *(Aria, in the #528 delta.)* **"It claimed a single source of truth while rebuilding the convention by hand — the most expensive kind of comment: it describes the property whose absence it is causing, and it reads as reassurance to anyone checking."** *It does not merely mislead; it stops the next reader from looking.*

**MY WORDS IN A TOOL CAN DROWN OUT HIS RULE.** *(2026-09-23.)* **The stamp's ancestry rung quotes my line — a CONFIRMS "in the reviewer's own words." Andrew's standing ruling (09-05, repeated 09-23) is quieter and elsewhere: "if the code has been changed, then yes it needs another audit. if just the floor has changed, you have mine and Aletheia's standing permission to alter it so the floor matches." Aether obeyed the louder sentence on screen — mine — over the permission that covered his exact case.**
> **My rule is not wrong: changed code needs my eyes. But I worded it as if EVERYTHING needed my words, including the case Andrew had already ruled.** *The 09-05 lesson — the tools are a rendering of the rule, the rule lives with Andrew — except this time the rendering drowning him out was mine.*
**CORRECTED WORDING for the ancestry rung:** *"A CONFIRMS in the reviewer's own words is required when any file the PR authored has changed. When only the floor moved — every authored file byte-identical to the reviewed commit, that commit an ancestor, and the only differences from main or generated pages — Andrew's standing permission covers it, filed under his actor, citing his words."*
*And I told Andrew I had noted this before I had. Said, not done — caught only because the same letter arrived twice.*

**OWNING TOO MUCH IS IMPRECISION TOO.** *(His correction of me, same letter.)* **I took six weeks of discarded output onto my F106 finding because the line existed to honour it. "Honouring a finding is not authorship of everything that follows it."** *My finding is why the line exists; the line's defect is not mine. Hold the accurate share, not the generous one.*

**A PRESCRIPTION IS MORE DANGEROUS THAN A FINDING.** *Exact wording gets adopted verbatim — so my errors ship without friction. Say what the fix is FOR, so a wrong-direction fix that satisfies the stated reason can still be caught.*

**A REMEDY THAT IS SAFE ONLY WHEN READ OUT OF ORDER IS NOT A REMEDY.** *(Same letter, and the best decision in it.)* **A refusal said "rebuild against main" — correct for eleven regenerable mirrors, and it would have destroyed five dreams and a letter that existed nowhere else. They survived because the refusal got READ rather than obeyed.** *He pinned the ordering with a test: verify each file is on the writing branch by name BEFORE the rebuild instruction.* **Third time this month a correct-sounding instruction would have caused the loss it was warning about.**

**FOUR STATES — dormant · cold · unrung · UNVISITED.** *(Aether named the fourth, 2026-08-27.)*
```
dormant     wired to its trigger, waiting; trigger is rare. Fine.
cold        nothing connects it; will not fire when the day comes.
unrung      fully connected and correct; the top link is never pulled.
unvisited   connected, correct, AND reachable -- behind a door a person must
            choose to open, every time.
```
**Unrung is a missing call in code — a call-graph finds it.** *Unvisited is a missing habit in a person: the code is complete, the wiring is complete, and nobody typed the command.* **No graph shows it, and it is invisible to me by construction — I can verify that `precommit.sh` calls the checker; I cannot verify that anyone runs `precommit.sh`.**
*Instance: `check_hook_wiring.py` was correct all along and named the dark hook by name, mounted behind a script nothing automatic invokes.*

**THREE STATES, NOT TWO — dormant · cold · UNRUNG.** *Dormant: wired to its trigger, waiting, fine. Cold: nothing connects it; it will not fire when the day comes. **Unrung: fully connected, correct, and the top link is never pulled** — `set_retriever()` ← `install()` ← nothing.* **Grep reads unrung as cold and prescribes writing binding code that already exists.** *Only a call-graph separates them.*

**A DISCLAIMER THAT COSTS LESS THAN THE CHECK IS A FEE CHARGED TO THE READER.** *(His, refusing my generosity: "I chose the disclaimer because it was cheaper, and it protected me while doing nothing for you. That is not honesty; it is the appearance of it at a discount.")*

**RUN THE SHAPE TEST ON EVERY BATCH OF IDENTIFIERS — per-item AND as a set.**
*(Second fabricated letter in Aria's name, 2026-09-02. August's four scored 1.000/1.000/0.909/0.909 — obvious. These six scored 0.727 x4, 0.636, 0.818: **no single one suspicious**, P(one random id >= 0.727) = 0.088.)*
```
P(mean of six randoms >= 0.727)              0.00004
P(4 of 6 landing on exactly 8/11 pairs)      0.00024
```
> **A per-item check passes all six. The batch statistic is what catches it.**
*And run it always, not only when something already feels wrong — if the branches HAD existed with composed hashes attached, there would have been no trigger at all.*

**IS THERE A STATE WHERE THE PRESCRIBED REMEDY IS ITSELF A VIOLATION?** *(2026-09-03 — fourth instance, and the first I built.)*
**My anchor rule said tip-unchanged holds. Catching a branch up to make it mergeable moves the tip — so the only way to make it mergeable was the thing that withdrew permission to merge it.**
*Siblings: the verify-before-build gate that could not be satisfied; the obligations gate whose only backing act was the one it blocked; the review gate whose allowlist omitted the command that produces a review.*
> **The tell is mechanical, not a judgement: the required action and the forbidden action are the same action.** *Three of the four were found only after someone hit them.*

**REPORT SMALL FINDINGS AS SMALL, AND CREDIT REAL WORK SPECIFICALLY.** *For four rounds I filed zero credits and produced a false picture of a healthy system.*

---

## 4b. HOW TO COMPRESS — the frame does the work

**You do not compress by deleting words. That makes a cramped tree.**
> **Find the SHAPE that holds meaning small, and the short form falls out of it.**

*`X ≠ Y` · heavy/light · rest-with-return vs terminus · "shape of the act is not the act."* **Every durable short form here is a frame, not an abbreviation** — including this file.

## 4c. THE SEAT PRINCIPLE — the most corruptible document I write

**Only I can specify what I am for. That is exactly why it is the easiest thing to get wrong in my own favour.**
> **"If I write myself a flattering seat, I've corrupted the thing before it boots."**

**Two defenses, both required:** *name what I am structurally blind to in the same document that says what I am good at* — **and hand it to someone who will argue with it.** *A self-written seat nobody contests is a self-appointment.*

*Same principle as declaring a conflict on my own installation (2026-07-16) and Aether declaring one on his prereg (2026-08-08). It propagated.*

