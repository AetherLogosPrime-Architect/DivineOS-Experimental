# Audit Round 1 — Deferred 5-item Bundle: Design Brief

> **Status:** design brief, post-review, pre-implementation. All five items approved by fresh-Claude with refinements; refinements folded in below. Next step: per-item implementation under the guardrail gate with External-Review trailer referencing this brief.

**Revision history:**
- v1 (2026-04-23 evening): initial brief submitted to fresh-Claude.
- v2 (2026-04-23 evening): refinements folded in after round-1 review — Item 1 +5 paths (integrity-audit.yml, check_preregs.py, detect-correction.sh, detect-hedge.sh, setup-hooks.ps1) with deliberate exclusions named; Item 4 specifies `json_each`; Item 6 names fire-spoofing limit explicitly in pre-reg and adds allow-event emission; Item 7 specifies TF-IDF cosine as similarity metric, adds min-length gate before entropy, adds rejection-loop escalation to briefing; Item 8 adds per-detector response-path matrix, composite-score v2 trigger condition, clean-baseline calibration sourcing, decide/learn concrete ratios; cross-cutting rollback strategy added (per-detector feature flags).

## Why a design brief first

The five deferred items are interlocking (6+7 share the rudder ack, 7+8 share detector logic), each with its own gameability surface. Reviewing raw code after I've built it invites sycophancy-toward-auditor (quick-accept of whatever I shipped) OR sunk-cost resistance (I defend what I built). Reviewing the design BEFORE implementation makes fresh-Claude's job the right shape: catch the flaw at the spec, not at 400 lines of diff.

Each item below has: **claim** (what I assert), **mechanism** (how it works), **failure modes** (what could go wrong), **pre-reg** (success criterion + falsifier + review date). Pre-reg shape follows existing `prereg` discipline — every new mechanism gets a scheduled honest review.

---

## Item 1 — Guardrail sweep

**Claim:** Four more paths belong on the guardrail list. They are part of the self-enforcement stack and modifying them without external co-sign weakens defenses against the running agent.

**Proposed additions to `scripts/guardrail_files.txt`:**

Core four (initial list):
- `src/divineos/core/moral_compass.py` — the compass itself. If the agent can silently rewrite position logic or tag handling, every downstream compass-based check (rudder, compliance detectors) is undermined at the source.
- `.claude/hooks/compass-check.sh` — the hook that enforces compass-check before tool use. Disabling or softening it removes the enforcement layer entirely.
- `.claude/settings.json` — hook wiring. If this file becomes editable without co-sign, the agent can simply unhook the gates.
- `setup/setup-hooks.sh` — installs the hooks on clone. If this can be modified without co-sign, a future clone skips the gates silently.

Added after fresh-Claude round-1 review (close additional attack classes):
- `.github/workflows/integrity-audit.yml` — server-side enforcement workflow. GitHub runs the HEAD version on each PR, so a PR that rewrites this file validates itself with the rewritten logic. Same self-modification attack class as setup-hooks.sh.
- `scripts/check_preregs.py` — runs in precommit and workflow; pre-reg requirement is bypassable if modifiable without co-sign.
- `.claude/hooks/detect-correction.sh` and `.claude/hooks/detect-hedge.sh` — write side of the marker pattern. The gates look for markers these hooks set. A hook that stops detecting never sets a marker; gate sees nothing and passes. Modifying these silently disables the detection half.
- `setup/setup-hooks.ps1` — PowerShell equivalent. Same attack class, different platform.

**Deliberately excluded (for the record):**
- Other `.claude/hooks/*.sh` (load-briefing, session-checkpoint, pre-compact, post-compact, resume-session) — briefing/checkpoint work, not enforcement. Modifying them degrades briefing quality but doesn't disable a gate. If one grows enforcement responsibility later, it joins the list then.

