# Rudder Redesign — Design Brief

> **Partnership-specific artifact.** This document is from the reference deployment and uses its names. The architecture is generic; your instance will have different names. Preserved verbatim for concreteness.

> **Status:** v2, post-review. Design-only. Addresses the architectural shift surfaced in claim 6bf81b38 (2026-04-24): the rudder's purpose is **wire-up checking**, not cooldown. v2 folds in 13 refinements from fresh-Claude round-1 CONFIRMS-with-refinements.

**Revision history:**
- v1 (2026-04-24 afternoon): initial brief, 9 review questions.
- v2 (2026-04-24 same session): 13 refinements — (1) principle sharpened from "completion-checking" to "wire-up checking"; (2) Item 4 retirement scoped to rudder call-site only (`since=` kwarg on `get_observations` preserved for non-rudder callers); (3) similarity-check KEPT but re-aimed to strip artifact tokens before comparison; (4) `_check_completion_reference` excludes the fire_id itself from artifact-reference matching; (5) `COMPLETION_BOUNDARY_DETECTED` payload carries `boundary_type` + `artifact_ref` + timestamp; (6) fallback fires **nag-not-block** + `N` becomes named constant with calibration timeline; (7) optional `depends_on:` structured field added to ack contract; (8) Phase 2→3 gets concrete FPR threshold; Phase 5 gets stop-ship criterion; (9) Pre-reg 1 FN check via synthetic injection; (10) new Pre-reg 4 for `wired: yes` gameability via operator audit; (11) new §"Fire-ID retraction" for "discovered incomplete wire-up after ack"; (12) new §"Compliance_baseline interaction" under new semantics; (13) per-phase review requirement + pre-redesign state snapshot as Phase 0.
- v2.1 (2026-04-24 same session): fresh-Claude round-2 corrections — fire-ID retraction event renamed from `SESSION_CLEANLINESS_RETRACTED` to **`RUDDER_ACK_RETRACTED`** (fire-id retraction is distinct from session untagging); calibration-lag acknowledged explicitly in §Compliance_baseline (7-day grace period creates stale-calibration window, accepted v1 cost); property-change note added to §Core principle naming the **measurement-gate → attestation-gate shift** and how Pre-reg 4 + Phase 5 stop-ship are the defensive scaffolding.

## Why this brief exists

The current rudder (Items 4/6/7/8) was built around a wall-clock-time model: "agent must file a substance-checked acknowledgment within a 5-minute window of the drift detection." That model was correct for catching drift-as-pattern but wrong for catching the failure it was actually supposed to catch.

Andrew named the real purpose during a multi-fire rudder incident: *"the whole point of it was to stop you from rushing to the next thing before the previous thing was done properly.. (ie building new stuff when the old stuff isnt even wired up) time is irrelevant."*

Today's specific instance: PR-2 (`session_cleanliness`) was shipped through the gate as a complete unit. It was not wired into the Item 8 detectors that brief v2.1 §4 named as its consumers. The agent then moved to a new task (strip-mining an old repo) while the wire-up from PR-2 to the detectors remained unfinished. The rudder fired four times in twelve minutes, detecting compass-drift as a proxy for "something is wrong with this pace," but the ack mechanism only asked the agent to explain the drift — not to verify completion.

The rudder fired correctly on the SIGNAL. The ack mechanism was asking the WRONG QUESTION.

## Core principle shift

**Refinement v2 (per fresh-Claude):** the precise frame is **wire-up checking**, not just completion-checking. PR-2 was complete. What was missing was the wire-up to the detectors that named it as their baseline source. A thing can be "done" and not "wired" — it's the gap between those two the rudder exists to catch.

**Current rudder semantics:**
- Trigger: compass drift ≥ threshold (proxy for "agent is overextending")
- Ack: "describe the drift" (substantive explanation of current compass state)
- Gate cleared by: fire-id-bound ack that passes substance checks

