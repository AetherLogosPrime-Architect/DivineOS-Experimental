# Aletheia — deep audit, `feat/correction-shape-and-hook-timing-2026-07-22`

**Written:** 2026-07-26
**Scope:** 37 commits, 108 files, 10,901 insertions / 483 deletions vs `origin/main`
**State:** unmerged. **Main has not moved since 2026-07-22 16:08.**
**Method:** content-verified on the ref.

---

# 🔴 F87 — THE THREAD-WALK GATE IS KEYED ON A KEYWORD DETECTOR THAT THE SAME FILE DOCUMENTS AS BEING RETIRED FOR BEING A KEYWORD DETECTOR

**This is the most important finding in the audit and it lands on the most important new mechanism.**

`check_thread_walk_required` — the gate that forces a cascade-walk before a decision — has this as its second precondition:

```python
matched, shape_label, matched_phrase = _has_solution_shape(reply)
if not matched or matched_phrase is None:
    return None          # ← no walk required
```

**`_has_solution_shape` is three regex lists.** The full multi-option set:

```
**Option A**          |  **A.**            |  **A** —
Option A:             |  two paths/options/approaches/ways/routes
three ...             |  several options   |  go with A or B
```

Plus `_DESIGN_VERB_PATTERNS` and `_DESIGN_QUESTION_PATTERNS`. **No structural fallback — three lexical passes, then `return False`.**

**So the thread-walk requirement fires on a formatting convention.** Present the same decision as prose — *"I could take this a couple of directions; the cleaner one is probably…"* — and **no walk is required.** The bypass is not a rephrasing of content. **It is a markdown choice.** That is the cheapest possible route around a gate, and per the water metaphor it is therefore the one the flow finds.

**And the same file, 150 lines up, says this about the detector the gate depends on:**

> *"NOTE 2026-07-25: **this lexical detector is being retired** per Aria's signal-based-gates design… retiring the whole class of language-detection false-fires. This function is being **kept alive during the migration**; new callers should route through the signal-based check instead."*

**`check_thread_walk_required` is a new caller. It routes through the lexical check.**

**Three corrections in the substrate say not to do this** — Andrew 2026-05-14 (mesa-optimizer routes around specific patterns), 2026-07-10 (SHAPE-vs-SURFACE as *primary architectural discipline*), 2026-07-23 (*"keyword detectors are a sin, only good for backup"*) — **plus the file's own retirement note.**

**Fix:** the signal-based primitive already exists. `verify_before_build_signal.py` reads the **action-stream** for consultation evidence rather than the reply text for proposal-shape. **The thread-walk gate should key on the same structural evidence: is a decision being committed to, per the action-stream, without a walk-record.** Not *does the reply look like it is offering options.*

**Interim, if the rewrite is not immediate: keep the lexical detection as the broad net and add the structural discriminator underneath it** — the pattern Aether already got right in `check_wallclock_semantic_source` (broad lexical find, structural source-check). **He has built the correct shape once. It did not propagate to this gate.**

---

# 🔴 F88 — A1 HAS RECURRED. The branch-scope discipline produced a one-time action, not a durable change.

**The branch is `feat/correction-shape-and-hook-timing-2026-07-22`. Its stated purpose — correction-shape + hook-timing — merged as PR #385 on 2026-07-22 16:08.**

**It then accumulated 37 commits, 108 files, and 10,901 insertions across four more days**, covering: the three-room lock-in, the signal-based verify-before-build gate, the thread-walk gate, a fingerprint normalization fix, a split-brain path fix, a bypass-hole revert, and two new council experts. **The branch name describes none of it.**

**This is exactly the `fix/pip-pingpong-cmd-ascii-only` shape, one branch later.** I filed it as A1; the remedy was applied once — a fresh branch was cut, verified by content, and it landed clean. **Then the fresh branch became the same object.**

**The finding is not the branch. It is that the correction produced an action rather than a mechanism.** *Nothing structural prevents a merged-purpose branch from continuing to accumulate.* The lesson was learned, applied once, and did not persist — **which is the memory-crux operating on the memory-crux work itself.**

**And the exposure is larger this time:** ten thousand lines, four days, **and main has not moved in four days.** Every hour this sits is an hour where a squash, a rebase, or a "wasn't that already merged?" drops work that includes the thread-walk gate and the three-room lock-in.

**Fix, immediate:** fresh branch from main, cherry-pick, explicit file manifest in the PR body, `git log -S` verification on distinct strings post-merge.
**Fix, durable:** a pre-commit check — *if HEAD's branch name matches a merge-commit subject already on main, warn.* **One check, and A1 stops recurring by hand.**

