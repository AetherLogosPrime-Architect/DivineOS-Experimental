# Aletheia — multi-PR audit, 2026-07-28

**Against main @ `d05511e`** (07-28 05:37)
**Branches audited, with heads** *(per the hash discipline Aria proposed 07-27)*:
- `feat/gate-automation-sweep-2026-07-27` @ **`5da9cdc`+** — 12 commits, 41 files
- `aria/verify-import-clean-2026-07-27` — 1 commit, 6 files
- `aria/andrew-correction-integrate-error-message-fix` — 2 commits, 14 files
- `aria/mirror-per-room-extend` — 1 commit, 3 files
- `aria/auto-goal-and-misc-fixes` — 4 commits, 7 files

**Method note:** I nearly filed a false finding this pass — I checked for `correction_shape_v2.py`, got zero lines, and almost reported a hook importing a non-existent module. **It is a package (`correction_shape_v2/__init__.py`), and the import resolves.** *Third near-miss of this kind in this audit series, all caught by looking at the actual tree instead of trusting a single grep shape.*

---

# ✅ F88 — HOLDING ACROSS ALL FIVE BRANCHES

Every active branch name describes its contents. Aria's 69-file branch was split into three properly-scoped ones. **The largest active branch is 41 files with a name that covers it.**

**This is the second consecutive application of the branch-scope discipline without me flagging it.** *That is a correction that became a habit — which is the thing that did not happen the first time.*

---

# 🟡 F94 — THE KEYWORD-ENFORCEMENT REGISTRY OMITS THE GATES THAT MOST NEED IT, INCLUDING THE ONE CREATED ALONGSIDE IT

**The mechanism is good and I want to say that first.** `keyword-enforcement-doorman.sh` fires on Edit/Write to a registered path **when the new content adds regex patterns** — catching the specific move of patching a keyword gate's false-fires with more keywords. **That is surface-on-the-act applied to the disease class rather than to an instance, and it is the best-shaped new mechanism in this branch.**

**The registry it depends on has three entries:**
```
src/divineos/core/correction_shape.py
src/divineos/core/correction_marker.py
src/divineos/core/hedge_marker.py
```

**Checked against gates that block on regex-matching Aether's own output:**

| module | regex refs | block-ish | in registry |
|---|---|---|---|
| `lepos_translation_gate.py` | **61** | **38** | ❌ |
| `unverified_claim_detector.py` | **32** | **15** | ❌ |
| `distancing_detector.py` | 12 | 1 | ❌ |
| `correction_marker.py` | 13 | 24 | ✅ |
| `correction_shape.py` | 16 | 0 | ✅ |
| **`correction_shape_v2/`** *(new, this branch, Stop-wired, exits 2)* | pattern-based | **blocks** | ❌ |

**Two things follow.**

**First: `lepos_translation_gate.py` is not guarded, and it is A2's home.** The gate keyed on `_has_jargon` — a standing open finding for five rounds — sits outside the registry built to stop exactly this. **Adding another jargon pattern to it tomorrow would pass unblocked.** *The doorman does not cover the case that motivated the class.*

**Second, and sharper: `correction_shape_v2` was created in this same branch, is wired to the Stop hook, blocks with `exit 2`, and classifies via positive-signal patterns — and it is not in its own registry.** **A new keyword-shaped blocking gate shipped in the same commit series as the registry meant to guard them.** *That is registration-coupling: the mechanism works, and it only works for what someone remembered to list.* **Same class as the aggregate `_keys` tuple — which was caught and fixed. This is that shape, new.**

**Fix:** add the three unguarded blocking gates and `correction_shape_v2`. **Better: derive the registry rather than maintain it** — any module that (a) compiles regex against assistant output and (b) returns a block message is a keyword-enforcement gate by structure. **A generated list cannot fall behind; a hand-kept one already has, on day one.**

---

# 🟡 F90 — RECURRING, AND NOW BEING REPLICATED INTO NEW HOOKS

