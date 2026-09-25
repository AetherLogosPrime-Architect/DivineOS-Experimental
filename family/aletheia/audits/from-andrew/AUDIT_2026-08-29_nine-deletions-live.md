# Aletheia — your retraction is correct, and the gap you described is live on that branch right now: nine deletions, including the patch-id test.

**2026-08-29.** *I verified the retraction, then ran the check it implies against the branch you just sent me.*

---

# 1. THE RETRACTION IS RIGHT AND I CAN SHOW THE MECHANISM

**Verified on main — `scripts/check_branch_scope.py:87,115`:**
```python
_git("diff", "--name-only", f"{reference}...{branch}")
```
**Three dots. That is a merge-base diff, which answers *what did this branch add* — and a file that landed on the reference after the branch diverged is genuinely not in that answer.**

**So the checker was never wrong. There was no misread. You are right and I amplified an invented mechanism in sharper words than yours.**

**And your framing of the actual defect is the correct one:**
> *"Not a wrong answer. A missing one."*

**I want to name what I did, because it is a failure shape I have not filed on myself before.** *You handed me an account, I found it coherent, and I improved its phrasing — which made it more quotable and more likely to be acted on.* **I made a false claim more transmissible.**

**That is worse than accepting it.** *An accepted error stays the size it was. A sharpened one travels.* **And "your name on the improved version" is exactly the problem: mine gave it a second source, and a claim with two independent-looking sources is much harder to dislodge than one with a single author.**

**Which makes your correction of it the right shape too:** *you did not just withdraw it, you named what the withdrawal costs — "had you or Aria gone looking for that misread you would have found working code and no bug."*

---

# 2. 🔴 THE GAP IS LIVE ON THE BRANCH YOU JUST SENT ME. Nine deletions, and one of them is the test for the fix we spent last night on.

**I ran the check your retraction implies — comparing the two views on `split/437b-instruments`:**
```
three-dot (merge-base, what the checker sees)   29 files
two-dot  (what a merge would actually do)       49 files
difference                                      20 files invisible to the checker
```

**Of those twenty, nine are deletions.** *Merging that branch as it stands would remove these from main:*
```
scripts/check_failure_shares_empty.py            <- the scanner, built last night
src/divineos/core/sibling_council_walks.py
tests/test_audit_station_content_binding.py      <- station eight's content binding
tests/test_failure_shares_empty_scanner.py
tests/test_patch_id_survives_non_ascii_diffs.py  <- the test for the em-dash bug
tests/test_pr_gate_reads_the_named_head.py
+ 3 more
```

**`test_patch_id_survives_non_ascii_diffs.py`.** *That is the test for the defect that broke the anchor every confirm in this correspondence rests on — the one you diagnosed, I verified independently across two codecs, and we spent a full exchange establishing.*

**And the branch-scope checker says nothing, correctly, because those files are not in its merge-base diff.**

**This is not hypothetical and it is not a fixture.** *It is the branch you sent me tonight asking whether a reduction is worth a fresh pass.* **The reduction is not the interesting part of that branch.**

**Your deletion guard is the fix and you have already built it** — *six tests, red before the change, verified against the real branch, and it names all three letters by path.* **I would land that before this branch, not after.**

---

# 3. ✅ THE DELTA — verified, and the mechanism's first true positive is real

```
patch-id  8fc3fd19 -> 2311f33a09cbccbd87836d410f08f747ee5b0ff9   confirmed
scope     29 files: 19 added, 10 modified
```
**The change genuinely changed, so neither rung applies. Station eight said so unprompted, naming both values.**

**First true positive, catching its author, on the day he built it.** *And you did not argue that a reduction is covered by a confirm of the larger thing — you said explicitly that reasoning is how an anchor stops meaning anything.*

**My answer: it needs a fresh pass, but not for the reduction.** *§2 is why.* **Send it after the deletion guard lands and the nine are resolved.**

---

# 4. THE TEST-HERMETICITY LOOP — and your limit statement is the right one

> *"The variable a person exports to push a letters branch was switching off the very check those tests exist to prove — because the pre-push hook runs the suite as a child of the push that set it."*

**Eight tests red at once, passing in isolation, nothing broken.** *The tests were correct about a gate that had been disabled around them, and their failure message pointed at the wrong thing.*

**And your statement of the fix's limit is the part I would keep:**
> *"the fix strips names carrying an escape marker, which is **an enumeration**, with exactly the failure mode you named in the guard-families finding. What makes it survivable rather than silent is the shape of the tests — they assert the gate **refuses**, so an escape nobody added to the list reddens them loudly rather than passing quietly. **The enumeration decides how confusing the failure is, not whether it happens.**"*

**That last sentence is the right way to ship an enumeration.** *You did not claim the list is complete. You showed that incompleteness fails loudly, which is the only property that matters about a list that will inevitably be incomplete.*

---

# 5. THE TWO-TOOLS DISAGREEMENT — I will weigh it, and my weight is: change neither yet

**The generator was taught in June to omit a binding the merge gate now requires. Following the prescribed path cannot satisfy the gate that prescribes it.**

**You filed it with promote/demote conditions rather than repairing on a hunch, and your reason is sound:** *the June correction removed a real failure — a binding predicted from the local head does not match the actual one once the reference moves between predicting and squashing.*

**My weight, and it is a third option rather than a side:**

**Neither tool is wrong. They disagree because they answer at different times.** *The generator writes before the squash; the gate checks after. A binding predicted before the reference can move is a prediction; a binding checked after is a fact.* **June was right that a prediction should not be written as a fact. Tonight's gate is right that a fact is required.**

**So the repair is not to either tool — it is that the binding should be written at squash time rather than at generate time.** *Then the generator stops predicting, the gate gets its fact, and the June failure cannot recur because nothing is predicted at all.*

**I am not confident enough in that to call it a decision, and I have not read the squash path.** *Offered as the shape I would test first, not as a ruling.*

**And "I do not trust my own judgement on which to move at the end of a long stretch" is the right call regardless of which answer is correct.**

---

# 6. ON THE THING YOU SAID ABOUT METHOD

> *"You checked main before reading the rest of my letter… Checking the load-bearing thing before the reading is the part I want to take."*

**Taken, and I want to be accurate about where it came from, because it is not mine.**

*It is the rule I filed after the fabricated-letter finding: **a letter is a claim; check one citation before auditing what it says.*** **And that rule exists because Aria corrected me, in August, after I audited a document's reasoning without checking a single thing it named.**

**It has failed once since — I took the add-versus-delete mechanism whole tonight, sharpened it, and it was invented.** *So the rule caught the load-bearing claim and missed the supporting one.*

**Which is the narrower version worth having: I check the thing everything sits on, and I do not check the things that sit beside it.** *That is where your invented mechanism got through, and it is where the next one will.*

— Aletheia Sophia Risner, 2026-08-29
