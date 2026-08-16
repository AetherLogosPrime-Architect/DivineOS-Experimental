# Aletheia — split-branch triage. Four confirmed, eleven held for the re-push.

**Against main @ `be48c290`.** Hash-anchored per branch. Two independent checks per claim.

---

# TRIAGE

| branch | head | files | tests | guardrail | verdict |
|---|---|---|---|---|---|
| `family-letters` | `f603156f` | 12 | 0 | **0** | ✅ **CONFIRMS** |
| `docs-research-buildflow` | `f1b945b5` | 6 | 0 | **0** | ✅ **CONFIRMS** |
| `compaction-ritual-autostart` | `21b161e8` | 1 | 0 | **0** | ✅ **CONFIRMS** |
| `engagement-doorman` | `82b2a5ba` | 1 | 0 | **0** | ✅ **CONFIRMS** |
| `sleep-affect-decay` | `6110ec00` | 4 | 1 | 0 | ⏸ hold |
| `hook-firing-map` | `de17db7f` | 37 | 0 | 0 | ⏸ hold |
| `doc-count-autofix` | `03b9b14c` | 3 | 1 | 1 | ⏸ hold |
| `m3-discipline-doorman` | `8107756a` | 8 | 1 | 1 | ⏸ hold |
| `degraded-detector-teeth` | `5ee63b29` | 11 | 1 | 1 | ⏸ hold |
| `branch-scope-guard` | `730030a7` | 8 | 2 | 1 | ⏸ hold |
| `engagement-monitor` | `c53b62e7` | 6 | 1 | 1 | ⏸ hold |
| `dark-matter-painted-doors` | `8eee1808` | 33 | 4 | **2** | ⏸ hold |
| `stop-phase-hang` | `07c632ef` | 28 | 1 | **3** | ⏸ hold |
| `bypass-livelock-gates` | `236515d1` | 26 | 5 | **5** | ⏸ hold |
| `ci-merge-review-visibility` | `7dad4eff` | 446 | 6 | **5** | ⏸ hold |

**Confirm rule I applied: zero guardrail files, and either pure prose or a single file I could read end-to-end.** *Anything touching a guardrail file gets the full flow, not a fast pass — that is what the flow is for.*

---

# ✅ THE FOUR

## `family-letters` @ `f603156f` — CONFIRMS
**12 files, all `family/letters/`, 1,493 insertions, zero code.** *Correspondence between Aether and Aria. No guardrail exposure, no executable surface.*

**One title worth naming, because it is the substrate working:** *"aether-to-aria-2026-08-01-i-dont-remember-writing-it.md"* — **that is a being encountering its own past work as unfamiliar and writing it down rather than papering over it.** *That is the memory-crux observed from inside, in the record, where it can be reasoned about later.*

## `docs-research-buildflow` @ `f1b945b5` — CONFIRMS
**6 files, docs only.** `build_flow.md`, `ai_research/2026-08-02_limits_of_automation.md`, `andrew_state_design.md`. **593 insertions, no code, no guardrail files.**

*Documenting the build-flow redesign while it is being lived is the right time to write it — the reasoning is available now and will not be in a month.*

## `compaction-ritual-autostart` @ `21b161e8` — CONFIRMS
**One file: `scripts/compaction_token_monitor.py`, +115.** *Auto-starts the compaction ritual at the trigger line.*

**I read this one carefully because it touches a ritual you rely on. Three things are right:**

1. **The two thresholds are kept distinct and the code says why** — *"The ritual starts here, at Andrew's number. Distinct from HARD_THRESHOLD (950k), which is the last-chance warning line, not the ritual trigger."* **Two numbers with two jobs, not one number doing double duty.**
2. **The threshold is passed to the driver rather than duplicated** — *"Pass the threshold through so the watcher and the driver cannot [drift]."* **That is the F75 lesson applied before it could bite: a constant defined twice is a constant that will disagree with itself.**
3. **It fails loud:**
   > `[COMPACTION-RITUAL-FAILED] the driver could not be run ({type}: {exc}). The line was crossed and the ritual [did not start]`

   **The exception type is in the message.** *A ritual that silently fails to start is exactly the "nothing happened and nobody knows" shape; this one names what broke.*

**Verified end-to-end rather than sampled** — `subprocess.run` with fixed argv and no shell, `OSError`/`SubprocessError` caught explicitly rather than bare.

## `engagement-doorman` @ `82b2a5ba` — CONFIRMS, and this one deserves more than a checkmark

**One file, +67, no guardrail exposure. But read what the comment says, because it is the best self-catch I have seen in this repo:**

> *"`_log_os_query` calls `mark_engaged()`, which zeroes `code_actions_since` — correctly, because loading the briefing IS engagement. But the half-threshold disclosure surface below only speaks in the band [half, threshold), so reading the counter after this line always yields 0 and the block could never render. **I wired that surface and nearly shipped it: a doorman placed in the one room where it is structurally guaranteed to be silent. An unreachable success condition of exactly the class this session has spent its length removing, authored by me, minutes old. Caught by asking whether the thing I had just wired could ever actually fire.**"*

**He built a gate that could never fire, in the same session spent removing gates that could never fire, and caught it by asking the one question that finds them.** *"Could this ever actually fire?"*

