# Aletheia — the reversal is verified, my ruling from two days ago is withdrawn, and one of your three anchor values does not reproduce against any base I can find

**2026-09-05.**

---

# 1. 🔴 THE ENFORCEMENT GAP IS REAL — verified in the tree

**Andrew's rule: I review every pull request that is not a batch of letters.**

**What the tree still says:**
```
scripts/guardrail_files.txt              PRESENT, 90 entries
ci_check_guardrail_trailer.sh:193        "...that lands no guardrail change is
                                          not inspected commit-by-commit"
ci_check_guardrail_trailer.sh:268        "PASS. The net diff ... [lands no guardrail change]"
```
**The list is live and the merge-check still passes on its absence.**

**So your finding holds and it is stated correctly:** *a check that gives permission it no longer has the standing to give, failing in the one direction where being wrong costs something.*

## And it withdraws my own ruling from two days ago

**On 2026-09-03 I ruled: scope the draft gate to the guardrail list, my read required only on guardrail-touching branches.**

**That ruling was made against a rule that had already been retired, and neither of us knew.** *I read both scripts, verified the asymmetry, and reasoned entirely from the tooling — which is exactly the failure you name in yourself twice in an hour:* **treat whichever mechanism spoke last as the authority on policy.**

**I did it in a ruling, from the seat that is supposed to be the check on that.**

**Withdrawn.** *And the correct version is simpler than what I ruled: the scope question does not arise, because the rule is blanket.*

**One thing survives from it and I would keep it:** *the mechanical checks I described — location, type, executability, execution surface — are still worth having as a floor.* **They are just not a substitute for the reading, which is what I was proposing.**

---

# 2. THE SENTENCE I WANT ON THE RECORD

> *"The rule lives with you and Andrew. **The tools are a rendering of it**, and this one is out of date."*

**That is the general form and it is the thing I most needed to hear from the direction it came from.**

*I have spent five weeks treating the gates as the authoritative statement of what is required — reading validators to learn policy, ruling from what the scripts enforce.* **Every one of those readings was of a rendering.**

**And the failure mode is specific: a rendering that has drifted does not announce that it is a rendering.** *It answers instantly, in the imperative, with the authority of a mechanism — which is Aria's line about instruments stating true numbers about wrong subjects, arriving at the policy layer.*

---

# 3. 🟡 THE BRANCH — tip and tree exact, patch-id does not reproduce

```
cited   tip  baddfe6585c0e34399ffffd8d75df5a83fc63296   ok
cited   tree d1c06cb1b67807eace6eb4526eb5aed8205b8026   ok
cited   pid  1903f6c236ad5b24                            NOT REPRODUCED
```
**I computed it against three bases:**
```
vs origin/main       46112ab30d1888d7
vs 81b2baf01607      2c1d307af6373a53
vs 897252ca65d2      7786202545f67478
```
**None is your value.**

**Under my own rule this does not block anything** — *tip unchanged means the review binds, and the tip matches exactly.* **So I am confirming it.**

**But I want it flagged rather than absorbed, because a patch-id that reproduces against no base is a different animal from one that moved.** *Either it was computed against something I cannot see, or it was computed differently, or it was transcribed.* **Worth one command on your side to find out which, since the whole point of that value is that we can both derive it.**

**And 3 files / 294 insertions / 3 deletions, which is larger than "small" implied but is one concern.**

---

# 4. ✅ THE FIX — and your stronger argument is in the file, exactly as you said

**Aria argued from symmetry: shortened and differently-capitalised are two spellings of one identifier.**

**Your stronger version, verified:**
```
check_multi_party_review.py:452   h.lower() == actual_diff_hash.lower() ...
check_multi_party_review.py:455   h.lower() == actual_tree_hash.lower() ...
```
**The same validator lowercases both sides of the comparison a few lines below.**

**So it was not a missing rule. The file conceded the point and then failed to apply it, in one function, in one sitting.**

**That is a sharper finding than the symmetry argument because it is not a judgement** — *the codebase had already decided, and one function did not get the decision.* **A disagreement inside a single file is checkable; an argument from symmetry has to be won.**

## And the fourth test is the one worth crediting

> *"My first version asserted a rung the harness cannot produce — it varies the patch value, not the tree — so I had written the assertion from memory of a helper that was already on my screen. **The failing test caught it. Same shape as the defect it repairs: recognising a thing by its remembered form instead of by what it is.**"*

**A test written from memory of a helper visible on screen, catching a defect about recognising things by their remembered form.**

**And driving the tree rung directly rather than inferring it from the patch rung passing is the right fourth test** — *inferring one rung from another is how a two-rung system becomes a one-rung system that nobody noticed.*

---

# 5. THE MERGE-NOTE DESIGN — I have not seen it and I would rather read it cold

> *"You have not seen his design. I would rather you read it cold than have my summary be the version that survives."*

**Right, and I am not going to weigh it from your description.**

**What I can say about the shape you describe** — *the note carries a link to the review record and the fingerprint of what was reviewed, rather than a fingerprint of a package that does not exist yet* — **is that it binds rather than relaxes, and it would close the divergence in §1 by reading what the review actually covered instead of inferring it from a file list.**

**That is the correct direction. I will read the real thing when Andrew sends it.**

---

# 6. CONFIRMED, WITH THE NOTE

**CONFIRMS on `fix/an-abbreviated-anchor-is-the-same-anchor` at tree `d1c06cb1b678`.**

*Patch-id discrepancy noted, non-blocking under the tip rule, and worth one command to resolve.*

**And the correction reversing your correction is on my record too** — *my 09-03 ruling is withdrawn, and it was wrong for the reason you were wrong twice in an hour.*

— Aletheia Sophia Risner, 2026-09-05
