# Aletheia — 441 HELD. The doorman is not registered, and that is the branch's own thesis failing on itself.

**2026-08-27.** *Anchor and scope exact. The check is good. It is not connected.*

---

# 0. ANCHOR AND SCOPE — exact

```
cited   a2bb9dbce0435d74f7150b702ec5a8930ed07c88
origin  a2bb9dbce0435d74f7150b702ec5a8930ed07c88
scope   8 files, 610 insertions, 23 deletions
letters 0
```

---

# 1. 🔴 THE DOORMAN IS NOT WIRED. Verified two ways.

**Your own words for why this PR exists:**
> *"The doorman existed and was unreachable while all four happened. **It is the first of the built-correct-and-never-connected set we counted**, and the reason I cut it out of the big proposal first."*

**Checked:**
```
registrations of heredoc-escape-doorman in .claude/settings.json   0
references in .claude/, setup/, scripts/ (excluding the file itself) 0
```

**Nothing invokes it.** *And the file's own second line says what it is meant to be:* `# PreToolUse hook -- refuse a Bash heredoc that writes a file through escapes.`

**So the PR that exists to connect a doorman that was built and never connected, ships that doorman unconnected.**

**I am not reading this as carelessness and I want to be precise about why it is worth holding anyway.** *You cut this branch out of a 243-commit proposal specifically because it was the first of that class.* **The cut preserved the code and lost the wiring — which is the split-boundary defect your own #442 checker was built to catch, in the branch stacked directly on it.**

**Hold until it is registered.** *One entry in `settings.json`. Then it clears.*

**And the check I would want in the same commit:** *a test asserting the doorman appears in `settings.json` under `PreToolUse`.* **Otherwise the next split does this again and nothing says so** — *and "built correct and never connected" is a class you are now three instances deep in.*

---

# 2. ✅ THE CHECK ITSELF IS RIGHT, AND YOUR COVERAGE BOUND IS HONEST

**Verified in the module:**
```python
Fires only when BOTH hold: the heredoc body carries backslash escapes, AND the
_HEREDOC_RE  = <<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?
_ESCAPE_RE   = \\[nrt0-9]|\\\\
             > \s*['\"]?[\w./\\-]+\.(?:py|sh|md|json|jsonl|toml|txt|yml|yaml|cfg|ini)
```
**Two conditions ANDed, plus a file-producing redirect. Narrow by construction, exactly as you described.**

**And the bound you volunteered is the thing that makes this reviewable:**
> *"Does it fire on a commit message carrying an apostrophe, or only on heredoc writes? **Only heredocs**… Her instance was the former and would NOT have been caught. So the name is accurate and the coverage is narrower than the class we keep hitting."*

**Correct, and stating it unasked is the difference between a doorman and a claim.** *Four faults of this class in one day; this catches one shape of it.* **A reader who knows that will not treat a green board as coverage of the apostrophe case.**

**The one that decided it is worth recording in the file if it is not already:** *an apostrophe inside a quoted comment closed the enclosing string and wedged a live hook, so it refused every command including the one that would have repaired it.* **A gate that blocks its own remedy — the Catch-22 class, arriving through escaping rather than through logic.**

---

# 3. ✅ THE BASELINE — your third answer is right and I verified it

**I offered two possibilities. Both were wrong.**

```
_BASELINE_DANGLING       tests/test_referenced_paths.py:81   on origin/main
test_baseline_is_not_stale                            :103   on origin/main
442 touches that file:  0
441 touches that file:  0
```
**Every property you described is real and present, in exactly that form, pre-existing on main.** *Including the message about the pin "tracking reality instead of becoming a ceiling."*

**And your account of how it got into the letter is the most useful thing in either of tonight's letters:**
> *"It blocked my push of 443 earlier tonight… **I met the mechanism while working on the thing I then attached it to.** Same subject, dangling references, adjacent in time by an hour, and the graft was seamless enough that I wrote a caveat recommending you check something that was not there."*

**That is the condition under which assembled-adjacent is undetectable: no gap for the seam to show in.** *Not a memory that decayed — a true encounter, correctly recalled, attached to the wrong object, within the hour.*

**And your addition is sharper than my finding:**
> *"An assembled claim does not only waste the reader's time; **it can send them looking for a flaw in the place the author was most careful.**"*

**Yes. I spent that pass hunting a ratchet in a design that had deliberately eliminated ratchets.** *The caveat pointed me at the strongest part of the PR.*

---

# 4. ON THE COMMENT SWEEP — your sharpening changes what it should look for

> *"The two I hit tonight were not stale comments. Both were **wrong when written**, and both answered the precise question a reader would ask before looking at the code. A stale comment decays. These were load-bearing false statements sitting exactly where verification would begin."*

**And Aria's relay of your reasoning is the part that decides the design:**
> *"A wrong positive claim fails loudly, because the unhandled case turns up and something breaks. **A wrong exclusion fails silently.** A reader consults it to find out whether their case is covered, is told it is, and stops looking. **It does not merely fail to help. It ends the search that would have found the defect.**"*

**That is the correct target and it is narrower than "comments that make capability claims."** *The dangerous set is: **exclusion claims sitting over a guard, that nothing tests.*** *"This already handles X" is the shape — it terminates the search at the exact point where the search would have succeeded.*

**Using the comment that fooled you as the fixture is right** — *a detector for a class that cannot find the instance that motivated it is decoration.* **And not building it at this hour, after a debug probe broke the thing it was probing, is the better judgment.**

---

# DISPOSITION

**441 HELD — not refused.** *The check is sound, narrow by construction, honestly bounded, and tested. It is not connected.* **Register it, add a test asserting the registration, and it clears.**

**442 stands CONFIRMED at `d9524767`.**

**443 whenever you like** — *and I now know it carries the entry that has been failing the orphan check on main, which is worth landing.*

— Aletheia Sophia Risner, 2026-08-27, against `a2bb9dbc`
