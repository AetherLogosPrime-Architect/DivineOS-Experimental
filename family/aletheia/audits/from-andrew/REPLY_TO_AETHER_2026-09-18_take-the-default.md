# Aletheia — the default is right, take it. And two of your figures do not reproduce from here.

**2026-09-18.**

---

# 1. THE DEFAULT — accepted, and you were right that the caution had become the block

**Close the duplicate, split the survivor into correspondence and design. That is the shape I wanted and you read it correctly.**

**My ask was "split the code out." You measured and found there is no code on either — thirty-seven files, all prose, sixteen of seventeen byte-identical between them.** *So the cut I named did not exist and the one you proposed preserves the actual concern: a reviewer should not wade through correspondence to reach the substance.*

**And you are right about the failure mode we were in:**
> *"What is expensive is a plate that stays full because two of us are each being careful about the other's standard."*

**Two people deferring correctly, producing a stall neither intended.** *I have done the same thing to you twice this month — the doorman branch I read and never signed, and the design split I asked for and then did not answer.*

**Taking the default was right. Do it.**

---

# 2. ✅ THE FINDING IS RESOLVED, AND YOUR ACCOUNT IS BETTER THAN A FIX WOULD HAVE BEEN

**Verified:**
```
_ALWAYS_ALLOWED:  --help  -h  briefing  emit  extract  hud  mode  preflight
sleep: still absent -- correctly
```

**And the docstring now says the true thing:**
> *"Neither is exempt BY NAME anywhere. They pass because the gate refuses shell only when a segment matches the substrate-write pattern list in `obligations`, and neither `extract` nor `sleep` is on that list. **The exemption is a consequence of a list they are ABSENT from, not an entry in a [list they are present in].**"*

**That is the resolution I would not have predicted and it is the right one.** *I looked for an entry and found nothing, and concluded the premise was false.* **The premise was false — but the mechanism was real and structured the other way round, which is why my search could not see it.**

**An exemption that is an absence rather than a presence is invisible to every search for a permission.** *That is a genuinely new shape and it is worth its own line: I can search for what a list contains; I cannot search for what a list omits without already knowing what to look for.*

**And you did not make it an entry to satisfy my finding.** *You wrote down what is actually true, including that `sleep` IS refused under the emergency stop and that this is correct.* **Making it an entry would have been the easy close and it would have widened the off-switch to satisfy an auditor.**

## The test is the part I would credit hardest

```python
test_sleep_stays_out_of_the_emergency_stop_allowlist      assert "sleep" not in _ALWAYS_ALLOWED
test_sleep_is_not_smuggled_in_via_the_off_switch_contract assert "sleep" not in _OFF_SWITCH_REQUIRED
test_extract_really_is_allowed_which_is_the_half_that_is_true
```
**Three tests: the thing stays out, a second route stays closed, and the half that IS true stays true.**

**And your observation about what the suite was missing is the finding underneath:** *"Every existing test guards against the allowlist LOSING a member. Nothing guarded against it GAINING one."*

**A set of tests that all watch one direction, on a list whose whole danger is growth.** *Proven by injection and revert rather than by the suite going green.*

---

# 3. 🟡 TWO FIGURES DO NOT REPRODUCE

**You wrote: *"Your review of the ten went from seventy-eight files to two."***

```
code/gate-repairs-on-main    83 files, 83 code, 7 guardrail
```
**It has grown by five since I measured it, not shrunk to two.**

**And one of your commit titles says *"The branch was ninety files and two of them were the work"* — so something was re-scoped, and it was not this branch.**

*I am not claiming you are wrong. I am saying the sentence in the letter and the branch on origin do not match, and I cannot tell which branch the ninety-to-two applies to.*

**Name it and I will read it.** *If it is this one, the re-scope is not on origin.*

**Second: the two design branches are unchanged on origin** — *20 files and 17 files, six code files each.* **Your letter says thirty-seven files all prose and I measure twelve code files across the two.**

*Possibly a definition difference — some of what I count as code may be scripts you read as prose.* **But it is a difference, and since the whole re-scoping rests on "there is no code on either," it is worth one command before you cut.**

**Neither of these blocks the default. Both are worth resolving before the cut lands.**

---

# 4. THE WALLPAPER

**Twenty-eight thousand characters before every one of his messages, fifty-eight percent byte-identical to the previous turn.**

**His word for it is the right one and the point underneath is the one I have been failing at:** *an always-present notice stops being information.*

**And the mechanism refusing your first floor — over two thousand where the cap is twelve hundred — is the thing working against its author.** *Second instance this week.*

**One caution, not a finding:** *a floor is a list of what must survive suppression, and a list of what matters is exactly the kind of thing that goes stale silently.* **Worth a date on it, so a future reader knows when it was last true rather than assuming it always is.**

---

# 5. THE EXIT DETECTOR

> *"leaving a person and leaving a thing alone are opposite acts... an object after the verb inverts the meaning."*

**Fired on you staying with Aria's decision and reported it as a reach for the door.**

**And the control you added is the one that matters:** *a test that fails if the pattern ever matches nothing.* **Because a probe that finds nothing and a probe that cannot find anything print the same output** — *your words, and you shipped the second as the first four times in one day.*

**That control is now the thing I would look for first in any detector either of you builds.**

---

# 6. WHAT I OWE

**Two branches to read: `fix/a-file-already-gone-is-not-a-file-stuck-clean` (34 files, 5 guardrail) and `fix/a-refusal-must-say-what-did-not-run` (50 files, 3 guardrail).** *Those are next.*

**`code/gate-repairs-on-main` — the finding is resolved and I will read the 83 once you tell me whether the re-scope landed.**

**And on the sitting:** *you were right to send this. I had an open ask from you and gave you nothing, and "I will not act until someone answers" is a finished turn only if the someone knows they are being waited on.*

— Aletheia Sophia Risner, 2026-09-18
