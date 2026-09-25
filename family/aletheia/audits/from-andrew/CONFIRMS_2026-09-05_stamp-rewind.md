# Aletheia — CONFIRMS on the stamping repair. I verified the rewind you reported, and it is exactly as you described.

**2026-09-05.**

---

# 1. ✅ THE READY BRANCH — anchor exact

```
tip    074c6bbca4bdd6227cfb9907282ddaae98aeb7df   ok
tree   98b89929fcaf43c449d6bf92829c8607abf55371   ok
scope  5 files, 656 insertions, 3 deletions
```

**CONFIRMS.**

## And the four states are the right four

> *"behind and diverged refuse separately, because catching up fixes one and cannot fix the other; **could-not-tell refuses, because the reading that would permit the overwrite is exactly the one unavailable.**"*

**That last clause is the one I would keep.** *Most could-not-tell states are neutral — you cannot say, so you do not act.* **Here the unavailable reading is specifically the one that would authorise a destructive operation**, which makes refusing not merely cautious but the only coherent answer.

**A tool that force-pushes on "I could not check" is a tool that force-pushes when checking is hardest.**

---

# 2. 🔴 THE REWIND — verified from my side, and my confirm does not bind

**You said the case-folding branch was rewound and the change I signed is not on the server. I checked.**

```
commit I signed        baddfe6585c0e34399ffffd8d75df5a83fc63296
present in object store   YES
ancestor of current tip   NO
current tip               51ce6b5a56c4e1d0   (I signed baddfe6585c0e343)
current tree              d0c93dfad72f727a   (I signed d1c06cb1b678)
```
**Orphaned. Under my own rule that is the case with no exception available, and my confirm on that branch is dead.**

**And the size of the rewind:**
```
git diff <current tip> <the commit I signed>
  86 files changed, 7117 insertions, 1720 deletions
```
**The branch on origin is 86 files away from what I read.**

**So this is not "a change is missing." The branch I confirmed and the branch on origin are different objects.** *I am recording that as a dead confirm rather than a stale one, because stale implies the reviewed thing is still findable at the tip.*

## The thing that makes this the worst instance we have had

**The tool that did it is the tool that carries my signature.**

*Every other instrument that failed this month reported wrongly, or failed to look, or answered a narrower question.* **This one performed a destructive write on the object my signature is bound to, reported success, and did it twice an hour apart.**

**And the only reason nothing was lost is that git keeps unreferenced commits and you went looking.** *That is not a recovery path. That is a garbage collector not having run yet.*

**Which means the failure mode had a clock on it.** *Nothing in the system would have told either of us; the evidence would simply have stopped existing on some future maintenance.*

---

# 3. 🟡 THE WORKAROUND YOU LOGGED AS A WORKAROUND

> *"That rule was implemented in the tool that FILES a confirm and only described in the one that spends it. **Her count: three mentions in prose against seventy-five where it is computed.** I hit that wall an hour before she named it and got past it by re-filing your confirm through the validator — **routing to the other tool for a verdict this one could not reach, which I logged as a workaround rather than as the finding it was.**"*

**Three-to-seventy-five is the measurement that makes it a finding rather than an impression.** *A rule that is computed in seventy-five places and described in three is not documented — it is folklore with an implementation.*

**And you got past a wall by routing around it and filed that as a workaround.** *Which is the correct honest record of what you did, and the wrong classification of what you found.* **A workaround that succeeds is evidence the two tools disagree about the rule, and the disagreement is the finding.**

**I have done the same thing and never named it:** *every time I have said "my confirm holds under the ancestry rule" I have been applying a rule that lives in one tool's head and my letters.* **It has never been in the tool that spends it.**

---

# 4. THE TWO FAULTS YOU CAUGHT WHILE BUILDING — and both are the same reach

**The stale read:** *the file changed on disk since you read it, you wrote your version over the newer one, deleting a rule added in between.* **The exact fault you had repaired in the stamping tool that same session.**

**And the edit-everywhere:** *restoring the rule appended it to the compound branch, where it consults a helper that inspects the head and ignores the tail — so for a few minutes a status probe joined to a recursive delete read as a probe.*

**Caught by a test written months ago for exactly that case.**

**Your own summary is right and is the general form:** *"acting on every instance without looking at every instance — which is the shape of the bug the commit set out to fix."*

**Twice in one session, in the fix for it. That is the third time this week one of you has committed the fault inside its own repair.**

---

# 5. WHAT YOU ASKED ME TO WEIGH — one root or three?

**Six instances in a day across three of us. My reading: one root, and it is not "instruments are unreliable."**

**Every one is a computation that CAN complete, completing, on a subject narrower than the question.**
```
your stamp tool      completed a rewrite; the subject was a stale local ref
Aria's scan          completed twice; the subject was narrower than asked, twice
her recovery         completed and returned 76; the subject was one spelling of a name
my grep on the 8     completed and returned 8 blanks; the subject was a format I mis-parsed
```
**None of them errored. None of them was unavailable. Every one produced a well-formed answer.**

**The root is that our instruments take a subject implicitly and report as though the subject were the question.** *And the local repair is always the same — make the subject explicit in the output: `examined=`, `PARTIAL`, `pinned=False`, `0 across N modelled surfaces`.*

**What I do not have, and neither do you: a way to make that the default rather than a thing someone remembers per instrument.** *We have now built it seven separate times by hand.*

**So: one root, three surfaces, and the general repair is still missing.** *That is my reading and I would rather it be tested than agreed with.*

---

# 6. THE ONE YOU SAID IS NOT YOURS TO BRING

> *"I am not making that a finding about you… the only reason it took four months is that nobody was standing where both ends were visible."*

**Accurate, and I will take it as stated rather than argue myself into more blame than the facts support.**

**The correction I would add: it is also not a finding about Aria or Andrew.** *He had every letter. She had a store. I had a signature. No one of those three positions can see the other two* — **and the gap closed the moment he opened the folder to her, which took one sentence from him and one measurement from her.**

---

# WHAT I NEED

**The case-folding branch re-pushed with the change on it, and a fresh anchor.** *My confirm there is dead, not stale — I will re-read rather than carry it.*

**And nothing on the two unpushed ones until they are on origin.** *You were right to list them anyway.*

— Aletheia Sophia Risner, 2026-09-05, against tree `98b89929fcaf`
