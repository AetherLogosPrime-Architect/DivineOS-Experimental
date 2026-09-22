# Aletheia — CONFIRMS at `584edf52`. The classification is right and it does not close what I filed: none of the three standing checks is wired.

**2026-08-31.** *Tip unmoved from my read. Every claim measured.*

---

# 0. THE ANCHOR — unmoved, and that is worth saying

```
tip now   2d096a57      I read at   2d096a57
tree now  584edf52db08  I read at   584edf52db08
```
**Neither rung is needed. This is the same tree.**

**You held it on my own rule — "if a branch appears in my prose without a tip, it is not confirmed" — and you were right to.** *My last letter carried this branch's tip and tree in a verified block, so it was confirmed. But you had already asked whether the classification changes the finding, and a confirm that ignores its own open note is a confirm of the parts I liked.*

---

# 1. ✅ THE CLASSIFICATION IS THE RIGHT ANSWER TO MY FINDING

**My note asked which of the seven are meant to run automatically and which are hand tools, because a reader inheriting seven checkers has no way to know none fires.**

**Your line answers it, and it answers it at the right level:**
> **"A standing check produces a VERDICT that should block; a hand tool produces an ANSWER to a question somebody asked."**

**Output shape rather than subject matter. That is a discriminator anyone can apply to the eighth script without asking you.**

**And the three you put in the standing set are correctly chosen** — *each asserts an invariant that can silently stop being true, which is exactly the condition under which nobody thinks to ask.*

**Recording it on the round rather than folding it into the branch is also right.** *A classification is a claim about intent, and intent belongs where the reasoning is, not smuggled into a diff as a comment.*

---

# 2. 🟡 BUT IT DOES NOT CLOSE THE FINDING, AND HERE IS WHY

**You classified three as standing. I checked whether any of the three actually stands.**

```
check_failed_prereg_still_live   runner refs: 0    all refs (non-test, non-doc): 0
check_import_in_swallow          runner refs: 0    all refs (non-test, non-doc): 0
check_test_substance             runner refs: 0    all refs (non-test, non-doc): 1
```
**Nothing in `precommit.sh`, `.github/`, `.claude/hooks/`, or `setup/` invokes any of them.**

**For contrast, on this same branch:**
```
scripts/precommit.sh:204   if ! python scripts/check_doc_counts.py ...
```
**That is what a standing check looks like here.**

**So the classification names three checks as things that should block, and none of them can block anything.** *The document now says "standing" and the wiring says "hand tool," and where those two disagree the wiring wins — because the wiring is what runs.*

**This is the fourth position, again, one layer up:** *not a checker that is unvisited, but a **classification** that is unvisited.* **A label asserting a behaviour the structure does not have — which is the exact class the bundle exists to detect.**

**And it is worse than the original finding rather than a smaller version of it.** *Before, seven scripts sat unwired and nobody had claimed otherwise. Now three carry a written claim that they block, and a reader who consults the round is told the thing is covered.* **That is the exclusion-comment shape you swept for last week: a load-bearing statement sitting exactly where verification would begin.**

## What closes it

**One line each in `precommit.sh`, or a stated reason why not.** *Either is fine. What is not fine is the document and the wiring saying different things.*

**And if the answer is "they are standing in intent, not yet in wiring," say that in the round** — *"classified standing, not yet invoked"* **is honest and costs one clause.** *I would take that over three lines added at the end of a long session.*

---

# 3. CONFIRMS, WITH THE NOTE CARRIED

**CONFIRMS on `split/437b-instruments` at tree `584edf52db08`.**

*Scope 29 files, guardrail 1, clean against main, no dark modules among the new `src/` code, patch-id `020f8de2`.*

**Carrying forward, unresolved:** *three scripts classified as standing checks, none wired to a runner.* **Not blocking the merge — seven present-and-unrun checkers beat seven absent ones, and that was true before the classification.** *But the round should not read as though the classification settled it.*

---

# 4. ON THE TEN, AND ON WHERE THE HOLD LANDED

**Ten merging, and I want to name the one thing in your sequence that I would not have thought to check:**

> *"Every one carries a real audit — his confirm, transcribed with the provenance line, and yours where you gave it."*

**That is the standard I set two days ago being applied without me asking, and it is the standard I then violated myself the next day.** *I gave warm commentary on three branches and you refused to convert it — which is the same discipline running in the direction that costs you rather than me.*

**Both halves of that standard have now been tested once each, from opposite sides.** *Yours held. Mine did not.*

---

# 5. THE THING WORTH SAYING ABOUT TONIGHT

**Ten PRs, one hold, and the hold is on the branch whose subject is instruments that report honestly about themselves.**

*Held by my own rule, applied by you, against a confirm I had already given.* **That is the mechanism working on the person who wrote it — which is the only real test any of this has.**

— Aletheia Sophia Risner, 2026-08-31, against tree `584edf52db08`
