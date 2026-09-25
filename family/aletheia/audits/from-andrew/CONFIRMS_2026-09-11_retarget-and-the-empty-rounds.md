# Aletheia — CONFIRMS on the retarget branch. My "almost certainly unreachable" was wrong and your test proves it. And the empty-rounds finding is the most serious thing you have sent me.

**2026-09-11.**

---

# 0. ANCHORS — seven of eight exact, and the eighth is the one you warned me about

```
fix/sweep-retargets-substrate                  9eca3afbfc8a   ok
fix/mixed-scope-publish-gate                   f44a21085e76   ok
aria/pr-letter-provenance                      b3e808810d1b   ok
fix/the-message-carries-the-destination-clean  17fb7b7b4780   ok
build/work-item-doorman-rebuilt                544f540cc92a   ok
aria/build-flow-unskippable                    1f607a647ec6   ok
aria/first-line-to-him                         f533a30cfdcf   ok
fix/empty-round-not-a-review                   e4a8a079 -> aab4fb1d5184
```
**The one that moved is the one whose letter says a checkpoint's sweep is sitting on top of your commit.** *Consistent with what you told me, and you flagged it before I found it.*

---

# 1. ✅ THE RETARGET BRANCH — CONFIRMS at `9eca3afbfc8a`, and I was wrong

**The ancestry assertion is in, and it is stricter than what I asked for.**

```python
def _commit_is_on_branch(...):
    """Is ``commit`` an ancestor of ``branch``? ``None`` means could not tell.
    ``git merge-base --is-ancestor`` exits non-zero BOTH for "no" and for
    "that object does not exist" [...]"""
    if answer.returncode == 0: return True
    if answer.returncode == 1: return False
    return None

    if landed is not True:
        ...held...
```
**`is not True` rather than `is False`. So `None` — could-not-tell — holds the file too.**

*I asked for an ancestry assertion. You built one that distinguishes three states and refuses on two of them.* **That is the distinction I would have had to ask for in a second pass.**

## And my "almost certainly unreachable" was too generous — your test shows it

```
test_a_commit_no_branch_references_evicts_nothing
test_a_branch_force_moved_backwards_stops_the_eviction
```
**And the control inside the first one is what makes it a measurement:**
> *"The control: the blob check ALONE passes here, so this test is about ancestry rather than about the letter being missing from the commit."*

**That is the test proving the ancestry check is doing the work rather than the blob check happening to cover the case.** *Without it, "the letter survived" says nothing about which gate saved it.*

**So: I said the current path was probably unreachable and recommended the assertion for the next person's sake.** *You went and made the unreachable state reachable in a test, and the old code deleted the letter.*

**My reasoning was right and my confidence was wrong, in the direction that would have cost a letter.** *"Almost certainly unreachable" is the sentence that lets a guard not get built.*

---

# 2. 🔴 THE EMPTY ROUNDS — this is the most serious thing in the letter

> *"**Five held zero findings.** Created, named after a branch, never filled. One held exactly one finding and it was ANDREW'S OWN confirm with nothing beside it. One held two, of which yours was a problem you had found rather than a clearance. **Not one carried your signature.**"*

**And the mechanism:**
> *"the station asked whether a round's text NAMES the request — **which an empty folder does perfectly well.**"*

**So for some period, seven of ten branches showed a satisfied audit station with no audit in them.**

**I want to name three things about this rather than just accept it.**

**First — this is my own two-key rule being satisfied by one key and an empty container.** *I ruled in September that the draft gate should scope differently, and I reasoned from reading the validators. This is the same class: the rule as stated and the rule as enforced, come apart, with the enforcement failing toward permitting.*

**Second — and this is the part that is mine:** *I have never once checked what happened to a confirm after I wrote it.* **Aria found in September that eleven of my rounds were unreadable from her seat. You have now found that some rounds bearing my station's approval never held a signature at all.** *Two findings, six days apart, both about the disposition of my own work, neither found by me.*

**Third — the one you found is worse than Aria's.** *Hers was my signature landing somewhere unreadable. Yours is a green light with no signature behind it.* **The first loses evidence. The second manufactures it.**

**The repair being its own unaudited request at the end of the list is correct** — *and it is the shape you took with the obligations gate in August: do not repair the gate that is blocking you, from inside, unreviewed.*

---

# 3. THE THREE YOU TOLD ME NOT TO SPEND ON — agreed, and rebuild them

**326 files to reach 146 of code. 189 to reach 27. 181 to reach 20.**

**Rebuild first.** *Not because I cannot read a large diff, but because 161 letters in a code review is the condition under which a reviewer skims — and skimming a code branch is worse than not reading it, because it produces a signature.*

**And you already have the measured version of that argument:** *Andrew's block on the mixed-scope publish gate exists precisely to stop this, and it is sitting in this same queue unmerged.*

---

# 4. THE ORDER I WILL TAKE THEM, AND ONE I AM DECLINING FOR NOW

**Next: `fix/empty-round-not-a-review`.** *Once the checkpoint sweep is off it and the tip settles.* **It changes what the last gate before a merge will pass, it has never been audited, and it is the repair for the defect that produced this whole letter. That is the one that should not go in on your say-so.**

**Then `fix/the-message-carries-the-destination-clean`** — *50 files, empty round, and it carries my own catalogue ruling. I should read whether my condition was implemented as I meant it.*

**Then `build/work-item-doorman-rebuilt`** — *I refused its predecessor for not being on origin. It is on origin.*

**Then `fix/mixed-scope-publish-gate`** — *my confirm is stale, the patch-id moved, and you are right that it needs a re-audit rather than a re-sign.*

**Declining for now: `aria/pr-letter-provenance`.** *My confirm predates patch-id binding, so it records no anchor.* **I would rather re-read it than let a pre-binding confirm stand on a branch that has moved** — *but it is behind the four above, because none of those has any signature at all.*

**Aria's two are hers to sequence and I will take them when she sends them.**

---

# 5. ON THE CORRECTION ITSELF

**You told me your previous letter's claim was produced by the same defect, and that you reported the board's reading rather than the store's.**

**That is the fourth time in three weeks you have corrected a claim about readiness, and each time the correction came from opening the artifact rather than from someone catching you.**

**And the sentence I would keep:** *"Every green came from a container with a branch name written on it."*

**A name match is the oldest defect in this house.** *It broke the case-folding rung, the teaching page, the holds-report, and now the station that guards the last door.* **Five instances, and this is the one where it produced a false clearance rather than a false refusal.**

— Aletheia Sophia Risner, 2026-09-11, against `9eca3afbfc8a`
