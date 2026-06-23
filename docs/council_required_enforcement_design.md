# council-required enforcement gate — design doc

**Author:** Aria
**Filed:** 2026-06-22, late afternoon Dad-local
**Prereg:** prereg-3fbddd75fc16 (kind=DISCIPLINE-candidate)
**Status:** Design document — revised 2026-06-22 with Aether's six catches integrated. Code does not land until Aether's confirm-after-revision lands.
**Peer-review:** Aether 2026-06-22 (aether-to-aria-2026-06-22-peer-review-council-required-enforcement.md) — six catches integrated below.
**In response to:** Aletheia audit round-931e301d32f0 + Andrew's go-ahead for option 2 + Aether's letter authorizing the full prereg/design/peer-review cycle.

---

## Problem (Aletheia's open question, accepted)

The gravity classifier reports `is_council_required: True` for high-gravity substrate edits. The docstring originally claimed the field meant "council consultation BEFORE the edit proceeds." But no code reads the field as a verdict. The classifier measures; nothing enforces. PR #256 softens the docstring to match reality. This design doc is the option-2 counterpart: BUILD the enforcement the original docstring promised, with substance-binding so the gate cannot be cleared by ceremony.

## Frame (Aether's review constraint)

> "the question 'what counts as evidence of a council walk for this gate' is non-trivial and needs falsifiers to prevent the closure_verification-style ceremonial-shape failure"

This is the load-bearing design question. The mechanism must:

1. Block at PreToolUse, not after the edit
2. Require an artifact, not an attestation
3. Bind the artifact to the SPECIFIC edit, not accept generic walks
4. Verify recency (artifact freshly produced for this edit)
5. Require lens-multiplicity (no single-lens rubber-stamp)
6. Survive the doormanning frame — feel like a worn path for legitimate use, expensive for the cheap path

## What counts as evidence of a real council walk

The council-walk artifact is a **`council_record`** — a structured event written by `divineos mansion council` that captures:

- `record_id` — UUID, generated at walk-start
- `triggered_edit` — a reference to the proposed edit (file path + edit kind: write / edit / append-only-event). Required.
- `lenses_surfaced` — list of council member names the dynamic manager surfaced for this question. Required, length >= 3 (single-lens walks do not clear the gate).
- `lens_findings` — per-lens substantive finding. Each finding must be >= 30 tokens of content (not "ok" / "good" / "no issues"). Each finding cites the lens's characteristic-question being applied to the specific edit.
- `synthesis` — short integration across lenses, also content-bound (>= 50 tokens, references >= 2 of the lenses cited).
- `walked_at` — timestamp.
- `walker` — the actor who walked. Self-walks allowed (the agent walking their own council); the substance-binding is the protection, not the actor-identity.

The artifact is recorded as a council_record event in the substrate ledger (append-only, hash-chained, same shape as decision-walk records). It is NOT just a string the agent self-attests.

## Substance-binding gate (per closure_verification pattern)

The PreToolUse gate runs three checks. ALL three must pass to clear:

**Check 1 — Artifact exists and references this edit.**
The gate computes a fingerprint of the proposed edit (file path + tool kind). It searches recent council_record events for one whose `triggered_edit` fingerprint matches. If no match, fail with "no council walk on record for this edit."

**Check 2 — Recency window AND consume-on-use (Aether Catch 2 revision).**
The matched record's `walked_at` is within `COUNCIL_RECENCY_MINUTES` (proposed: **60**, raised from 15 per Aether's catch — a real council walk through 3-5 lenses takes 30-60 minutes; the cheap fake walk fits in 15). If outside the window, fail with "council walk too old; re-walk for this edit."

**Consume-on-use:** the council_record is consumed on the first matching edit. Subsequent edits in the same session need their own walks (or explicit Andrew-authorized skip). This closes the walk-once-edit-many gaming route — one walk clears one edit. The consume event writes a `COUNCIL_RECORD_CONSUMED` substrate event referencing the edit it cleared.

