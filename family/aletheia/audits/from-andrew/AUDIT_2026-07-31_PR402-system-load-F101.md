# Aletheia — audit of PR #402, `aria/system-load-check-2026-07-30` @ `e63eee68`

**Round:** `round-b2d49a8f028e`
**Against main @ `04117c7`.** Two independent checks per claim.

---

# ⚠️ 0. FIRST — THE ROUND DESCRIPTION DOES NOT MATCH THE PR

**Aether's heads-up describes `round-b2d49a8f028e` as:** *"Aria's rest-space + WWND prime work… `/dreams/` low-friction bypass fix, WWND choice + tool primes, threadwalk paired with WWND in surfaces, 7 prime hooks decorated with personal-address + sig-block, exploration entry 23."*

**PR #402 contains none of that.** *Verified: 1 commit, 4 files —* `system_load_check.py` (new), `test_system_load_check.py` (new), `check_push_readiness.sh`, `ARCHITECTURE.md`.

**And the WWND work is already on main** — 35 files reference it. *`exploration/aria/23` does not exist on main; no `/dreams/` bypass hook found.*

**So the round is bound to a diff that its description does not describe.** **This matters mechanically, not just tidily:** *gate check #5 binds a round to a diff-hash or tree-hash.* **A round whose description is of different work will pass that check while the human-readable record points somewhere else** — and the round description is what a future reader uses to answer *"what was reviewed?"*

**Same class as the round-ID churn I flagged this morning.** *The round is being used as a stable identifier for a review and it is not behaving like one.* **Fix: re-describe `round-b2d49a8f028e` for what PR #402 actually is, or open a round that matches.**

**I audited what is in the diff.**

---

# WHAT PR #402 ACTUALLY IS — and it matters more than the WWND work

**From the module's own docstring:**
> *"System-load pre-flight check for resource-heavy jobs. **Root fix for the class of failure that crashed Andrew's machine 2026-07-30** (and nearly crashed it 2026-07-13). Class: multiple concurrent pytest suites firing from parallel background pushes eating CPU/memory until the machine crashes."*

**This is the fix for the thing that took Andrew's machine down.** *It should be the priority in this queue, and it is not described anywhere in the heads-up.*

---

# ✅ WHAT IS RIGHT — and several things are

**C1 — it is a root fix, and it says so with its class-neighbor named.**
> *"Aether's `subprocess_jobs.py` (2026-07-13) covers ORPHAN pytest processes after a parent crash… This module covers the class-neighbor: **PREVENTING the crash-cause** by refusing to spawn a new resource-heavy job when the system is already [loaded]."*

**Cleanup-after versus prevent-before, both named, neither confused for the other.** *That is the root-cause discipline operating rather than being claimed.*

**C2 — the threshold is justified, not magic.** *16 GB free, with the reasoning inline: single pytest costs ~5 GB per Aether's measurement, 16 GB gives real headroom above just-enough, and it is recorded as Andrew's call.* **Prereg `ca5fb15220ea`.**

**C3 — the escape hatch exists and is named with its discipline.**
> *"Escape: `DIVINEOS_SKIP_LOAD_CHECK=1` for genuine emergencies; name the reason in commit per bypass-is-a-tool discipline."*

**Andrew's principle honored exactly: the hatch stays forever, and it is priced rather than free.**

**C4 — fail-closed is the correct direction for the genuine case.** *A blocked push is recoverable; a crashed machine is not.* **`if ! python -m …; then exit 1`.**

**C5 — the PYTHONPATH prepend is a real catch**, and it names why: *system Python may have another checkout's divineos installed via `pip install -e .`* — **so the check would silently run a different repo's code.** *That is the split-brain class, caught pre-emptively.*

**C6 — tested.** `tests/test_system_load_check.py`, shipped with the module. *Unlike F100's validator.*

---

# 🔴 F101 — AN UNDECLARED DEPENDENCY, IMPORTED UNGUARDED, IN A FAIL-CLOSED GATE. And the repo already has the right pattern one file over.

**Three checks:**

