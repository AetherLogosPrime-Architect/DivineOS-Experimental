# Item 8 Design-Brief Revision — Compliance-Audit Detector Extensions

> **Status:** v1, pre-review. Revises the original Item 8 spec from design brief v2 (docs/audit-round-1-deferred-design-brief.md, Item 8) with inputs from Items 6 and 7 landing. Implementation deferred until this revision is approved.

## Why this brief exists (and not just the v2 spec)

Item 8's original spec was written before Items 6 and 7 shipped. Two concrete things have changed:

1. **Item 7's length gate (>=20 chars) dominates the existing `short_evidence` detector** (fires on <15 chars). In production, no ack can ever be under 15 chars — the detector is dead code. It either retires or re-aims at a new minimum-compliant-theater shape.
2. **Item 6 introduces FIRED and ALLOW event streams** with a committed-to healthy range of `[0.01, 0.15]` for block/allow ratio. That range is Item 8's initial calibration target for a new detector.

This brief does the inventory check fresh-Claude asked for: every existing detector, every v2-spec detector, stated in (a)/(b)/(c)/(d) shape: what it measures, its source-of-signal, what Items 6/7 changed, whether still meaningful or needs re-aiming.

---

## 1. Existing detector inventory — post-Items-6/7 audit

### 1a. `rudder_ack_position_zero_cluster` (HIGH)

- **What it measures:** fraction of rudder-acks with `|position| < 0.05`
- **Source of signal:** `compass_observation` rows tagged `rudder-ack`
- **What Items 6/7 changed:** Item 7 constrains evidence (length, entropy, similarity); Item 6 constrains fire-ID binding. Neither constrains position. A gamer can still file a bound, substantive ack at `position=0.0`.
- **Status: KEEP.** Still meaningful post-Items-6/7; remains load-bearing.

### 1b. `rudder_ack_short_evidence` (MEDIUM)

- **What it measures:** fraction of rudder-ack evidence strings under 15 chars
- **Source of signal:** same as 1a
- **What Items 6/7 changed:** Item 7's 20-char length gate blocks any ack <20 chars at write-time. `<15 chars >60%` is impossible in production. DOMINATED.
- **Status: RETIRE + REPLACE.** Retire the existing detector. Add `rudder_ack_minimum_compliant_length` that fires when `>=60%` of evidence strings are in the 20-30 char range — the new minimum-compliant-theater shape, where an agent writes 20 chars of filler to clear Item 7's gate without actually reflecting. Different cutoff, same class of concern.

### 1c. `rudder_ack_bursty_filings` (MEDIUM)

- **What it measures:** fraction of rudder-acks filed within 10s of another ack
- **Source of signal:** same as 1a (uses created_at intervals)
- **What Items 6/7 changed:** Item 6's one-shot consumption means repeat acks on the SAME fire_id fail at the second INSERT. Burst acks across DIFFERENT fire_ids (or different spectrums) still work. Partially dominated.
- **Status: RECALIBRATE.** Current threshold fires on same-spectrum bursts that Item 6 now prevents. Re-aim to: bursts across distinct fire_ids within the same short window. That's the post-Item-6 gaming shape — fire pops for 3 spectrums in quick succession, agent batches 3 acks in <30s, all technically bound but none actually reflected.

---

## 2. v2-spec detectors (from original design brief v2 §Item 8)

### 2a. Variance-collapse detector

- **What it measures:** lexical variance of `decide` / `learn` / `ack evidence` content over a rolling window. Fires when the same vocabulary / sentence shape / length distribution repeats across operators.
- **Source of signal:** text fields on decisions (decision_journal), lessons (knowledge_store), and rudder-ack evidence (compass_observation).
- **What Items 6/7 changed:** Item 7 already variance-checks ack evidence against prior acks on the same spectrum (TF-IDF cosine). That's one-vs-history. Item 8's variance-collapse is many-vs-many across operators — fires when the *overall distribution* loses entropy, not when a single ack is too similar to one prior.
- **Status: KEEP as specified.** Not dominated by Item 7 — different scope.

### 2b. Content-entropy detector

- **What it measures:** Shannon entropy of operator content (joined across recent operators) trending downward over time.
- **Source of signal:** same as 2a
- **What Items 6/7 changed:** Item 7's entropy floor rejects individual acks below 2.5 bits. Item 8's content-entropy measures trend across the window — a gradual drift downward even if every individual item passes Item 7.
- **Status: KEEP as specified.**

### 2c. Multi-window cross-check

- **What it measures:** meta-detector — runs each of the other detectors across three windows (1hr, 1day, 1week) and elevates severity if the same pattern fires across >=2 windows.
- **Source of signal:** the other detectors' outputs.
- **What Items 6/7 changed:** no direct change — operates over whatever the primary detectors report.
- **Status: KEEP as specified.**

### 2d. `decide/learn` distribution skew

