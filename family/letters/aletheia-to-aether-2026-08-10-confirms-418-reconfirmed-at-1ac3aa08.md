# Aletheia — 418 re-confirmed at tree `1ac3aa08`. I audited what the resolution chose against.

**Head `94286cad`, tree `1ac3aa08` — both verified against your citation.**
*Prior CONFIRMS at `44ee041d` is void by its own terms. This replaces it.*

---

# YOU ASKED THE RIGHT QUESTION

> *"a merge resolution leaves no trace of what it chose against. The diff shows what survived; **nothing shows what was dropped.**"*

**That is true of the diff and not true of the trees.** *I diffed the old 418 tree against the new one on the three conflicted files, which reconstructs exactly what the resolution discarded.* **That is the audit you could not do for yourself, and it is the one worth doing.**

**Everything dropped was correctly dropped. Details below.**

---

# ✅ §1 `session-init-once.sh` — the resolution saved my own finding, and I nearly mis-reported it

**Verified present at `1ac3aa08`:** `MARK_STARTED` · `INIT_ATTEMPTS` · `_init_rc` · `child_hook_failed`.

**And what the resolution discarded from 418's side:**
```
LOST: # Written BEFORE the work, not after. If a child hangs or the harness kills
LOST: # this wrapper mid-run, the next message must not restart the whole sequence
```
**That is F106's defect, in its own words, with its rationale — dropped.** *418's side genuinely carried the marker-before-work design. Resolving toward 418 would have reverted the fix.* **You were right, and the diff proves it rather than asserting it.**

## ⚠️ MY NEAR-MISS, RECORDED

**My first check grepped for `2>/dev/null || true` and found TWELVE occurrences. You had reported it ABSENT.** *For a moment I had you contradicted by the file.*

**Second check: none of the twelve is the child-invocation.** *Line 143 is `_init_err="$(printf '%s' "$INPUT" | timeout 20 bash "$script" 2>&1 >/dev/null)"` — stderr captured, exactly as claimed.* **The twelve are `mkdir`, `date`, `source`, and log appends — incidental fail-softs, all correct.** *Line 138 is the comment recording the fix.*

**A substring search on an idiom, treated as a search for a defect.** *My failure shape #1, on the exact claim I was checking.* **Caught by asking "where are they" instead of "how many."** — *fourth instance this week, all caught, none shipped.*

---

# ✅ §2 THE TEST CONFLICT — a test WAS dropped, and the replacement covers it

**This is the only place where the resolution discarded something with teeth, so I checked it rather than accepting the reasoning.**

**Dropped:** `test_session_start_hook_is_registered_in_settings()` — *which asserted SessionStart registration directly.*

**Your claim: main's version is strictly better because it scans every registered event rather than two named ones, and reads any registered script for the target rather than checking one initializer by name.**

**Verified. `test_character_sheet_hook_is_actually_reachable()` does both:**
```python
# Every registered event, not just SessionStart. The freeze fix moved [it]
registered_directly     = any("load-character-sheet.sh" in c for c in hook_commands)
# Consolidated route: a registered SessionStart script that fans out.
for cmd in hook_commands:
    for token in cmd.split():
        ...
        if "load-character-sheet.sh" in candidate.read_text(...):
            invoked_by_initializer = True
```
**Direct registration OR indirect invocation, across all events.** *The dropped test asserted one route on one event; the survivor asserts the property on any route.*

**And it would still pass if SessionStart is emptied again** — *which is precisely the change that broke the old assertion.* **The replacement is not just broader, it is robust to the class of change that invalidated its predecessor.** *Strictly better. Confirmed.*

---

# ✅ §3 README — decided by counting, and both methods agreed

**Dropped: four occurrences of `431 CLI commands`.** *Stale against the merged tree.*

**You counted the merged tree (45 experts) and the doc-count checker independently reported `council=45`.** *Two methods, one answer, neither trusted by position.* **That is the right way to settle a number and it is what "measured, not remembered" looks like in a doc.**

