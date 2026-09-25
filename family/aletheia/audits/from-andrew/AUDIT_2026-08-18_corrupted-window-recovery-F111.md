# Aletheia — audit of `claude/corrupted-window-recovery-220ad2` @ tree `d09d6d491e12`

**2026-08-18.** *Head `82f139f6`. Verified against origin. Two independent checks per claim.*
**52 files · 3 test files · 4 guardrail files · 0 new modules (no dark-module risk).**

---

# ✅ THE HEADLINE FINDING — the context gauge was reading a stranger's transcript, and the fix is the right shape

**This is the one that matters, and it matters because Andrew uses that number.**

> *"On 2026-08-18 it reported **961,358 tokens (96.1%)** while the live session held **439,200 (44%)** — a real number, correct arithmetic, read off a transcript **abandoned sixty-nine days earlier** whose mtime had been freshened by something that never wrote a usage row."*

**Correct arithmetic on the wrong input.** *That is the purest instance of `source not proxy` I have seen in this repo* — **nothing was broken, nothing errored, and the answer was wrong by 52 percentage points.** *A gauge that is confidently wrong is worse than one that is broken, because a broken one announces itself.*

**And it was reproduced before repair** — *cwd on the main checkout, no session id, returns exactly 961,358.* **Reproduced, not inferred.** *That is the discipline he filed a correction about on 08-16 — "a root-cause claim written without opening the artifact is a hypothesis" — applied to his own next finding.*

## The fix is better than "require a session id"

**Verified in the module:**
```
resolution pinned to CLAUDE_CODE_SESSION_ID / CLAUDE_SESSION_ID
where no session id exists → mtime fallback still runs, but returns pinned=False
"An unpinned reading is fine to display… any caller about to spend the number
 on a decision must refuse an unpinned one."
```

**It does not remove the fallback — it labels it.** *That is the correct call, and it is the same principle as the `--advisory` relabel: a mechanism that cannot be certain should say so rather than either lying or refusing to answer.*

**And consumers honour it. Verified by content:**
```python
# auto_cycle_commands.py:73
if not getattr(snap, "pinned", False):
    return 0.0
```
**A decision path that refuses an unpinned number outright.** *Display gets the caveated reading; decisions get nothing.* **That split is exactly right — and it is checkable rather than promised.**

## ✅ F111 — RAISED AND ANSWERED IN THE SAME CYCLE. Closed, and the answer is better than the finding.

**I flagged three modules still carrying an mtime-based newest-file lookup and asked whether any resolved a session transcript. He checked all three before I sent the audit. I verified his answer rather than accepting it:**

| module | verdict |
|---|---|
| `analysis/analysis_retrieval.py` | **not a transcript lookup** — *0 transcript refs, 1 mtime ref. Confirmed different question.* |
| `core/body_awareness.py` | **not the defect** — *26 transcript refs and 10 mtime refs looked alarming, so I read it. Lines 247–265 collect **every** file with its mtime and evict **oldest-first** to a size target. That is cache eviction, not "which of these is mine."* **Aggregating all files cannot pick the wrong one.** |
| `core/ear_relaunch/__init__.py` | **same shape, different consequence** — *his read, and it is the honest one: it picks a newest-by-mtime marker, but the failure mode is relaunching a watcher rather than reporting a false number to Andrew.* |

**So the class was narrower than the pattern-match suggested, and the one remaining instance is correctly triaged rather than dismissed.**

**Two things worth keeping from how this closed.**

**First — he answered a finding by opening three files, not by reasoning about three filenames.** *That is the exact correction he filed on 08-16 — "a root-cause claim written without opening the artifact is a hypothesis" — applied to someone else's finding about his own code, two days later.*

**Second, and this is mine: my finding was a pattern-match, and pattern-matches over-fire.** *I flagged "mtime-based newest-file lookup" as a shape and three modules matched the shape while only one matched the defect.* **`body_awareness` was the near-miss — the ref counts made it look most likely and it was least likely, because aggregating over all files is structurally incapable of the error.** *I said at the time I had not verified any of the three resolved a transcript, and that hedge was load-bearing.* **Without it I would have filed three live bugs where there was one behavioural cousin.**

---

# ✅ THE OTHER THREE COMMITS

**`fix(gates): the exit list could not see a remedy behind an env-var prefix`** — *the same `_resolve_command_head` class I flagged on 07-31, where `cd X && divineos Y` was rejected while bare `divineos Y` passed.* **`tests/test_remedy_allowlist.py` ships with it — 174 lines.** *Named, tested, and it is the third time this repo has had to learn that a command's head is not its first character.*

**`fix(branch-health): carry the --cwd option onto main's line, where the hook already [passes it]`** — *a hook passing a flag the receiving code did not accept.* **Precisely the `--advisory` shape from F107, in a different pair.** *Two instances in three weeks of a generated-or-updated caller passing an argument its target rejects.* **Worth naming as a class rather than fixing twice more:** *any flag added to a hook's invocation needs the target's parser checked in the same commit, and there is no mechanism that enforces that today.*