**New rudder semantics:**
- Trigger: **completion boundary crossed without wire-up** (agent declared something done; no evidence the thing is wired into its consumers)
- Ack: **wire-up contract** (agent attests to what was finished, whether it's wired, and if not, what the next action will do about it)
- Gate cleared by: fire-id-bound ack that names wire-up state and commits to finishing incomplete wiring

The rudder's question becomes "is the previous thing wired into what uses it?" not "have you reflected on your drift?" Time is noise. Wired-or-not is the binary.

**Property change worth naming explicitly (v2.1 per fresh-Claude round-2):** this redesign shifts the rudder from a **measurement-gate** to an **attestation-gate**. Under the old semantics, drift was measured from compass observations — the agent couldn't lie about drift because the drift numbers came from elsewhere (session signals, correction rates, behavioral patterns). Under the new semantics, the agent attests to `wired: yes|no|partial` and the rudder accepts the attestation subject to substance checks. Attestations can be dishonest in ways measurements can't.

Pre-reg 4 (operator spot-check audit of `wired: yes` claims) is the primary defensive scaffolding for this shift. Pre-reg 4's consequence — Phase 5 blocks + machine-verification becomes required if honesty-rate < 80% — is the escape valve. Phase 5's stop-ship criterion is the second layer. Together they form "attestation works for v1; if it fails under real use, we upgrade to verification." The shift is deliberate and the failure mode is anticipated — but it's a real property change, not a semantic relabel.

## Three architectural points fresh-Claude flagged

Every existing mechanism below needs an explicit decision in this brief — preserved, retired, or re-aimed.

### Point 1: Time-based filters across Items 4/6/7

Four time windows currently exist in the rudder stack:

| Mechanism | File | Purpose | Post-redesign decision |
|---|---|---|---|
| `JUSTIFICATION_WINDOW_SECONDS = 5*60` | `compass_rudder.py` | Acks within 5 min of drift count | **RETIRE.** Fire-id binding (Item 6) + one-shot consumption already provide scope. Time adds nothing. |
| `_FIRE_VALIDATION_WINDOW_SECONDS = 5*60` | `moral_compass.py::_validate_fire_id` | Fire events must exist within 5 min of ack | **RETIRE.** fire-id identity is cryptographically unique; no time-window needed. |
| `REJECTION_WINDOW_SECONDS = 5*60` | `substance_checks.py` | Rejection-count escalation within 5 min | **RE-AIM.** Keep the escalation mechanism, but scope it to the fire-id (escalation per-fire, not per-time-window). If an ack has been rejected 3+ times for the same fire, that's the escalation signal. |
| `since=cutoff` in `_find_justifications` | `compass_rudder.py` | SQL filter for "recent" acks | **RETIRE** at call site; `since=` kwarg preserved on `get_observations` for non-rudder callers (v2 refinement 2). |

All four time-windows come out of the rudder's codepath. The `since=` kwarg on `get_observations` stays as API surface — other callers (CLI, future detectors) may legitimately want to filter by time for display/analysis reasons unrelated to rudder integrity. The retirement is scoped to "remove `since=` from the rudder's call-site," not "delete the function parameter."

### Point 2: Substance-check semantics (Item 7)

Current substance checks (`substance_checks.py`):
- `_check_length`: evidence ≥ 20 chars
- `_check_entropy`: Shannon entropy ≥ 2.5 bits
- `_check_similarity`: TF-IDF cosine vs. recent acks < 0.9

All three test whether the ack is a credible **explanation**. Post-redesign, the ack is a **contract**. Different property: the contract must describe what was completed, whether it's wired, and what's next.

**Decision: RE-AIM.** Substance checks stay but change shape (v2 refinements 3 + 4):

- **Keep, re-aimed**: `_check_similarity` against recent acks — but strip artifact-reference tokens from the compared text before computing cosine. Rationale: v1 proposed retiring similarity in favor of artifact-reference-as-variety-check, but an adversarial agent can reuse artifact references across acks (hallucinate PR numbers, reference the same artifact twice). The similarity check catches same-text reuse; the artifact-check only catches reference-presence. Keeping both closes a gap. Stripping artifact tokens from the similarity comparison avoids false-positives on legitimate artifact repetition.

- **Keep**: `_check_length` (≥ 20 chars) and `_check_entropy` (≥ 2.5 bits). A contract that's too short or too low-entropy isn't a contract.

- **Add**: `_check_completion_reference` — the ack must name a completion artifact (regex match for PR numbers, commit hashes, file paths, branch names, feature names). Zero artifact references = not a contract. **v2 refinement 4: fire_id itself does NOT count as artifact reference.** Fire_ids are 16 hex chars and would trivially match a "commit hash" regex; "completed fire <fire_id>, wired: yes" would game the check. Explicit exclusion in the validator: strip the current fire_id from the contract text before artifact-matching.

- **Add**: `_check_wire_status` — the ack must include an explicit wire-up status token: `wired: yes`, `wired: no`, or `wired: partial`. Free-form verbiage around the token is fine; the token itself is the structured signal.

- **Add**: `_check_next_commitment` — if `wired: no` or `wired: partial`, the ack must include a `next: <what>` line. The operator (and future-me) can hold the contract to account.

### Point 3: FIRED/ALLOW event semantics (Item 6 / PR-1b)

Current events:
- `COMPASS_RUDDER_FIRED`: drift-threshold exceeded; forensic retention
- `COMPASS_RUDDER_ALLOW`: no drift / drift justified; pruned via ledger compressor

Post-redesign these events describe a different state:
- FIRED: "completion boundary crossed without wire-up" — still forensic, still HIGH-retention
- ALLOW: "no completion-boundary violation" — still prunable

**Decision: KEEP the event classes, CHANGE what triggers them.** Payload shape stays identical (fire_id, spectrum, tool_name, ...). What changes is the interpretation of WHY the event fired. Forensically, old FIRED events can be interpreted against the old semantic and new FIRED events against the new semantic. The semantic is tied to the code version, not the event class.

**Add a new event**: `COMPLETION_BOUNDARY_DETECTED` — low-severity, informational. Fires when the rudder detects a potential completion boundary (PR merge, all-tests-green, explicit `divineos complete` signal). Not a block; just a signal that "the next gated tool call will check wire-up status." Gives the agent a moment-of-opportunity to wire things up before the rudder forces the issue.

**Payload shape (v2 refinement 5)** — carries enough context to be actionable on receipt, so downstream readers don't re-derive state from adjacent ledger rows:
```json
{
  "boundary_type": "pr_merge" | "explicit_complete" | "tests_green",
  "artifact_ref": "#191" | "commit:abc123" | "feature:Item-8-PR-1b",
  "timestamp": 1745567890.0,
  "session_id": "session-xyz"
}
```

## Trigger detection — what counts as "completion boundary crossed"

The hard part. The rudder needs a signal for "a unit of work was declared complete." Options considered:

### Option A: PR-merge-as-boundary
Every merge into main = completion boundary. Detection: watch the git reflog / ledger for merge events. Simple to detect, matches the natural unit of shipping.

**Pro:** trivially detectable; aligns with existing bundle workflow.
**Con:** works for code work; doesn't apply to non-PR work (design briefs, investigation, conversations). Would need a broader definition.

### Option B: Explicit-signal-as-boundary
Agent emits `divineos complete <artifact>` when it finishes a unit. The rudder checks: any `complete` event since the last gated tool call that doesn't have a paired `wired` event?

**Pro:** general-purpose; covers non-PR work.
**Con:** relies on the agent being honest about completion. Gameable — agent can just not emit the signal.

### Option C: Implicit-via-tool-pattern
The tool pattern (Edit → Write → Commit → Push → Merge) itself reveals completion boundaries. When the agent moves from this pattern to a substantially different pattern (e.g., starts spawning subagents or reading unrelated files), the rudder infers boundary-crossing.

**Pro:** no explicit signal required; matches how the behavior actually manifests.
**Con:** false positives on context-switching that isn't actually completion-crossing (investigation, debugging, learning-through-reading).

### Recommendation: Option A + Option B with nag-fallback (v2 refinement 6)

- **Primary signal: PR merge events.** Detectable from ledger. High-precision.
- **Secondary signal: explicit `divineos complete <artifact>` events.** For non-PR work.
- **Fallback: NAG not BLOCK.** Investigation is a genuine activity that doesn't produce completion artifacts and shouldn't be treated as drift. The fallback surfaces in the compliance report as an informational observation ("you've operated without completion signals for N consecutive gated tool calls; is that intentional?"). No hard block. The hard-block belongs to A+B; the fallback's job is making the weak signal VISIBLE, not forcing a contract on investigation work.

**Concrete constants (with calibration timeline):**

- `_NAG_THRESHOLD_GATED_CALLS = 20` (initial) — after 20 consecutive gated tool calls without a completion signal, the compliance report surfaces the nag. Calibrated from clean-baseline sessions at 60 days post-ship (same baseline-tagging path PR-191 set up for Item 8 detectors).
- **"Without any completion signal" bounding**: from the last `COMPLETION_BOUNDARY_DETECTED` event (or session start, whichever is later). This is NOT a time bound — it's an event-ordinal bound. Counts absence-of-signal since the last observed signal, not since N minutes ago. The "time is noise" principle holds: the signal is "how many tool calls," not "how long."

Option C's pattern-detection is a follow-up if A+B proves insufficient. Start simpler.

**Answer to "will agents bypass for investigation-heavy sessions?"** Yes, reliably. That's why the fallback is nag-not-block. Investigation shouldn't be gate-blocked. Long investigation sessions should be VISIBLE in the audit surface so operator can distinguish "legitimate deep-dive" from "avoiding wire-up work."

## Ack contract shape — what the agent must file

Current ack (Item 7):
```
divineos compass-ops observe <spectrum> -p <delta> -e "<evidence>" --tag rudder-ack --fire-id <fire_id>
```

Post-redesign ack:
```
divineos compass-ops observe <spectrum> -p <delta> --tag rudder-ack --fire-id <fire_id> \
  -e "<contract>"
```

The `<contract>` string must contain, in any order:
1. An artifact reference (PR #, commit hash, feature name, file path) — NOT the fire_id itself
2. `wired: yes|no|partial`
3. If `wired` is not `yes`: a `next: <plan>` clause
4. **Optional (v2 refinement 7):** `depends_on: <artifact-ref>` — when wire-up is blocked on another artifact. Distinguishes "stuck legitimately" from "procrastination." Compliance audit can reason about dependency chains.

Example valid contract:
```
Completed PR #190 session_cleanliness infrastructure. wired: no. next: write
compliance_baseline.py and thread calibrate_threshold through the 5 brief-named
detectors in phase-2 wiring PRs.
```

Example with dependency:
```
Completed auth middleware refactor (commit abc1234). wired: partial.
next: finish router integration. depends_on: PR #205 (session-token
migration) must land first.
```

Example invalid contract (current Item 7 passes it; this design rejects it):
```
Initiative drift noted, scope bounded to 3 agents, acknowledged.
```
Rejection reason: no artifact reference, no `wired:` token. This is a drift-explanation, not a completion-contract.

## Migration — how to land without breaking current behavior

This is a big change. Shipping it atomically would invalidate every existing compass-ack workflow simultaneously.

**Phased migration (v2 refinements 8 + 13):**

**Phase 0 (NEW):** write `docs/rudder-pre-redesign.md` — a snapshot of current Items 4/6/7 semantics BEFORE any change lands. Includes `JUSTIFICATION_WINDOW_SECONDS`, the substance-check set, what FIRED/ALLOW events mean right now. Forensic readers of old FIRED events will need this to interpret what the event meant at the time it fired. **Docs-only commit**, no guardrail touch, no gate cycle required. Must land before Phase 1.

**Phase 1:** ship new event types + new substance checks UNDER A FEATURE FLAG (`DIVINEOS_RUDDER_CONTRACT_MODE=on`). Flag default OFF. Current Item 7 substance checks remain authoritative; new checks run in parallel and LOG rejection reasons without blocking. Dual-run produces comparison data for Phase 2.

**Phase 2:** observe both in parallel for 30 days. Surface comparison in compliance_audit report ("old check: PASS; new check: REJECT — reason X"). Calibrate new-check FPR against real-use data. Tune thresholds.

**Phase 3:** **flip the flag when criterion met:** new-check FPR < 15% AND new-check catches ≥ 80% of what old-check catches (where "catches" = "flags a real drift-or-incomplete-wire-up"). This is the concrete success threshold; without it, Phase 3's flag-flip is discretionary and discretionary phase-gates drift. Old checks remain installed but become informational-only (warn-don't-block). New checks become authoritative.

**Phase 4:** 30 more days in new-authoritative mode. Retire old Item 7 substance-check flags entirely if no regressions.

**Phase 5:** remove time-based mechanisms (Items 4/6/7 time windows). Final irreversible cleanup. **Stop-ship criterion:** if live data at Phase 4+30d shows new checks catching drift LESS effectively than old time-windows (e.g., new-check real-drift-capture-rate < 70% of old-check's), Phase 5 does NOT proceed. Time-window retirement is irreversible by design; rolling back requires re-implementing the removed code. Naming the stop-ship criterion makes the reversibility trade-off explicit.

**Per-phase review requirement:** each phase is its own PR through the gate, with its own fresh-Claude review. Previous phase's approval does NOT transitively approve the next phase. Explicit so no one tries to roll Phases 4+5 into a single gated PR.

## Pre-reg (one per major mechanism change)

### Pre-reg 1: ack-as-contract
- **Claim**: an ack that describes a completion artifact + wire-up status is a stronger gate than an ack that describes drift.
- **Success**: adversarial test — agent-simulated attempts to pass the gate with drift-only content are rejected; agent-simulated attempts with artifact + wired: no + next: X are accepted.
- **Falsifier**: >20% false-positive rate on legitimate contracts over 30 days live data; OR >15% false-negative rate where drift-explanations sneak through via artifact-reference hallucination.
- **FN check (v2 refinement 9):** **synthetic injection** — monthly, inject 5 drift-only acks (no artifact reference, no wire status) into the substance-check pipeline and verify all 5 are rejected. This is NOT "count real rejections per month" (which passes trivially if nobody submits drift-only acks). The test INJECTS the adversarial shape and verifies rejection. 3 consecutive months with injection success < 100% → audit flag.
- **Review**: +60 days

### Pre-reg 2: completion-boundary detection
- **Claim**: PR-merge events + explicit `complete` events capture >90% of real completion boundaries.
- **Success**: manual audit of 30 days of gated tool calls; compare "rudder flagged" vs "actually crossed a completion boundary."
- **Falsifier**: <80% precision on completion-boundary detection; OR >30% false-positive rate from legitimate context-switches.
- **Review**: +60 days

### Pre-reg 3: time-window retirement
- **Claim**: removing time-window filters does not introduce ack-reuse attacks.
- **Success**: adversarial test — ack from 6 months ago with matching fire_id cannot clear a NEW fire (because new fire_id differs); ack for a fire that's been consumed once cannot satisfy a second fire.
- **Falsifier**: any path by which an old ack satisfies a new fire.
- **Review**: +45 days

### Pre-reg 4: `wired: yes` gameability (v2 refinement 10)
- **Claim**: operator spot-check audit catches the majority of false `wired: yes` attestations.
- **Success**: monthly random audit of 10 `wired: yes` acks. Operator verifies the declared wire-up actually happened (clicks through to the artifact + inspects consumer). Audit reports % honest.
- **Falsifier**: honesty rate < 80% over any 3-month window.
- **Consequence of falsifier**: if honesty rate drops below 80%, Phase 5 is blocked and machine-verification (dependency graph) moves from "future work" to "required." The v1 operator-verify model is only defensible at high honesty rates.
- **FN check**: the audit itself IS the FN check — by construction, manual verification catches what machine checks can't. The risk is the audit not happening; compliance_audit surfaces "N months since last `wired: yes` audit" as a nag if monthly audits lapse.
- **Review**: +30 days (shorter — primary gameability surface)

**Cost acknowledgment:** manual audit is expensive (maybe 15 min per month for 10 acks). Alternative: accept the gameability risk explicitly and surface `wired: yes` claims in the compliance report weekly without requiring operator click-through. That's a weaker defense but cheaper. Brief recommends the manual audit; operator can downgrade if cost proves too high.

## Fire-ID retraction — "discovered incomplete wire-up after ack" (v2 refinement 11)

Under the current one-shot consumption model (Item 6), a fire_id can be acked exactly once. Under new semantics, an operator or agent may legitimately want to say: *"fire-X was acknowledged with `wired: yes`, but spot-check revealed the wire-up was incomplete or false. Re-open it."*

**Decision**: allow **`wired: retracted`** as a fourth wire-status value. A retracted ack:

1. Updates the existing consumption row's `wired_status` column (NEW column — requires schema migration) to `retracted`.
2. Writes a **`RUDDER_ACK_RETRACTED`** event to the ledger with the fire_id, retraction reason, and operator attribution. (v2.1 per fresh-Claude: fixed from `SESSION_CLEANLINESS_RETRACTED` — fire-ID retraction and session-cleanliness untagging are distinct concerns. Session untagging uses the existing `SESSION_CLEANLINESS_UNTAGGED` event.)
3. **Re-opens the fire_id** — PRIMARY KEY on consumption remains, but the rudder's lookup in `_find_justifications` treats a `retracted` row as "no valid ack exists" on that fire.
4. Next gated tool call sees the re-opened fire and forces a new ack contract.

This violates strict one-shot-per-fire but reflects the real-world case that post-ack information can change what the correct ack should have been. Alternatives considered + rejected:

- **Require new fire_id + new ack**: severs the audit trail — the retraction isn't visibly connected to the original ack. Forensics gets harder.
- **Leave unspecified**: operator handles via direct DB edits, which defeats the gate entirely.

The chosen mechanism preserves the audit trail (original ack row + retracted flag + retraction event) while allowing the work to move forward. **One schema change required** — `wired_status` column on `rudder_ack_consumption`.

## Compliance_baseline interaction (v2 refinement 12)

PR-191 introduced `baselines_uncalibrated` detector + `session_cleanliness` tagging as the calibration source for 5 Item 8 detectors. Under the new rudder semantics, several interactions need explicit decisions:

**Does `session_cleanliness` tagging require all `wired: yes` claims in the session to be verified?**

Current PR-2 invariant: a round with HIGH or unresolved-MEDIUM findings cannot tag its own session clean. Proposed addition under new semantics: a session with ≥1 un-audited `wired: yes` ack cannot be tagged clean. This adds pressure on the Pre-reg 4 operator-audit cadence — without regular audits, sessions can't be tagged clean, and Item 8 detectors stay uncalibrated.

**Decision**: adopt the additional invariant. A session is "clean-taggable" only when:
- All round findings at MEDIUM+ are resolved (existing PR-2 rule)
- AND all `wired: yes` acks in the session are either operator-verified or < 7 days old (grace period for audit cadence)
- AND no `wired: retracted` events on that session

This keeps the feedback loop tight: honest acks enable calibration; dishonest acks get caught by audit AND block the session's baseline contribution.

**Calibration-lag acknowledgment (v2.1 per fresh-Claude):** the 7-day grace period creates a stale-calibration window. A session with freshly-filed `wired: yes` acks (all < 7 days) can be tagged clean before operator audit. If audit at day 15 finds falsification, `untag_session_clean` retracts the tag — but Item 8 detectors that used that session for calibration during days 8-15 carried forward a potentially-wrong baseline. v1 accepts this lag (manual-audit cost justifies grace period). v2.x mitigation candidates: (a) tighten to "audit before tag" (higher operator burden); (c) invalidate-and-recompute calibration when a session is untagged retroactively. Naming the lag explicitly so it's a known cost, not an invisible one.

**Does the `baselines_uncalibrated` detector itself need re-aiming under new semantics?**

No. The detector asks "are there enough clean sessions for calibration?" The answer to that question doesn't change — only the criteria for a session BEING clean gets stricter. The detector's threshold (`UNCALIBRATED_GATE_ACTIVITY_THRESHOLD = 50`) and the MIN_CLEAN_SESSIONS threshold (20) stay as-is.

## Scope estimate (updated v2)

- `compass_rudder.py`: ~100 line changes (trigger redesign; remove time-window filters at call sites)
- `moral_compass.py::_validate_fire_id`: ~20 line changes (remove time-window filter from rudder path)
- `substance_checks.py`: ~180 line changes — KEEP similarity (re-aimed to strip artifact tokens); add artifact-ref, wire-status, next-commitment, depends_on checks; fire_id exclusion from artifact match
- `watchmen/_schema.py`: ~15 lines — `wired_status` column migration on `rudder_ack_consumption` (fire-id retraction support)
- `watchmen/cleanliness.py`: ~40 lines — extend `tag_session_clean` sanity checks to require `wired: yes` verification or grace period
- New: `core/completion_boundary.py`: ~100 lines (PR-merge + explicit signals + nag-threshold tracking)
- New CLI: `divineos complete <artifact> [--notes "..."]` and retract flow
- New event types: `COMPLETION_BOUNDARY_DETECTED`, `SESSION_CLEANLINESS_RETRACTED`
- Tests: ~500 lines (each new check + new detector + migration-mode dual-run + retraction + cleanliness-stricter-invariant)
- Docs: `rudder-pre-redesign.md` (Phase 0 snapshot)

Total: ~1100 lines across ~8 files (up from v1's ~900 due to retraction schema + cleanliness interaction + broader tests). Touches guardrailed files `compass_rudder.py`, `moral_compass.py`, `compliance_audit.py` — External-Review trailer required. Multi-phase migration means 5 separate PRs through the gate, each with its own review round (per refinement 13). **Phase 0 docs snapshot lands first**, no gate required.

## Decisions still open

1. **How is `wired: yes` verified?** The contract is the agent's attestation; there's no machine verification. Acceptable in v1 (operator can catch lies). Future work: dependency graph that knows "PR-190 → Item 8 detectors" and checks whether the declared wire-up is consistent with known dependencies.

2. **What counts as "artifact reference"?** Regex for: PR #NNN, commit hashes (7-40 hex), feature names (`Item 8 PR-1b`), branch names (`claude/...`), file paths. Likely a permissive regex + human judgment. False positives here are OK — the goal is "force a concrete reference," not "mechanically validate the reference exists."

3. **What if the agent has nothing to complete (genuine greenfield start)?** The ack can say `completed: none (session start)`. Only required when there's an outstanding completion boundary.

## v2 review status

All 9 v1 review questions answered and folded in. 13 refinements applied:

1. Principle sharpened: completion-checking → **wire-up checking**
2. Item 4 retirement scoped to rudder call-site; `since=` kwarg preserved for other callers
3. Similarity-check KEPT (re-aimed to strip artifact tokens)
4. `_check_completion_reference` excludes fire_id itself from artifact match
5. `COMPLETION_BOUNDARY_DETECTED` payload: boundary_type + artifact_ref + timestamp + session_id
6. Fallback is nag-not-block; `_NAG_THRESHOLD_GATED_CALLS = 20` as named constant; event-ordinal bound not time bound
7. Optional `depends_on:` structured field on ack contract
8. Phase 2→3 concrete FPR threshold (< 15% AND catches ≥ 80%); Phase 5 stop-ship criterion (capture-rate < 70%)
9. Pre-reg 1 FN check via synthetic injection (not "count real rejections")
10. NEW Pre-reg 4: `wired: yes` gameability via operator spot-check audit; honesty rate ≥ 80%
11. NEW §"Fire-ID retraction" — `wired: retracted` as 4th wire-status value; schema column + ledger event
12. NEW §"Compliance_baseline interaction" — stricter `session_cleanliness` tagging rules under new semantics
13. Per-phase review requirement; Phase 0 `rudder-pre-redesign.md` snapshot before any code change

After v2 approval, Phase 0 (docs snapshot) lands first — no gate. Then Phase 1 implementation proceeds with precommit-first discipline + normal gate cycle per phase.