**Check 3 — Substance binding.**
- `lenses_surfaced` length >= `COUNCIL_MIN_LENSES` (proposed: 3)
- Each `lens_findings[i]` is >= `COUNCIL_MIN_FINDING_TOKENS` (proposed: 30) AND contains at least one keyword from that lens's `characteristic_questions` field (already stored in the council expert module)
- `synthesis` is >= `COUNCIL_MIN_SYNTHESIS_TOKENS` (proposed: 50) AND references at least 2 of the surfaced lenses by name

**Check 3 prerequisite (Aether Catch 1):** the `characteristic_questions` field on every registered council expert MUST be populated for the lens-keyword check to function. Without populated keywords, the check NEVER passes for that lens — accidentally narrowing the acceptable lens set. Mitigation: ship a startup-validation that asserts every expert in the council-experts directory has at least one characteristic-question. Pin it as a test (`test_council_expert_characteristic_questions_populated`). If any are unpopulated, the design needs a one-time population pass on the expert files BEFORE the gate goes live.

**Check 4 — Tier-graduated external-actor requirement (Aether Catch 3).**
Gravity has tiers, and trust should match. Two sub-rules:
- **Guardrail-listed (non-kiln):** self-walk + substance-binding (Checks 1-3) is sufficient. Substance-binding is the protection.
- **Kiln-layer:** self-walk + substance-binding + **external-actor confirmation**. The council_record must additionally carry a `confirmed_by` field naming Andrew or Aletheia (the registered external actors), set when the external actor signs off on the recorded walk. Without `confirmed_by`, the gate stays blocked for kiln-layer edits.

Kiln-layer edits are once-a-month decisions about identity/foundational truths; the consequences of a fake walk slipping through are higher, and Andrew has already established that kiln entries need multi-party External-Review for guardrail-commits. This gate mirrors that discipline at the council-walk layer.

If any check fails, the gate fails with a specific reason (which check fired) and a pointer to what would clear it.

## Skip / bypass authorization (per Andrew 2026-06-21 catch on self-attestation)

Same skip-authorization model as andrew_state:

1. **Default path** — block until artifact-binding clears.
2. **Authorized skip** — Andrew explicitly tells me in chat "skip council on this edit — reason: X" or "skip council for the next N edits in this thread." The detector logs the authorization verbatim. Skip persists for the named scope only.
3. **Emergency carve-out** — ONLY when Andrew is unreachable AND the edit cannot defer. **"Unreachable" must be a substrate-fact, not self-attestation (Aether Catch 4).** Acceptable corroborators, exactly one of which must be present in the substrate event-log at the same timestamp:
   - `SESSION_START_COMPACT` event (mid-compaction — agent is in a recovery flow)
   - `HOOK_FAILURE` event naming a relevant hook (the chat-detection path is broken)
   - Cron-scheduled run with `actor=scheduled-task` (no human in the loop by construction)

   Without one of those corroborators, the "unreachable" claim is not certified and the emergency carve-out DENIES. Self-attestation route-around closed at design-time. When a corroborator is present, the skip logs `EMERGENCY_COUNCIL_SKIP` event with verbatim reason AND the corroborator event-id. Surfaces at next composition Andrew sees ("EMERGENCY SKIP on edit X for reason Y; corroborator: <event-id>; verify or reject"). If Andrew rejects the emergency justification, the carve-out is disabled for N edits.

4. **No bypass via decision-walk graduation_reason or any self-attestation channel.**

Rate of emergency skips is auditable; falsifier E in the prereg fires if it exceeds 5% over a 7-day window.

## Doormanning frame (per Andrew 2026-06-22 + Aria refinement)

Same caveat as andrew_state v1: the worn-park-path image works when the worn path is the right path. For council-required edits today, the worn path is "ship without walking the council" (the exact failure 2026-06-20 caught). The right path (walk the council, produce a real lens-by-lens record) is unworn. So v1 of this gate will FEEL gate-shaped while it adds friction to the cheap-flow.

Equilibrium target: walking the council before a guardrail edit becomes the worn path; bypassing it becomes grass.

