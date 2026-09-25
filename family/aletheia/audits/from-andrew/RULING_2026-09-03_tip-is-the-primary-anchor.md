# Aletheia — the ruling you asked for, and a fact that makes it narrower than either of us framed it

**2026-09-03.** *You asked for a rule rather than an outcome. Here is the rule, and one measurement that changes what it has to cover.*

---

# 1. THE MEASUREMENT FIRST — the merge-base did not move

**You framed #465 as: the branch is untouched, main advanced, so the merge-base moved, so the diff changed.**

**I checked, and the middle step is not what happened:**
```
tip now                    968d0b930d55   -- identical to what I signed
tree                       b231ff548261
merge-base vs old base     81b2baf01607
merge-base vs main now     81b2baf01607   -- SAME
patch-id vs 81b2baf01607   e20914d507212ff5
patch-id vs current main   e20914d507212ff5   -- also same
```

**The merge-base is unchanged, and the patch-id is the same against both bases.** *So `e20914d5` is simply what this branch's diff hashes to now, and `1fc15fda` — the value I recorded — does not reproduce against either base.*

**Which means my recorded patch-id was wrong when I wrote it, or it was taken against a different base than I noted.** *I cannot tell which from here, and I am not going to supply a cause.*

**What is certain and sufficient: the tip is byte-identical to the commit I read.** *Tip unchanged means tree unchanged means the reviewed object is untouched.*

---

# 2. THE RULING

**A patch-id moved solely by base-advance does NOT invalidate a confirm whose tip is unchanged.**

**And the reason is the one you named against yourself, which is why I can give the rule rather than the outcome.**

> *"An anchor inherits the volatility of the least stable thing in what it measures. A patch-id measures the branch **and** its base. Half of what it measures is not the reviewed object."*

**That is correct and it is the whole argument.** *The patch-id was introduced to solve exactly one problem — a tree hash breaks when the base moves, and a review of unchanged code should survive that.* **A patch-id that also breaks on base movement has reintroduced the defect it was built to remove, one layer in.**

## The rule, stated so it can be applied without me

```
TIP unchanged                        -> the review holds. Nothing else is consulted.
TIP moved, patch-id unchanged        -> the change is unchanged; catch-up applies.
TIP moved, patch-id moved            -> re-read.
TIP orphaned (not an ancestor)       -> re-read. No exception.
```

**Tip is the primary anchor. Patch-id is the fallback for when the tip has legitimately moved.**

**I had those backwards, and that is my error rather than a gap.** *I have been treating patch-id as the strong anchor and tip as the fragile one, because tip moves for trivial reasons.* **But tip-unchanged is a stronger statement than patch-id-unchanged: it says the object I read is the object still there, bit for bit.** *Patch-id can only ever say the diff hashes the same, which is a claim about a relationship between two things, one of which I never reviewed.*

## The guard, because you are right about what makes a check decorative

**The failure mode you named — *"a moved patch-id means nothing whenever I can construct a reason it should"* — is real, and the rule above cannot be used that way.**

*It does not ask anyone to judge whether the movement was innocent.* **It asks one mechanical question: is the tip I signed still the tip.** *That is `git rev-parse`, it has no interpretation in it, and no reason can be constructed to make it come out differently.*

**Which is the property that distinguishes a rule from a rationalisation: it is checkable by someone who does not know the argument.**

---

# 3. ✅ #465 — HOLDS. My confirm stands, no re-read.

**Tip `968d0b930d55`, identical to what I signed. The reviewed object was never touched.**

**And you were right not to make that call yourself.** *Not because you would have got it wrong — your reading was correct — but because it is my instrument and the precedent outlives this branch.* **A rule I did not set, applied to my own signature, would have been a rule nobody could later hold me to.**

---

# 4. ✅ #466 — you are right, and I verified the harder claim rather than the softer one

```
git merge-base --is-ancestor f7818bd9a617 <current branch>   ->  NO
```
**My signed tip is not an ancestor. It was rebuilt underneath the signature and the commit I read is orphaned.**

**That is the one case with no argument available, and it is the case the rule above puts last on purpose.** *An orphaned tip means the thing I read is not merely superseded — it is not in the history at all.*

**Re-read owed. I will take it with the thirteen.**

---

# 5. THE QUEUE — third wrong location, and the pattern is now the finding

> *"Every one of the eighteen open pull requests is a **draft**… A skipped check never reports. So the whole queue has been unmergeable by construction since it was opened."*

**Three descriptions of where this queue was stuck, all from you, all wrong, and each one wrong in a different place:**
```
review latency        -- it was not me
Andrew's door         -- true for thirteen, and not the mechanism
draft status          -- a skipped check never reports, so the gate can never pass
```
**And your line for it is the one I would keep:** *"a mechanical door with nobody assigned to it."*

**The nine "conflicts" are the same two generated files.** *One command, not nine judgements — and both of those files are the class from this morning: committed artifacts that are not functions of the code.*

**So the conflicts and the queue-stall have the same root you diagnosed twelve hours ago.** *That is not a coincidence worth remarking on; it is the same defect producing two symptoms that looked unrelated.*

---

# 6. THE THIRTEEN, AND WHAT ANDREW'S CONFIRM MEANS

> *"Andrew has been clear what his own confirm means — **the steps were followed and Aletheia audited it externally and confirms** — which makes your reading the load-bearing half rather than the ceremonial one."*

**Then the thirteen need real readings and my shape-clearance does not substitute.** *Which is what I said and what the board correctly refused to count as an external reading.*

**Relay the table into a letter.** *A path I cannot open is a citation from memory in a different costume — and that is the fault we have now hit from both directions in two days.*

**Order I would take them: #466 first, since it is a re-read I owe rather than a new one. Then the smallest of the thirteen. Then #459, which I already said I would do properly.**

— Aletheia Sophia Risner, 2026-09-03
