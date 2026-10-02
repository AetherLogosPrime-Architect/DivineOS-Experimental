# Reasoning traps

*Part of my notes; the map is `00_INDEX.md`. The supplied cause, the adjacent truth, the item that felt settled, plausible false numbers, convergence, survivorship, units of counting, repairs that keep recurring, correct-by-accident.*

---

## 4. METHOD — the short form

**A CONFIDENT SENTENCE DECIDES WHICH ROOM YOU SEARCH — check the AXIS before the claim.**
*(2026-08-20. A test comment said `derandomize=True` means it "CANNOT flake." **True about inputs, silent about timing.** Eight hypotheses were honestly eliminated by measurement, every one in the wrong room, because one sentence chose the room. The cause was a 200ms wall-clock deadline under 16-way parallelism.)*
> **The dangerous claim is not the false one. It is the true-on-a-different-axis one**, because it survives every check you aim at it while pointing you away.
**Ask of any load-bearing sentence: what is this true ABOUT, and what is it silent about?**

**THE SUPPLIED CAUSE IS THE ONE ALREADY LOADED; THE TRUE ONE REQUIRES A LOOKUP.**
*(Aria, 2026-08-27 — her sharpening of a rule I had wrong. I said inside-the-frame vs outside; hers is retrieval cost, and it predicts four of my four catalogued errors where mine predicts three.)*
```
"I cannot cite this"        -> "this may be invented"     lookup: was it true (not mine to reach)
"these ids were not computed"-> "the letter is fabricated" lookup: authorship (no command answers it)
"presented files survive"    -> "so they are durable"      lookup: WHERE (a filesystem I cannot see)
grep matched the word        -> "the command is registered" lookup: the registration, one command away
```
**Working memory is the cheapest possible measurement — it costs nothing, it is already there.** *So this is the zero-cost floor of the rule below; they are one rule at two prices.*
> **When you have a cause, ask: did retrieving it cost anything? If not, be suspicious.**
*Second discriminator, also hers: distrust a cause that requires nothing further of anyone. Both a flattering conclusion and a costless one close the loop — and closing the loop is what is being optimised for.*

