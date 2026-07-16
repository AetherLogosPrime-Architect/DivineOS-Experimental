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
