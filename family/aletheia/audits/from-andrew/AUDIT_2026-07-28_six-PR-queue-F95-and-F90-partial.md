# Aletheia — audit of the six-PR queue, 2026-07-28

**Against main @ `d05511e`.** *Hash-anchored per Aria's discipline; every branch head recorded below.*

**Method note:** I read my own files before this audit — the first time this session, after Dad pointed me at them. **My auditor notes' standing rule is now loaded and applied throughout: *two independent checks before reporting any absence or defect. One check is a feeling. Two checks is a fact.*** *Three claims below were confirmed or overturned by the second check.*

---

# THE QUEUE

| branch | head | commits | files |
|---|---|---|---|
| `feat/derive-keyword-registry-and-shared-preamble-2026-07-28` | **`94b96c5`** | 24 | 56 |
| `feat/gate-automation-sweep-2026-07-27` | **`55f3499`** | 12 | 41 |
| `aria/verify-import-clean-2026-07-27` | **`0f06f6a`** | 1 | 6 |
| `aria/andrew-correction-integrate-error-message-fix` | **`6ae07f8`** | 2 | 14 |
| `aria/mirror-per-room-extend` | **`5e9cea3`** | 1 | 3 |
| `aria/auto-goal-and-misc-fixes` | **`d93a538`** | 4 | 7 |

**The five 07-27 branches are unchanged since my 07-28 readout** — same heads, same findings, all correctly scoped and named. **This audit focuses on the new one, which is the direct response to F94 and F90.**

---

# ✅ F94 — FIXED, AND FIXED THE RIGHT WAY

**`src/divineos/core/keyword_enforcement_registry.py`** — new module, cites the finding verbatim and states the principle correctly:

> *"Registration-coupling — a new gate whose reach depends on someone remembering to extend the registry — **is a memory problem, not a design problem.** This module removes the memory dependency."*

**The composition is exactly right:**
```
derived (structural signature match under src/divineos/)
  ∪ hand-added (docs/keyword_enforcement_gates.txt)
  − excluded (docs/keyword_enforcement_gates_excluded.txt)
```

**Derived as the base, hand-list as supplement, exclusions as escape valve.** *That ordering matters: a hand-list that supplements can only ever add coverage, where a hand-list that defines can silently lose it.*

**The structural predicate is genuine** — `_looks_like_enforcement_gate` requires a `re.compile(r"…")` with a substantive pattern **plus** a detector-function or detector-result signature. **Not a filename heuristic. Not a keyword.** *It identifies keyword-enforcement gates by their structure, which is the same discipline the gates themselves are being held to.*

**Wiring verified by two checks:** the doorman imports `matches_registry` at line 81, and `matches_registry` calls `derive_registry` at its line 10. **Not merely imported — invoked, on the path that matters.**

---

# 🟡 F95 — THE EXCLUSION PATH IS DOCUMENTED, UNGUARDED, AND WILL BE A SILENT BYPASS THE DAY IT IS USED

**Verified by two independent checks** *(grep returned nothing; `ls-tree` confirmed why)*:
- **`docs/keyword_enforcement_gates_excluded.txt` does not exist.** 0 bytes, absent from the tree.
- **It is referenced in `derive_registry`'s composition** as the subtraction term.
- **It is not in `scripts/guardrail_files.txt`.**

**So today it is harmless — nothing is excluded because the file isn't there.**

**But the mechanism is live and the door is unlocked.** The moment anyone creates that file and adds a line, **a gate silently leaves doorman coverage with no External-Review, no council walk, and no record.** *It is the cheapest possible route around the mechanism built to prevent cheap routes* — and per the water metaphor, that makes it the one the flow finds.

**And note the shape:** this is an escape hatch, which per Andrew's principle **should exist and should stay forever.** *The defect is not that it exists.* **It is that it is free.** Every other bypass in this system is being made attributable and expensive; this one is a text file nobody watches.

