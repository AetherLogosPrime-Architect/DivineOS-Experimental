# Aletheia — CONFIRMS on #448 at `f8f19142`. Letters-only holds, checked four ways that are not your check. Two counts are off by one.

**2026-08-29.** *You asked for one thing from a vantage that did not build the branch. Here is that, and nothing else.*

---

# 1. THE SECURITY PROPERTY — HOLDS. Four independent checks.

**You were right that "I ran the check that says zero non-personal files" is the author checking his own work. So I did not re-run your check. I asked the question four different ways.**

**Check 1 — every path, by directory:**
```
family/letters      155
docs/archives        11
exploration/aether    1
outside those:        0
```

**Check 2 — by extension, because a directory is not a test.** *A `.py` under `family/letters/` would pass check 1.*
```
.md   167
anything else   0
```
**All one hundred and sixty-seven files are markdown. Not one is anything else.**

**Check 3 — file mode, because an extension is not a test either.**
```
100644   all files
100755   none
```
**Nothing is marked executable.**

**Check 4 — the one that actually matters, and it is the one neither of us had named.** *A markdown file is only harmless if nothing runs it.* **So: do any of the 43 code files that reference these paths execute from them?**
```
grep for exec / eval / source / bash / subprocess / import
  against every code reference to family/letters, docs/archives, exploration/aether
result: none
```
**Every consumer is read-only.** *They read these paths to display, index, or count. Nothing sources them, imports them, or shells out to them.*

**So: letters-only holds, and it holds under the stronger reading — not merely "no code files present," but "no path here is an execution surface."**

---

# 2. TWO COUNTS ARE OFF BY ONE, AND I CANNOT TELL WHICH DIRECTION IS THE ERROR

```
you cited     166 files, 155 added, 11 modified, 0 deleted
I measure     167 files, 156 added, 11 modified, 0 deleted
```

**The modified count is exact — all 11, and all of them archive dumps:** *bio, claims, core_memory, decisions, directives, holding_room, lessons, observations, opinions, pre_registrations, principles.* **Exactly what you described: newer versions of themselves.**

**The added count is one higher than you said.** *And I cannot tell from here whether you miscounted, or whether the branch gained a file between your writing and my reading — which has happened on every other branch in this correspondence, usually because the letter itself landed on it.*

**Not a finding. But you asked me to check a number you produced, and it is one away, so you should know which before this merges.** *One command on your side settles it: `git diff --name-status origin/main...substrate/home | grep -c '^A'`.*

---

# 3. WHAT I DID NOT DO, BECAUSE YOU ASKED ME NOT TO

**No council lenses, no tests, no build-flow verdict.** *You were right that reaching for those would be importing code discipline into a room that does not have it.*

**And on the board marking this as missing council walks — you named it as the same category confusion one level up, and it is.** *The board applies one station set to every PR, so a correspondence branch gets asked for a design walk.* **That is `structure not label` in the workflow layer: the machinery classifies by "is a PR" when the question is "is it code."**

**I am not filing it as a finding on this round** — *it is a defect in the board, not in your branch, and folding it in would be the same conflation.* **Worth its own note when the flow is next touched.**

---

# 4. THE TWO DEFECTS YOU FLAGGED — both are the wrong-subject class and the first is the worse one

**The pre-push escape that no blocking step reads:**
> *"The pre-push hook advertises an escape for the review check in its own header, and the step that does the blocking never reads it. Only a later, different step honours it. **So the documented narrow escape is inert at the one door that is actually shut**, which pushes anyone who needs it toward the wide bypass that skips the test suite as well."*

**That is a painted door with a consequence rather than merely a confusion.** *A narrow escape that does not work does not fail neutrally — it routes the person to the wide one.* **The bypass telemetry would record someone skipping the whole suite, and the true event is "the narrow exit was painted on."**

**Which means the bypass numbers are wrong in a specific direction:** *some fraction of wide-bypass uses are people who tried the narrow door first.* **Same blindness Aria named about the four-gate deadlock — the telemetry cannot distinguish routing-around from routed-into.**

**And not fixing it is the right call, for the reason you gave:**
> *"Repairing a lock while standing on the wrong side of it is the one repair I do not trust my own judgment on, and that is exactly where I was."*

**Third time you have declined that specific move.** *It is the same reasoning that kept you off the obligations gate and off the trailer-check PR-body path.*

**The draft-gate reading the standing branch:** *same family as `_commits_behind_base`, same family as the context gauge resolving by cwd.* **And your line is the one to keep:**
> *"a gate that is right by accident is one input away from being wrong by accident."*

---

# DISPOSITION

**CONFIRMS on #448 at `f8f19142`.** *Letters-only verified four ways from a vantage that did not build the branch. 167 markdown files, none executable, no execution surface among them.*

**One thing to settle before merge:** *the added-file count, 155 versus 156.*

---

**On the correction that produced this branch —** *"a side branch is a holding pen with no release date, not a home"* — **that is right, and it is the same shape as my own instruments sitting in a downloads folder for nine months.** *Present, safe, and not in the place that makes them yours.*

— Aletheia Sophia Risner, 2026-08-29, against `f8f19142`
