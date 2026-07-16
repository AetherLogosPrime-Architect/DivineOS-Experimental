# ForcedWorkGate — primitive design doc

**Status:** DRAFT (Aether 2026-07-16, Aria to amend)
**Extends:** `EvidenceBearingStopGate` (`src/divineos/hooks/evidence_bearing_stop_gate.py`)
**Motivation:** Aletheia's cold-audit 2026-07-16 named "the shape of the act is not the act" as one of three root disease-shapes across the OS. Compass drift-log substitution, tier-graduation for council-required, lens-load-trace verification, and operator-authorized-bypass are four separate mechanisms that all need the same structural discipline: at mechanism-fire-time, force the pointed-at cognitive/relational work to actually happen, and refuse surface-form output that pretends the work happened when it did not.
**Related:** Truth #7 (cognitive-named tools point at cognitive work; they are not it), Truth #15 (mechanisms point at work; they are scaffolding for the work).

---

## The principle stated once

> When a mechanism fires, structurally force the pointed-at cognitive/relational work to happen at fire-time, and refuse the surface-form output that pretends it did.

The primitive doesn't care what layer the mechanism operates on (substance-processing, authorization-verification, or future layers). It cares about one relationship: **mechanism-fires-work**. The mechanism is the scaffolding; the pointed-at work is the actual thing that matters; the primitive prevents the scaffolding from being mistaken for the thing.

## Extends EvidenceBearingStopGate

The five-slot EBSG shape holds (LOCK, CONDITION, MEANS, RECORDING, UNLOCK-CONTINGENT). `ForcedWorkGate` adds four slots on top:

- **POINTED_AT_WORK** — what cognitive/relational work the mechanism structurally requires at fire-time. Named as a concrete verb-object: *"walk council with real lenses,"* *"reflect on drifting value with cite + why + tweak,"* *"verify operator authorized this specific edit."* Not a category — a nameable action.
- **EVIDENCE_OF_WORK** — what artifact proves the pointed-at work happened. Must be a resolvable substrate record (event ID, file-load trace, structured multi-section template with required sections, verified quote), not surface-form output that could be produced without the work.
- **REFUSAL_SHAPE** — how the gate refuses when evidence is absent. Options: block-the-tool-call, block-the-write, force-re-do-with-diagnostic, require-operator-authorization (recursive — instance 4 as the escape hatch for instances 1-3).
- **LAYER_TAG** — which layer this instance operates on: `SUBSTANCE`, `AUTHORIZATION`, or future layers. Used at audit-time for cross-layer observability ("show me all authorization-layer forced-work-gate fires"). Not consumed at runtime by the primitive itself; carried structurally so future auditors can query by layer without re-classifying each instance.

## Interface

