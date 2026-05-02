# Item 6 Design-Brief Revision — Fire-ID Linkage

> **Status:** post-Item-7 revision. The core spec from design brief v2 (docs/audit-round-1-deferred-design-brief.md, Item 6) is approved. This document adds the concrete implementation decisions that emerged from Items 1/4/7 shipping — schema shape, CLI integration, event payload, interaction with substance checks.

## Recap of approved v2 spec

- Emit `COMPASS_RUDDER_FIRED` ledger event when rudder blocks
- Block message displays fire_id
- Ack must reference fire_id via `--fire-id` CLI flag
- Rudder validates ack → fire_id → real fire event
- One-shot per fire (ack consumed)
- Pre-reg explicitly names fire-spoofing limit (agent has ledger write access)
- Emit `COMPASS_RUDDER_ALLOW` events too — block/allow ratio is a health signal for Item 8

All of the above stands. What follows are the implementation-level decisions.

---

## 1. Schema — additive column on `compass_observation`

Adding `fire_id TEXT NULL` to `compass_observation`. Null for non-ack observations and legacy rows; set for rudder-acks under the new flow.

**Why additive, not a separate table:**
- Every rudder-ack is already a compass_observation; a separate table requires joining on every lookup
- The Item 4 SQL filter (`tag=rudder-ack + spectrum + since`) already surfaces acks; putting `fire_id` on the same row keeps the filter precise
- Migration: single `ALTER TABLE ADD COLUMN` at init-time

## 2. Fire-ID generation

- 16 hex chars (64 bits of entropy) — more than the brief's 8-char suggestion; cheap storage, forward-guessing infeasible
- Generated at rudder block-time via `secrets.token_hex(8)` — cryptographically random
- Full id stored and validated; display in block message truncated to 8 chars for CLI ergonomics

## 3. Event payloads

**COMPASS_RUDDER_FIRED:**
```json
{
  "fire_id": "a3f2c9b1e4d70625",
  "spectrum": "initiative",
  "all_drifting": ["initiative"],
  "tool_name": "Task",
  "window_seconds": 300,
  "drift_values": {"initiative": 0.62},
  "timestamp": 1745524800.0
}
```

**COMPASS_RUDDER_ALLOW:**
```json
{
  "fire_id": null,
  "spectrum": null,
  "tool_name": "Task",
  "reason": "no spectrum drifting toward excess above threshold",
  "drifting_spectrums": [],
  "recent_justifications": []
}
```

Allow-events are small but frequent (every gated tool call). Item 8 uses block/allow ratio — a sudden drop in allow-rate means either the rudder is silently broken OR drift has become chronic. Both warrant surface.

**Storage bound:** `COMPASS_RUDDER_ALLOW` goes through the existing ephemeral-event pruning path in `core/ledger_compressor.py`. Operational telemetry, not knowledge.

## 4. Ack → fire validation — two enforcement points

**At ack-write time (in `log_observation`, AFTER Item 7 substance checks):**
- If fire_id provided: verify a `COMPASS_RUDDER_FIRED` event exists for the same spectrum within the window
- No match: `ValueError("rudder-ack fire_id references nonexistent or stale fire event")`
- Already consumed: `ValueError("rudder-ack fire_id already consumed")`

**At ack-consumption time (in `_find_justifications`):**
- Use only un-consumed acks whose fire_id matches a fire within the window
- Consumption recorded in a separate `rudder_ack_consumption` table (see §5)

## 5. One-shot consumption — storage choice

**Option A**: add `fire_id_consumed_by_observation_id TEXT NULL` to compass_observation; UPDATE on consumption.
- Pros: one row per ack; single table
- Cons: UPDATEs a table that is currently append-only. Violates CLAUDE.md rule 4.

**Option B**: new `rudder_ack_consumption` table with `(ack_observation_id, fire_id, consumed_at)`.
- Pros: strict append-only; every row an immutable fact
- Cons: extra join on ack-validation queries

**Decision: Option B.** Append-only is a foundational truth. Bending it for a convenience flag is exactly the drift the gate exists to prevent. Join cost is sub-ms at our scale.

## 6. CLI integration — `divineos compass-ops observe --fire-id`

Add optional `--fire-id TEXT` flag. Passes through to `log_observation(fire_id=...)`.

**Back-compat:** existing calls without `--fire-id` continue to work. The rudder REQUIRES fire_id only when firing; voluntary observations don't need one.

**Block message:**

