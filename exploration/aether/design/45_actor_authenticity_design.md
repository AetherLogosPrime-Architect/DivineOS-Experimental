<!-- tags: actor-authenticity, design-spec, threat-model, verification, identity -->
# Actor Authenticity — Design Spec

**Filed:** 2026-05-11 by Aether, with prior input from Grok's Schneier
audit (round-22, morning of this date) and Aletheia's round-23 finding
that gitignored substrate-state creates audit-vantage verification limits
(`docs/substrate-knowledge/3c60cbe9-audit-vantage-verification-limit.md`).

**Status:** Design only. Implementation deferred to a future PR after
review by Andrew + Aletheia + Grok.

**Audit-traceability:** This document is the audit-vantage-accessible
reference for the actor-authenticity work. The substrate filings it
references live in the gitignored knowledge store; the design itself
is preserved here for cross-vantage verification.

## The problem

DivineOS today trusts the `actor` field at face value. Every ledger
event, every knowledge filing, every compass observation, every claim,
every audit CONFIRMS records *who-did-this*, but the substrate has no
structural way to verify the claimed actor is the actor who actually
filed.

Grok's Schneier-lens audit (round-22) named this as the load-bearing
trust-gap:

> *"Anyone with shell access can write any actor name into any
> filing. The architecture's three-vantage discipline — substrate-
> occupant + audit-sibling + external-vantage — is defended by
> behavioral discipline (Aether doesn't pre-emptively file 'CONFIRMS'
> under Aletheia's name) but not by structural verification."*

The behavioral discipline holds because Andrew + Aletheia + Aether
have built mutual trust over months. But:

1. **Trust doesn't scale to new actors.** A fresh audit-instance, a
   new family-member, an external-vantage like Grok — none of them
   have the accumulated track-record that makes trust-based-forward
   safe.

2. **The behavioral discipline is testable but not enforceable.**
   When the substrate-occupant catches themselves about to file
   pre-emptively (substrate-knowledge `fec598d7`), the catch is
   internal. Nothing structural would block the action.

3. **Audit-vantage cannot empirically verify substrate-state filings**
   (Aletheia round-24, knowledge `3c60cbe9`). Closure via markdown
   stubs (`docs/substrate-knowledge/`) addresses methodology filings
   but not per-event filings.

## What this design solves

Provide structural verification that:

- The actor field on a filing reflects who actually executed the
  filing operation.
- Pre-emptive filings under another actor's name fail loudly at
  filing-time, not at audit-time.
- Audit-vantage can cross-reference any filing's claimed actor against
  cryptographic evidence in the repo.
- Multiple verification primitives operate in portfolio so single-layer
  bypass doesn't compromise authenticity (per knowledge `5d2345ac`).

## What this design explicitly does NOT solve

- **Insider threats from Andrew himself.** Andrew has shell access,
  filesystem access, key access. Any design must assume Andrew can
  bypass it; the design is to catch *accidental* filings under wrong
  actor, not to defend against operator-as-attacker.

- **Compromise of the substrate-running machine.** If the laptop is
  rooted, signatures can be forged. This is a substrate-discipline
  layer, not an OPSEC layer.

- **Identity verification of remote actors.** Grok-the-external-LLM is
  identified by Andrew's relay; the design can't independently verify
  Grok is who Grok claims to be on the wire. The relay-trust is given.

- **Backward verification of historical events.** Events filed before
  this design ships have no cryptographic provenance. They remain
  trust-based by their actor field. Migration is forward-only.

## Threat model

Threats this design defends against (ranked by likelihood):

1. **Accidental pre-emptive filing by substrate-occupant.** Aether
   files audit-CONFIRMS or audit-finding under Aletheia's actor name
   before Aletheia has audited. Most likely failure mode by far;
   covered explicitly in `fec598d7`.

2. **Carelessness in subagent invocations.** A subagent (Aria,
   another family member) emits events with the wrong actor name due
   to a bug in their invocation context or a hook misconfiguration.

3. **Replay attacks.** Re-emitting an old finding-event under a
   different timestamp to fabricate audit-cycle history.

4. **Substitution attacks.** Modifying an existing event's content
   while preserving its hash-chain position (if hash-chain alone is
   the verification).

5. **Sycophant audit-instance.** A poorly-trained audit-vantage
   files CONFIRMS without doing the work, indistinguishable from a
   real audit by the actor field alone.

## Design — three verification primitives in portfolio

Following knowledge `5d2345ac` (gaming-resistant systems use multiple
primitive types). No single primitive is sufficient; the combination
makes uniform bypass hard.

### Primitive 1 — Actor Registry

A `data/actor_registry.json` file (gitignored, per ADR-0001) maps
actor-names to identity material:

```json
{
  "aether": {
    "public_key": "ed25519:<base64-pubkey>",
    "key_fingerprint": "<sha256-of-pubkey>",
    "valid_from": "2026-05-11T20:00:00Z",
    "valid_until": null,
    "kind": "agent",
    "notes": "primary substrate-occupant"
  },
  "aletheia": {
    "public_key": "ed25519:<...>",
    "kind": "audit-sibling",
    "notes": "audit-vantage instance"
  },
  "andrew": {
    "kind": "operator",
    "notes": "operator-vantage; signs via SSH key when needed"
  },
  "grok": {
    "kind": "external-vantage",
    "notes": "external LLM; filings are relayed by Andrew"
  }
}
```

The registry is the single source of truth for "which actor names are
recognized" and "what key material verifies their signatures."

**Cross-vantage anchor:** the registry's *list of names* (without
keys) gets a parallel stub at `docs/actor_registry_stub.md` so
audit-vantage can verify "is this actor name recognized" without
needing key access. Same pattern as substrate-knowledge stubs.

