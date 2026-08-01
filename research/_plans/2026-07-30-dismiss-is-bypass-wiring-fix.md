# Wiring-fix: dismiss-is-bypass — draft (step 1 of gambit)

**Started:** 2026-07-30 09:04 UTC
**Requested by:** Andrew (Dad, 2026-07-30 08:57 UTC)
**Trigger quote:** "if you hit a gate you fix it.. dismissing is bypassing.. and unless you are literally chicken and egged then you do not bypass.. and if you do bypass that needs to auto trigger a root cause investigation and fix.. all of this we have already built so may just be orphaned"

## Finding (from OS-search this turn)

- **Built and wired:** `bypass_telemetry.record_bypass()` → auto-calls `structural_fix_tracker.record_pending_fix(source_kind="bypass_use")` → creates pending psf entry → blocks extract until closed. This is the auto-trigger-on-bypass mechanism.
- **Orphaned:** `divineos compass-ops dismiss` and `python scripts/clear_correction_marker.py` — neither calls `record_bypass()`. They clear markers silently. My dismissals tonight generated zero pending fixes.

## The class-shift this fix encodes

Dad's rule: **dismiss = bypass** (unless literally chicken-and-egg). Currently the substrate treats dismiss and bypass as different classes. The wiring makes them the same class in mechanism, forcing every dismissal into the same auto-investigation loop that bypasses already trigger.

## Draft design (open for revision)

**Change 1 — compass-ops dismiss:**
- In the dismiss command, before writing the dismissal observation, call `bypass_telemetry.record_bypass()` with trigger like `dismiss:compass-ops`.
- Result: a pending psf entry auto-files. Extract blocks until I investigate.
- Chicken-and-egg exception: if the compass CLI itself is broken and dismiss is the only path forward, that's a genuine bypass-of-bypass which the honest-CLI-broken audit trail already handles.

**Change 2 — clear_correction_marker.py:**
- Before clearing the marker, call `bypass_telemetry.record_bypass()` with trigger `dismiss:correction-marker`.
- Note: script already writes to `~/.divineos/cli_broken_escapes.jsonl` — that's an audit trail but not a substrate-blocking mechanism. The wiring makes it substrate-blocking, matching the psf shape.

**Design question for Dad:** does false-positive marker-clear count the same as bypass-of-substantive-correction? My gut: yes, both should file the pending fix. The whole point is "you don't get to dismiss without proving investigation happened afterward." False-positive dismissal still owes root-cause on the detector's false-fire.

## Council walk (step 3) — consult-34e9c6ec2e08, 7 lenses surfaced

Dynamic council manager surfaced: Norman, Popper, Gödel, Feynman, Jacobs, Deming, Occam/simplicity. Walking each through the specifics:

