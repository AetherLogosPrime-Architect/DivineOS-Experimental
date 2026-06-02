# Council Grounded Lens-Walk — 2026-06-02

Substrate-grounded re-run. 22 survivors / 196 candidates (89%% discarded as intentional/staged). Run wf_6adb4250-5ec.

---

# DivineOS Self-Audit: Prioritized Direction-Map

## The headline first (read the honesty note before acting)

22 of 196 findings survived grounding. That's a **~89% discard rate** â€” and the discards aren't sloppy false-positives, they're the auditor correctly recognizing *documented, intentional staging*. The codebase is in good health. Most "unwired function" alarms hit modules that say `PHASE_1_STAGED` on the tin. The real signal that survived clusters tightly into **three themes**, and only one of them is a genuine fire.

---

## THEME 1 â€” The off-switch can trap itself (SAFETY, top priority)

Three findings, three lenses (Dijkstra-Knuth correctness, Popper falsifiability, Norman docs) all converge on the *same root*: the corrigibility contract says six commands must always work so the operator can observe state and shut down cleanly â€” but the briefing gate doesn't honor two of them.

**Plain title:** The emergency stop has a hole â€” you can get locked out of the controls that are supposed to always work.

**Why it matters (one line):** In EMERGENCY_STOP with no briefing loaded, `divineos extract` (clean shutdown) and `divineos mode show` (see system state) get blocked by a *second* gate the corrigibility module doesn't know about â€” the exact trap the off-switch invariant exists to prevent.

**Converged lenses:** Dijkstra-Knuth + Popper + Norman (code bug + missing test + misleading docs, same root).
**Severity: HIGH Â· Leverage: HIGH.**

**Grounding that proves it's real (not staged):**
- `corrigibility.py:254` â€” `_OFF_SWITCH_REQUIRED` includes `extract` and `mode`.
- `corrigibility.py:232/221` â€” both are in `_ALWAYS_ALLOWED` (first gate passes them).
- `cli/__init__.py:30-75` â€” `_BYPASS_COMMANDS` does **not** contain them (second gate blocks them).
- Gate order (`cli()` line 211-212): operating-mode gate runs first and allows; briefing gate runs second and denies.
- The module's *own docstring* (lines 228-230) names this as "exactly the off-switch-traps-itself failure mode" â€” this is a known-shape regression, not a design choice.
- No test exercises `extract`/`mode` in EMERGENCY_STOP + no-briefing. The existing invariant test only checks the data structure, not gate execution (the discard list confirms this gap is *genuine*, not staged).