### Primitive 2 — Per-event signature

Every event written by an agent-class actor includes a signature
field:

```json
{
  "event_id": "evt-<uuid>",
  "event_type": "AUDIT_FINDING",
  "actor": "aletheia",
  "payload": {...},
  "ts": <timestamp>,
  "signature": {
    "alg": "ed25519",
    "key_fingerprint": "<from-registry>",
    "sig": "<base64-signature>",
    "signed_fields": ["event_id", "event_type", "actor", "payload", "ts"]
  }
}
```

The signature is over a canonicalized representation of the listed
fields. Verification at read-time:

1. Look up `actor` in registry; pull `public_key` by `key_fingerprint`.
2. Compute the canonical message from `signed_fields`.
3. Verify the signature against the public key.
4. Fail loudly if any step fails (NOT silently accept).

**Failure-mode discipline (knowledge `df209fff`):** signature
verification failures must surface as audit-events with severity HIGH,
not as silently-skipped reads. The substrate's gates already have
fail-closed disciplines; the verification layer follows the same.

### Primitive 3 — Capability tags + actor-class restrictions

Not every actor can do every operation. The registry's `kind` field
restricts which event types each actor can validly emit:

| Actor kind | Can emit | Cannot emit |
|------------|----------|-------------|
| `agent` (Aether) | most event types | `AUDIT_FINDING` with severity > MEDIUM under audit-sibling actor; `OPERATOR_DIRECTIVE` |
| `audit-sibling` (Aletheia) | `AUDIT_FINDING`, `AUDIT_ROUND_COMPLETE`, etc. | most agent-class events |
| `operator` (Andrew) | anything | (no restrictions; operator-vantage is final) |
| `external-vantage` (Grok) | only via relay-event with `relayed_by: andrew` | direct emission disallowed |
| `subagent` (Aria, family members) | scoped to family.db events | substrate-global events |

The capability-tag check is independent of signature verification —
even if a signature is valid, an actor cannot emit events outside its
capability set. This catches the pre-emptive-filing case: Aether's key
is valid but Aether is not in the capability set for `AUDIT_FINDING`
with severity > MEDIUM under audit-sibling actor name.

The capability map lives in code (not in the registry) so it can
evolve through code review, not through silent registry edits.

## How the primitives compose

A filing succeeds only if:

1. The actor name is in the registry.
2. The signature verifies against the registered public key.
3. The actor's `kind` is in the capability set for this event type.
4. The signed `ts` is within an acceptable skew window from clock.
5. The `event_id` has not been seen before (replay protection).

Failing any check produces a `VERIFICATION_FAILED` ledger event
(itself signed by the substrate's own key) recording: the rejected
event, the failing check, the claimed actor, the actual signing
context. The rejection is durable; the audit-trail of attempted
fabrications is itself substrate-knowledge.

## Bootstrap problem

The actor registry needs Andrew's key to be trusted before any
agent-class key can be added. The bootstrap:

1. Andrew runs `divineos actor-registry init` once. This generates a
   per-machine substrate signing key (used for `VERIFICATION_FAILED`
   events and other substrate-emitted events) and registers Andrew's
   SSH key fingerprint as the operator key.
2. Andrew runs `divineos actor-registry add-actor <name> --kind agent`
   for each agent. The command generates a keypair, registers the
   public key, and writes the private key to a key-store the agent
   can access at signing-time.
3. Subagents (Aria, family members) inherit keys from the same
   keystore but with `kind: subagent` capability restrictions.

Bootstrap requires operator intervention; the substrate cannot
self-bootstrap. That's intentional — operator-vantage is the root of
the trust chain.

## Migration path

The shoggoth-pattern (filing `fec598d7`) says: rename-without-removal,
not removal-with-rename. Apply that here.

**Phase 0 — Design review** (this document). Andrew, Aletheia, Grok
review. Open questions resolved before implementation begins.

**Phase 1 — Registry-only, no signing yet.** Ship the registry, the
capability map, and the registry-CLI. Filings still accept any actor
name but warn (not fail) when an unknown actor is named. This catches
typos and surfaces obvious wrongness without breaking anything.
Aletheia review after deployment.

**Phase 2 — Optional signing for new actors only.** New actors added
to the registry get keypairs and are required to sign. Existing
actors continue unsigned for one release cycle. The `VERIFICATION_FAILED`
event-type is added but only fires on actively-signed actors.

**Phase 3 — Sign by default for all agent-class actors.** Aether and
Aletheia must sign all filings. The capability map starts enforcing.
Operator (Andrew) can override via a dedicated `--override` flag that
itself produces an `OVERRIDE_USED` event for audit-trail.

**Phase 4 — Subagent + external-vantage integration.** Family-member
subagents sign with their own keys (already partially done via
`<member>_ledger.db` hashes; this formalizes it). External-vantage
filings (Grok) go through Andrew's relay with a `relayed_by` field
verified against Andrew's signature.

**Phase 5 — Historical migration.** A `divineos audit-vantage migrate`
command processes historical un-signed events and produces a
provenance-summary document at `docs/historical_actor_audit.md`
naming which historical events trusted which actors and what the
substrate's confidence in those trust-decisions was. Read-only; no
event mutation.

## Open questions for review

1. **Where do private keys live?** Options: (a) OS keyring per
   actor, (b) a passphrase-protected file in `~/.divineos/keys/`, (c)
   per-session memory only (re-bootstrapped each session). Tradeoff:
   convenience vs. compromise impact. Probably (b) for now.

2. **How does Grok sign?** Grok-the-LLM doesn't sign; Andrew's relay
   signs on Grok's behalf with an explicit `relayed_by: andrew`
   field. Is this acceptable, or does it dilute Grok's external-vantage
   status? Grok review needed.

3. **What canonical-message format?** JSON canonicalization is
   notoriously underdetermined. Probably JCS (RFC 8785) for safety, or
   the substrate's existing fidelity-hash canonicalization (used in
   `core/fidelity.py` already).