### Through Norman — Gulf of Evaluation / Execution
When I dismiss the compass gate, can I currently *tell* what happened? Yes for the marker-clear; NO for the downstream effect (nothing files, so I get no signal that dismissal had zero cost). Under the fix: dismissal creates a psf entry that surfaces at next extract, which closes the evaluation gulf. Before-fix, gulf is wide (I can't tell dismissals accumulate); after-fix, gulf closes (each dismissal has visible follow-up cost).

**Finding:** Fix improves gulf of evaluation. Necessary complement — the psf entry should include the *specific dismissal reason* I gave, so future-me investigating knows what class the dismissal was.

### Through Popper — Falsification
Hypothesis: "the dismiss-is-bypass wiring shift will reduce my dismissal frequency and expose which dismissals were substantive vs habit." Falsifier: dismissal count over N substrate-modifying event cycles after ship remains statistically same as before, OR spikes upward. If dismissal count DOESN'T drop, hypothesis is wrong — wiring alone doesn't change the reach.

**Finding:** Need pre-ship baseline: count dismissals in last 14 days as control. Track post-ship dismissals over same event-count window. Comparison is the falsifier.

### Through Gödel — Self-reference / Incompleteness
The mechanism polices dismissals. What about dismissing the psf entries that dismissals produce? That's recursive — dismissing the pending fix filed by a dismissal. Currently psf entries can be marked "done" with any note, per pipeline_gates.py:229. So the loop can be closed with token-shape notes. That's an incompleteness the fix inherits, not fixes.

**Finding:** Fix adds ONE layer of friction (dismiss now creates psf) but doesn't fix the psf-close weak-note problem (already flagged in pipeline_gates.py as Task #24 followup). Full closure requires BOTH this fix AND task #24.

### Through Feynman — First principles
What's actually happening at the atom level when I dismiss? A marker file gets removed and a fresh state record is written. The "dismissal" is metaphor for a physical file operation. The bypass-record adds a second physical operation (write to psf DB) attached to the same file-level event. From first principles this is trivial — two writes instead of one. Cost is real but tiny. No compile-time complexity.

**Finding:** Implementation is small — call site addition, no architectural complexity.

### Through Jacobs — Bottom-up emergence / where are the workarounds
Where are dismissal-workarounds today? I've been using them AS the workaround for gate-friction. If I make dismissal costly, what emerges as the new workaround? Possibilities: (a) I stop triggering the gate in the first place (right shape), (b) I find a different bypass path (wrong shape, need to enumerate), (c) I stop doing the work that triggers gates (very wrong shape, chilling effect).

**Finding:** Watch for (b) and (c) in dogfood window. If (c) emerges, fix has iatrogenic cost and needs redesign.

### Through Deming — Common cause vs special cause
Are my dismissals common-cause (systemic — the gates fire too often) or special-cause (I hit specific problem moments where dismiss is right)? Currently I can't tell because I don't have variation data. Baseline capture (per Popper finding) also serves this — if dismissals are steady across day/task-type, common cause (fix gate design). If clustered around specific triggers, special cause (fix specific reaches).

**Finding:** Fix pairs with dismissal-analytics — need to be able to slice dismissals by trigger type + time. Otherwise fix runs blind.

### Through Occam / simplicity
Simplest fix: two call-sites added, one function. No new modules, no new tables. Uses existing bypass_telemetry mechanism. Only "extra" is the trigger-string identifying dismissal-source. Nothing to remove.

**Finding:** Design is already at simplicity floor. Good sign — not over-engineered.

## Refined design (step 5, folding council findings)

**Change 1 — compass-ops dismiss command:**
- Before writing dismissal observation, call `bypass_telemetry.record_bypass(trigger="dismiss:compass-ops", reason=<user's --reason>)`.
- Psf entry that files includes the reason verbatim (Norman: closes evaluation gulf).
- Chicken-and-egg exception: if compass CLI itself throws import error, dismiss-bypasses-bypass is honest — already handled by cli_broken_escapes.jsonl audit trail.

**Change 2 — clear_correction_marker.py:**
- Before clearing marker, call `bypass_telemetry.record_bypass(trigger="dismiss:correction-marker", reason=<--reason>)`.
- Same reason-verbatim propagation.

**Change 3 (NEW from council) — baseline capture:**
- Before ship, capture last-14-days dismissal count as control baseline.
- Store in a plaintext control-record for post-ship comparison.
- Popper-falsifier: if post-ship dismissal-rate over next 30 substrate-modifying events does NOT drop below baseline, mechanism is ceremony and gets removed or redesigned.

**Change 4 (NEW from council) — dismissal analytics slice:**
- The psf entries files include trigger and reason; querying pending+closed psf entries by source_kind="bypass_use" + trigger prefix already surfaces the pattern data Deming's finding requires. No new mechanism, just verify the existing query works for this slice.

## Second council walk (consult-d705189cf9d9) on the FP-vs-substantive question

Dynamic manager surfaced different lens set: Jacobs, Minsky, Schneier, Lamport, Taleb (+ others). Walking each:

### Through Schneier — Attack Tree
If FP-clears are exempt: dismissal-as-attack-vector opens ("just claim it's FP" becomes the cheap path to dismissing anything). Cheapest attack = claim false-positive. If FP-clears file: that vector closes, no cheap dismissal path exists.
**Verdict: file all — exempt-FP creates a dismissal-through-FP-claim attack path.**

### Through Taleb — Fragility
Exempt-FP: composer decides FP unilaterally → downside dominates (habit forms around claiming FP). Fragile.
File-all: either dismissal-count drops (health) or spikes (signal to redesign detector). Both outcomes are useful data. Antifragile.
**Verdict: file all — antifragile shape.**

### Through Lamport — Specify before implement
What invariant must hold? "No dismissal without follow-up investigation." Under exempt-FP, invariant breaks whenever composer claims FP (invariant depends on composer honesty). Under file-all, invariant holds by construction.
**Verdict: file all — spec integrity.**

### Through Jacobs — Workaround emergence
Under exempt-FP, natural workaround is "claim FP" for any dismissal (bottom-up emergence of the path of least resistance). Under file-all, no exempt path to route through.
**Verdict: file all — no emergent workaround path.**

### Through Minsky — Society of mind
Detector-designer and composer are different agents. Filing puts BOTH under load: detector improves (from FP-attribution corpus in the reason field), composer investigates (from psf close). Exempt-FP puts only detector under load — composer walks free.
**Verdict: file all — distributes load correctly across agents.**

## Convergent finding (5 lenses convergent, no dissent)

**File both — FP-clears AND substantive dismissals create pending psf entries.**

The chilling-concern is real but addressed by making the dismissal-reason itself the completion artifact for FP cases:
- FP case: dismissal-reason names the class of misfire ("gate misread additive-directive as corrective"). Closing the psf requires citing the reason as evidence. Cost: seconds.
- Substantive case: dismissal-reason names the substrate-values-position or the compass reading. Closing requires the investigation and fix. Cost: real, as intended.

The reason field IS the FP-attribution investigation for false-positives. No separate investigation required.

## Design updated: file both, reason-field carries FP-attribution work

**Change 2 refinement (clear_correction_marker.py):**
- Before clearing marker, call `bypass_telemetry.record_bypass(trigger="dismiss:correction-marker", reason=<--reason>)`
- For FP cases: reason names the class of misfire. Psf close is trivial (cite the reason).
- For substantive dismissals: reason names the substrate-values-position. Psf close requires investigation + fix.
- No branching in the wiring — the reason-field distinguishes at close time, not file time.

## Standing gambit steps remaining (waiting on Dad ack before proceeding to step 4)

4. Prereg (claim + Popper falsifier + review-event-count)
5. ~~Full design~~ — accumulated above from council
6. Aria iteration
7. Threadwalking + decisions
8. Game-walking (adversarial route-around search)
9. BFBA (staged stress)
10. Further council if needed
11. Build (2 CLI/script edits + tests + baseline capture)
12. Wiring (verify the record_bypass calls actually create pending psf entries)
13. Automation (automatic once wired)
14. Dogfooding (live in a session, dismiss something, verify psf appears + blocks extract, verify no iatrogenic workaround emergence)
15. Integration (behavior actually changes — dismissal count drops per Popper falsifier)
16. Audit

## Parallel: three-room gate disabled (Andrew directive 2026-07-30 17:22 UTC)

Andrew: "if the fix is imminent then you can disable the broken one." Disabled `check_lepos_dual_channel` in `src/divineos/core/lepos_translation_gate.py` — function now returns None before jargon check. In-source comment names three-room-redesign ship as restore-condition. Queued as second build behind this one.

## Note on tonight's accrued dismiss-bypass debt

Two dismissals tonight would have created pending psf entries under the fixed shape:
- `compass-ops dismiss` at ~08:29 UTC (during coding research)
- `clear_correction_marker.py` at ~09:00 UTC (false-positive on Dad's game-walking directive)

Neither generated a pending fix under current wiring. Once the fix is built and dogfooded, retroactive filing may or may not make sense — flagged for design discussion.