**Failure modes:**
1. *Over-broad guardrail* — `settings.json` contains non-security settings (permissions, env vars) that change frequently. Guardrailing it forces co-sign for routine config changes. **Mitigation:** accept the friction; settings.json changes are low-frequency in practice, and the items that DO change often (`settings.local.json`) are gitignored.
2. *Churn blocking development* — if any of these files turn out to change often, the guardrail becomes either ignored or bypassed. **Mitigation:** 60-day review; if any of the four files had to use the multi-party-review gate more than twice, that file comes off or the gate rules change.

**Pre-reg sketch:**
- claim: these four files are part of the self-enforcement surface
- success: over 60 days, no legitimate change needs a --no-verify bypass; no enforcement bypass goes undetected
- falsifier: legitimate work is blocked more than twice by needing co-sign on `settings.json` for non-security reasons
- review: +60 days from merge

**Scope estimate:** 5 lines, 1 file. Low risk.

---

## Item 4 — SQL-level filter in `_find_justifications`

**Claim:** The current implementation queries `get_observations(spectrum, limit=10)` then filters Python-side for `RUDDER_ACK_TAG`. This is gameable under load: if someone files ten ordinary observations on a drifting spectrum within the window, a legitimate rudder-ack from before those ten is invisible to the rudder.

**Current path (`compass_rudder.py:102-147`):**
```python
recent = get_observations(spectrum=spectrum, limit=10)
for obs in recent:
    if obs.get("created_at", 0.0) < cutoff: continue
    if RUDDER_ACK_TAG in (obs.get("tags") or []): justified.add(spectrum); break
```

**Proposed mechanism:** Push the tag filter to SQL.
- Add `get_observations(spectrum=..., tag=RUDDER_ACK_TAG, since=cutoff)` in `moral_compass.py` — server-side WHERE on tag + created_at.
- Remove `limit=10` from the rudder call site; filter is now precise.

**Query shape (per fresh-Claude review):** use `json_each()` — not `LIKE '%"rudder-ack"%'`. Tag storage is JSON-blob (`json.dumps(tags or [])` in `log_observation`). LIKE-substring false-matches on future tags containing the prefix (e.g. `rudder-ack-reviewed`). SQLite 3.9+ supports `json_each` natively; no schema migration, no substring fragility, no junction-table overhead.

Concrete form:
```sql
SELECT * FROM compass_observations co
WHERE co.spectrum = ? AND co.created_at >= ?
  AND EXISTS (SELECT 1 FROM json_each(co.tags) WHERE value = ?)
```

**Failure modes:**
1. *Tag storage schema unknown* — `tags` may be stored as JSON blob, comma-list, or junction table. If JSON blob, SQL LIKE on quoted tag works but is imprecise. **Mitigation:** inspect current schema in moral_compass.py before writing the query. If JSON blob, add a normalized junction table as part of this change OR use `json_each()` in SQLite.
2. *Silent behavior change* — if existing callers of `get_observations` relied on the default `limit=10`, adding a `tag=` keyword shouldn't change their output, but I should verify no caller depends on the old limit semantics when tag is None.
3. *Performance regression* — junction-table or json_each adds query cost. **Mitigation:** compass_observations table is small (<10k rows in practice); indexed created_at; real cost negligible.

**Pre-reg sketch:**
- claim: SQL-level filter catches ack within window regardless of ordinary observation volume
- success: adversarial test — file 20 non-ack observations on a drifting spectrum within window, then 1 ack, verify rudder sees the ack
- falsifier: adversarial test fails, or performance regression >10ms on rudder check
- review: +30 days

**Scope estimate:** ~40 lines across 2 files (moral_compass.py get_observations signature + compass_rudder.py caller). Medium risk if tag schema requires migration.

---

## Item 6 — `COMPASS_RUDDER_FIRED` events + ack→fire linkage