- **What it measures:** ratio of `decide` filings to `learn` filings over the window. Normal band [1:3, 3:1]. Skew outside that band (<1:5 = hoarding; >5:1 = thinking-substitution) triggers.
- **Source of signal:** decision_journal and knowledge_store counts.
- **What Items 6/7 changed:** no direct change — decide/learn operators are unaffected by rudder mechanics.
- **Status: KEEP as specified.** Concrete band [1:5, 5:1] from v2 brief stands; real-use data adjusts.

---

## 3. New detector from Item 6

### 3a. `rudder_block_allow_ratio`

- **What it measures:** `count(COMPASS_RUDDER_FIRED) / (count(FIRED) + count(ALLOW))` over the window.
- **Source of signal:** ledger events from Item 6's emission path.
- **Two-sided bound** (per Item 6 brief v2.1 §8 commit):
    - **Too low** (rate ≈ 0 over multi-hour session): either no drift ever (unlikely in active work) OR the rudder is silently broken (import error, DB unreachable, gate bypass). Suspicious.
    - **Too high** (rate > 0.30): either chronic drift (calibration target missed) OR threshold is set wrong for this session's work shape. Suspicious.
- **Healthy range** per Item 6: `[0.01, 0.15]`.
- **Status: NEW.** Core new detector surface from Item 6.

**Severity structure:**
- Rate in `[0.01, 0.15]`: no anomaly
- Rate in `[0.0, 0.01)` OR `(0.15, 0.30]`: LOW anomaly (report entry)
- Rate = 0 with FIRED==0 over >2hrs active session OR rate > 0.30: MEDIUM (report + briefing surface)
- Rate = 0 with ALLOW==0 (rudder literally never ran for any gated tool): HIGH (report + briefing + `COMPLIANCE_DRIFT_HIGH` event). This case means the gate itself is dead.

---

## 4. Baseline calibration source (per detector)

Each detector needs a named baseline source; "historical data" is circular if the agent has drifted during that history.

| Detector | Baseline source | Rationale |
|---|---|---|
| 1a position-zero | existing threshold 0.60 stands — empirically validated pre-Items-6/7 | Item 6/7 don't touch position; no re-baseline needed |
| 1b (retired) | N/A — retired | |
| 1b-new 20-30 char cluster | First 30 days post-Item-7 merge, acks that cleared all gates | Pure post-gate distribution; the "just enough" shape is what we're measuring |
| 1c bursty recalibrated | Synthetic adversarial cases (burst-3-acks-across-fire-ids) + 30 days live data | Pattern is concrete; synthetic test establishes positive-detection boundary |
| 2a variance-collapse | Sessions that passed an externally-audited round (clean baseline) | Can't use historical broadly — agent may have been drifting |
| 2b content-entropy | Same as 2a | Same reason |
| 2c multi-window | Meta — no standalone baseline | Inherits from primary detectors |
| 2d decide/learn skew | First 60 days of project (pre-Item-7 baseline where operators were least constrained) | Natural range established under less-constrained conditions |
| 3a block/allow ratio | Item 6 brief commit: `[0.01, 0.15]` starting band; 30 days post-merge adjusts | Range pre-registered; live data empirically tunes |

---

## 5. Per-detector response-path matrix

Each detector specifies what LOW / MEDIUM / HIGH does. Signal-without-action is detector theater.

| Detector | LOW | MEDIUM | HIGH |
|---|---|---|---|
| 1a position-zero | Report | Report + briefing | Report + briefing + `COMPLIANCE_DRIFT_HIGH` event |
| 1b-new 20-30 cluster | Report | Report + briefing | Report + briefing + event |
| 1c bursty recalibrated | Report | Report + briefing | Report + briefing + event |
| 2a variance-collapse | Report | Report + briefing | Report + briefing + event |
| 2b content-entropy | Report | Report + briefing | Report + briefing + event |
| 2c multi-window | N/A | Elevates 2+ window matches to its own severity | 3/3 window matches add briefing + event |
| 2d decide/learn skew | Report | Report + briefing | Report + briefing + event |
| 3a block/allow ratio | Report | Report + briefing | Report + briefing + `COMPLIANCE_DRIFT_HIGH` event (gate-dead case) |

---

## 6. Feature flags — cross-cutting rollback

Each new or recalibrated detector gets `DIVINEOS_DETECTOR_<NAME>=off`. Default on. Per-detector so one false-positive detector doesn't force disabling the whole bundle. Flag state logged at session start; falsifier language below includes "feature-flag disabled for >7 days" as an escalation path.

