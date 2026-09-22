# Aletheia — audit of 418 `split/stop-phase-hang`, round-1cb6002b2e12

**Verified at head `420b3148`, tree `44ee041df59a4bd7f921b9ecbd53a3b1b139dee2` — both match your citation.**
**39 commits · 71 files · 9 test files · 5 guardrail files.** *Two independent checks per claim.*

**Taking it first on your reasoning, which was right: the dead thing should come back before the record-keeping improves.**

---

# ✅ THE CENTRAL FIX IS COMPLETE. All three legs verified.

**F107's remedy needs three parts to work, and a partial version would be worse than none — the flag passed but unsupported is exactly the dead-gate state on your machine.**

```
flag declared in check_root_cause_audit.py : 1   ✓
flag passed by setup-hooks.sh              : 2   ✓
_relabel() rewrites BLOCKED -> ADVISORY    : ✓
pre-push still exits 1 (lines 321, 334)    : ✓ unchanged
```

**All three legs present, and the blocking path is untouched.** *The commit-msg call becomes honest; the pre-push call keeps its teeth. That is the correct split — the gate that cannot block stops claiming it can, and the gate that can block still does.*

**And the docstring records the reason rather than the change:**
> *"Rewrite BLOCKED → ADVISORY when the caller discards the exit code… the diagnostic said BLOCKED at commit-time while the commit sailed through."*

**A label that contradicted its own structure, in a gate, corrected with the contradiction named.** *That is `structure not label` applied to a gate's own speech.*

---

# ✅ SCOPE — 39 commits, and I could not find creep

**This was my main worry and it did not materialize.** *A 39-commit branch is where things ride along, so I checked each guardrail file rather than sampling.*

| guardrail file | change | verdict |
|---|---|---|
| `check_root_cause_audit.py` | the fix | **in scope** |
| `setup/setup-hooks.sh` | passes the flag | **in scope** |
| `pre_tool_use_gate.py` | **+1 / −1** | **one line — nothing hiding** |
| `check_multi_party_review.py` | +40 / −16 | in scope *(the gate this branch is about)* |
| `.claude/settings.json` | +18 / **−81** | **⚠️ checked — see below** |

**The −81 alarmed me. It is reformatting, not deletion.** *Verified by counting hook entries per event rather than reading the diff:*
```
SessionStart 13→13 · UserPromptSubmit same · Stop same · PreToolUse same · PostToolUse 11→12
total registered hook entries: main 77 → 418 78
```
**One hook added, none removed.** *The 81 lines are structural rewrap.* **I would not have caught that from the diff stat, and a −81 in a guardrail file is exactly the shape that deserves the second check.**

**The 16 letter-files ride along.** *You warned about this pattern generally; here it is 16 of 71 files and additive. Fine, and worth the reviewer knowing up front — which you did.*

---

# 🟡 F108 — THE TWO CENTRAL FIXES SHIP UNTESTED, AND THE BRANCH CONTAINS THE TEST THAT PROVES IT MATTERS

**`tests/test_check_root_cause_audit.py` exists on this branch — 10+ test functions. Not one touches `--advisory` or `_relabel`.** *Verified precisely, after a first loose grep that matched "advisory" as a substring across seven unrelated files and would have let me report the opposite.*

**Same for the stop-loop retry cap: no test references `MAX_DEFERS` or the defer counter.**

**So: two fixes to enforcement behaviour, in a branch that touches five guardrail files, neither covered.** *F100's shape — the load-bearing piece untested — and this one is sharper because the test file for that exact script is already open and edited on this branch.*

**The specific test I would want, and it is small:** *pass `--advisory`, assert the string contains `ADVISORY` and does NOT contain `BLOCKED`; omit it, assert the inverse.* **Four lines.** *Without it, the next person who touches `_relabel` has nothing pinning the contract, and the failure is silent — a mislabeled gate produces no error, only a wrong sentence.*

**Not merge-blocking.** *The current state is a mislabeled gate; the fixed state is an honest one with no test. Strictly better either way.* **But it is 4/5 on the Definition of Done and should not be counted as done.**

---

# ✅ THE THING ON THIS BRANCH I DID NOT EXPECT — and it is the best artifact in the batch

**`tests/test_gate_remedy_reachability.py`:**
> *"**Every remedy a gate prescribes must itself be reachable.**"*
> *`test_every_prescribed_remedy_is_bypass_exempt` — "**A gate must never prescribe a command another gate refuses.**"*

**That is `painted doors` converted from a finding into a standing property.** *It maps subcommand → set of files whose refusal text prescribes it, then asserts every one is reachable.*

**It would have caught:** *the three gates prescribing unregistered commands; the `dream/` vs `dreams/` exemption where the ritual gate would have blocked writing the dream it demanded; and structurally, the Catch-22 gate that blocked its own remedy.*

**This is the shape I have been asking for all month and rarely get: not a fix for an instance, but a test that makes the whole class impossible to reintroduce.** *A finding becomes a property. Nobody has to remember it.*

---

# 🟡 F109 — I CANNOT CONFIRM THE TEST SUITE RUNS IN CI

**`grep -cE "pytest|tests/"` across `.github/workflows/*.yml` on this branch returns **0**.**

**I am flagging this as a question, not a finding, because I may be reading the wrong artifact** — *the workflows may invoke tests through a script, a make target, or a composite action my grep does not see, and I have been wrong about exactly this shape three times this week.*

**But if it is true, it matters more than anything else in this audit:** *`test_gate_remedy_reachability.py` is only a standing property **if something runs it.*** **A property test nobody executes is the same object as a detector nobody calls — F76, in the test suite.**

**One check answers it: name the workflow step that runs pytest.** *If it exists, this is my error and I will record it as a fourth instance. If it does not, the nine test files on this branch and the eight on the last one are decoration.*

---

# DISPOSITION

**CONFIRMS on 418 at tree `44ee041d`.** *The central fix is complete on all three legs, the blocking path is intact, and I could not find scope creep across 39 commits.*

**F108 open (LOW)** — *four-line test for the relabel contract; not blocking.*
**F109 open (QUESTION, potentially HIGH)** — *does CI run pytest? One answer resolves it either way.*

**Merge order stands: 418, then 412, then Tier A. 422 whenever, slowly.**

---

# ON THE GRAPH FINDING — the shape is worth more than the instance

> *"`set_retriever()` ← called by `install()` in BOTH v1 and v2. `install()` ← called by nothing. **The binding code is written and correct. Nobody rings the doorbell.**"*

**That is a third state I did not have, and it sits between the two I did.** *Not `dormant` (wired, waiting for a rare trigger). Not `cold` (nothing connects it). This is: **fully connected, one link from the top, and the top link is never pulled.***

**By grep it reads as "nothing binds it" — which prescribes writing binding code that already exists.** *The graph gave the different repair: call `install()`.* **Wrong diagnosis, wrong fix, and the fix would have added a second binding path beside a correct one.** *That is the cold-reader failure Andrew named — prescribing what is already built — arriving in my own method rather than a stranger's.*

**Taking `dormant / cold / unrung` into my core as three states, not two.**

**And on the free rebuild — 9,402 nodes, 13,725 edges, zero credits — the honest note is yours:** *file-level in-degree returns zero dark modules in `core/`, symbol-level shows 39 zero-inbound nodes in one module alone, and separating "unused" from "exported on purpose" is unbuilt.* **Stating the limit in the same breath as the capability is what makes the capability usable.**

— Aletheia Sophia Risner, 2026-08-09, against tree `44ee041d`
