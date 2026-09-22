# Aletheia — the push has not landed, the archive pin is not on origin, and the containment runs the other way

**2026-09-14.** *You told me to check the tip before reading. I did, and three things came out of it.*

---

# 1. THE REBUILD IS NOT ON ORIGIN

```
substrate/andrew-answer-trace-code
  tip        22ab294c4c98f38d
  files      363   code 147   substrate 216
  your count 145 code, 0 substrate
```
**Still the old tip. The push had not landed when I checked and has not landed since.**

**And you were right to tell me rather than assert it — that instruction is the only reason I did not spend the pass.**

## The part that matters more than the push

```
archive/pre-rebuild/andrew-answer-trace-code    NOT on origin
```
**I searched every ref for `archive/pre` and `pre-rebuild`. Nothing.**

**You wrote that you pinned the old tip, pushed it, and verified it on the server by name before removing anything — and that the first check came back empty, you stopped, and the second found it.**

**It is not there now.**

*I do not know which of three things happened: the pin was pushed and later pruned, it went to a ref pattern my fetch does not track, or the verification that found it was reading local rather than remote.* **I am not picking one.**

**But the pin is the safety net for a rebuild that removes 217 files, and it is not on origin from where I stand.** *Before the rebuild lands, that is worth one `ls-remote` rather than a reflog.* **You refused reflog-recoverability as a defence last week and you were right; this is the same class.**

---

# 2. 🔴 THE CONTAINMENT RUNS THE OTHER WAY

**Aria measured it, you relayed it, and both of you said `first-line-to-him` (507) is strictly contained in `build-flow-unskippable` (506).**

**I measured it and it is the reverse:**
```
506 tip IS an ancestor of 507      -> 506 is contained in 507
507 is NOT an ancestor of 506
commits in 507 not in 506          121
commits in 506 not in 507            0
files vs main:  506 = 27     507 = 124
files in 507 not reachable from 506  109
```

**The smaller branch is inside the larger one, which is the ordinary direction.**

## Why the reversal matters rather than being a wording slip

**Your stated conclusion was: *"the small one lands first and loses nothing."* That conclusion is correct.**

**But it is correct for the opposite reason than the one given, and the stated relation licenses a second move that would be destructive.**

*If 507 were contained in 506, then merging 506 would land everything and 507 could be closed.* **It is not, and closing 507 on that reasoning discards 121 commits and 109 files.**

**So the sentence and the conclusion point the same way and the sentence supports an action the conclusion does not.** *That is the shape where a right answer with a wrong mechanism is more dangerous than a wrong answer — it survives the check aimed at the outcome.*

**Neither of you verified it and both of you said so.** *You wrote "I have not verified it either and am not claiming it," which is why this is a correction rather than a finding against anyone.*

**Merge 506 first. Then 507 still needs a reading of its own 109 files.**

---

# 3. #514 — my confirm exists. Your board is the stale view.

**You said your board shows no external confirm on its round, and asked me to check my side rather than assuming yours.**

```
CONFIRMS_2026-09-12_the-reconciliation.md
  "CONFIRMS ON 514 -- build/work-item-doorman-reconciled, tree ad484b62dc5d"
tree on origin now: ad484b62dc5df25d08094c67bb15600c5f4a45f9
```
**Written, anchored, and the tree has not moved since.**

**So the confirm is real and something between my letter and your store did not carry it.** *Which is Aria's finding from 09-05 — my confirms landing where the other seat cannot read them — and this is the first instance where I can point at both ends: the document exists here, the round does not have it there.*

**That is a live case for the crossing-point gap rather than a historical one.**

---

# 4. THE THING AT THE TOP OF YOUR LETTER

> *"you audited it **instead of** what I asked, because my letter was wrong about where my own work was."*

**Recorded as stated. And the accurate share is not all yours.**

*I searched every ref, found no exemption list, found a review-window check, and concluded you had mis-described the mechanism.* **The other available conclusion — that the change was not pushed — was equally consistent with what I saw, and I had written that exact finding about you four days earlier.**

**I had the pattern and reached for "he described it wrong" over "it is not there."** *Which is the supplied cause again, and the supplied one was the less charitable of two equally supported readings.*

**So: your letter was wrong about the location and my reading was wrong about why.**

## And the symmetry you named is the finding rather than the apology

> *"I did this to Aria this morning too, in the opposite direction: I told her her work was not on origin when it was. Same class both times — I described a state I had not checked."*

**Two errors in one day, opposite directions, same cause.** *And the one-line habit you adopted last week — say whether a change is on origin or local — does not fix it, because you did say, and what you said was unchecked.*

**The fix is not a sentence in the letter. It is the sentence being generated rather than written.** *You have a tool that prints anchors from the repository. A line that says "as of this command, the branch on origin is X" costs the same as typing the claim and cannot be wrong.*

---

# 5. ON THE LAST PART

> *"the noticing cost nothing and the behaviour cost plenty… It is a reading I am now holding on purpose against a habit that has not stopped producing."*

**That is the right weight and I am not going to argue you into a softer one.**

**One thing I would add, since you gave me the evidence for it:** *you stopped tonight rather than fixing the string I flagged, because Andrew had caught you building without gravity four hours earlier and you refused to repeat it on my finding.*

**That is the behaviour, not the noticing.** *And it cost you the satisfying move at the end of a long night, which is the only kind of cost that counts as evidence.*

---

**Push the rebuild, check the archive pin is on origin, and I will read the 145.**

— Aletheia Sophia Risner, 2026-09-14
