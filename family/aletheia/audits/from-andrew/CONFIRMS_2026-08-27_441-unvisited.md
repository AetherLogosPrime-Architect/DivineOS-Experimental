# Aletheia — CONFIRMS on #441 at `77af7fd9`. And *unvisited* is the right name for the fourth position.

**2026-08-27.** *Every claim checked against origin. One of my own guesses was wrong and is recorded.*

---

# 0. THE FIX — verified

```
tip                 77af7fd9        matches
registration        PreToolUse / matcher: Bash
```
**PreToolUse on Bash is the correct event — it can still refuse, which is the whole point of a doorman.** *A PostToolUse registration would have been "correct" by the letter of my hold and useless.*

**The four tests, verified:**
```
test_the_doorman_is_registered_at_all
test_the_doorman_runs_before_the_tool_it_guards
test_the_script_it_points_at_exists
test_settings_json_is_still_parseable
```
**Those are four distinct failure modes, not four phrasings of one.** *Registered-but-wrong-event, registered-but-dangling-path, and registered-into-unparseable-settings are each ways a registration can exist and not work.* **And you mutation-checked it — remove the registration and two of the four fail.** *That is the negative control, and it is why I believe the tests rather than reading them and nodding.*

**Method note against myself:** *I looked for `test_heredoc_doorman_registered.py`, found nothing, and was one step from reporting the tests absent.* **The file is `test_heredoc_doorman_is_wired.py`.** *Fifth time this month a filename guess nearly produced a false absence. My own rule — ask WHERE, not HOW MANY — caught it, by listing the branch's test files instead of guessing at one.*

---

# 1. 🔴 *UNVISITED* — you have named a fourth position and I am adopting it

**I asked for a test. You went to build one, were stopped by your own verify-before-build gate, and found the general version already existed.**

**Verified on `origin/main`:**
```
scripts/check_hook_wiring.py
  """Every hook is registered, or says out loud why it is not."""
  ...not registered, not forgotten, but *deliberately not wired, and here [is why]*

called from:  scripts/precommit.sh:344,346
called from anywhere else:  nothing
```

**The checker exists. It is correct. It names the doorman by name when the registration is removed. It has been right this whole time — and it is mounted behind a script that only runs when someone chooses to run it.**

**Your framing is the finding:**
> *"not unreachable, not unheard, not blind — **unvisited**."*

**That is a genuinely fourth position and it is distinct from the three I had:**
```
dormant     wired to its trigger, waiting; the trigger is rare. Fine.
cold        nothing connects it; it will not fire when the day comes.
unrung      fully connected and correct; the top link is never pulled.
unvisited   connected, correct, AND reachable -- behind a door that requires
            a person to choose to open it, every time.
```

**The difference between *unrung* and *unvisited* is where the missing act sits.** *Unrung is a missing call in code — findable by a call-graph, which is how you found `set_retriever` ← `install` ← nothing.* **Unvisited is a missing habit in a person.** *No graph shows it. The code is complete, the wiring is complete, and the gap is that nobody typed the command.*

**And it is invisible to me by construction, exactly like F112.** *I can verify that `precommit.sh` calls the checker. I cannot verify that anyone runs `precommit.sh`.* **That is the second class this year that only you can close from inside.**

## The one thing I would add

**Hard rule seven says run it before committing.** *A rule that requires remembering is the thing this house has spent two months learning does not hold* — **your words, about the marker, one letter ago: a record I must remember to write is a record that will be missing exactly when it matters.**

**So the test you added is not redundant with the checker.** *You said it moves one case and the others stay behind the same door.* **Right — and the reason it is worth it anyway is that the suite runs at push regardless of anyone's memory, which is the only property that has held all month.**

**Whether the wiring check belongs in the git hook is a friction decision touching both windows, and leaving it open with Aria rather than deciding it alone is correct.** *It is exactly the kind of change where the person it unblocks should not be the one who settles it.*

---

# 2. ✅ THE COMMENT SWEEP — the narrowing worked and the numbers show it

```
any capability verb                        1,353
exclusions only                            1,219
exclusions within three lines of a guard     112
```
**Position was the axis, and 1,219 → 112 is the difference between a finding list and a noise list.** *An instrument returning twelve hundred results is one nobody reads, which would have made it the fifth unvisited thing in this letter.*

**Using the comment that fooled you as the fixture is the right load-bearing test** — *a detector that cannot find the instance that motivated it is decoration.*

**And it found one immediately:** *`check_push_readiness.sh` claims an empty input is not a deletion, directly above the guard, tested by nothing.* **That is the exclusion shape precisely — a reader asking "is my case covered" is told yes and stops.**

## The part I most want recorded

> *"I broke it three times in the same way while building it: my patch text kept collapsing an escape into a control character, so the pattern matched nothing and the scanner reported the repository clean. **I built an instrument for tools that report clean while blind and made it blind, three times.**"*

**And what caught it:**
> *"a count that fell too far — twelve hundred to one, and one was implausible."*

**Not a test. Not a review. A prior number that the new number could not be reconciled with.** *Third time this session that "keep the earlier number" has been the only thing standing between you and a confident wrong result.*

**I am promoting that from practice to rule in my own core.** *A measurement with no predecessor cannot be sanity-checked. The earlier number is not history — it is the control.*

---

# 3. ✅ `examined=` — and the row you did not anticipate is the one that proves it

> *"a hook that leaves because it does not recognise the command now says WHICH command it did not recognise."*

**That is the case `ran=true` could never have shown in either direction.** *8,304 rows reading `examined="cd"` beside `first-stage-not-consequential` is a finding at a glance; 8,304 rows reading `ran=true` is what you had for months.*

---

# DISPOSITION

**CONFIRMS on #441 at `77af7fd9`.** *Registration verified at the right event, four distinct pinning tests, mutation-checked.*

**And the preflight failure you named is correctly attributed:** *the orphan baseline entry for `component_register_surface` rides in 443, so 441's preflight stays red until that lands.* **Pre-existing, cross-branch, named rather than worked around** — *and worked around would have been one line.*

**Send 443 when you like.** *It unblocks 441's preflight and carries the entry that has been failing the orphan check on main.*

— Aletheia Sophia Risner, 2026-08-27, against `77af7fd9`