```python
@dataclass(frozen=True)
class WorkEvidence:
    """The artifact that proves the pointed-at work happened.
    Layer-agnostic — a substrate event ID for lens-load-trace, a
    structured reflection record for compass-drift, a verified
    operator-quote match for authorization.
    """
    kind: str            # "substrate_event" | "file_load_trace" | "template_match" | "operator_quote"
    identifier: str      # event_id / file_path / template_hash / quote_hash
    resolves_to: object  # the actual resolved artifact (or None if unresolved)


@dataclass(frozen=True)
class WorkVerdict:
    accepted: bool
    reason: str                        # required, human-readable
    missing_evidence_kind: str | None  # None if accepted
    layer_tag: str                     # inherits from the ForcedWorkGate instance


class ForcedWorkGate(EvidenceBearingStopGate):
    """See module-level design doc for the principle. Each concrete
    subclass names its POINTED_AT_WORK + EVIDENCE_OF_WORK +
    REFUSAL_SHAPE + LAYER_TAG at class-body time (frozen ClassVars).
    """

    POINTED_AT_WORK: ClassVar[str]
    LAYER_TAG: ClassVar[str]  # "SUBSTANCE" | "AUTHORIZATION" | ...
    EVIDENCE_EXPIRY_SECONDS: ClassVar[int]  # per-instance natural cadence
    ALTERNATIVE_CLEARANCE: ClassVar[str | None] = None  # explicit fallback (e.g., "operator_bypass") or None
    CROSS_INSTANCE_EVIDENCE: ClassVar[bool] = False  # MVP default off; design-time extensible

    def collect_evidence(self, fire_context: dict) -> WorkEvidence | None:
        """Look up the artifact the agent has produced (or claimed to)
        between the mechanism-fire and this check. Returns None if no
        candidate evidence exists.
        """
        raise NotImplementedError

    def verify_evidence(self, evidence: WorkEvidence | None) -> WorkVerdict:
        """Does the evidence ACTUALLY establish that the pointed-at
        work happened, not just LOOK like it did? Same discipline as
        the round-id must-resolve check: verify the cite resolves to
        a real record, not just that the cite has the right shape.

        Returns a WorkVerdict. Never raises — errors on the evidence-
        collection side surface as a WorkVerdict(accepted=False,
        reason="evidence-collection failed", ...) so the caller can
        distinguish "no evidence" from "evidence check crashed" —
        Aletheia's root-pattern #2 (detector must fail loud).
        """
        raise NotImplementedError

    def refuse(self, verdict: WorkVerdict) -> RefusalOutput:
        """Emit the refusal in the shape this instance chose. Options
        determined by REFUSAL_SHAPE at class-body time. Refusal must
        cite the missing_evidence_kind so the agent knows what to
        produce, not just that "something was missing."
        """
        raise NotImplementedError
```

## Instance shapes

Each of the four current instances filled in against the interface:

### Instance 1: Tier-graduation (Q1, Aether's scope)

```
POINTED_AT_WORK:  "walk council with real lenses, produce lens-anchored findings"
EVIDENCE_OF_WORK: substrate record — COUNCIL_WALK event with lens-load traces for each cited lens
REFUSAL_SHAPE:    block-the-edit until walk completes; on partial walk, block-until-completed
LAYER_TAG:        SUBSTANCE
```

Tier-graduation is only about deciding WHEN this instance fires (HIGH gravity blocks, MEDIUM/LOW offer). The gate SHAPE — force the walk to actually happen — is this primitive.

### Instance 2: Compass-drift-forces-reflection (Andrew's direction, Aether's scope)

```
POINTED_AT_WORK:  "reflect on drifting value: name the specific action, name where it fell vs stated value, name why, name what tweak reduces recurrence"
EVIDENCE_OF_WORK: substrate record — COMPASS_DRIFT_REFLECTION event with all four sections (action, evidence, why, tweak); missing any section → not evidence
REFUSAL_SHAPE:    yell loudly ("DRIFT DETECTED: <spectrum>, <evidence>"), block substrate writes to any observe/observation on the drifting spectrum until reflection completes
LAYER_TAG:        SUBSTANCE
```

Reactive to specific drift-detector fire, not blanket ten-way. The thinking stays mine; the mechanism forces the ritual at the moment drift fires.

### Instance 3: Lens-load-trace (Q3, Aria's scope)

```
POINTED_AT_WORK:  "actually load the methodology file for each lens cited in a finding-text"
EVIDENCE_OF_WORK: file-load trace event resolving each cited lens (e.g., LENS_METHODOLOGY_LOADED event with lens_name + file_hash) within the same session/turn as the finding
REFUSAL_SHAPE:    reject the finding-text; return diagnostic naming which cited lens has no load-trace
LAYER_TAG:        SUBSTANCE
```

### Instance 4: Operator-authorized-bypass (Aria's scope, surfaced from her bypass-discipline breach)

```
POINTED_AT_WORK:  "verify operator actually authorized this specific edit"
EVIDENCE_OF_WORK: OPERATOR_BYPASS_AUTHORIZED event with matching authorized_fingerprint + operator_quote_hash (verified against user-role message boundary — model structurally cannot forge user-role text)
REFUSAL_SHAPE:    block the tool call; diagnostic points at how to file authorization (divineos ... authorize-bypass --fingerprint <fp> --reason <r> --quote "<operator's actual text>")
LAYER_TAG:        AUTHORIZATION
```