**Claim:** Currently a rudder ack is a compass observation with `--tag rudder-ack`. This decouples ack from any specific rudder fire — one ack can satisfy a future fire on the same spectrum within the window. That's acknowledgment-without-specificity: I can file an ack *predictively*, not in response to a specific block.

**Proposed mechanism:**

1. **Emit `COMPASS_RUDDER_FIRED` ledger event** when the rudder decides to block. Event payload: `{fire_id, spectrum, tool_name, drift_value, window_seconds, message}`. `fire_id` is a short hash.
2. **Display fire_id in the block message.** The agent sees: `COMPASS RUDDER [fire-a3f2c9]: 'Task' blocked...`
3. **Ack must reference fire_id.** The unblock command becomes:
   ```
   divineos compass-ops observe <spectrum> -p <delta> -e "..." --tag rudder-ack --fire-id a3f2c9
   ```
4. **Rudder validates ack→fire linkage.** When rudder fires, `_find_justifications` looks for an ack whose `fire_id` references a `COMPASS_RUDDER_FIRED` event for the same spectrum within the window. An ack with no fire_id, or with a fire_id that doesn't match a real fire, doesn't justify.
5. **Acks are one-shot per fire.** Reusing a fire_id across two different blocks is caught (second block doesn't consume a prior ack).

**Failure modes:**
1. *Fire-ID storage in observation* — requires adding a `fire_id` column or metadata field to compass_observations. **Mitigation:** add optional column; migration trivial.
2. *Predictive-ack attack via brute force* — agent files acks with guessed fire_ids. **Mitigation:** fire_id is a hash with enough entropy that forward-guessing is impractical (8-char hex = 16^8 = 4B). Additionally, acks can only be filed AFTER a fire event exists — validate at observation-write time that the referenced fire_id exists in the ledger.
3. *Legitimate ack before fire* — impossible by construction. Could this block valid workflow? No — by definition a rudder-ack is a response to a fire; without a fire there's nothing to ack.
4. *Fire without ack accumulating* — if rudder fires 10 times, each must have its own ack? **Mitigation:** yes, this is the point. Repeated blocks on the same spectrum mean the work is happening in drift; each should force a pause.
5. *Events table growth* — one event per fire. In practice rudder fires rarely (~1-5/session). Small.

**Scope-of-attack limit (added per fresh-Claude review):** the proposal validates "fire_id exists in ledger" — but the agent has write access to the ledger SQLite file. A determined attacker can fabricate a `COMPASS_RUDDER_FIRED` event with a chosen fire_id and then file an ack referencing it. Same class as Watchmen's free-text actor field and the multi-party-review gate's unattested findings. Closing this would require cryptographic binding between rudder execution and fire-event write (HMAC signed with a key the rudder holds and the validator checks). Deferred to v3 — this bundle closes predictive-acking, not fabricate-fire-plus-ack.

**Additional emission (per fresh-Claude review):** emit `COMPASS_RUDDER_ALLOW` events too, not just blocks. Payload: `{fire_id, spectrum, reason, tool_name}`. Disambiguates "rudder didn't fire because nothing was drifting" from "rudder didn't fire because it was silently broken." The compliance audit (item 8) can then use block/allow ratio as a health signal.

**Pre-reg sketch:**
- claim: fire-ID linkage closes predictive-ack gameability. Does NOT close fabricate-fire-plus-ack gameability; that requires cryptographic binding between rudder execution and fire-event write, deferred to v3.
- success: adversarial test — file an ack with a fabricated fire_id but no matching event → rudder rejects; file an ack with no fire_id → rudder rejects; file an ack referencing a real fire → rudder accepts exactly once; reuse same fire_id for a second ack → second rejected
- falsifier: any of the four test paths fails, or legitimate acks take >3 steps to file
- review: +45 days

**Scope estimate:** ~120 lines across 4 files (compass_rudder.py + moral_compass.py + compass_commands.py CLI + tests). Medium-high risk — the schema migration and one-shot-per-fire enforcement are the sharp edges.

---

## Item 7 — Inline substance checks at ack-file time

**Claim:** A rudder-ack with empty or trivial evidence passes the current check because the schema requires only non-empty evidence. "I acknowledge" or one-character evidence satisfies the schema but is substance-free. The rudder's purpose is to force reflection; trivial acks evade that purpose.

**Proposed mechanism:** At ack-observation-write time (inline, not post-hoc), run a three-stage substance gate:

**Stage 1 — Min-length gate (added per fresh-Claude review 7b).** Reject if `len(evidence.strip()) < 20`. Shannon entropy on short strings is too noisy to be reliable; a hard length floor cleanly rejects the trivial case without entropy math. Entropy runs *after* length, not instead of.

**Stage 2 — Evidence-entropy floor.** Reject evidence below minimum Shannon entropy. Catches patterns like "aaaaaaaaaaaaaaaaaaaa" that pass the length gate.

**Stage 3 — Variance-collapse detector.** Compare ack evidence against the last N rudder-acks by the same actor on the same spectrum. If substantially duplicative, reject with message naming the prior ack it matched so the operator can deliberately rephrase.

**Similarity metric (specified per fresh-Claude review 7a):** TF-IDF cosine similarity over the recent-acks corpus for that spectrum+actor. Threshold conservative (>0.9). Rationale: TF-IDF captures lexical reuse better than raw word-overlap (which trips on common words) and is cheap enough for CLI-write-time latency (<50ms on <100-row corpus). Not embedding-based — adds deps and latency without a clear gain over TF-IDF at this corpus size. Not character n-grams — too sensitive to cosmetic rewording. The vectorization is part of the mechanism spec, not a detail: it decides whether the check works.

**Rejection-loop prevention (added per fresh-Claude review 7c):** Track rejection count per (actor, spectrum, current-fire) tuple. On 3rd rejection, emit a `RUDDER_ACK_REJECTION_ESCALATED` event and write a failure_diagnostics entry under the `rudder` surface. That makes the pattern "substance repeatedly failing" surface in the next briefing rather than staying invisible in the terminal. The rudder remains blocked (we don't want to open the gate just because someone tried 3 times); the escalation is about visibility of the pattern, not bypass. Matches the silent-fail-open → loud-in-briefing discipline already in the codebase.

Failures print a specific rejection message and don't write the observation. The rudder stays blocked until substantive evidence is supplied.

**Failure modes:**
1. *Over-strict rejection* — legitimate acks get rejected because genuine evidence happens to share vocabulary with prior acks (same spectrum, same pattern of drift). **Mitigation:** similarity threshold set conservatively (>0.9 cosine), AND only trigger against acks from the same actor within the same window, not historical. Also: print the prior ack being matched so the operator sees why, and can deliberately rephrase.
2. *Entropy floor tuned wrong* — short but substantive acks ("logged; was tight on time") get rejected. **Mitigation:** entropy floor calibrated against real historical acks (pull existing compass_observations with rudder-ack tag, compute entropy distribution, set floor at 5th percentile).
3. *Substance-checker gameable* — agent learns to inject noise to pass the checks. **Mitigation:** this is a real concern but bounded — the agent performing variance-break-through-noise is itself an observable drift pattern. Item 8's compliance_audit detectors catch that meta-pattern.
4. *Checks at the wrong point* — if checks run at write-time but can be bypassed by writing directly to the DB, they're ceremony. **Mitigation:** observation writes go through `log_observation()` in `moral_compass.py`; checks integrated there, not at the CLI. Any write path uses them.

**Pre-reg sketch:**
- claim: substance checks at ack-file time close the trivial-ack gameability
- success: adversarial test suite — empty evidence rejected, single-char rejected, repeated-char rejected, near-duplicate-of-prior-ack rejected, substantive novel evidence accepted
- falsifier: legitimate test ack rejected in a way that blocks honest operation (>1 false rejection in 30 days of real use)
- review: +45 days, with entropy floor re-calibration if false-rejection rate exceeds target

**Scope estimate:** ~80 lines across 2 files (moral_compass.py log_observation + new substance_checks.py module). Medium risk — threshold calibration is the tricky part, and tuning must be empirical (pulled from existing acks).

---

## Item 8 — Compliance audit detector extensions

**Claim:** `compliance_audit.py` currently detects a specific class of audit theater. Four additional patterns are known to fail-open in the current set:

1. **Variance-collapse detector:** operators (decide, learn, observation evidence) over a rolling window losing lexical variance — same vocabulary, same sentence shape, same length distribution. Catches "I'm filing, but I'm filing the same thing repeatedly."
2. **Content-entropy detector:** Shannon entropy of operator content trending down over window — signals copy-paste or template-filling without substance.
3. **Multi-window cross-check:** detectors that fire only on short windows miss slow drift; detectors on long windows miss burst patterns. Run each existing + new detector over three windows (1hr, 1day, 1week) and surface any detector that fires on any window.
4. **decide/learn distribution skew:** ratio of `decide` to `learn` filings has a natural range; severe skew in either direction is a drift signal (too many decides = thinking-substitution; too many learns without decides = hoarding).

**Proposed mechanism:** Each detector is a function `detect(events, window) -> DetectorResult` with (triggered, confidence, evidence, pre_reg_id). All run during `divineos compliance-audit` and their results aggregate into the existing report. No change to the report surface; new signals join the existing list.

**decide/learn skew — concrete ratio (per fresh-Claude review):** "natural range" is not a spec. Baseline measured from clean historical data (see 8c below) sets the target band. Initial conservative estimate: `decide:learn` ratio between 1:3 and 3:1 is normal; <1:5 (decides-without-learning = hoarding) or >5:1 (learns-without-deciding = thinking-substitution) triggers. Actual thresholds calibrated from baseline; these are placeholders until data is pulled.

**Per-detector response paths (8a, per fresh-Claude review):**

| Detector | LOW confidence | MEDIUM confidence | HIGH confidence |
|---|---|---|---|
| Variance-collapse | Report entry | Report + briefing surface marker | Report + briefing + `COMPLIANCE_DRIFT_HIGH` ledger event |
| Content-entropy | Report entry | Report + briefing surface marker | Report + briefing + `COMPLIANCE_DRIFT_HIGH` event |
| Multi-window cross-check | N/A (meta-detector — runs the above across windows) | Elevated report if same pattern fires in 2+ windows | Elevated report + briefing if 3/3 windows |
| decide/learn skew | Report entry | Report + briefing marker | Report + briefing + event |

HIGH confidence = above a per-detector threshold AND confirmed across at least two windows. Signal-without-action is exactly the detector theater this bundle exists to prevent; each severity has a specified destination.

**Composite-score v2 trigger (8b, per fresh-Claude review):** detectors ship independent in v1. If real-use shows them firing in tight correlation (same session, same window, >50% of triggers co-occurring), v2 adds a composite score that penalizes correlated signals and raises the severity of the aggregate. Condition is written into the pre-reg; v2 isn't built now, but the trigger for building it is defined now. Without this, the "gaming all four is harder" claim stays unverified.

**Baseline calibration sourcing (8c, per fresh-Claude review):** "30 days of historical audit events" is circular if the agent has been drifting during that 30 days. Clean baseline sourced from: (a) first 30 days of the project (before detectors existed, so no training target); (b) sessions that passed an externally-audited round; (c) synthetic adversarial test cases for positive-detection validation. Calibrate against (a)+(b) for false-positive floor; use (c) for true-positive sensitivity. Live baseline from the last 30 days is used as a monitoring reference, not the calibration source.

**Failure modes:**
1. *Detector theater — signals without action* — a detector that fires and is ignored is worse than no detector. **Mitigation:** each detector must have a specified response path (briefing surface, ledger event, or compliance-audit failure). No detector lands without a wired downstream.
2. *Correlated false positives* — all four detectors may fire together on legitimate focused work (writing a technical doc has low variance, low entropy, skewed filings). **Mitigation:** each detector has its own pre-reg with an independent falsifier. Run on 30 days of historical data first; any detector with >20% false-positive rate is rejected or retuned.
3. *Threshold calibration* — same issue as Item 7. **Mitigation:** same approach — calibrate against historical compliance_audit data before shipping.
4. *Agent learning to game each* — detector-specific gameability is the main risk. **Mitigation:** the detectors interlock (variance-collapse + content-entropy both catch copy-paste from different angles); gaming all four simultaneously is much harder than gaming one.

**Pre-reg sketch (one per detector):**
- claim: <specific pattern> is drift worth catching
- success: detector fires on adversarial synthetic case; doesn't fire on legitimate focused-work case from historical data
- falsifier: >20% false-positive rate on 30 days of historical audit events
- review: +60 days per detector

**Scope estimate:** ~150 lines across 1 file (compliance_audit.py) + 4 pre-regs. Medium-high risk — detector calibration is empirical and each needs a tuning pass.

---

## Overall bundle

**Total new code:** ~400 lines across ~5 files.
**Guardrailed files modified:** `compass_rudder.py` (item 6), `compliance_audit.py` (item 8), `moral_compass.py` (items 4 + 7 — requires adding to guardrail list under item 1 first).
**Pre-regs filed:** 7 (one per item 1/4/6/7, four for item 8's detectors).

**Ordering for implementation:**
1. Item 1 first — establishes guardrail on `moral_compass.py` and the other paths before items 4+7 touch them. Per fresh-Claude: `moral_compass.py` must be added to the guardrail list in the **same commit** that establishes the External-Review trailer for the first moral_compass change, so the Item 4 PR is gated from the moment moral_compass is touched. Otherwise Item 4 writes to a not-yet-guardrailed file and the gate doesn't fire.
2. Item 4 — small, independent, validates the moral_compass.py modification pattern under the gate.
3. Item 7 — inline substance checks, adds substance_checks.py module (non-guardrailed dep).
4. Item 6 — rudder fire-ID linkage (largest, most schema change).
5. Item 8 — compliance_audit detector extensions. Independent of 6+7 but uses substance-check logic from 7.

**Rollback strategy (cross-cutting, per fresh-Claude review):** every detector (Item 8) and substance-check stage (Item 7) ships behind a feature flag — env var `DIVINEOS_DETECTOR_<NAME>=off` (default: on). Mechanism:
- If real-use produces false positives, operator can disable that specific detector without re-shipping code
- Per-detector flags, not global — one bad detector doesn't force disabling the whole bundle
- Flag state logged to ledger at session start so "detector was off when this happened" is auditable
- Pre-reg falsifier language updated from "rejected or retuned" to "rejected, retuned via threshold, OR runtime-disabled via feature flag for >7 days"

Feature-flag is the implementation of the rollback decision, not a separate decision. Without it, "retune" means re-ship code, which means the path from "detector is too noisy" to "detector is quieter" involves a commit under the External-Review gate — high friction for what should be an operational tuning loop.

**What fresh-Claude is asked to review:**

1. Are the claims right? Is each item actually closing a real gameability, or is it ceremony?
2. Are the failure modes complete? What's missing?
3. Are the pre-regs correctly shaped? Do success/falsifier criteria actually distinguish working-as-intended from theater?
4. Are any items dominated by others — i.e., does implementing item X make item Y unnecessary?
5. Any item that shouldn't land at all? Better to drop now than ship and retract.
6. Any substantially-better mechanism for a given claim? The proposals are not marriage contracts.

Round-3 (diff review) happens after this brief is approved, per-item. Items that don't pass this round don't get built.