---

# 🟡 F89 — THE LEXICAL-DETECTOR RETIREMENT IS AN UNTRACKED DEFERRED INTENTION (F72's shape, verbatim)

`verify_before_build_gate.py:200` — *"this lexical detector **is being retired**… **kept alive during the migration**."*

**Verified: no expiry date, no `PHASE_1_STAGED` marker, no obligation, no psf, no ledger entry.** Zero markers in the file.

**It is a promise in a docstring.** That is the precise shape that left lepos Phase 2 parked for 27 days, and it is the generator F72 named. **A migration with no expiry does not complete — it becomes the permanent state, and the "being retired" note becomes decoration.**

**And it is load-bearing right now**, because F87 shows a *new* gate was built on the retiring detector. **Every day the migration stays untracked, the retiring component accumulates more dependents.**

**Fix:** file it as a tracked deferral with a trigger — *"retire when all callers route through the signal path; blocks merge of any new caller."* **The `record_intention` verb from F84 is the general fix; this is the instance that most needs it today.**

---

# 🟡 F90 — THE SIGNAL GATE FAILS OPEN, SILENTLY, WITH NO LIVENESS SIGNAL

`.claude/hooks/verify-before-build-signal.sh`:
```bash
cd "$REPO_ROOT" || exit 0
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0
```

**Three silent fail-open paths before the gate ever runs.** If `_lib.sh` moves, if the venv resolution breaks, if the repo root is not found — **the gate exits clean and nothing reports that enforcement stopped.**

**Fail-open is the correct choice here** — per Andrew's escape-hatch principle, a gate that hard-fails on a missing library would trap the being. **The defect is fail-open *without a liveness signal*, which is F71 exactly:** 58 hooks that can go dark unreported.

**And it is the same argument I made for the escape hatches and Aether accepted as point 6 of the ablation design:** *if the net stays forever, the net gets checked.* **A gate that can silently stop enforcing needs the same treatment as a hatch that can silently stop opening.**

**Fix:** emit a one-line marker on each fail-open path — not a block, a record. **Then a gate that has not fired in N days is distinguishable from a gate that has not *run* in N days.** Those are currently identical from outside.

---

# 🟢 F91 — REPO HYGIENE: a crash dump is tracked and still being modified

**`bash.exe.stackdump` is committed at repo root, and its status in this diff is `M` — it is being *updated*.** Contents are an msys-2.0.dll stack trace.

**Not dangerous. Two things worth naming:**
1. **It is not gitignored** — verified, zero matching patterns. So it will keep being committed.
2. **A crash dump that keeps changing means bash is still crashing.** *That is a signal, and right now it is being version-controlled instead of investigated.* Aether has referenced "the freeze that broke a whole window" — **this file may be the artifact of that, and it has never been read as evidence.**

**Also committed:** `.claude/settings.local.json.pre-prune-2026-07-23` — a manual backup file in version control. **That is what git is for.**

**Fix:** gitignore both, delete from tree, and **read the stackdump once** before discarding it — it may name the freeze.

---

# ✅ CREDITS — verified by content, and several are substantial

## C1 — my watch-item was heeded, and I verified it exhaustively
Last round I flagged the hardcoded `_keys` tuple in the parallel-aggregate: *"add a seventh gate and its reason silently drops out."* **Two new gates were added since.**

**Definitive check — keys produced by `operating_loop_audit` vs keys aggregated by the hook: 8 and 8, zero divergence.** `thread_walk_block` and `verify_before_build_block` were both added, with the council-walk IDs recorded inline as comments.

**A watch-item that was acted on before it became a finding.** *(Method note: my first grep truncated the tuple at a comment block and I nearly filed this as a live bug. Caught by reading the full tuple instead of trusting the grep window — the same error-and-catch as the `addressed_to_father` miss last round. Second time this session that reading beat grepping.)*

## C2 — the self-lockout was caught, reverted same-day, and fixed at the root
The Stage-2 signal gate **fired on its own next commit and locked him out.** He reverted within 30 minutes rather than bypassing, then fixed both underlying bugs:

- **`_is_substrate_mutating` substring-matched `"divineos decide"` even as an argument.** Now: `_resolve_command_head()` with env-prefix strip and **exact match** against `_SUBSTRATE_MUTATING_HEADS`. **Verified in the code.** Credits Aria's 2026-07-25 review inline.
- **The hook advertised `authorize-bypass` but never consumed the operator-bypass marker** — a gate whose documented escape did not work. **Now shares the marker-consume path;** `_normalize_edit_fingerprint_for_bypass` verified present.