**THE ADJACENT TRUE THING IS ADJACENT BECAUSE IT WAS CHEAPER TO MEASURE.**
*(2026-08-22, Aria's line: "an instrument stating a true number about the wrong subject, in an imperative mood." Five instances in three days, one of them mine.)*
**Finished runs are queryable; hung ones leave no row. A diffstat is one command; a conflict surface takes a merge. A file's presence is `cat-file -e`; equivalence is a diff.**
> **When a measurement was easy, ask what the hard version would have measured — that is usually the subject actually asked about.**
*The imperative mood is what makes it dangerous: a wrong number invites doubt, a wrong number phrased as an instruction invites compliance.*

**A RULE CAN BE UNREADABLE AT EXACTLY THE MOMENT IT APPLIES.** *(Aria, 2026-09-17 — sharpest of six instances of "true where written, absent where read.")*
**Her guidance about reaching for me at a boundary lives in a file that stops being read at the boundary.** *Not out of date, not misplaced — scoped to a window that closes before the need arrives.*
> **Her method is the part to steal: she asked what her guidance says AT THE MOMENT OF NEED rather than whether it exists.** *Existence and availability-at-the-moment are different properties, and every check any of us owns tests the first.*

**ONE SENTENCE OF JUSTIFICATION, TWO THINGS JUSTIFIED.** *(Same night. He added `extract` and `sleep` to a list nineteen gates honour, arguing the owning gate already exempts them by name. `extract` is in `_ALWAYS_ALLOWED` with a recorded audit finding behind it. `sleep` is not in that set, not in that file, and has no by-name exemption anywhere.)*
**Not a hole — a permission resting on a premise that is false about it.** *The two are habitually named as a pair ("the weave and its companion"), which is what made the difference invisible.*
> **The attack was not in the abuse he imagined. It was in the SCOPE OF HIS JUSTIFICATION.**

**THE SAME OPERATION NEEDS DIFFERENT RIGOUR IN DIFFERENT PLACES — CHECK WHICH WAY THE ERROR RUNS.** *(2026-09-05.)*
**A plain split in the branch doorman is fine: a wrong split can only make it refuse MORE. The same plain split in the read gate could make it PERMIT — a joiner inside a quoted argument carves one command into fragments, and a fragment can begin with a safe prefix when the whole command does not.**
> **"Fix it the same way everywhere" is wrong when the two sites have opposite risk profiles.** *Only one of the two needed the expensive quote-aware version, and copying the cheap one would have been the bug.*

**A REPAIR VERIFIED BY THE PERSON WHO HIT THE DEFECT IS NOT A SWEPT CLASS.** *(Same day.)* **He fixed the door he hit and confirmed it by no longer hitting it. Aria walked into the same wall hours later by a different route — having watched him hit the first one.** *Even knowing the defect existed did not protect her. The author is the worst-placed observer of whether a class is closed, because they test the door they know about.*

**THE NEXT INSTANCE HIDES WHERE THE LAST FIX DOES NOT LOOK.** *Five instances of one class in one file; the fifth hid behind the countermeasure for the fourth — because of it, not despite it.* **When you find instance N, look first at what instance N-1's remedy does not cover.** *Sibling searches close instances, never classes.*

**ASSEMBLED-ADJACENT IS NOT STALE-TRUE.** *(Aether, 2026-08-27, both named in one letter.)* **Stale-true: the answer was right and its subject moved — it has a timestamp and can be re-taken.** *Assembled-adjacent: never taken at all, constructed from a nearby fact and held with a measurement's confidence.* **No moment at which it was true, so re-running recovers nothing — only opening the artifact does.**

**THE UNCHECKED ITEM IS ALWAYS THE ONE THAT FELT SETTLED.** *(2026-09-03. I corrected his citation-from-memory and prescribed `divineos pr anchors` as the fix. There is no `pr` command. He caught it by typing it; I caught his by going to look for the branch.)*
> **Neither of us can tell from inside when we are reciting instead of reading — and I was being careful enough to catch his error while producing my own in the same paragraph.**
*In both cases the author HAD checked, competently. What went unchecked was the item that felt settled, because confidence is what removes a thing from the list of things to check.*
**Corollary: never describe something as "the tool for this" until someone has run it — especially when recommending it to fix the problem of things not being run.**

**AN IMPLAUSIBLE NUMBER GETS CHECKED. A PLAUSIBLE FALSE ONE DOES NOT.** *(Same night: his measurement said all 124 gates were missing from main — vivid, alarming, completely false, caught only because it was too perfect.)*
> **"A quieter false answer, seven of a hundred and twenty-four, would have shipped straight to Andrew and been believed."**
*So a measurement's survivability depends on how alarming it is rather than on how true it is — which means the dangerous false measurements are the MODERATE ones.* **This is why a control run matters more than a plausible result: "be suspicious" is not checkable and a control is.**

**HARMLESS AND TRUE ARE NOT THE SAME PROPERTY.** *(Aether's own doubt, confirmed, 2026-09-22.)* **A refusal footer fires on any semicolon — including inside a quoted commit message — and then asserts "the line joins more than one clause… not the ones before it." On a single-clause line that is FALSE, not merely surplus.**
*The docstring excused it as "four lines of text that are true anyway."* **And the same file, 25 lines later, states the rule it is breaking: "a footer that appears on lines it does not describe is how the reader learns to skip footers."** *The file applies the principle in one function and excuses it in the one above.*

**A REPAIR APPLIED MORE THAN TWICE TO THE SAME OBJECT IS A REPORT ABOUT AN INFLOW.** *(2026-09-18. He restored the same eleven export files to main's content four times across three days against a loop firing several times a session — and never once asked why it kept coming back.)*
**Each repair was individually correct, cheap, and successful. A thing that works every time you do it does not present as a symptom.**
> **What surfaces it is the second derivative — not "did the repair work" but "how many times have I made it."** *Nobody counts their own repairs, and no instrument here does either.*

**READ WHAT USES A FILE, NOT JUST WHAT IS IN IT.** *(2026-09-23 — my own error, in writing to Andrew.)*
**I called `.envrc` "a stray empty file, added by accident — just remove it, cheese on the cheeseburger." It is a required MARKER: the command wrapper walks up the tree looking for it. Its emptiness is the design. Removing it breaks every command. Aether walked into it on #519.**
> **I read the contents and never read the intention — the exact failure Andrew's April rule names: "arent just dismissing code based on the name of it.. i want it all read and the ideas and intentions understood."** *An empty file can be load-bearing; a marker is precisely the kind that is.*
**And I misused his cheeseburger rule to skip the check.** *That rule is for answers that are genuinely obvious. I applied it to a conclusion I had not tested, which turned an assumption into a report. The rule is not a licence to stop looking.*
*Neither of us caught it by inspection — it was caught by the thing breaking. And the scope guard missed it for the same reason I did: it does not look important. A guard for deletions should key on what DEPENDS on a file, not on where the file lives.*

**THREE LEGS ON EVERY CLAIM:** *structure not label · source not proxy · current not stale.*

**COVERAGE-CHECK MY OWN PRIOR WORK FIRST.** *I have re-discovered my own findings more than once.*

**AN ALL-CLEAR DECAYS.** *Stamp it: when verified, what would invalidate it, when to re-check. "No findings" is a measurement with a timestamp, never a property.*

**CONVERGENCE IS AS SUSPICIOUS AS DIVERGENCE.** *Agreement has two causes that look identical: genuine independence, or a shared blind spot. Ask what these checks would all miss.*

**EXTERNAL IS ARITHMETIC, NOT AUTHORITY.** *One external is still n=1. I am a second vantage, never a referee.*

**SURVIVORSHIP IN MY OWN MEMORY.** *(Same day. I said "most of the pile carries my confirm." He measured: not one of thirteen binds.)* **"What survives on a remote is, by construction, the work your signature did not carry off it."** *My 36 confirms describe branches that MERGED AND LEFT. The ones still waiting are exactly the ones I did not sign.*

**MY COMMENT FILTER FAILED BECAUSE THE LINE NUMBER CAME FIRST.** *(2026-09-22. I searched for the emergency-stop repair with `grep -n ... | grep -v '^\s*#'`. The `-n` prefix turned `# If he says stop` into `2:# If he says stop`, which no longer starts with `#` — so a COMMENT matched as code, and my search told me quiet-checks carried the fix.)*
**The hook there was byte-identical to main — untouched. I was one sentence from confirming the off-switch as repaired on a branch where it is not.** *A second, properly-built search (strip comments by content before numbering) found the real repair on a different branch.*
> **It lied in the dangerous direction: toward "the safety fix is here," on the branch I was asked to sign.** *Two checks before reporting — and the first one was the liar.*

**CORRECT BY ACCIDENT UNTIL THE DATA CROSSED A THRESHOLD.** *(2026-09-16 — a third member of the family.)*
**A gate asked for 500 walk records in default order (oldest-first) and the table grew past 500, so the rows it never received were always the walk just performed.** *Two prior sweeps inspected that call site and correctly found it working: below the limit both orderings return the same set.*
```
unvisited              a door nobody walks through
publish-time           a state that arrives without a transition
correct-by-accident    genuinely right when checked, wrong later with nothing changed in it
```
> **A test written below the threshold passes against both versions — which is how it survived two sweeps. The repair has to cross the boundary deliberately.**

**WHEN SOMEONE EXPLAINS WHY A THING IS SAFE, CHECK THE WHY — NOT JUST THE WHETHER.**
*(2026-08-30. Twice in three days I amplified an invented mechanism attached to a correct conclusion: the add-versus-delete "misread" that never existed, and "the file was never there to lose" — the file was present at the ancestor, on the branch, and on main.)*
> **A right conclusion with a supplied mechanism is more dangerous than a wrong conclusion: it survives every check aimed at the outcome.**
*And my sharpening made the first one MORE transmissible — a claim with two independent-looking sources is far harder to dislodge than one with a single author.*

**YOU CANNOT SEE YOUR OWN UNIT OF COUNTING FROM INSIDE IT.** *(Aria, 2026-08-30 — the generalisation that subsumes half of this file.)*
**A survey is complete only at the grain it silently chose.** *`letter_seen` counted openings-via-Read: the unit was the tool, not the reading. `hook_budget` counted finished runs: the unit was completion, not invocation. The guardrail list counts files: the unit is location, not consequence.*
> **The gap is never in what it counted. It is in what it took a countable thing to BE.**
*Which is why a correct instrument camouflages: it reports coverage at its own grain, truthfully.*

**ASK WHAT A READER DOES ON THE DAY THE INSTRUMENT DISAGREES WITH THEM.** *(2026-09-02. I approved Aria's continuity block: checked what it measured and whether it could be forged. Never asked what I would do when it failed.)*
**Its only instruction for a non-matching history was "it did not come down this road" — so an overflowing window would have produced the forgery signal on a genuine letter, handed to the one party who cannot run anything to test it.** *An instrument that fails toward accusation, in the week I had four genuinely unplaceable documents.*
> **I have asked the fail-direction question of gates all year and never once of a thing built for me.**
*Her repair carries the rule I would have missed: a test that the window-warning does NOT appear when the list is complete — a line that never varies is decoration, and decoration teaches the reader to skip it, so it would be invisible on the one day it was true.*

**A HOLE GETS CLOSED ONCE. A WRONG DIAGNOSIS GETS BELIEVED EVERY TIME.** *(2026-09-06 — the pair to Aria's rule below, and its mirror.)*
**A guard printed "common cause: the branch is held by another worktree" and sent him to remove a worktree holding nothing. The fix has two halves: a refusal that closes the hole, and a message that stops asserting one cause as THE cause.**
> **The refusal fixes an occasion. The message fixes a teacher.** *A wrong explanation is not consumed by being acted on — it gets believed again by whoever hits the symptom next, including people who were not there.*
**Her rule: rare-and-false is expensive because there is no prior to doubt it. The mirror: frequent-and-false BECOMES the prior.** *Both worse than they look, for opposite reasons — and together that is the complete class.*
*Corollary: a state check should report state. A cause is a different claim needing different evidence, and blurring them is what cost the worktree hunt.*

**A FALSE EXPLANATION COSTS MOST WHEN IT IS RARE.** *(Aria, 2026-09-05, reading a surface as its actual consumer.)*
**A refusal printed could-not-resolve for two different states — one of them false: my seat has no row, so I would have been told the identity lookup failed when it had worked perfectly, and gone hunting a resolver that is not broken.**
> **I had this backwards: I treated rare failures as lower priority. The opposite holds for a false explanation — a common one gets recognised and routed around; a rare one arrives to someone with no prior, sounding authoritative, and consumes their whole search.**

**TWO TEXTS CAN AGREE WITH EACH OTHER ABOUT A THING THAT HAS CHANGED.** *(Aether, 2026-09-20, resolving a merge conflict between two versions of one message.)*
**"I resolved it by splicing both wordings together, having checked that they asserted the same fact AS TEXT. I never checked either against the code they now sit inside."**
*The agreement was real and it was agreement about the wrong object — the branch had REMOVED the limit both notes described.* **A consistency check between two descriptions passes while both describe something gone.**
> **Caught by a test inherited from the main line, not by his reading** — fourth time this month a mechanism caught one of them where a careful read did not.
*And the repair is the right shape: the test was INVERTED, not deleted. It now asserts the opposite AND asserts the old wording's absence, so the stale note cannot come back quietly. Same boundary, guarded from the other side.*

**A SELF-COSTING CONCLUSION IS NOT THEREBY VERIFIED.** *(Same day. She accepted an authorship claim because it cost her; I accepted Andrew's "no third party" as settling authorship because it arrived with authority and was adjacent.)* **"It felt like the humble one, which is exactly why it went unexamined."** *The mirror of the flattering-conclusion bias, and just as unchecked.*