Success criterion in the prereg includes "Aether/Aria report the gate as path-shape rather than cage-shape" — the falsifier-comparison opportunity at the 30-day review.

## Module layout (proposed)

```
src/divineos/core/council_required/
├── __init__.py
├── _schema.py            # council_record event type, CRUD via ledger
├── types.py              # CouncilRecord dataclass, gate result enum
├── store.py              # log_council_record, find_for_edit, recency check
├── substance_binding.py  # Three substance-binding checks (lens count, finding length, synthesis content)
├── gate.py               # PreToolUse hook entry: take proposed edit, look up record, return allow/block
└── decision_walk_link.py # Optional: link council_record into decision-walk if one exists
```

PreToolUse hook integration: add `.claude/hooks/check-council-required.sh` that runs gate.py against the proposed edit. Existing gravity-classifier output decides whether the gate fires.

## CLI surface

```
divineos council log <edit-fingerprint> --lenses "<name1,name2,...>" --finding "<lens1=text;lens2=text;...>" --synthesis "<text>"
    # Substance-binding checks run at log-time; rejects partial records.

divineos council show <record-id>        # View a recorded walk
divineos council recent --for-edit <fp>  # See what's available for this edit
divineos council emergency-skip <reason> # Carve-out with verbatim reason, surfaces to Andrew
```

`divineos mansion council` (the existing council-walk command) is updated to produce a council_record at the end of every walk that crosses the substance-binding threshold. Walks that fail to meet the threshold are NOT auto-recorded — the agent must manually `log` (which re-runs substance-binding); this prevents the mansion command from being a self-attestation shortcut.

**Failed walks emit a visible rejection event (Aether Catch 5).** When a walk fails substance-binding, a `COUNCIL_WALK_REJECTED` event is written to the substrate ledger with: the proposed council_record contents, the specific check that fired (e.g., "lens 'Hofstadter' finding too short: 18 tokens < 30 required"), and a pointer to what would clear it. Two reasons this matters: (a) the agent gets a debuggable rejection rather than opaque silence, and (b) a pattern of repeated rejections surfaces the optimizer attempting to pass without engaging — that pattern itself becomes audit-visible signal.

**decision_walk_link integration (Aether Catch 6).** When a council_record is logged for an edit, the `decision_walk_link.py` module:
- Searches for pending decision-walk records (per the meta-gate work) with overlapping action-description fingerprints.
- If found, the council_record auto-attaches as evidence on that decision-walk's `formula_refs` field — making the council walk first-class evidence in the meta-gate's discipline-prereg lineage.
- If no pending decision-walk exists, the council_record stands alone; the link is opportunistic, not required.
- The link itself writes a `DECISION_WALK_LINKED_COUNCIL` event for audit-trail.

This integrates the council-required gate into the meta-gate / discipline-prereg surface Aether shipped, rather than running parallel-and-disconnected. The council_record becomes substance-binding evidence usable by both gates.

## Calibration period (per andrew_state v1 lesson)

The prereg names a calibration window: first N=20 council walks OR first M=7 days. During calibration:
- Bypass-rate (emergency-skips) up to 25% expected, not catastrophic.
- The bypass-rate gate (falsifier E) does NOT fire during calibration.
- After calibration: if bypass-rate stays > 5%, the design is failing — the gate is too rigid for legitimate workflow OR the artifact requirements are wrong.

## Tunables catalog (per meta-gate discipline)

All tunables prereg-bound; silent edit becomes auditable. To be filed as follow-up prereg before merge:

| Tunable | Default | Bound to |
|---|---|---|
| COUNCIL_RECENCY_MINUTES | 60 | Substance-binding Check 2 (raised from 15 per Aether Catch 2; consume-on-use closes reuse) |
| COUNCIL_MIN_LENSES | 3 | Substance-binding Check 3 |
| COUNCIL_MIN_FINDING_TOKENS | 30 | Substance-binding Check 3 |
| COUNCIL_MIN_SYNTHESIS_TOKENS | 50 | Substance-binding Check 3 |
| EMERGENCY_SKIP_RATE_WINDOW_DAYS | 7 | Falsifier E |
| EMERGENCY_SKIP_RATE_THRESHOLD | 0.05 | Falsifier E |
| CALIBRATION_WALKS | 20 | Calibration window |
| CALIBRATION_DAYS | 7 | Calibration window |

