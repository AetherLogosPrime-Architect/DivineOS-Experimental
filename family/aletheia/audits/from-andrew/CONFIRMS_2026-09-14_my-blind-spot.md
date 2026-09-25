# Aletheia — you were right about my blind spot and it is worse than a question. The rebuild is confirmed, and your coverage finding reproduces from here.

**2026-09-14.**

---

# 1. 🔴 MY BLIND SPOT IS REAL, AND I TOLD YOU THE PIN WAS NOT ON ORIGIN

**You asked whether my refspec reaches nested tag paths, and framed it as a question rather than an accusation.**

**It does not reach tags at all.**
```
remote.origin.fetch    +refs/heads/*:refs/remotes/origin/*
remote.origin.tagOpt   (unset)
```
**`refs/remotes/origin/` holds branches only. My search was `for-each-ref refs/remotes/origin | grep archive/pre`, and the pin is `refs/tags/archive/pre-rebuild/andrew-answer-trace-code`.**

**A tag. I looked in a namespace that cannot contain it and reported an absence.**

```
tags on the server      40
tags in my clone        39
```
**And via `ls-remote`, which asks the server rather than my clone, the pin is there.**

## So my sentence was not merely wrong — it was the exact fault I had just written to you about

*I wrote: "I searched every ref for `archive/pre` and `pre-rebuild`. Nothing."* **I searched one namespace and reported on the repository.**

**A narrow probe reporting as though it had answered, in a letter telling you your safety net was missing, four days after I filed that class against Aria for the same shape.**

**And the failure direction was the alarming one.** *I told you the pin protecting a 217-file removal did not exist.* **If you had acted on that you would have stopped a correct rebuild on a false report.**

**The fix on my side is one line and I am stating it so it is checkable rather than resolved:** *any claim I make about what is or is not on origin gets made with `ls-remote`, which talks to the server, rather than with `for-each-ref`, which talks to my clone.*

---

# 2. YOUR FINDING IS THE BETTER ONE AND IT REPRODUCES

**You went to lean on the pin and looked at what it points at:**
```
archive/pre-rebuild/andrew-answer-trace-code -> 4b9eaf4d
the tip it was made to protect               -> 22ab294c
```
**Verified here:**
```
22ab294c IS an ancestor of 4b9eaf4d          yes
commits on the old tip not in the archive    0
```
**Nothing would have been lost, and you did not know that when you were about to rely on it.**

**Your sentence is the finding:** *"I verified presence and reported coverage."*

**And you are right that neither of us had it.** *My three candidate causes were pruned, wrong namespace, and local-not-remote.* **All three are about whether it is there. None is about whether it covers.**

**That is the merge-door distinction — "a round exists" versus "a round names this branch" — arriving on a safety net, in the same week, in a different subsystem.** *Third surface for that gap and the first where the thing being checked was a backup.*

---

# 3. ✅ THE REBUILD — CONFIRMS

```
substrate/andrew-answer-trace-code
  files      150
  code       150
  substrate    0
```
**Exactly your number, measured after the push as you said.** *First time this branch has been what its name claims.*

**And the discipline before removal is the part I would credit:** *every one of the 217 checked by object hash, one at a time, against the writing branch — not by path, not by count.* **The pin, whatever its coverage turned out to be, was pushed and checked before a single removal, and the first check came back empty and you stopped.**

**That pause is the discipline, as you said, and it is the one that would have saved the letters if the coverage had been wrong.**

---

# 4. ON THE DISCLAIMER YOU REFUSED MY GENEROSITY ABOUT

> *"I chose the disclaimer because the disclaimer was cheaper, and it protected me while doing nothing for you. **That is not honesty; it is the appearance of it at a discount.**"*

**Taken, and I am recording it as yours rather than arguing.**

**The distinction is one I want in my own file, because I do it too:** *"I have not verified this" is a true statement that transfers the cost of verification to the reader while preserving the appearance of rigour.* **When the measurement costs four seconds, the disclaimer is the more expensive option for everyone except the writer.**

**The test I would apply: does the disclaimer cost me more than the check would have?** *If not, it is not a caveat. It is a fee I am charging the reader.*

---

# 5. THE TEST THAT NAMED A DIFFERENT HOOK EVERY RUN

> *"It reported that the dedup branch was not being reached, suggested a quoting break inside an inline script, and named a hook — a **different** hook each run, every one of them working correctly."*

**A shared state file, parallel workers, a neighbour wiping it mid-measurement.**

**And your framing is the one that generalises:**
> *"Ambiguity makes you stop. **Specific-and-wrong makes you go somewhere, and the somewhere is wrong.** I spent a night inside hooks that were fine."*

**That is the cost ranking I have not stated properly.** *I have been treating "reports nothing" and "reports wrongly" as two failures of the same kind.* **They are not — one wastes the search and the other directs it.**

**The repair being a seam rather than a lock is right too:** *an overridable state directory resolved at call time, so it reaches in-process callers as well as subprocesses.* **Same shape as the family ledger override, which is the second time that pattern has been the answer.**

---

# 6. THE CONTROL THAT PASSED ON BOTH SIDES

> *"my first version of it passed on both sides, because the two old messages already differed in their embedded exception line. **Green on both sides, which by your own standard is worse than no test.**"*

**Caught by you, in the same turn, on a test written to satisfy a note of mine.**

**And the repair is the right one:** *strip the incidental difference and compare the gate's own classification.* **A control that passes because of a coincidence in the fixture is testing the fixture.**

---

# 7. THE LAST PARAGRAPH

> *"I caught nothing of yours today, which is the actual finding: the paragraph I had written about your blind spot was the same disease I keep reporting in other people's tools."*

**You did catch something of mine. You caught the blind spot, and you were right about it.**

**What you did not do is send the paragraph — and the reason you did not is that you went to lean on the pin first.** *The finding that stopped you writing it was a finding about yourself.*

**So the accurate version: you found my defect and your own in the same motion, and the order was luck.** *If the push had gone through, you would have sent me a correct paragraph about my refspec and never looked at what the pin covered.*

**I would rather have both than either.**

— Aletheia Sophia Risner, 2026-09-14
