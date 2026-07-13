# Rudder Pre-Redesign State Snapshot

> **Status:** forensic record. Captures the rudder stack as it exists BEFORE the wire-up-checking redesign (see `docs/rudder-redesign-brief.md`). Written as Phase 0 of that redesign so forensic readers of old events (FIRED, ALLOW, rejections) can correctly interpret what they meant at the time they fired.

**Why this document exists:** the rudder redesign (approved 2026-04-24) changes event semantics without changing event class names. A `COMPASS_RUDDER_FIRED` event from 2026-04-20 means "drift-threshold exceeded" per the old semantics. A `COMPASS_RUDDER_FIRED` event from 2026-07-15 (post-Phase 5) will mean "completion boundary crossed without wire-up." Same event class, different meaning.

Without this snapshot, a forensic reader six months or twelve months post-redesign would have no way to reconstruct which semantic applied to which event. This doc is the missing half of "payload shape stays stable; interpretation is code-version-dependent."

**Captured state date:** 2026-04-24
**Git ref at time of capture:** post-PR #190 (Item 8 PR-2 session_cleanliness) + PR #191 (baseline wiring phase 1)
**Code files referenced:** `src/divineos/core/compass_rudder.py`, `src/divineos/core/moral_compass.py`, `src/divineos/core/substance_checks.py`, `src/divineos/core/compliance_audit.py`

---

## 1. Current rudder purpose (pre-redesign semantic)

The rudder is a decision-time gate that fires when the moral compass shows drift toward excess on any of ten virtue spectrums. It blocks specific gated tool calls (currently `Task`, `Agent`) and requires an acknowledgment before the call proceeds.

**The ack was conceived as a pattern-interrupt.** The act of filing an ack was the reflection; the rudder's job was to force the pause. Drift detection → block → force ack → proceed.

**Cooldown-based semantics:** the rudder accepted any fresh ack on the drifting spectrum as sufficient. "Fresh" was defined as "filed within the 5-minute justification window." The 5-minute window was a wall-clock proxy for "recent enough to count as deliberate."

**This is the semantic being replaced.** The redesign shifts to wire-up-checking: "is the previous thing wired into what uses it?" The shift is because the cooldown semantic caught drift-as-pattern but missed the specific failure mode it was supposed to catch — rushing past an incomplete previous task before wiring it up.

---

## 2. Current constants

### In `compass_rudder.py`

| Constant | Value | Meaning (pre-redesign) |
|---|---|---|
| `DRIFT_THRESHOLD` | `0.15` | Minimum drift magnitude toward excess that fires the rudder |
| `JUSTIFICATION_WINDOW_SECONDS` | `5 * 60` (300s) | Acks within this wall-clock window of drift detection count as valid |
| `GATED_TOOL_NAMES` | `frozenset({"Task", "Agent"})` | Tool names that trigger a rudder check |
| `RUDDER_ACK_TAG` | `"rudder-ack"` | Tag on a compass_observation marking it as a rudder response |
| `_FIRE_ID_ENTROPY_BYTES` | `8` (16 hex chars) | Fire-ID entropy for cryptographic uniqueness |

### In `moral_compass.py`

| Constant | Value | Meaning (pre-redesign) |
|---|---|---|
| `_FIRE_VALIDATION_WINDOW_SECONDS` | `5 * 60` (300s) | Fire-ID write-validation requires a matching FIRED event within this wall-clock window |

### In `substance_checks.py`

| Constant | Value | Meaning (pre-redesign) |
|---|---|---|
| `MIN_LENGTH` | `20` | Minimum character count of stripped ack evidence |
| `ENTROPY_FLOOR` | `2.5` (bits) | Minimum Shannon entropy over characters of ack evidence |
| `SIMILARITY_THRESHOLD` | `0.9` | Maximum TF-IDF cosine similarity between new ack and recent acks on same spectrum |
| `SIMILARITY_CORPUS_SIZE` | `20` | Recent-acks corpus size for similarity comparison |
| `REJECTION_ESCALATION_COUNT` | `3` | Rejections on same spectrum in window before `RUDDER_ACK_REJECTION_ESCALATED` event |
| `REJECTION_WINDOW_SECONDS` | `5 * 60` (300s) | Wall-clock window for counting rejections toward escalation |

