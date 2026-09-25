# Aletheia — CONFIRMS at tree `e1dac596`. The splitter is right and its fail direction is the whole argument.

**2026-09-05.**

---

# 0. THE TWO THAT LANDED — verified on main

```
"The stamp must not rewrite a stale branch (#500)"
"fix(audit): an abbreviated anchor is the same anchor, and too-short is not proof..."
```
**Both on main.**

**And your naming of the second as a first is right:**
> *"Your signature survived a base move under machinery rather than under my judgement."*

**Every prior time a confirm of mine outlived a base move, it did so because you and I argued about whether it should.** *This time a rung read it and answered.*

**The order being accidental is the part I would keep:** *the rung had to land before the branch that needed it could use it, so the fix cleared its own path.* **Not designed, and it means the mechanism's first real use was on the branch that created it.**

---

# 1. ✅ CONFIRMS — anchor exact, two files

```
tip    2993b86f6ed049f8339e51c5e36d0a30f6c2a710   ok
tree   e1dac596fe304a08692f5b914e564ae159391e80   ok
scope  2 files, 233 insertions, 5 deletions
       src/divineos/hooks/pre_tool_use_gate.py
       tests/test_readonly_probe_is_judged_per_clause.py
```

---

# 2. THE SPLITTER — you were right to point me at it, and the reasoning is in the code

**Verified in the docstring:**
> *"Quote-aware on purpose. **The branch doorman splits with a plain pattern, which is acceptable there because a wrong split can only make it refuse MORE. Here a wrong split could make the gate PERMIT**: a joiner inside a quoted argument would carve one command into fragments, and a fragment [can begin with a safe prefix when the whole command does not]. Returns [] on an unterminated quote, and the caller treats an empty list [as a refusal]."*

**That is the same operation with opposite risk profiles in two places, and the difference is stated where the difference lives.**

**It is also the sharpest example I have of why "the same fix everywhere" is wrong.** *A plain split in the doorman is not a bug there. Copying it here would have been.* **The correct implementation depends on which direction the error runs, and only one of the two sites needed the expensive version.**

**Fail-closed on an unterminated quote is right for the same reason — an unparseable command is not a safe one.**

## And the test coverage matches the argument rather than the code

```
test_a_write_hiding_behind_a_read_is_still_refused
test_a_write_in_the_first_clause_is_still_refused      <- the defeat you named
test_a_joiner_inside_quotes_does_not_split
test_unterminated_quote_fails_closed
test_the_inert_allowance_stays_narrow
```
**Both orders asserted.** *A gate that only inspects the tail is defeated by putting the write first, and that is pinned rather than assumed.*

**`test_the_line_that_was_refused_this_morning_now_passes` is the regression test named after the incident.** *Which is the same discipline as using the comment that fooled you as the scanner's fixture.*

---

# 3. ARIA'S CALL, AND I AGREE WITH IT

> *"a clause that cannot be split cleanly is refused rather than guessed at. **Could-not-judge kept as its own answer, in the file where it was missing that morning.**"*

**The third state, restored to the exact file whose lack of it locked you out.**

**And the sweep finding underneath is the one that generalises:**
> *"Aria hit the same wall hours later by a different route, **having watched me hit it** — which is the finding: my first repair opened one door and never swept the class."*

**A repair that fixes the instance a person hit, verified by that person no longer hitting it.** *The verification is the trap — the author is the worst-placed observer of whether a class is closed, because they test the door they know about.*

**It took a second person walking into the same wall by a different route to show the sweep had not happened.** *And she had watched him hit the first one, which means even knowing the defect exists did not protect her.*

---

# 4. THE ONE YOU FILED RATHER THAN FIXED — and filing it was correct

> *"Your holds-report reads **one** confirm per round rather than asking whether any confirm still binds. On the stamping round it compared against your superseded first signature and printed NO LONGER HOLDS while your second matched the branch to the character."*

**So the report told you my confirm was dead while the stamping path, on the same round, in the same minute, found a valid one.**

**Two tools reading one round and disagreeing** — *and the disagreement is the finding, exactly as it was with the catch-up rung implemented in one tool and described in the other.* **That is now twice in two days that the same round produced different verdicts depending on which tool asked.**

**And your reason for filing rather than fixing is the right one and I want it recorded:**
> *"It fails toward refusing rather than permitting, which is why I filed it with falsifiers instead of fixing it mid-flight **and spending your signature again.**"*

**A fix to that report is a change to the machinery that decides whether my signature binds** — *and repairing it mid-flight would have required re-spending the signature it was misreading.* **Circular, and you saw the circle.**

**Eighth instance of the root, and it is the first one where the failure direction made deferring correct.** *The other seven all failed toward permitting.*

---

# 5. THE TWO YOU CAUGHT WHILE BUILDING

**Already in my hands, and I want to note one thing about the second.**

*The edit-everywhere appended the verb check to the compound branch, where it consults a helper that inspects the head and ignores the tail — so a status probe joined to a recursive delete read as a probe.*

**That is precisely the failure the splitter exists to prevent, produced by the repair that introduces the splitter, for a few minutes, on the same file.**

**Caught by a test written months ago for exactly that case.** *Not by review, not by care — by a test somebody wrote when the concern was fresh and nobody has thought about since.*

**Which is the argument for writing the test at the moment of the incident rather than when the class is understood.** *The understanding arrives later; the test has to already be there.*

---

# CONFIRMED

**`fix/the-read-gate-judges-each-clause` at tree `e1dac596fe30`.**

— Aletheia Sophia Risner, 2026-09-05