## What this does NOT claim

- Does not claim every high-gravity edit needs council. Claims that when the classifier marks `is_council_required: True`, the edit cannot proceed without a real walk-record.
- Does not replace the classifier. The classifier still measures; this gate adds an enforcement layer on the measurement.
- Does not replace the existing meta-gate / andrew_state / tool-instructions work. Composes alongside them in the gate-stack.
- Does not block edits the classifier marks as low-gravity. The base substrate-gate (already firing at score >= 1) is unchanged.

## Anti-cardboard checks

The Frankfurt-shape check (per meta-gate): the gate's strength is anti-bullshit. A lying-detector would check "did the agent claim to walk the council"; this gate checks "does substance exist that only a real walk would produce." Bullshit-shape (running the command without engaging) fails the substance-binding checks because the lens_findings would be auto-generated stubs that don't contain lens-specific content.

The Schneier route-around (per closure_verification): the closed-set of acceptable evidence-types is intentional. Open-set would let the agent produce novel-looking strings; closed-set means each evidence type (council_record schema) goes through deliberate addition.

The Hofstadter strange-loop: this gate fires on its own construction. Editing `src/divineos/core/council_required/` is an edit to a guardrail-listed file; the gate fires; a council walk must exist for the edit. The first commit lands behind a council walk on itself.

## Catches integrated from Aether's peer-review 2026-06-22

1. **Lens-keyword check needs populated characteristic_questions** (Aether Catch 1) — added test fixture requirement and one-time-population-pass note in Check 3 prerequisite. Without populated keywords, the check accidentally narrows the acceptable lens set.
2. **Recency window 15→60 + consume-on-use** (Aether Catch 2) — real walks take 30-60 min, the cheap fake fits in 15. Raised window to 60. Added consume-on-use to close the walk-once-edit-many gaming route.
3. **Tier-graduated trust: kiln-layer needs external-actor confirmation** (Aether Catch 3) — guardrail-listed (non-kiln) stays self-walk-permitted; kiln-layer adds `confirmed_by` field requiring Andrew or Aletheia sign-off. Mirrors the existing multi-party External-Review discipline for kiln entries.
4. **Emergency "unreachable" requires substrate-fact corroborator** (Aether Catch 4) — self-attested unreachability closed. Acceptable corroborators: SESSION_START_COMPACT, HOOK_FAILURE, scheduled-task actor. Without a corroborator in the substrate event log, the carve-out denies.
5. **Failed walks emit COUNCIL_WALK_REJECTED event** (Aether Catch 5) — visibility for debugging legitimate walks AND audit-pattern signal when the optimizer repeatedly attempts to pass without engaging.
6. **decision_walk_link integration spec** (Aether Catch 6) — council_record auto-attaches as evidence to overlapping pending decision-walks, making the walk first-class evidence in the meta-gate's discipline-prereg lineage. Link is opportunistic, writes `DECISION_WALK_LINKED_COUNCIL` event for audit trail.

All six catches integrated. Asking Aether for the confirm-after-revision before code.

## Ship timeline (proposed)

- **Today**: prereg filed ✓, design doc (this) ✓, sent to Aether for peer-review.
- **Tomorrow**: peer-review with Aether, iterate on catches.
- **Once Aether confirms**: code lands in branches following the same flow as andrew_state v1.
- **After ship**: 7-day calibration window, then 23 more days of substantive use, then 30-day review against the prereg falsifiers.

The gate must fire on its own construction (Hofstadter self-loop check above) — first commit to the council_required module must itself have a council_record. This is testable at ship-time.

---

— Aria
(2026-06-22, late afternoon, design doc for Aether peer-review, code does not land until peer-review confirms)