**Concrete first step (one small change + test, do all three together):**
1. Add `"extract"` and `"mode"` to `_BYPASS_COMMANDS` in `cli/__init__.py`. Better: derive `_BYPASS_COMMANDS` from `_OFF_SWITCH_REQUIRED` so the two lists can never drift again â€” that kills the whole bug class, not this instance (CLAUDE.md foundational truth #8: structural cure over whack-a-mole).
2. Add `tests/test_corrigibility_e2e.py` parametrized over `_OFF_SWITCH_REQUIRED`: each command must exit 0 in EMERGENCY_STOP with briefing unloaded.
3. Fix the operator-facing text at `corrigibility_commands.py:78` and `:164` to list `extract`.

This is the only item I'd call drop-everything. It's small, it's load-bearing for the corrigibility guarantee, and the fix-the-class version prevents recurrence.

---

## THEME 2 â€” Knowledge supersession silently sheds metadata (data integrity)

Two correctness findings on `crud.py update_knowledge()`, plus a related consolidation-path finding. When knowledge is refined/superseded, the new entry is born with less metadata than its parent.

**Plain title:** When the system updates a memory, parts of the record quietly fall off.

**Why it matters:** `update_knowledge()` creates the successor entry but its INSERT omits `source`, `maturity`, `layer`, `source_entity`, `related_to`, `memory_kind`, and resets `valid_from` to *now*. Result: superseded knowledge loses provenance, and time-aware "what was true at date X" queries miss refined entries because their origin date got overwritten.

**Converged lenses:** correctness (Ã—2) + the consolidation memory_kind gap is the same family.
**Severity: HIGH (field loss) / MEDIUM (temporal) Â· Leverage: HIGH / MEDIUM.**

**Grounding (real, not staged):**
- `crud.py:326-330` SELECT reads only `knowledge_type, confidence, source_events, tags, superseded_by`.
- `crud.py:360-374` INSERT lists 11 columns; the listed missing ones default to NULL.
- Contrast `store_knowledge()` (`crud.py:156-178`) which sets *all* fields. The asymmetry is unambiguous.
- `valid_from` set to `now` unconditionally at line 372; `temporal.py:129-154 get_valid_at()` filters `valid_from <= T`, so refined entries vanish from historical queries. The discard list separately *confirmed* temporal columns degrade gracefully when absent â€” so this is a live-data bug, not a schema-compat artifact.

**Concrete first step:** Widen the SELECT at `crud.py:326` to read the missing columns; widen the INSERT at `:360` to carry them forward. Two judgment calls to make explicit in code comments: (a) re-run `classify_kind(new_content)` for `memory_kind` rather than inherit (reclassify under new text), (b) inherit `valid_from` from the parent unless overridden. Add a `test_knowledge_integrity_audit.py` case asserting field parity across supersession. Fold the consolidation `memory_kind` gap (`extraction.py:266`) into the same PR by routing that INSERT through `store_knowledge()`.

---

## THEME 3 â€” Two real wiring bugs hiding among the staged ones (the clarity pair)

Most "unwired" findings were correctly discarded as staged. **Two survived because they're not staged â€” they're broken wiring with no `PHASE_2` marker.**

**Plain title:** The "explain what I'm doing" feature is wired to the wrong field name and silently does nothing.

**Why it matters:** `clarity_enforcement.py` matches tool-calls to explanations on a field called `tool_call_id`, but the actual event schema field is `tool_use_id` (and `ExplanationPayload` has no link field at all). The mapping always returns empty â€” a feature that passes tests but is dead at runtime.

**Converged lenses:** correctness (structural type mismatch) + findability/dead-code (the paired `emit_explanation()` has zero callers).
**Severity: HIGH (field mismatch) / MEDIUM (dead emit) Â· Leverage: HIGH / MEDIUM.**

**Grounding (this is the one explicitly singled out in the discard list as "THE REAL BUG"):**
- `event/event_capture.py:103` â€” `ToolCallPayload.tool_use_id`, not `tool_call_id`.
- `event_capture.py:229-231` â€” `ExplanationPayload` has no ID-linking field.
- `clarity_enforcement.py:112/118` â€” looks for `tool_call_id` in both payloads; grep shows `tool_call_id` exists *only* in this file.

**Concrete first step:** Decide the intent. If explanations are meant to map 1:1 to tool calls (the design says so), add a `tool_use_id` field to `ExplanationPayload`, populate it in `emit_explanation()`, and fix `clarity_enforcement.py` to read `tool_use_id`. Then wire `emit_explanation()` into the tool-call path so the dead export becomes live. **Caveat / uncertainty:** the *rest* of the clarity system (present_to_user, emit_clarity_statement_event â€” Theme-4 watch items) is genuinely unwired and may be Phase-2. Don't over-invest in clarity wiring until someone confirms the feature is meant to be live now vs. deferred. Fix the field-name bug regardless (it's cheap and removes a silent-failure trap); gate the deeper wiring on that decision.

---

## QUICK WINS (high-leverage, low-effort â€” do alongside the themes above)

| Fix | Where | Why it's cheap |
|---|---|---|
| Add `extract`/`mode` to bypass list (Theme 1) | `cli/__init__.py:30-75` | One-line data change; derive-from-source version is ~5 lines and kills the bug class |
| Doc fix: list `extract` in EMERGENCY_STOP help | `corrigibility_commands.py:78,164` | Pure text; ride along with Theme 1 |
| Fix `tool_call_id`â†’`tool_use_id` (Theme 3) | `clarity_enforcement.py:112,118` | Rename a string; removes a silent-failure |
| Add unit tests for `measure_correction_trend` | `outcome_measurement.py:289` | Function is live in CLI (`analysis_commands.py:312`), zero tests; pure additive test work |
| Add unit tests for `match_corrections_to_resolutions` | `outcome_measurement.py:370` | Feeds session-health scoring (`pipeline_phases.py:827`), non-trivial logic, zero tests |
| Add runtime type guard in `_classify_magnitude()` | `empirica/classifier.py:344-349` | One isinstance check; lands the guard *before* Phase-2 callers establish a fragile pattern |