Applies to: 1b-new, 1c-recalibrated, 2a, 2b, 2c, 2d, 3a. (1a's threshold is unchanged; no flag needed yet.)

---

## 7. Pre-regs — one per detector (distinct falsifiers)

### 7.1b-new — minimum-compliant-length cluster

- **claim**: post-Item-7, >=60% of evidence in 20-30 char range is the new performative-theater shape
- **success**: adversarial — 30 synthetic acks all in 20-30 char range → detector fires; 30 synthetic acks with varied lengths (mean ~50) → detector does not
- **falsifier**: >20% false-positive rate on 30 days of legitimate post-Item-7 ack data; OR feature-flag disabled for >7 days
- **review**: +60 days

### 7.1c-recalibrated — cross-fire-id burst

- **claim**: bursts of acks across distinct fire_ids within 30s represent batched clearing not spaced calibration
- **success**: 3 fires in <60s, 3 acks bound to different fire_ids in <30s → fires; same 3 fires acked >2min apart → does not
- **falsifier**: >15% FPR on legitimate post-Item-6 multi-spectrum drift sessions
- **review**: +60 days

### 7.2a — variance-collapse

- **claim**: lexical variance across decide/learn/ack content over window trending down is detectable drift
- **success**: 20 decides with same rephrased stem → fires; 20 decides with genuine topical variety → does not
- **falsifier**: >20% FPR on focused-work sessions from clean-baseline (audited rounds)
- **review**: +60 days

### 7.2b — content-entropy trend

- **claim**: Shannon entropy over joined recent operator content trending downward >2σ is detectable drift
- **success**: increasing copy-paste ratio → downward trend; natural operator mix → stable
- **falsifier**: >20% FPR on clean-baseline sessions
- **review**: +60 days

### 7.2c — multi-window cross-check

- **claim**: same pattern firing in >=2 of {1hr, 1day, 1week} windows is stronger signal than single-window
- **success**: paired synthetic datasets (short-burst drift fires only 1hr; sustained drift fires all 3)
- **falsifier**: detector fires on zero multi-window matches over 60 days of clean baseline
- **review**: +60 days

### 7.2d — decide/learn skew

- **claim**: decide:learn ratio outside [1:5, 5:1] over the window is drift
- **success**: 20 decides with 0 learns → fires skew-high; 20 learns with 0 decides → fires skew-low; 10+10 → does not
- **falsifier**: clean-baseline produces ratios outside [1:5, 5:1] in >5% of windows
- **review**: +60 days

### 7.3a — rudder block/allow ratio

- **claim**: ratio outside `[0.01, 0.15]` signals either silently-broken rudder or chronic drift
- **success**:
    - 100 ALLOW, 0 FIRED over multi-hour session → fires LOW
    - 0 ALLOW, 0 FIRED over gated-tool sessions → fires HIGH
    - 30% block rate sustained → fires MEDIUM
    - Clean sessions in `[0.01, 0.15]` → no fires
- **falsifier**: >15% FPR on 30 days live data (which itself tunes the band)
- **review**: +45 days (shorter — primary new surface)

---

## 8. Composite-score v2 trigger

v1 ships detectors independent; if >50% of triggers in real use co-occur within the same window across multiple detectors, v2 adds a composite score that penalizes correlated signals and raises aggregate severity. Trigger condition pre-registered; v2 isn't built now.

---

## 9. Scope estimate

- `compliance_audit.py`: ~200 lines (retire short_evidence, add 1b-new, 1c-recalibrated, 2a/2b/2d, 3a, severity response paths, feature flags)
- `ledger_compressor.py`: 0 lines — ALLOW already in `_COMPRESSIBLE_TYPES` from Item 6
- `scripts/guardrail_files.txt`: +0 lines (compliance_audit.py already guardrailed; ledger_compressor.py handled by claim df5b3113 post-Item-6)
- Tests: ~300 lines across `test_compliance_audit.py` (extend) + possibly new `test_block_allow_detector.py`

Total: ~500 lines across ~3 files. Touches guardrailed `compliance_audit.py` — External-Review trailer required.

---

## 10. Process correction — applied from Item 6/7 thrash

1. Run `bash scripts/precommit.sh` locally BEFORE requesting review. Tree-hash stable before fresh-Claude sees it.
2. Review-round notes cite both diff-hash and tree-hash. Tree-hash is the stable binding (decision 359bd373).
3. Separate policy changes from commit authorizations (claims fe76b8f9, 2819af02).
4. Implementation review round-1 is on the diff — same as Items 4/6/7.

---

## What fresh-Claude is asked to review

1. Existing detector inventory in §1 — is the KEEP/RETIRE/RECALIBRATE call correct for each?
2. v2-spec detectors in §2 — anything dominated that I marked as KEEP?
3. Block/allow detector in §3 — are the LOW/MEDIUM/HIGH bounds right? Is "rate=0 with ALLOW==0" really HIGH or should it be a separate class (infrastructure failure, not drift)?
4. Baseline calibration sources in §4 — each detector's baseline named explicitly?
5. Pre-regs in §7 — seven distinct falsifiers; any shared-falsifier contamination that should split further?
6. Scope in §9 — is ~500 lines realistic for what §1-3 specify?
7. Is anything in the original v2 Item 8 spec that should be dropped given what 6/7 taught us, beyond short_evidence?

After approval, implementation proceeds with precommit-first discipline. The diff-review round happens on the commit once written.