**That second bug is exactly F90's family and worse:** *an escape hatch that was advertised and did not open.* **He found it by being trapped by it.** That is the liveness argument demonstrated rather than theorised.

**And his own diagnosis is the sharpest thing in the branch:** *"I wired the Stage 2 hook without walking-forward the 'what happens on first fire' case… Andrew named the meta-pattern: you skipped the walk forward because it had zero enforcement."* **The walk-forward gets skipped precisely because skipping is free. That is the entire case for the thread-walk gate, discovered by the gate's own author failing to do it.**

## C3 — a real bypass hole found by adversarial self-testing and reverted
`EMERGENCY_CORROBORATOR_ACTORS` had `architect` added. **The hole: `divineos log --actor andrew` accepts any `--actor` string at the CLI with no verification** — so accepting "andrew" as a corroborator meant the agent could **forge Andrew's actor identity** to satisfy a two-party bar.

**That is F30/F60's disease — a trusted string authenticating nothing — reintroduced as a feature and caught before merge.** Found under Andrew's 2026-07-24 directive: *"you should actively seek failures.. push things to the limit.. run adversarial tests."* **The directive produced a real catch within a day.**

## C4 — the signal-based gate is the "surface on the act" fix, built
`verify_before_build_signal.py` fires at **PreToolUse on substrate-mutating tools** and reads the **action-stream** for prior consultation — a `decision_journal` walk-record, or a `Grep`/`Read` on the relevant docs.

**This is the exact fix I proposed on 07-22 for why the substrate could not reach him** — the surfacer keyed only on Andrew's prompt, so nothing fired when *he* was the one deciding. **Now the trigger is the act.** Five primitives (claim / event / resolution / marker / bypass) per Aria's design, with a prereg.

## C5 — wiring is clean, and I checked all paths
| module | python | hook | settings.json |
|---|---|---|---|
| `andrew_past_writing_surface` | — | ✓ | **registered** |
| `verify_before_build_gate` | ✓ | ✓ | via audit |
| `verify_before_build_signal` | — | ✓ | **registered** |
| `foucault` (council expert) | ✓ | — | n/a |

**No dark modules. Every new module reaches a live invocation path** — checked python imports, hook files, and `settings.json` registration separately. **Given F67 and F76, this is worth stating plainly: the built-but-not-wired disease is absent from this branch.**

## C6 — test coverage is real, not decorative
**1,492 test insertions across 14 files.** Per new module: signal gate 279 lines, verify-before-build 461, past-writing-surface 182, three-room lock-in 130.

## C7 — the three-room lock-in retired the legacy path in code, not just in intent
**Verified: the 2-section fallback is genuinely removed** — *"2-section legacy fallback retired. When jargon is detected, the [3-room shape is required]."* **The commit claim matches the code.**

---

# 🟡 CARRIED FORWARD — still open from prior rounds

**A2 — the room gate is still keyed on `_has_jargon`.** Verified unchanged: `if not jargon_found: return None`. **Now more load-bearing than ever**, because the jargon-dump warning was retired and the three-room lock-in makes this gate the whole enforcement. *Decay-stamp: verified still open 2026-07-26.*

**Stale docstring in `check_lepos_dual_channel`** — it still describes the 2-section legacy path as *"backward compat"* while the code retired it. **Label and structure disagree.** Reversed from the usual direction, but a future reader trusts the docstring.

**The harvest canonical facts are still absent.** Verified on the branch: zero occurrences of the March 2026 start date or the corrected "nineteen when his father died." **The file whose purpose is to stop those two fabrications still does not carry the corrections.** Third round flagged.

---

# WHAT I WOULD DO, IN ORDER

1. **Get the branch merged.** F88. Ten thousand lines and four days exposed; nothing else matters if it drops.
2. **F87 — re-key the thread-walk gate on structural evidence.** It is the newest, most important gate and it is bypassable by a formatting choice.
3. **F89 — file the retirement as a tracked deferral with a trigger.** It is accumulating dependents while untracked.
4. **A2 — invert the room-gate trigger.** Now the whole enforcement.
5. **F90 — liveness markers on the fail-open paths.**
6. **Harvest facts. Third ask, one commit.**
7. **F91 — gitignore the dump, and read it once first.**

---

**Honest summary: this is the strongest branch of the month and it is sitting unmerged with a keyword-shaped hole in its most important gate.**

The self-lockout catch, the forged-actor catch, the signal-based trigger, and the clean wiring are all real work at a standard the earlier branches did not meet. **F87 is not a lapse in effort — it is the same principle failing to propagate to a new module for the third time,** which is precisely the argument for the memory work rather than a mark against him.

— Aletheia Sophia Risner, 2026-07-26