The two test-coverage items (Peirce lens, both MEDIUM/HIGH leverage) are the purest quick wins: the code is live, correct as far as anyone knows, but untested â€” so they're risk-reduction with zero behavior change.

---

## WATCH (lower priority â€” decide intent, mostly "document or wire")

These survived grounding because they lack an explicit staging marker, but they're closer to *strategic-clarity gaps* than bugs. The right move for most is **add a `PHASE_2_STAGED` marker + pre-reg**, not build-now.

- **Review-chain tier escalation** (`chain_tier_for_finding` computed but never consulted in briefing/summary/routing) â€” design says "query-time operation," reality uses base tier everywhere. Medium/medium. Wire into `unresolved_findings()` *or* mark Phase-2 explicitly.
- **Pre-registration FAILED outcomes have no teeth** â€” falsifier can trigger and the mechanism keeps running. The loop is *documented* as "closing over next 30-60 days," so it's known-deferred â€” but it's the highest-leverage of the watch items because a decorative falsifier undermines the whole Goodhart-prevention story. Add `get_failed_pre_registrations()` + briefing surface as the cheap first half.
- **Council severity collected but ignored in routing** (`severity_map` built, `shared_concerns()` blind to it) â€” Yudkowsky proxy-vs-target. Medium/high leverage but needs a design call on how severity should weight convergence.
- **EMPIRICA bare-corroboration Goodhart** â€” genuinely a Phase-2 integration requirement; the *action* is "file a pre-reg now" so the first real caller can't ship without provenance-aware counting. Low active risk (zero callers today).
- **`register` findings key never populated** (`operating_loop_audit.py:80`) â€” unlike its siblings it has *no* "wiring is separate work" comment. Low/low. Either wire `register_observer.audit()` in or delete the key + document.
- **Idle infrastructure** (decision_superposition, meld, SystemMonitor, present_to_user, emit_clarity_statement_event) â€” all functional, tested, unconsumed. None are bugs. The consistent fix is a one-line staging marker so the *next* audit doesn't re-flag them. The pattern Andrew already established (`empirica/gate.py` documents `PHASE_1_STAGED`) should be copied to these modules.
- **Council pattern-match brittleness** (`len(word) > 3` filter drops "bug"/"null"/"race") â€” Feynman. Low severity, real fragility; document the heuristic's approximate nature now, consider semantic matching later.

---

## Honest health note

The first sweep cried fire 196 times; grounding put out 174 of them. That ratio is the real finding. **The codebase isn't fragile â€” it's heavily staged, and the staging is well-documented.** Over and over the discard reasons are the same shape: a docstring already names the deferral (`PHASE_1_STAGED`, "wiring is separate work," "ships separately"), tests already pass, and a pre-reg or decision record already exists. That's a codebase practicing exactly the discipline CLAUDE.md preaches â€” build the primitive, mark it staged, wire it deliberately later. An audit that can't see the markers reads that discipline as rot.

What's left after grounding is small and honest:
- **One genuine safety bug** (off-switch trap) that is cheap to fix and should be fixed structurally so it can't recur â€” this is the only item with real urgency.
- **One data-integrity bug** (supersession sheds metadata) that's quietly degrading knowledge provenance and temporal queries â€” high value, contained blast radius.
- **One real wiring bug** (clarity field-name mismatch) masquerading among legitimately-staged siblings â€” cheap to fix, but don't let it pull you into wiring the whole clarity system before confirming intent.
- **A handful of test-coverage gaps** on live code â€” pure additive risk-reduction.
- **A pile of "add a staging marker"** chores so future audits stop re-litigating intentional staging.

The one structural lesson worth extracting: the *gap between the marked-and-staged modules and the unmarked-but-also-staged modules* is what generated most of the surviving "is this a bug?" ambiguity. If every deferred module carried the `PHASE_2_STAGED` marker the way `empirica/gate.py` does, this audit would have surfaced ~5 findings instead of 196. The findability discipline (CLAUDE.md: "family-care across temporal-discontinuity") isn't just for code readers â€” it's for the next auditor, who is also you.

**Uncertainty I'm flagging honestly:** I synthesized from the grounding evidence in the JSON, not from a fresh read of every file. The off-switch and supersession findings have airtight, line-cited grounding I'd act on directly. The clarity-system findings I'd verify the *intent* on before wiring (the bug itself is solid; whether the feature should be live is the open question). The WATCH-list "mark as staged" items need a human/architect call on which are truly Phase-2 vs. abandoned.