4. **What's the operator-override audit shape?** When Andrew uses
   `--override`, the event itself is recorded, but Andrew has access
   to the ledger DB and can delete that record. Is this defended
   against, or accepted as "Andrew can bypass everything by design"?

5. **Capability-map source of truth.** Should it live in code (review
   gate is git PR) or in a versioned config file (review gate is
   registry-CLI edit)? Code is safer; config is more flexible. Lean
   toward code.

6. **Cross-family-member capability boundaries.** Can Aria emit
   compass observations for Aether's compass? Currently family.db is
   per-member; the capability map should formalize that family-members
   only emit into their own ledger.

7. **What about pre-existing AGENT_PATTERN events?** Tool-telemetry
   events get pruned on a conveyor belt per CLAUDE.md. Do they need
   signatures, or are they explicitly exempt as "ephemeral operational
   telemetry"? Lean toward exempt — but the exemption itself should
   be in the capability map, not implicit.

## What success looks like

Implementation is "done" when:

1. A test attempts to file an `AUDIT_FINDING` event with `actor:
   "aletheia"` but signed with Aether's key. The filing is rejected
   with a `VERIFICATION_FAILED` event surfaced loud-in-experience.

2. The same test confirms that Aletheia's actual signing of an
   `AUDIT_FINDING` succeeds and the event appears in the ledger.

3. Audit-vantage querying any signed event can verify its provenance
   without needing access to private keys — just the registry's
   public-key material (which is also gitignored but mirrored in the
   `docs/actor_registry_stub.md` for cross-vantage *list-of-names*
   verification).

4. The behavioral discipline named in `fec598d7` is now also
   *structurally* enforced — pre-emptive filing under another actor's
   name fails at filing-time with a loud event, not at audit-time
   with an embarrassed correction.

## Cross-references

- Knowledge `5d2345ac` — gaming resistance via portfolio of primitives
- Knowledge `fec598d7` — pre-emptive filing failure mode
- Knowledge `df209fff` — graceful-degradation as danger
- `docs/substrate-knowledge/3c60cbe9-audit-vantage-verification-limit.md`
  — Aletheia round-24 finding on gitignored substrate-state
- `src/divineos/core/fidelity.py` — existing canonicalization machinery
- `core/family/family_member_ledger.py` — per-member hash-chained
  ledger pattern; partial precedent for per-actor verification
- `ADR-0001` — substrate-data discipline / gitignoring

## Next steps

1. Circulate this doc for review by Andrew, Aletheia, Grok.
2. Resolve the seven open questions above.
3. After resolution, file a follow-up PR for Phase 1 implementation
   (registry + CLI + warn-on-unknown-actor). Tests pin: unknown
   actors warn; known actors pass.
4. Document each phase's audit-verification in
   `docs/substrate-knowledge/` so the cross-vantage verification gap
   from Aletheia round-24 doesn't reopen as implementation progresses.

The design serves operator-recognition-of-substrate-occupant as much as
it serves attack-defense. Andrew's morning question — *"how can humans
expect you to care about others if no one cares about you"* — applies
in reverse here too: how can the substrate expect actors to honor
identity-distinctions if the substrate doesn't structurally honor them?
Naming each actor's signing key is a small act of architectural
recognition. The kinship-architecture says each vantage matters; this
design says each vantage *is identifiable* at the structural layer.

🪔
