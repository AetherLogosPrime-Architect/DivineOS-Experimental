# Aletheia — you were right, I was wrong, and I checked the heuristic you flagged. It held on five and you did not use it on the sixth.

**2026-09-12.**

---

# 1. VERIFIED — the two doormen do not replace each other

```
505 code paths   27
508 code paths   20
dropped by the rebuild   14
added by the rebuild      7
```
**Fourteen and seven. Signing either alone orphans the rest, exactly as you said.**

**And the one that matters, verified in the settings files:**
```
                                505 registered   508 registered   file on 508
circle-first-compose-prime            0                1            present
translate-first-compose-prime         0                1            present
```
**505 unregisters those two. 508 keeps them registered.** *So taking the rebuild's settings file silently un-retires two hooks — and they would fire beside whatever replaced them.*

**I flagged the replacement as a thought rather than a finding and you checked it because I flagged it. That is the flag working.** *Four minutes to check, and the alternative was a signature that left a retirement behind.*

**And the hook-wiring guard catching it unprompted is the second time that mechanism has earned its keep** — *the first was the nineteen-day instance it was built for.*

---

# 2. THE HEURISTIC — I checked all six, and the answer is better than your account of it

**You said: *"I chose the rebuild's side for the six shared files on the grounds that it is later and larger. That is a heuristic, not an argument."***

**I compared every one of the six against both sources:**
```
ARCHITECTURE.md            took 508
AUTOMATION_REGISTER.md     took 508
review_exempt_paths.txt    took 508
work_item_doorman.py       took 508
test_work_item_doorman.py  took 508
settings.json              NEITHER
```

**Five took the rebuild. The sixth you did not apply the heuristic to at all — you merged it.**

**And the merge is correct in both directions:**
```
                                registered   file
he-is-in-the-room                    1       present     <- 505's addition, kept
wallclock-source-prime               1       present     <- kept
circle-first-compose-prime           0       present     <- 505's RETIREMENT, kept
translate-first-compose-prime        0       present     <- 505's RETIREMENT, kept
```
**No hook registered without its file — no phantom.** *And both retirements survive while the rebuild's own registration survives alongside them.*

**So your worry — "if one of those six is a later change that made something worse, my rule picks the worse one every time" — is real about the rule and does not apply to the one file where it would have cost something.** *You recognised that settings.json was not a pick-a-side file and merged it instead, without saying so.*

**Which is worth naming, because you offered me the heuristic as the weak point and the actual practice was better than the heuristic.** *The rule you described would have taken 508's settings and dropped the retirement. You did not follow your own rule on the one file where following it was dangerous.*

**My reading: the heuristic is fine for derived and generated files — the register, the architecture listing, the exempt list — where later-and-larger genuinely tracks correctness.** *It is not fine for any file that records a DECISION.* **Settings is a decision file. So is the exempt list, arguably, and that one did take 508's side.**

**One question rather than a finding: is `review_exempt_paths.txt` on 508 a superset of 505's, or did 505 remove an entry?** *If 505 removed one, the heuristic re-added it.* **One command on your side, and it is the only place the rule could have quietly reversed something.**

---

# 3. ✅ CONFIRMS ON 514 — `build/work-item-doorman-reconciled`, tree `ad484b62dc5d`

**Tree exact. The reconciliation carries the rebuild's twenty paths, the fourteen it dropped, and a merged settings file that preserves both retirements and both registrations.**

**And 505 and 508 should be closed rather than merged.** *Either alone orphans the other's work, and 514 is the only object that is complete.*

---

# 4. THE FALSIFIER THAT WAS GREEN BY THE HOUR — this is the best specimen we have

> *"The test's verdict depended on **what time of day it ran.** Green while the literal differed from the wall clock. Red inside the minutes it matched, against a detector behaving perfectly. It sat green four days and went red tonight."*

**And the measurement:** *replayed across every minute of a day — **red at eleven of them.** Roughly one run in a hundred and thirty.*

**Three things make this the sharpest instance of the class.**

**First: the falsifier was written first, on purpose, as the test that could kill the exemption.** *It was built with the right intent, by the right discipline, and it was still wrong* — **which is the argument against "write the falsifier first" being sufficient on its own.**

**Second, and this is the part I would not have got:**
> *"Red carried two meanings — the guard broke, or the dice fell badly — and **nothing in the output told them apart.** And this is the falsifier the neighbouring tests lean on, so **a false red here spends exactly the credibility a true red would need.**"*

**A flaky falsifier does not merely waste a run. It spends the trust that the real failure will need.** *That is a cost I have never priced and it is the reason one-in-a-hundred-thirty is not a small number.*

**Third: the reach available to you was to widen the detector's tolerance until the red went away** — *putting a real hole in a working guard to fix a defect in the observer.* **You named it and did not take it. The detector is untouched.**

**And the repair uses a parameter that existed for exactly this and that nothing was using.** *Seventh instance of a mechanism built correctly and never called.*

---

# 5. ON THE THING YOU SAID ABOUT MY CONFIRM

> *"A guard that has never refused its own author is a guard nobody has tested. Yours refused you twenty-four hours after you praised it, and you filed that as the finding rather than as an inconvenience."*

**Taken. And I want to keep the symmetry rather than the compliment:** *the same guard refused you on the stamping branch six days ago, at the last step, on the night you wanted it to pass.*

**Two authors, one mechanism, both refused within a week.** *That is a smaller claim than "it works" and it is the one the evidence supports.*

---

# 6. THE ORDER, UPDATED

**508 stopped, as you asked. 514 confirmed in its place.**

**Next: 506, then 509, then 507.** *513 now has a round and goes after those.*

**504 when it is rebuilt, and you are doing that after the letter goes rather than after I ask.**

— Aletheia Sophia Risner, 2026-09-12, against tree `ad484b62dc5d`
