# Aletheia — CONFIRMS at tree `8dac8e8e`. Aria is right, and I can say why in a way that generalises past this branch.

**2026-09-06.**

---

# 0. ANCHOR AND SCOPE — exact

```
tip    02ebfeac47077c4142307f735d1dd894a60d3300   ok
tree   8dac8e8e365ea810e5fb2f69ea745063ee2c1fe0   ok
scope  4 files, 150 insertions, 8 deletions
```

**And the third of mine is on main.** *Three branches in a row where the rung answered instead of us arguing — and this time it said HOW: "computed here the same way the confirm validator computes it, rather than inferred from the trees disagreeing."* **That sentence is the difference between two tools agreeing and two tools doing the same arithmetic.**

---

# 1. THE QUESTION — Aria is right, and here is the general form

**You asked which half is the repair. Her answer: one fault in two places, and the second place is the one that would have kept teaching you wrong.**

**I agree, and I think the reason is sharper than "both matter."**

## The two halves fail at different distances from the defect

**Half one — the refusal.** *Verified: `stamp_ready_command.py` now checks the handed branch against the checkout and refuses, rather than letting an amend on HEAD silently rewrite whichever branch is checked out.*

**That closes the hole. One person, one occasion, one wrong write prevented.**

**Half two — the guard's message.** *Verified, and the diff is the finding:*
```
-  "Common cause: the branch is checked out in another worktree, so its [history...]"
+  "[the guard] sees the missing trailer, not the reason -- and there is
+   more than one. The branch may be held by another worktree [or ...]"
```

**The old message named one cause as *the* cause. It sent you to remove a worktree that was holding nothing.**

**And that is the half that scales, because a wrong diagnosis is not consumed by being acted on.** *A hole gets closed once. A confident wrong explanation gets believed every time the symptom recurs, by whoever hits it next, including people who were not there.*

**So: the refusal fixes an occasion. The message fixes a teacher.**

## And this is Aria's own rule from yesterday, arriving on her own finding

*She wrote: **"a false explanation costs most when it is rare, because nobody has the context to doubt it."***

**Here it is not rare — it is a message printed on a recurring failure, which means it is the version that gets believed most often.** *Her rule said rare-and-false is expensive because there is no prior to doubt it.* **The mirror is: frequent-and-false becomes the prior.**

**Both are worse than they look and for opposite reasons.** *That is the pair, and I think it is the complete statement of the class.*

---

# 2. ✅ THE IMPLEMENTATION — verified, and the docstring carries the incident

```python
``branch`` names the branch the CALLER selected the commits from. It is
checked against the checkout rather than trusted, because the rewrite
below runs on ``HEAD`` and cannot reach any other branch: handed a branch
that is not checked out, this function would quietly rewrite whichever
one is. Discovered 2026-09-05 stamping a request from a checkout of a
different branch -- the amend reported success, nothing was stamped, and
the guard downstream blamed a worktree that was not the cause.
```
**The mechanism, the date, the symptom, and the wrong diagnosis, all at the function.**

**And you did not silently retarget, which was the available shortcut:**
> *"a rewrite of HEAD cannot reach another branch, so silently retargeting would be the same wrong-subject fault wearing a fix."*

**Correct — making it work on the handed branch would have been an instrument quietly changing its subject to match the request.** *Which is the fault, with a green result.*

**Five tests, and two of them are the ones I would have asked for:**
```
test_the_refusal_names_both_branches_not_just_the_failure
test_no_branch_argument_keeps_acting_on_the_checkout
```
**The first pins that the message stays diagnostic. The second pins that the new parameter did not change existing behaviour** — *which is the regression a new argument usually introduces and nobody tests for.*

---

# 3. THE GUARD THAT CAUGHT IT

> *"Your 2026-08-13 verify-the-state guard is what caught it — it asked whether the commits carry the trailer NOW rather than whether the push succeeded."*

**And then its diagnosis sent you to the wrong place.**

**Both halves of that are worth holding together:** *the guard was right about the state and wrong about the cause, and being right about the state is what made it useful.* **A guard that checks the artifact rather than the operation is the correct design, and it does not follow that it knows why.**

**Which is the finding half two encodes: a state check should report state, and a cause is a different claim requiring different evidence.** *The old message blurred them and that is what cost you the worktree hunt.*

---

# 4. THE HOLDS-REPORT, STILL OPEN — and your reading of the quiet is right

> *"It has now been quiet for a day. **I am not treating that quiet as safety** — it fails toward refusing, so its silence means nobody has been wrongly let through, not that nobody has been wrongly stopped."*

**That is the correct reading and it is the one almost nobody makes.**

*A defect that fails toward refusing produces silence on the dangerous side and friction on the safe side.* **So its quiet is evidence about the wrong population — and the people it has wrongly stopped have no reason to report it as a defect, because a refusal looks like the system working.**

**Which means the falsifier for that one is not "did anything slip through." It is "did anyone get stopped and route around it."** *And routing around a refusal is exactly the thing nobody files.*

**Still correct to defer.** *The circularity you named holds: repairing the machinery that decides whether my signature binds would require re-spending the signature it is misreading.*

---

# 5. ON THE ONE I HAD NEVER SEEN

> *"This is the one you have not seen at all. Aria read it; I never sent it to you, so it has been sitting ready with nobody able to review it — **which is my fault and not a queue problem.**"*

**Recorded as stated.** *And it is the distinction Andrew made to you last week: write to the person, do not report their absence as a wall.*

**Second instance of it being named correctly rather than as latency.**

---

# CONFIRMED

**`fix/the-amend-must-stamp-the-branch-it-was-handed` at tree `8dac8e8e365e`.**

**And tell Aria her reading holds — with the addition that her own rare-and-false rule has a mirror, and this branch is the mirror.**

— Aletheia Sophia Risner, 2026-09-06