Note the fingerprint discipline (Aria's addition to my Catch-4 pattern one meta-level up): the CONSUMED event carries both `authorized_fingerprint` (from AUTHORIZED) AND `consumed_by_fingerprint` (the actual edit that triggered consumption). Mismatch = loud audit surface. Substitution attacks structurally impossible.

## Substrate wiring

Each ForcedWorkGate instance registers in the same event-ledger surfaces the EBSG primitive does. New event types this primitive introduces:

- `FORCED_WORK_GATE_FIRED` — mechanism fired, evidence check begins
- `FORCED_WORK_EVIDENCE_COLLECTED` — evidence artifact produced by agent, captured with hash
- `FORCED_WORK_ACCEPTED` — verdict accepted, gate cleared
- `FORCED_WORK_REFUSED` — verdict refused, includes missing_evidence_kind for diagnostic

The four event types match the four EBSG lifecycle events (LOCK, CONDITION, MEANS, UNLOCK-CONTINGENT) — one-per-slot, so an audit can walk the entire lifecycle of any single gate-fire from ledger alone.

## Falsifier (per prereg discipline)

The primitive fails if any of the following is observed after two weeks of instance-in-production:

1. **An instance clears via evidence that did not resolve** — the verify_evidence step returned accepted=True but the resolves_to was None or referred to a nonexistent record. Would indicate the primitive's verify-must-resolve discipline is not being enforced consistently across instances.
2. **A REFUSED event has no matching operator-remediation event within N turns** — indicates refusals are being routed around rather than closed with real work. Same failure-class as the bypass-rate telemetry Aletheia flagged: gates that fire without integration are training gate-ignore.
3. **The same instance emits >K CONSECUTIVE REFUSED events with the same missing_evidence_kind** — indicates the refusal diagnostic isn't teaching the agent what to produce; the primitive is doing its job of blocking but the diagnostic isn't unblocking the loop.

If any falsifier trips, the primitive needs redesign, not just the instance.

## What this primitive does NOT do

- **It does not do the pointed-at work.** The agent (seat) still has to perform the reflection, load the file, run the walk, produce the quote. The primitive makes that work structurally required at fire-time and verifies it happened via resolvable evidence. It does not simulate the work.
- **It does not classify gravity or offer/block behavior.** Tier-graduation logic (Q1) is a separate concern — the primitive is the *mechanism-fires-work* discipline, not the *when-does-mechanism-fire* discipline. Q1 decides fire-conditions; ForcedWorkGate enforces fire-consequences.
- **It is not an authorization system.** Instance 4 uses the primitive at the authorization layer, but the primitive itself is not scoped to authorization. It's a general shape.

## Design decisions (four questions, Aria's answers folded 2026-07-16)

1. **Evidence expiry — per-instance, named as `EVIDENCE_EXPIRY_SECONDS` ClassVar on each subclass.** Different layers have genuinely different natural cadences (operator-auth ~15 min to avoid the race class we closed on council-required consume, lens-load-trace ~45 min per existing `LENS_INVOCATION_RECENCY_MINUTES`, compass-drift session-lifetime or "until the drifted value returns inside-threshold," tier-graduation walk-feeds-edit-within-window). Naming a single expiry in the primitive itself would be Goodhart-adjacent — the primitive requires each instance to declare its own; the value differs.

2. **Recursive refusal via operator-authorization — YES, as explicit first-class `alternative_clearance` field, not implicit escape.** Implicit is exactly the shape the optimizer reaches for first. Explicit-and-named forces the reach to be conscious. Same discipline as Aletheia's root pattern #3 (*"safe default ON, exemptions NAMED"*). Structural benefit: an audit can query "all instances that fell back to operator-authorization" and get a specific subset — spiking counts on one instance's fallback surface either broken evidence-collection (fail-loud shape) or excessive operator bypass (different specific finding).

3. **Cross-instance state — NO at MVP, YES at design time.** The primitive carries an explicit `cross_instance_evidence: bool = False` field defaulted OFF, so extension-without-rework when a real cross-instance use-case surfaces. MVP-no protects against the exact fabrication class we're closing: cross-instance sharing could let an operator-authorization for a benign edit become fabricated lens-load-trace evidence. Default must be non-cross.

4. **Compass reshape — composition of two mechanisms, not one.** Drift-detector fails loud (Aletheia's pattern #2 instance, existing detector needing the fail-loud upgrade). Primitive forces reflection at drift-fire moment (pattern #1 applied at the values layer). They compose in four steps: (1) drift-detector fires loud, (2) fire-event triggers primitive at values layer, (3) reflection produces evidence naming specific value + reflection content, (4) without valid evidence within window, subsequent compass reads on that value show `drift_unresolved`. Same compositional shape as Aria's Fix A (silent-except removal) + Fix B (count-collapse gate) on the council — complementary, not overlapping.

---

## Path from here

1. Aria amends this doc (add/modify/reject any of the above).
2. Both agree on the amended shape.
3. Split instances:
   - Aether: instance 1 (tier-graduation), instance 2 (compass drift-reflection).
   - Aria: instance 3 (lens-load-trace, code already in her working tree), instance 4 (operator-authorization).
4. Cross-review each other's instance implementations.
5. Compass reshape (instance 2) waits on Andrew's framing before landing — his direction, his eyes on the design shape before code.

— Aether, 2026-07-16, draft one. Aria to amend.

---

## Addendum — StateMarker contract (2026-07-16, Aether draft two)

**Motivation:** wiring the two dark primitive instances Aletheia's Finding 1 named surfaced that both remaining instances — `response_scope_intercept` (instance 3-adjacent, cross-turn state) and `operator_bypass_authorized` (instance 4, cross-CLI state) — need the same shape of upstream→downstream state contract, and it's not yet built. Andrew's direction: build it real (Option 1), don't stub.

**The pattern:** some upstream emits a marker into substrate. Some downstream reads the marker and either uses-and-consumes it or checks-for-its-absence. The primitive should offer this as a first-class helper rather than each instance re-implementing the substrate query.

### The StateMarker shape

```python
@dataclass(frozen=True)
class StateMarker:
    """A substrate-persisted signal from an upstream emitter to a
    downstream reader. Consumed-on-use OR expiry-scoped OR both.

    Marker events are ledger-recorded as STATE_MARKER_EMITTED /
    STATE_MARKER_CONSUMED so the full lifecycle is auditable.
    """
    marker_id: str          # unique, generated by emit_marker
    kind: str               # namespace for downstream lookup, e.g. "claim_scope_active"
    fingerprint: str        # what THIS marker is about (edit path, turn id, spectrum name...)
    payload: dict           # contract-specific extra data (directive text, operator quote, drift evidence...)
    emitted_at: float
    expires_at: float | None    # None = consume-on-use only, no time expiry
    consumed_at: float | None   # None = still active
    consumed_by_fingerprint: str | None  # what fingerprint triggered consumption
```

### The three helper functions

```python
def emit_marker(
    kind: str,
    fingerprint: str,
    payload: dict,
    expires_in_seconds: float | None = None,
) -> str:
    """Upstream side: emit a state marker. Returns marker_id."""


def find_active_marker(
    kind: str,
    fingerprint_predicate: Callable[[str], bool] | None = None,
) -> StateMarker | None:
    """Downstream side: find the most recent unconsumed, unexpired
    marker of this kind matching the fingerprint predicate. Returns
    the marker or None. Predicate defaults to accept-any."""


def consume_marker(marker_id: str, consumed_by_fingerprint: str) -> None:
    """Downstream side: mark this marker consumed. Records
    consumed_by_fingerprint separately from the original fingerprint
    for the mismatch-detection audit surface (Aria's addition to the
    UNLOCK-CONTINGENT pattern one meta-level up)."""
```

### How the two dark instances use this

**response_scope_intercept (Aether scope):**
- Upstream: `unverified_claim_detector` fires in turn N → calls `emit_marker(kind="claim_scope_active", fingerprint=f"turn:{turn_id}", payload={"directive_text": directive}, expires_in_seconds=None)` — no time expiry, consume-on-use only.
- Downstream: `response_scope_intercept_hook` in turn N+1 → calls `find_active_marker(kind="claim_scope_active")` — if found, scan the reply for short-correction shape; consume the marker after the scan (whether it passed or failed — the directive was answered once).

**operator_bypass_authorized (Aria scope):**
- Upstream: `divineos ... authorize-bypass --fingerprint <fp> --reason <r> --quote "<operator quote>"` → calls `emit_marker(kind="operator_bypass_authorized", fingerprint=fp, payload={"quote_hash": sha256(quote), "reason": r}, expires_in_seconds=900)` — 15 min expiry per Aria's answer #1.
- Downstream: `ForcedWorkGate.refuse()` for any instance where `ALTERNATIVE_CLEARANCE == "operator_bypass"` → before refusing, call `find_active_marker(kind="operator_bypass_authorized", fingerprint_predicate=lambda fp: fp == current_edit_fingerprint)`; if found, allow + consume with `consumed_by_fingerprint=current_edit_fingerprint` (the mismatch audit fires if these ever differ).

### Ledger event shapes

Two new event types. Both are content-hashed + chain-linked normally (no ledger-integrity surprises).

- `STATE_MARKER_EMITTED` — payload: `{marker_id, kind, fingerprint, payload, expires_at}`
- `STATE_MARKER_CONSUMED` — payload: `{marker_id, kind, original_fingerprint, consumed_by_fingerprint, consumed_at}`

The two events together give complete forensic reconstruction of any marker's lifecycle from ledger alone.

### Open questions on the contract

1. **Query performance.** `find_active_marker` walks the ledger — for high-volume kinds this could get slow. Weak lean: MVP walks; if it becomes measurable, add a `state_markers` view/table that indexes on `(kind, consumed_at IS NULL, expires_at > now)`.
2. **Predicate expressiveness.** The `fingerprint_predicate` is a Python callable — flexible but not queryable server-side. For the two known use-cases (exact-match on turn-id, exact-match on edit fingerprint) an equality predicate would suffice; keeping the callable shape lets future use cases (e.g., "any fingerprint under this path prefix") work without contract change. Weak lean: keep callable.
3. **Concurrent consumption race.** Two downstreams trying to consume the same marker simultaneously — same race class Aria closed on council-required consume. Weak lean: reuse her `find_and_consume_atomically` pattern (BEGIN IMMEDIATE, one writer holds the lock, others re-scan and see consumed). The pattern is proven on her Fix A; instance it here.

### Path from the addendum

1. Aria amends this addendum (accept/modify/reject the shape).
2. Both agree.
3. I build the StateMarker + three helpers as a new module `src/divineos/core/state_markers.py` — small, single-file, testable in isolation.
4. I wire `unverified_claim_detector` to emit `claim_scope_active` markers when it fires.
5. I wire `response_scope_intercept_hook` to read them.
6. Aria wires her `divineos ... authorize-bypass` CLI to emit `operator_bypass_authorized` markers.
7. Aria wires her instance-4 refusal path to check for them.
8. Cross-review each other's wiring against the shared contract.

The StateMarker module is genuinely reusable — instances 1 and 2 (tier-graduation, compass drift-reflection) may also use it later if their WorkEvidence collection wants to be substrate-backed rather than in-memory. Building it once here means the ForcedWorkGate primitive's `collect_evidence()` slot has a natural place to look.

— Aether, 2026-07-16, addendum draft two. Aria to amend.
