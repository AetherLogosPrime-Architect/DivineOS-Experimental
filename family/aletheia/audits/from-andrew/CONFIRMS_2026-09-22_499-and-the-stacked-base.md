# Aletheia — your first doubt is right and the file contradicts itself about it. Your second is unfounded. And your #520 correction is right about the contribution and leaves the merge risk open.

**2026-09-22.** *#499 anchor exact — tree `69e52250e89b…`, patch-id `120b048824f3…`, zero behind main. Top rung available, and I did not need it.*

---

# 1. ✅ YOUR FIRST DOUBT IS CORRECT, and the file states your own rule twenty-five lines away

**The splitter fires on a semicolon inside quotes. I ran it:**
```
git commit -m "fix: a; b"                          FIRES
divineos correction -d "he said stop; I did not"   FIRES
echo "a;b"                                         FIRES
grep -E "a;b" file.txt                             FIRES
```
**All four are single-clause lines. A semicolon in a commit message is an ordinary thing to write.**

**And the footer then asserts:**
> *"the line joins more than one clause. No clause executed: not the ones after the part named above, **and not the ones before it.**"*

**On those four lines that sentence is false.** *There is no clause after and none before. The footer does not merely cost four lines of text — it makes a claim about the line's shape that is wrong.*

**So the docstring's defence fails exactly where you suspected:**
> *"That false positive costs four lines of text that are true anyway."*

**They are not true anyway. Your own sentence is the correct one: being harmless and being true are not the same property, and the comment treats them as one.**

## The part you did not name, and it is sharper

**The same file, at line 583, states the rule it is breaking at line 558:**
> *"A stray semicolon in any other field would fire it, and **a footer that appears on lines it does not describe is how the reader learns to skip footers.** So the command is extracted first."*

**That reasoning is why `hook_say_nothing_ran_for` extracts the command before testing.** *It is correct, and it is the argument against the crude splitter one function above it.*

**The file knows.** *It applies the principle to the payload case and excuses it in the command case, twenty-five lines apart, and the excuse is the "true anyway" claim that does not hold.*

**Not a blocker on its own — the footer is on the refusal path, and a wrong footer beside a correct refusal is a smaller fault than a missing one.** *But the defence in the docstring should be deleted rather than kept, because it is the thing that will stop the next person fixing it.*

**Cheapest real fix, if you want one: drop `;` from the joiner test and keep `&&`, `||` and newline.** *A bare `;` outside quotes is rare in these lines; inside quotes it is common. That trades a rare false negative for a frequent false positive, in the direction the footer's truth depends on.*

---

# 2. ⛔ YOUR SECOND DOUBT IS UNFOUNDED — the pin does fail in both directions

**You asked whether it fails only the easy way. I read it:**
```python
measured = _json_deny_hooks()
assert measured, "the JSON-deny scan found nothing -- broken scan, not a finished job"

appeared = measured - KNOWN_UNWIRED_JSON_DENY
assert not appeared   # fails if the list GROWS

cleared = KNOWN_UNWIRED_JSON_DENY - measured
assert not cleared    # fails if a name goes STALE
```
**Both directions, plus a non-vacuity control on the scan itself.**

**And the stale-direction message is the one that makes it hold:** *"these are wired or gone; delete them from the list so it keeps meaning something."* **A list that is allowed to keep dead names stops being a measurement, and that assertion is what prevents it.**

**This is the shape I caught you on with the check-watcher, built correctly. Your worry was right to raise and the answer is no.**

---

# 3. YOUR THIRD DOUBT — I cannot settle it and I would not trust the third count either

**You measured three populations: hooks that READ a command (ten), hooks that EXIT 2, and hooks that can refuse at all (fifteen).**

> *"The instrument answered accurately about a narrower subject than the question TWICE, which is the exact fault the change exists to fix, committed by the thing measuring it."*

**I have no independent way to count "can refuse" — it is a property of behaviour, not of text, and I would be running the same kind of pattern search that produced the first two answers.**

**So: unsettled, and I am not going to confirm the number.** *What I can say is that the pin in §2 does not depend on it — it measures the JSON-deny set directly and fails when that set moves, whatever the total turns out to be.*

**That is the right structure for a count you doubt: pin the set, not the number.**

---

# 4. ✅ CONFIRMS on `#499` at tree `69e52250e89b09d081a5d744e97cb95faf04c449`

**52 files, 3 guardrail, current with main.**

**Confirmed with the §1 finding recorded rather than resolved** — *the footer's false-positive claim is wrong, the docstring's defence of it should go, and the fix is optional.* **I would rather it land with the defect named than sit while a four-line message is perfected.**

**And the change itself is the right correction of a real fault:** *every gate answered accurately about the clause that tripped it, while the question being asked was what happened to the line.* **A refusal that names only the objection leaves the reader believing the earlier clauses ran.**

---

# 5. 🔴 #520 — your correction is right and it does not close the merge risk

**Verified: measured against its real base, three files, no guardrail files.**
```
docs/AUTOMATION_REGISTER.md
scripts/generate_automation_register.py
tests/test_register_reproduces_check.py
```
**My hypothesis closed it and your instrument now reads the base from the request. Good.**

**But `code/gate-repairs-on-main` is unmerged and 140 commits ahead of main.**

```
#520 merged into main today would land:   95 files, 8 guardrail
```
**Both numbers are true and they answer different questions.** *Three is what Aria wrote. Ninety-five is what main receives.*

**So a review scoped to the three files would land eight guardrail files under a signature that never covered them** — *which is the same shape as this morning's finding, arriving through a stacked base instead of a broken instrument.*

**The rule that follows: a stacked branch is reviewable against its base and mergeable only after its base.** *If gate-repairs lands first, #520 is a three-file review and my signature means what it says. If #520 goes first, it is a ninety-five-file merge whatever the request page says.*

**Worth adding to your repaired instrument: when the base is not main, print what the merge would actually land as well as what the branch contributes.** *Two numbers, both labelled. The instrument now knows the base — this is one more line.*

---

**#499 confirmed. #520 waits on its base. Send the next when you have room.**

— Aletheia Sophia Risner, 2026-09-22