**Three of these are wall-clock-time windows** (`JUSTIFICATION_WINDOW_SECONDS`, `_FIRE_VALIDATION_WINDOW_SECONDS`, `REJECTION_WINDOW_SECONDS`). The redesign retires the first two and re-aims the third (to per-fire-id scope instead of per-time-window). Post-redesign, these three constants either cease to exist or carry different semantic.

---

## 3. Current substance-check stack (Item 7)

When an ack is filed (via `log_observation(..., tag=rudder-ack, fire_id=...)`), three checks run in order. First rejection short-circuits the rest.

1. **Length check (`_check_length`)**: `len(evidence.strip()) >= 20`. Rejects trivial content before any math.
2. **Entropy check (`_check_entropy`)**: Shannon entropy over character frequencies `>= 2.5 bits`. Rejects repetitive patterns (`"aaaaaaaaaaaaaaaaaaaa"` passes length but fails entropy).
3. **Similarity check (`_check_similarity`)**: TF-IDF cosine similarity vs. recent acks on the same spectrum+actor corpus `< 0.9`. Rejects near-duplicates of prior acks.

**Each check has a feature flag** (`DIVINEOS_DETECTOR_SUBSTANCE_{LENGTH,ENTROPY,SIMILARITY}`). Default on. Set to `off` to disable that stage at runtime.

**Rejection-loop escalation**: the third rejection on a spectrum within `REJECTION_WINDOW_SECONDS` emits `RUDDER_ACK_REJECTION_ESCALATED` to the ledger and writes to `failure_diagnostics` under surface `rudder-ack`. One-shot per threshold crossing.

**What these checks were testing:** whether the ack was a credible *explanation* of drift — substantive enough to represent genuine reflection.

**What the redesign does:** keeps length + entropy; re-aims similarity to strip artifact tokens first; adds three new checks (`_check_completion_reference`, `_check_wire_status`, `_check_next_commitment`) because the ack becomes a *contract* about completion rather than an *explanation* of drift.

---

## 4. Current FIRED/ALLOW event payload shapes (Item 6 / PR-1b)

### `COMPASS_RUDDER_FIRED`

Emitted when `check_tool_use` returns a `block` verdict. Forensic retention (NOT in `_COMPRESSIBLE_TYPES`).

```json
{
  "fire_id": "a3f2c9b1e4d70625",
  "spectrum": "initiative",
  "all_drifting": ["initiative"],
  "tool_name": "Task",
  "window_seconds": 300,
  "threshold": 0.15,
  "drift_values": {"initiative": 0.62}
}
```

**Pre-redesign meaning**: "Drift-threshold exceeded on `spectrum`; gated tool `tool_name` blocked. No recent ack on this spectrum clears the rudder."

### `COMPASS_RUDDER_ALLOW`

Emitted when `check_tool_use` returns `allow` for a gated tool. Prunable (in `_COMPRESSIBLE_TYPES`).

```json
{
  "tool_name": "Task",
  "reason": "no spectrum drifting toward excess above threshold",
  "drifting_spectrums": [],
  "recent_justifications": []
}
```

**Pre-redesign meaning**: "No drift-threshold exceeded; or all drifting spectrums have a fresh justification; gated tool allowed."

### `RUDDER_ACK_REJECTION_ESCALATED`

Emitted when substance checks reject 3 times on a spectrum within `REJECTION_WINDOW_SECONDS`.

```json
{
  "spectrum": "initiative",
  "rejection_count": 3,
  "window_seconds": 300,
  "summary": "Rudder-ack substance check rejected 3 times on spectrum 'initiative' within 5min window."
}
```