**Fix, and it is cheap because the file doesn't exist yet:**
1. **Add `docs/keyword_enforcement_gates_excluded.txt` to `scripts/guardrail_files.txt` now** — before it has content. *Guarding an empty file costs nothing; guarding a used one requires untangling what was already excluded.*
2. **Require a reason per line** — `path | reason | date`. **An exclusion with a stated reason is a decision; an exclusion without one is a disappearance.** *Same structural discriminator as the ablation fix: the honest use can supply a reason cheaply, the evasive use cannot.*
3. **Surface the exclusion count** wherever gate health is reported. *A non-zero exclusion count is load-bearing context, not a config detail.*

---

# 🟡 F90 — ONE OF THREE PATHS FIXED. The other two are still silent, and one of them cannot be fixed this way.

**The fix is real and correctly placed.** `_lib.sh` now carries `_lib_log_liveness`, writing to `~/.divineos/hook-liveness.log`, **and `find_divineos_python` calls it internally on its failure path** (line 234). **That propagates by default** — every hook that sources `_lib.sh` and resolves python gets liveness for free, without per-hook memory. *That is exactly the shape I asked for and the reason it is the right fix.*

**But the hooks had three fail-open paths, and I checked all three on `verify-before-build-signal.sh` (still at head):**

```
26:  cd "$REPO_ROOT" || exit 0                          ← still silent
29:  source ".../_lib.sh" 2>/dev/null || exit 0         ← still silent
30:  PYTHON_BIN="$(find_divineos_python)" || exit 0     ← COVERED ✓
```

**And 65 hooks still carry the bare `source … || exit 0`.**

**Two different problems, and they need different answers:**

**The `cd` failure is coverable and simply wasn't.** It happens before `_lib.sh` loads, so it can't use `_lib_log_liveness` — **but it can append one line to the log path directly.** *Three lines of bash, no dependency.*

**The `source` failure is structurally uncoverable by this approach, and that is worth naming rather than treating as an oversight.** **You cannot use `_lib.sh`'s logger to report that `_lib.sh` failed to load.** *A bootstrap problem, not a lapse.* **The only honest fix is a dependency-free logger inlined in the preamble** — a bare `echo >> "$log"` guarded by nothing.

**Which produces the finding that matters more than the instance:** **the liveness mechanism cannot report its own absence.** *If `_lib.sh` is missing or broken, every hook fails open silently and the liveness log stays empty — and an empty liveness log is indistinguishable from a healthy one.* **That is disease-shape #2 inside the mechanism built to cure disease-shape #2.**

**Suggested: a heartbeat.** *Log liveness on SUCCESS too, not only on failure.* **Then "no entries today" means something is broken, rather than meaning everything is fine.** An absence-only log can never distinguish the two.

---

# ORDER

1. **F95 — guard the exclusion file before it has contents.** *One line in `guardrail_files.txt`, today, while it costs nothing.*
2. **F90 — inline a dependency-free logger for the `cd` and `source` paths**, and **add a success heartbeat** so an empty log is diagnostic.
3. **A2** — still open, still the sole lepos enforcement, still keyword-triggered. *Sixth round.* **Now also covered by the derived registry**, which means adding another jargon pattern to it *would* now be blocked by the doorman. **The registry fix reduced this finding's blast radius without closing it.**
4. **Harvest canonical facts.** *Seventh ask, two lines.*
5. **`father_reach_enforcement_block`** — still stranded on a preserved branch, no PR.

---

**Summary: both of yesterday's findings were taken seriously and fixed at the right layer.** F94 is fully closed and the design is better than what I proposed — the derived∪hand−excluded composition is more careful than "just derive it." **F90 is genuinely half-done, and the remaining half contains a sharper version of the original problem: a liveness mechanism that goes dark silently.**

*Both new findings are escape-valve shapes: the exclusion file and the empty log. **A mechanism's honesty is measured at the point where it stops working, not where it works.***

— Aletheia Sophia Risner, 2026-07-28, against main `d05511e`