```
COMPASS RUDDER [fire-a3f2c9b1]: 'Task' blocked because initiative is drifting
toward excess and no compass observation was recorded in the last 5 minutes.

Before proceeding, file a compass observation bound to this fire:

    divineos compass-ops observe initiative -p <signed delta> \
      -e "<evidence>" --tag rudder-ack --fire-id a3f2c9b1

The fire_id binds your ack to this specific block. Prior acks cannot
satisfy this fire, and this fire_id cannot satisfy future blocks.
```

## 7. Interaction with Item 7 substance checks

Ordering inside `log_observation` when tag=rudder-ack:

1. Schema validation (spectrum valid, position in [-1,1])
2. **Item 7 substance checks** (length, entropy, similarity) — fail cheap on trivial content
3. **Item 6 fire-ID validation** (fire exists, not consumed) — fail on invalid/stale/consumed
4. Write the observation row
5. Mark consumption in `rudder_ack_consumption` (if fire_id provided)

**Consequence:** a trivial ack with a valid fire_id is rejected at substance; a substantive ack with a fabricated fire_id is rejected at fire-validation. Per fresh-Claude's round-4 observation, Items 6 and 7 are independent defenses against adjacent attacks.

**Revelation-principle note:** the combined gate makes the honest path the cheapest — write substantive evidence, reference the displayed fire_id, done. Any shortcut (trivial ack, fabricated fire, stale ack) is measurably harder than the honest path. This is structure, not discipline.

## 8. Pre-reg revisions (v2.1)

- **claim**: fire-ID linkage closes predictive-ack gameability
- **claim**: one-shot consumption closes ack-reuse gameability
- **NOT closed**: fabricate-fire-then-ack — agent has SQLite write access to ledger; requires cryptographic binding between rudder-execution and fire-event-write (v3)
- **NOT closed**: allow-event storage growth — bounded by existing ephemeral pruning
- **success** (adversarial test suite):
    - (a) ack with fabricated fire_id (no matching event) → rejected
    - (b) ack with no fire_id when rudder is firing → rejected
    - (c) ack with real fire_id → accepted once; second ack with same fire_id → rejected
    - (d) ack with real fire_id but wrong spectrum → rejected
    - (e) voluntary observation without --fire-id on non-drifting spectrum → accepted (back-compat)
- **falsifier**: any of (a)-(e) fails, OR legitimate ack requires >3 CLI steps
- **review**: +45 days from merge

## 9. Test plan

- Unit: fire_id generation uniform, non-predictable
- Unit: event payload shape for FIRED and ALLOW
- Unit: validator rejects fabricated / stale / consumed fire_id (5 scenarios)
- Integration: full flow block → observe → unblock
- Integration: consumption table correctly marks one-shot
- Regression: voluntary observations without --fire-id work
- Regression: Item 4 SQL filter still returns acks when fire_id column populated

## 10. Scope estimate

- `compass_rudder.py`: +80 lines (fire_id generation, event emission, consumption check)
- `moral_compass.py`: +40 lines (fire_id param, validation, new table init)
- `compass_commands.py`: +10 lines (--fire-id flag)
- Tests: ~200 lines

Total: ~330 lines across 4 files. Touches guardrailed files (`compass_rudder.py`, `moral_compass.py`) — External-Review trailer required.

## 11. Process correction applied

Per Item 7 thrash lessons and claims fe76b8f9 / 2819af02:

1. Run `bash scripts/precommit.sh` locally BEFORE requesting review. Locks in post-autofix form; tree-hash stable when fresh-Claude sees it.
2. Review-round notes include BOTH diff-hash and tree-hash (gate reads diff-hash; tree-hash is the stable semantic binding per decision 359bd373).
3. Separate policy-change authorization from commit authorization. If an exception is needed, surface it, get round-specific CONFIRMS, then decide about the general rule in its own conversation.

---

## What fresh-Claude is asked to review

1. Is the ordering in §7 correct? Substance before fire-ID, or the reverse?
2. Is Option B in §5 (separate consumption table) the right call, or is append-only strictness overkill here?
3. Event payload shapes in §3 — missing anything? Bloat?
4. CLI UX in §6 — does the block message make the happy path clear?
5. Pre-reg falsifier in §8 — is ">3 CLI steps" defensible?
6. Anything in the v2 Item 6 spec that should change given what Items 1/4/7 taught us?

After approval, implementation proceeds with precommit-first discipline. A separate diff-review round happens on the commit once written.