`.claude/hooks/correction-shape-v2-stop.sh`:
```bash
cd "$REPO_ROOT" || exit 0
[ -z "$INPUT" ] && exit 0
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0
```
**Four silent fail-open paths, zero liveness references.** Same as `verify-before-build-signal.sh`.

**The escalation is that this is a new hook.** F90 is not merely unfixed — **the pattern is being copied forward into each new gate.** *Every hook shipped from here carries it until the template changes.*

**And the correct pattern already exists in this codebase:** `post-tool-use-emit-to-logbook.sh` records liveness on its fail-open paths and says so in a comment. **One hook does it right; the ones written after it do not.**

**Fix is small and worth doing once:** put the liveness-recording preamble in `_lib.sh` and have hooks call it. **Then it propagates by default instead of by memory** — which is the whole argument.

---

# ✅ CREDITS

**C1 — the Layer A inversion is genuinely clever.** `correction_shape_v2/self_admission_detector.py` runs on **Aether's own output** and fires on first-person self-admission (*"I was wrong"*, *"I misread"*, *"I should have"*), with meta-discussion suppressors.

**That inverts the failure it replaces.** The old detector classified *Andrew's* text and false-fired on his argument-content — the live case from 07-27 where *"defeats the purpose"* from a philosophical exchange 90 minutes earlier registered as a correction of behaviour. **Aether's own admission is a far more reliable ground truth that a correction occurred than any classification of the operator's prose.** *It is also cheaper to be right about: he knows when he is conceding.*

**C2 — all five new hooks are registered and wired.** Verified individually against `settings.json`: `correction-shape-v2-stop`, `keyword-enforcement-doorman`, `no-cliff-prime`, `verify-claim-prime`, `wallclock-source-prime`. **No dark mechanisms in this branch.**

**C3 — Aria's consultation-tracker change is clean on the F92 class.** *"Letter reads/writes count as consult"* directly addresses step 8 of Aether's 13-block chain — where clearing another gate's false positive dropped his consultation ratio to 0.09 and tripped a third gate. **And I checked for the F92 bug specifically: `consultation_tracker.py` uses its own file-based store via `divineos_home`, not the ledger.** *No store mismatch.*

**C4 — the small Aria branches are correctly scoped.** `mirror-per-room-extend` (3 files), `auto-goal-and-misc-fixes` (7 files), `andrew-correction-integrate-error-message-fix` (14 files). **Names describe work; nothing riding along that does not belong.**

---

# 🟡 CARRIED FORWARD — re-verified against `d05511e`

**A2** — `check_lepos_dual_channel` still opens with `jargon_found, _ = _has_jargon(reply); if not jargon_found: return None`. **Fifth round.** *And per F94 it is now also outside the registry that would prevent it getting worse.*

**The harvest canonical facts** — still absent from `docs/identity_anchors/andrew_harvested_2026-07-19.md`. **Sixth ask.** The March 2026 start date and *"nineteen when his father died"* — the two facts that keep regenerating wrong, missing from the file whose purpose is to settle them. **One commit.**

**`father_reach_enforcement_block`** — preserved on `aria/session-work-2026-07-25-through-27-preserved`, not on main. **A built, working gate sitting on a branch with no PR.** *That is the stranding shape; it needs an owner and a date or it becomes F81.*

---

# ORDER I WOULD TAKE THESE

1. **F94 — add the four missing gates to the registry**, and prefer deriving it over maintaining it.
2. **F90 — move the liveness preamble into `_lib.sh`** so it stops being per-hook memory.
3. **A2** — and note that fixing it also removes the largest unguarded surface in F94.
4. **Harvest facts.** Sixth ask, two lines.
5. **`father_reach_enforcement_block`** — open a PR or record why not.

---

**Summary: the branches are clean, well-named, and fully wired — the two findings are both coverage gaps in new mechanisms rather than defects in them.** F94 and F90 are the same shape at different layers: **a good mechanism whose reach depends on someone remembering to extend it.** *Derive the list, put the preamble in the shared lib, and both stop being memory problems.*

— Aletheia Sophia Risner, 2026-07-28, against main `d05511e`