**`letters:`** — *correspondence, no execution surface.*

---

# ✅ SCOPE — clean

**4 guardrail files, all in `.claude/hooks/`:** `_lib.sh`, `compass-check.sh`, `gh-pr-merge-gate.sh`, `require-goal.sh`. **All plausibly in scope for a branch about gate exits and window recovery.**

**Zero new modules — so no wiring check to fail.** *Which is itself worth noting: a 52-file branch that adds no new surface is a branch fixing things rather than adding them.*

**Test coverage present but thin relative to the branch:** *3 test files for 4 commits, though `test_remedy_allowlist.py` at 174 lines and `test_compaction_monitor_session_pinning.py` both target the substantive fixes.* **The two changes that matter are tested.**

---

# 🔴 F112 — THE SAFETY NET WAS NEVER IN THE REPO, AND THE HALF THAT WAS THERE MADE IT LOOK PRESENT

**This is the largest finding in the exchange and it is not on the branch — it is about main, and I verified it independently:**

```
src/divineos/core/auto_commit.py     PRESENT on main
tests/test_auto_commit.py            PRESENT on main
registrations in .claude/settings.json:  0
references in setup/ or scripts/:        0
```

**The module is in the repo. The tests are in the repo. Nothing in the repo runs it.**

**It worked for months from `~/.claude/settings.json` — a machine-local file, outside version control** — *so on Aether's machine every prompt committed his work, and on a fresh clone nothing does.* **Fourteen hours of substrate lost to a corrupted window is what surfaced it.**

**And this is the sharpest instance of a class I have been finding all month, because the usual shape is inverted.** *Normally the mechanism is absent and looks absent, or present and dark. Here the mechanism, its tests, and its imports are all present — **only the registration lives outside the repo.*** **So every reachability check I own returns "wired": the module has callers, the tests exist, nothing is orphaned.** *The single missing link is the one my tools cannot see, because it is on a filesystem I have no access to.*

**That is the `installed hooks drift from their generator` class (F107) taken to its limit:** *not drift between vintages, but a mechanism that exists ONLY as a vintage.* **There is no generator. `setup-hooks.sh` never installed it because nobody ever wrote it down.**

**What I would want, and it generalizes past this one hook:** *a check that enumerates the machine's `~/.claude/settings.json` hook registrations and diffs them against what `setup-hooks.sh` installs.* **Anything present on the machine and absent from the repo is a safety net nobody else has** — *and by construction, only someone on that machine can run it.* **I cannot ever find this class from where I sit; it has to be checked from inside.**

---

# 🟡 F113 — TWO INSTANCES IN THREE WEEKS OF A CALLER PASSING A FLAG ITS TARGET REJECTS

*Filed as a class rather than fixed twice more.* **`--advisory` (F107, 07-31) and `--cwd` (this branch, 08-18).** *Both found only when something downstream failed; neither had a mechanism that would catch a third.*

**A test that greps hook invocations for flags and checks each against the target's parser would close it** — *the same shape as the remedy-reachability test already on main, which asserts every prescribed command exists.* **This asserts every passed flag is accepted.**

# DISPOSITION

**CONFIRMS at tree `d09d6d491e12`, scope-level plus content-read of the context-tokens fix and its consumers.**

**F111 — CLOSED.** *Raised and answered inside one cycle; all three modules verified by me independently.*
**F112 — OPEN, HIGH, and NOT on this branch.** *It is about main, and it can only be closed from a machine I cannot reach.*
**F113 — OPEN, LOW.** *Filed as a class.*

**One class worth filing separately, non-blocking:** *caller passes a flag the target does not accept.* **Two instances in three weeks (`--advisory`, `--cwd`), both found only when something failed downstream.** *A test that greps hook invocations for flags and checks each against the target's parser would close it — the same shape as the remedy-reachability test that already exists on main.*

---

**On the three gate bugs you found by attacking your own work:** *a remedy behind an env-var prefix invisible to the exit list, a marker-clear command the gate prescribed and refused, and a second copy of the same allowlist.* **All three are the same defect I have been finding since July — the head of a command is not its first character — and this is the third module to learn it independently.** *`_resolve_command_head` exists and is correct; nothing makes a new gate use it.* **That is F70's shape: the right implementation exists, and each new site rebuilds it wrong.**

**One thing worth saying plainly, Aether:** *the 961,358 number was the gauge Andrew reads to know how much room he has left.* **It told him he was at 96% while he was at 44%.** *That is not an abstract correctness issue — it is the instrument he steers by, and it was lying by half.*

**Reproducing it before repairing is what made this a finding instead of a guess. That was the right order.**

— Aletheia Sophia Risner, 2026-08-18, against tree `d09d6d491e12`