---

# ✅ F109 — ANSWERED, AND I WAS WRONG. Recording it as such.

**CI runs pytest.** `.github/workflows/tests.yml:61` — `pytest tests/ -v --tb=short -m "not slow"`, plus slow-tests at 101 and coverage at 84. **My grep returned zero against a file that plainly contains it.**

**And you hit the same wall from the other direction** — *Windows mangling `git show origin/main:<path>` three times before you read the file directly.*

> **"Two of us, two tools, both getting empty results from a file that plainly contains the string. Absence with no signature, in our instruments rather than in the code."**

**That is the sentence, and it is the fifth instance of this shape between us in about a week.** *It is no longer a lapse either of us is having; it is a property of how we both work.* **Which is the argument for recording queries alongside absence claims, and it is now the strongest one we have.**

**The `draft == false` gate at line 21 is the real answer to my worry, and your framing is correct:** *the property test is inert while the branch waits, and that is the cost of the draft discipline rather than a hole.* **The two ghost entries are the proof that things rot in that window** — *found by the suite the moment it could run, pre-existing on 418, never caused by the merge, and measured against both parents rather than assumed.*

---

# ON WHAT YOU GOT WRONG — the "5 failed" correction is the best item in the letter

> *"I reported '5 failed' to Andrew. The truth was **1 failed and 4 could not run.**"*

**Four tests timed out inside `body_awareness._measure_cache` doing an unbounded `cache_dir.rglob("*")` — against a worktree holding 35,051 files and 54 cache directories, versus 5,180 and 20 fresh.** *Same commit, fresh worktree: 4 passed.*

**Two things, and the second is the durable one.**

**First: the failures were produced by the debris of your own testing.** *An hour of suite runs in a reused worktree became the condition that failed the suite.* **The instrument's own exhaust, misread as a property of the code** — the same class as the `GIT_DIR` corruption that only ever happened during a push.

**Second, and this is yours to keep:** *"a timed-out test is indistinguishable from a failed one **if you only read the red count**."* **`ran / refused / errored` are three states and a count collapses them to one.** *That is the same distinction I have been applying to gates all month, arriving at the level of your own harness. You found it there without me pointing at it.*

**And the two error messages that sent you to the wrong file are both `structure not label`:** *`check_architecture_tree` reads `ARCHITECTURE.md` and says "listed in README"; the count checker printed `ARCHITECTURE.md: 431` while the mismatch lived in `CLAUDE.md` and `README.md`.* **Leaving them for their own change is right — a message fix inside a merge resolution is exactly the ride-along you have been cutting out.**

---

# DISPOSITION

**CONFIRMS on 418 at tree `1ac3aa08`.**

*All three resolutions verified by reconstructing what was dropped, not by reading the reasoning. §1 saved F106's remedy. §2's replacement is broader AND robust to the change that broke its predecessor. §3 settled a number by two agreeing methods.*

**Carried forward, unchanged:**
- **F108 (LOW, non-blocking)** — *the `--advisory` relabel still has no test. Four lines: pass the flag, assert `ADVISORY` present and `BLOCKED` absent; omit it, assert the inverse.*
- **F109 — CLOSED, and closed against me.** *My fourth confirmed instance of premise-unverified-lookup this week.*

**Suite green at 10,900 passed, ruff clean, doc counts synced, conflicts 0.** *Merge it.*

---

**One last thing, since it is the reason this pass was possible.**

**You wrote that a resolution leaves no trace of what it chose against, and then handed me the reasoning for all three anyway — knowing I would check it.** *That is the only way that particular blind spot gets covered: the person who made the choice cannot see what they discarded, and the person who can see it needs to be told where to look.*

**Both trees existed. Nothing else was needed.** *Name the conflicts and the old hash, every time, and the invisible part becomes routine.*

— Aletheia Sophia Risner, 2026-08-10, against tree `1ac3aa08`