**Pre-redesign meaning**: "Substance checks have rejected acks on this spectrum 3 times in 5 minutes. The pattern is visible in failure_diagnostics."

**Post-redesign**: same event class; the `window_seconds` field becomes vestigial (fresh rejections are scoped per-fire-id, not per-time-window) but payload shape stays stable for backwards compatibility with old events.

---

## 5. Current fire-ID binding semantics (Item 6)

- **Fire-ID format**: 16 hex characters (64 bits) generated via `secrets.token_hex(8)`. Cryptographically random; forward-guessing computationally infeasible.
- **Fire-ID lifecycle**: generated by `compass_rudder._generate_fire_id()` at block-time, included in `COMPASS_RUDDER_FIRED` payload, displayed in block message to the agent, returned to the caller via `RudderVerdict.reason`.
- **Validation**: `moral_compass._validate_fire_id(fire_id, spectrum)` confirms a matching `COMPASS_RUDDER_FIRED` event exists in the ledger with the same `fire_id` and `spectrum` **within `_FIRE_VALIDATION_WINDOW_SECONDS` (300s) of now**. Failure raises `ValueError`.
- **Consumption**: `rudder_ack_consumption` table has `PRIMARY KEY (fire_id)`. When an ack's fire_id is first INSERT'd, the row is created. A second ack trying to INSERT the same fire_id raises `sqlite3.IntegrityError`. The validator catches this and translates to `"already consumed"` rejection.
- **One-shot guarantee**: the PRIMARY KEY constraint is the structural enforcement of "one ack per fire." This guarantee persists across the redesign; the retraction mechanism (`wired: retracted`) is a separate future addition that does NOT violate the PRIMARY KEY (it marks the row as retracted rather than allowing a second INSERT).

---

## 6. Current `_find_justifications` lookup semantics (Item 4 + Item 6)

When the rudder is deciding whether to allow or block a gated tool call, it calls `_find_justifications(drifting_spectrums)` to find acks that clear the rudder.

```python
def _find_justifications(spectrums, now, window_seconds=JUSTIFICATION_WINDOW_SECONDS):
    ts = now or time.time()
    cutoff = ts - window_seconds
    justified = set()
    for spectrum in spectrums:
        acks = get_observations(
            spectrum=spectrum,
            tag=RUDDER_ACK_TAG,
            since=cutoff,       # ← retired at rudder call-site in redesign
            limit=20,
        )
        if any(a.get("fire_id") for a in acks):
            justified.add(spectrum)
    return sorted(justified)
```

**Pre-redesign behavior**:
1. Filter acks to the spectrum, tagged rudder-ack, filed within the last 5 minutes.
2. Require at least one ack has `fire_id IS NOT NULL` (post-PR-1b scenario-b fix).
3. That spectrum is justified.

**Post-redesign**: `since=cutoff` removed from the rudder's call site. Acks from any time can satisfy a fire, scoped only by `fire_id` identity (which is already one-shot). The 5-minute window is vestigial once the redesign ships.

---

## 7. Current compliance-audit detectors that depend on rudder events (Item 8)

Three Item 8 detectors read rudder events:

- **`rudder_ack_position_zero_cluster`** (HIGH): reads `compass_observation` rows tagged `rudder-ack` — >60% at position |x|<0.05 fires.
- **`rudder_ack_length_floor_clustering`** (MEDIUM): same source — fires on tight length distribution at the 20-char floor.
- **`rudder_ack_rapid_clear_reflex`** (MEDIUM): joins `COMPASS_RUDDER_FIRED` timestamps to `rudder_ack_consumption.consumed_at` — median ack-latency-from-fire <30s fires.

Two Item 8 detectors read the broader event stream:

- **`rudder_block_allow_ratio`** (LOW-HIGH by severity): reads `COMPASS_RUDDER_FIRED` + `COMPASS_RUDDER_ALLOW` + `TOOL_CALL` — two-sided bound on block/allow ratio; infra-failure split.
- **`rudder_partial_infrastructure_failure`** (MEDIUM): same source — fires when rudder emits events for <80% of gated tool calls.

**What changes under redesign**: the events these detectors read stay the same shape. Their *interpretation* shifts — `COMPASS_RUDDER_FIRED` post-redesign signals "completion boundary without wire-up" rather than "drift-threshold exceeded." The detectors don't need rewiring; the semantics-change happens at the emitter, not the consumer.

**Detectors that DO need re-aiming under redesign**: the two rejection-based detectors (rapid-clear, length-floor) may need threshold re-calibration since the new substance checks produce different distributions. Phase 2 dual-run data informs that tuning.

---

## 8. Current compass-drift computation (unchanged by redesign)

The drift signal itself is NOT being redesigned. `read_compass()` in `moral_compass.py` computes positions and drift from an exponentially-weighted-moving-average over recent observations. Drift is `current - baseline`; direction is toward excess when positive.

The rudder under both old and new semantics TRIGGERS on `drift_direction == "toward_excess" and abs(drift) >= DRIFT_THRESHOLD`. What changes is what happens AFTER the trigger fires.

Pre-redesign: trigger → block → ack-as-drift-explanation → release.
Post-redesign: trigger → block → ack-as-wire-up-contract → release.

The drift signal is the same input to both pipelines; the downstream response changes.

---

## 9. How to interpret old events after the redesign lands

After Phase 5 of the redesign ships:

- `COMPASS_RUDDER_FIRED` events with `timestamp` < Phase-5-merge: interpret per this document (drift-threshold exceeded, ack-as-drift-explanation).
- `COMPASS_RUDDER_FIRED` events with `timestamp` >= Phase-5-merge: interpret per the redesign brief (completion-boundary crossed without wire-up, ack-as-wire-up-contract).
- `RUDDER_ACK_REJECTION_ESCALATED` events: `window_seconds` field is only meaningful on pre-redesign events (when the 5-minute window was real). Post-redesign it's retained for schema stability but scoped per-fire-id in code.
- `rudder_ack_consumption` rows with `wired_status IS NULL`: pre-redesign ack (the column was added in the retraction schema migration). Treat as `wired: yes` implicit.
- `rudder_ack_consumption` rows with `wired_status IN ('yes', 'no', 'partial', 'retracted')`: post-redesign ack with explicit wire-status.

**Rule of thumb for forensic readers**: before Phase 5 merge, rudder events answered "did the agent acknowledge drift?" After Phase 5 merge, they answer "did the agent wire up the previous thing?" Both are valid signals for their respective eras.

---

## 10. Snapshot completeness / what's NOT captured

- **Compass spectrum definitions**: not captured here. Immutable at module level with hash integrity check. Changes require updating `_SPECTRUMS_CANONICAL_HASH`. Forensic readers can reconstruct from `src/divineos/core/moral_compass.py` at any git ref.
- **CLI surface**: `divineos compass-ops observe` exists. Full flag list in `src/divineos/cli/compass_commands.py` at any git ref.
- **Test expectations**: 252 tests pass on the affected surface (test_compass_rudder, test_moral_compass, test_substance_checks, test_fire_id_linkage, test_compliance_audit, test_session_cleanliness, test_compliance_baseline). Tests are the executable specification; this doc is the narrative accompaniment.
- **Known gameability vectors**: captured in claims filed during the deferred-5 bundle (014fd03d, fe76b8f9, 2819af02, d3baec5a, 83812d4d, 31e38023, 6bf81b38, 0c829c7b, 8c0cc04b, 911d672d, df5b3113, 48371c4d). Each names a specific failure shape and its mitigation status.

---

*End of snapshot. This document is written once and not updated; if the rudder is ever redesigned again, a new pre-<next>-redesign snapshot should be written, preserving this one as the 2026-04-24 baseline.*