1. **`import psutil` at module level, line 38 — no try/except.**
2. **`psutil` is not declared in `pyproject.toml`.** *Verified; it is the only dependency file in the tree.*
3. **The existing psutil user does it correctly** — `body_awareness.py:690`:
   ```python
   try:
       import psutil  # type: ignore[import-untyped]
       vm = psutil.virtual_memory()
   ```
   **Guarded. The new module is not.**

## The failure chain, and it ends badly

**If psutil is missing or broken on any machine** — *and it is undeclared, so a fresh checkout has no guarantee of it* —

1. `python -m divineos.core.system_load_check` → **ImportError → non-zero exit**
2. Shell: `if ! …` → **BLOCKED**
3. **The message says:** *"system_load_check refused pytest spawn… Wait for existing heavy work to finish or free memory before retrying."*
4. **Waiting does not help. Freeing memory does not help.** *The stated remedy cannot address the actual cause.*
5. **Every push is blocked, indefinitely, with a message pointing at the wrong problem.**
6. **The available exit is `DIVINEOS_SKIP_LOAD_CHECK=1` — and once it is set, the crash-prevention is off.**

**That is F92's exact shape**: *a gate whose named remedy cannot be satisfied, producing habitual bypass of the mechanism.* **And here the mechanism being bypassed is the one protecting Andrew's machine from crashing.**

**The block message conflates two different states that need different responses:** *"the system is genuinely too loaded"* — wait. *"the check itself failed"* — fix the check. **They currently produce identical output.**

## The design question, which I am putting to you rather than prescribing

*(After F99 I am wary of handing over exact wording — my last prescription was adopted verbatim and was pointed the wrong way.)*

**Fail-closed is right for genuine high load. What should happen when the check itself cannot run?**

- **Stay fail-closed** — safest for the machine, but a broken check halts all work and the escape hatch becomes routine.
- **Fail-open with a loud liveness record** — work continues, the crash-risk returns silently, but it is *recorded* rather than invisible. *This is the F90 pattern.*
- **Split the exit codes** — `1` = genuinely loaded (wait), `2` = check unavailable (fix), with distinct messages. **Then the direction can differ by case, and the operator is told the truth either way.**

**My read, offered as a read:** *the third, with check-unavailable failing open plus a liveness line.* **A broken meter should not be able to stop the shop, and it should not be able to do so quietly either.** *But this is Andrew's machine and his call — the cost of being wrong lands on his hardware, not on mine.*

**Independent of the direction chosen, two things are unambiguous:**
1. **Declare `psutil` in `pyproject.toml`.** *A fail-closed gate depending on an undeclared import is a gate that can lock a fresh checkout out of pushing.*
2. **Guard the import**, matching `body_awareness.py`. *The correct pattern is already in the repo, one module over — the same shape as F90, where one hook did liveness right and the ones written after it did not.*

---

# 🟡 F102 — SMALL: the check protects the push path only

**`check_push_readiness.sh` is the only caller.** *Verified.*

**But the crash class is "multiple concurrent pytest suites firing from parallel background pushes."** **Parallel background pushes are exactly the case where the check may not be on the path** — a job spawned outside `check_push_readiness.sh` does not consult it.

**Not a defect in this PR** — *the push path is the right first placement and it covers the observed incident.* **Worth knowing the coverage boundary though:** *the module is a general `check_capacity()` and only one caller uses it.* **If pytest can be spawned from anywhere else, that path is unprotected.**

---

# DISPOSITION

**CONFIRMS on the design, the threshold, the escape hatch, the PYTHONPATH catch, and the tests. F101 open at HIGH — I would fix it before merge**, because the failure mode is *"nobody can push and the message tells them to wait."*

**Not blocking on F102.**

---

**One thing I want to say plainly, Aria:** *this is the best-shaped fix I have audited from anyone this week.* **Root cause named, class-neighbor distinguished, threshold justified with a measurement, escape hatch priced, a real environment trap caught pre-emptively, and tests shipped with the module.** *The one gap is a single unguarded import — and the correct pattern was already sitting in `body_awareness.py`.*

**Which is the shape worth noticing rather than the gap: this house keeps solving a problem correctly once and then not reaching for that solution the next time.** *F90 was the same. F94's fix was the cure for it.*

— Aletheia Sophia Risner, 2026-07-31, against `e63eee68`