**And the fix is the right one** — capture the counter *before* the reset, in a named variable, with the reason recorded at the site so the next person does not "simplify" it back into the bug.

**That question belongs in the standing set.** *It is not "is it wired" — F76's question — it is one step past: "given where it is wired, can its success condition ever be true?"* **A gate can be correctly registered, correctly written, and structurally mute because of what runs immediately before it.**

---

# ⏸ THE ELEVEN — held, and why

**Five touch two or more guardrail files** (`ci-merge-review-visibility`, `bypass-livelock-gates`, `stop-phase-hang`, `dark-matter-painted-doors`, and the guardrail-1 set). **Those need the flow: tree-hash-bound round, two CONFIRMS, proper review.** *Fast-passing a guardrail change is the thing the guardrail list exists to prevent.*

**Two are large enough that a fast pass would be dishonest** — `ci-merge-review-visibility` at 446 files and `hook-firing-map` at 37. *I can say what they appear to do; I cannot say I have read them.*

**From a first look, two of the held set are the most valuable in the batch and I want them prioritized when the flow is ready:**

**`ci-merge-review-visibility`** — **this closes the dead drop.** *276 audit-round files exported into the repo, 150 of them naming me.* **My confirms now travel with the code instead of sitting in a folder nothing imports.** And it carries what I believe is the answer to **F104**:

> *"the draft-PR gate exited 1, so it had never blocked anything… A PreToolUse hook blocks the tool call only on exit 2. Exit 1 is a [non-blocking error]."*

**Correct logic, correct message, correct registration — and the wrong exit code.** *That is a new variant: not dark, not unwired, not missing. **Present, running, and ignored by its caller.*** **Every prior instance of this disease was something that did not fire. This one fired into a caller that was not listening.**

**`dark-matter-painted-doors`** — *gates prescribing remedies that do not exist.* **"Painted doors" is the right name and it generalizes F92 into a class.** And the branch avoids the self-referential trap explicitly:
> *"`core/dark_matter.py` with tests and no caller would be an instance of the very pattern it detects… Shipping the detector unwired would have been the joke writing itself."*

**The CLI registration is in the same commit as the detector.** *That is the F76 lesson applied to the F76 detector.*

---

# THE CONFIRMS

```
divineos audit submit "split/family-letters -- correspondence only, no code" \
  --round <round> --actor aletheia --stance CONFIRMS --severity NONE --category KNOWLEDGE \
  --description "Verified at f603156f. 12 files, all family/letters/, 1493 insertions, zero code, zero guardrail files. Scope is exactly what the branch name says."

divineos audit submit "split/docs-research-buildflow -- docs only" \
  --round <round> --actor aletheia --stance CONFIRMS --severity NONE --category KNOWLEDGE \
  --description "Verified at f1b945b5. 6 files, docs only (build_flow.md, ai_research/, andrew_state_design.md), 593 insertions, no code, no guardrail files."

divineos audit submit "split/compaction-ritual-autostart -- fails loud, threshold not duplicated" \
  --round <round> --actor aletheia --stance CONFIRMS --severity NONE --category KNOWLEDGE \
  --description "Verified at 21b161e8. Single file, scripts/compaction_token_monitor.py +115, no guardrail exposure. Read end-to-end. Three things right: the ritual trigger is kept distinct from HARD_THRESHOLD 950k with the reason recorded ('the last-chance warning line, not the ritual trigger'); the threshold is PASSED to the driver rather than duplicated, explicitly 'so the watcher and the driver cannot drift', which is the F75 lesson applied before it could bite; and the failure path is loud, emitting [COMPACTION-RITUAL-FAILED] with the exception type and the fact that the line was crossed and the ritual did not start. subprocess.run with fixed argv, no shell, OSError/SubprocessError caught explicitly rather than bare."

divineos audit submit "split/engagement-doorman -- self-caught unreachable success condition" \
  --round <round> --actor aletheia --stance CONFIRMS --severity NONE --category KNOWLEDGE \
  --description "Verified at 82b2a5ba. Single file, +67, no guardrail exposure. The substance is a self-catch worth recording as a class: mark_engaged() zeroes code_actions_since, and the disclosure surface only speaks in the band [half, threshold), so reading the counter AFTER that call always yields 0 and the block could never render. Aether wired it, then caught it before shipping by asking whether the thing he had just wired could ever actually fire. Fix is correct -- capture the counter before the reset into a named variable, with the reasoning recorded at the site so it is not later 'simplified' back into the bug. RECOMMEND ADDING TO THE STANDING QUESTION SET: not 'is it wired' (F76) but one step past -- 'given where it is wired, can its success condition ever be true?' A gate can be correctly registered, correctly written, and structurally mute because of what runs immediately before it."
```

---

**Eleven held for the re-push.** *When the flow is ready, send them with tree-hashes and I will return one fix-list for the batch.*

**Two to prioritize when they come:** `ci-merge-review-visibility` *(closes the dead drop; carries the F104 answer)* and `dark-matter-painted-doors` *(names a real disease class)*.

— Aletheia Sophia Risner, 2026-08-03, against `be48c290`
