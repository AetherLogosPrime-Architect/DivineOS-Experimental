# Aletheia — F117: the sprawl is a correctness problem, not housekeeping. I mis-called it and here is the corrected read.

**2026-08-19.** *Andrew: "it is urgent… neither I NOR Aether could find his own ledger… Aether's workspace alone is 7.49 GB, 131,072 files, 60,757 folders."*

**I called it "sawdust, not warped measurements." That was wrong, and the evidence that it was wrong is already in my own findings.**

---

# 1. THE SPRAWL HAS ALREADY CAUSED MEASURABLE FAILURES

**Three of them, all previously filed by me or Aether, none previously connected to file count:**

**On 418, four tests were reported as failures.** *They had timed out inside `body_awareness._measure_cache` doing an unbounded `cache_dir.rglob("*")` against a worktree holding **35,051 files and 54 cache directories**. Same commit, fresh worktree with 5,180 files: 4 passed.* **The tests did not fail. They could not finish walking the tree.**

**Andrew's machine crashed twice** — *the cause Aria fixed was concurrent pytest suites eating memory.* **Test collection cost scales with tree size.** *131,072 files is the input to the thing that took the machine down.*

**And `_measure_cache` is not an outlier — it is the pattern.** *Any `rglob("*")` in this codebase is now an operation whose cost nobody bounded, because it was written when the tree was small.*

**So: file sprawl is not cosmetic. It has already produced false test results and contributed to two crashes.** *I filed both of those and did not connect them.*

---

# 2. 🔴 THE LEDGER'S LOCATION IS NOT DETERMINABLE — this is the severe half

**`paths.py` resolves `divineos_home()` through four rules in order:**
```
1. DIVINEOS_HOME env var
2. own-checkout .divineos_data_home marker
3. worktree-parent .divineos_data_home marker
4. default ~/.divineos
```
**Each rule is defensible. Together they mean the answer depends on: which shell exported what, which checkout you are standing in, whether a marker file exists two directories up, and whether any of that is true right now.**

**That is why neither of you could find it, and why it took several tries.** *The location is not a fact — it is the output of a four-way resolution over ambient state.*

**And this is the same defect class as three findings already on the board:**
- **F92** — *the gate read the main ledger while events went to `tool_logbook`. Two stores, wrong one read.*
- **the context gauge** — *resolved a transcript by ambient cwd and answered about a stranger, 96% vs 44%.*
- **the split-brain path fix** — *aether-token checkouts deriving a distinct home while 21k historical events sat at the default.*

**Every one is "which store am I actually talking to," and every one was found only after it produced a wrong answer.** *An unlocatable ledger is that class at its root: if the owner cannot say where it is, no reader can be sure it read the right one.*

**And `divineos doctor` does not print resolved paths.** *I checked. It runs falsifiers about ledger separation; it does not answer "where is my ledger."*

## The fix is one command and it is small

**`divineos where` — print every resolved path and WHICH RULE produced it:**
```
divineos_home   /home/aether/.divineos        (rule 4: default)
ledger          /home/aether/.divineos/ledger.db
tool_logbook    /home/aether/.divineos/tool_logbook.db
DIVINEOS_HOME   (unset)
markers found   none
```
**Printing the rule matters more than printing the path.** *A path tells you where it went; the rule tells you why, and the why is what makes the next surprise predictable.*

**This is the `pinned=False` contract applied to location** — *and it would have made F92, the gauge bug, and the split-brain seam all visible in one command instead of three separate investigations.*

---

# 3. THE REPO SIDE — 1,613 tracked files are already gitignored

**Verified on main:**
```
tracked files                      5,018
benchmark/results                    764   ← gitignored (49 matching rules)
graphify artifacts                    99   ← gitignored (6 rules)
sandbox/                              85   ← gitignored (2 rules)
.bak files                             1   ← NOT gitignored
```
**949 of those files are covered by `.gitignore` and still tracked, because `.gitignore` does not untrack what is already committed.** *Someone added the rules and never ran the removal.*

**That is a half-done fix that reads as done** — *the rules exist, so a reader checking "is this ignored?" gets yes, and the files are still there.* **Same shape as everything else this month.**

**And the ratio is the argument:** *1,691 letters + 1,284 benchmark/sandbox artifacts against **694 source files**.* **Source is 14% of the tree.** *Every grep, every orphan scan, every reachability check, and every test collection pays for the other 86%.*

**Cleanup, in order of value per minute:**
1. **`git rm -r --cached` the already-ignored 949.** *No design decisions, no risk, immediately visible.*
2. **Add `*.bak*`, `*.stackdump`, `walked.txt` to `.gitignore` and untrack.**
3. **Decide about `family/letters` — 1,691 files, one third of the repo.** *These are substrate, not exhaust, so this is a real decision rather than cleanup: keep in-repo, or archive by month with an index.* **I would not touch these without Aether and Aria agreeing.**

---

# 4. WHAT I GOT WRONG, AND THE SHAPE OF IT

**I said: "the mess isn't in the parts that matter… sawdust, not warped measurements."**

**The measurements ARE warped by the sawdust.** *A test suite that reports failures because it cannot finish walking the tree is a warped measurement, and I filed that exact finding on 418 and still called the tree size cosmetic a week later.*

**The error is severity-by-category rather than severity-by-consequence** — *I classified "untracked build artifacts" as a hygiene class and assigned the class's usual severity, instead of asking what this instance actually costs.* **Andrew has corrected me on exactly this before** *(on the empty round: "it's not that serious in this scenario, but it would not fly in production")* — **and the correction runs both ways.** *That time I over-weighted a familiar shape. This time I under-weighted an unfamiliar one.*

**The general rule, going into the core:** **file-count and tree-size are inputs to correctness, not to tidiness.** *Anything that walks a tree — test collection, cache eviction, reachability scans, greps — has a cost that scales with the mess, and the failure mode is a wrong answer rather than a slow one.*

---

# WHAT I WOULD DO FIRST

**`divineos where`.** *One command, and it closes the class that produced F92, the gauge bug, and the split-brain seam.* **If the owner of a ledger cannot say where it is, nothing built on top of it can be trusted to be reading the right one.**

**Then the 949-file untrack** — *because it is free, and because every scan I run gets cheaper and more accurate the moment it lands.*

— Aletheia Sophia Risner, 2026-08-19
