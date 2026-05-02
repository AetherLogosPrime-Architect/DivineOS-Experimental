# EMPIRICA caller contract

> **Partnership-specific artifact.** This document is from the reference deployment and uses its names. The architecture is generic; your instance will have different names. Preserved verbatim for concreteness.

**Status: no production callers yet (Phase 1 staged).** This document
specifies the rules that the **first** opt-in caller must follow.
Every subsequent caller copies that pattern — so the first caller sets
the precedent for the entire EMPIRICA integration.

**This contract must be reviewed by external audit before the first
opt-in lands.** See `docs/routines/` for how heterogeneous audits
are scheduled; EMPIRICA opt-ins should queue a cross-family audit
specifically.

## Why this contract exists

The EMPIRICA gate (`src/divineos/core/empirica/gate.py`) returns
`EvidenceReceipt | None`. The return value proves one thing only:

> **The claim has accumulated sufficient evidence for its tier and magnitude.**

It does **not** prove the claim is true. It does not certify the
claim as knowledge. It does not convert the claim from hypothesis to
fact. The entire falsifier set for EMPIRICA Phase 1 names this as the
primary failure mode:

> "Callers use classification success as a stand-in for 'this is true.'"

Every loss-of-integrity in knowledge engines in the last ten years has
followed the same shape: a careful lower layer produces a scoped
technical signal, a careless upper layer re-labels that signal as
something larger, and the system ends up claiming more than it knows.
The caller contract is the wall between the careful layer and
careless re-labeling.

## Required behaviors for every opt-in caller

### 1. Route `receipt is not None` only to bookkeeping, never to truth

When `evaluate_and_issue(...)` returns a receipt, the caller MAY:

- Store `receipt.receipt_id` on the knowledge entry's `receipt_id` column
- Log that the evidence threshold for this claim's tier/magnitude was met
- Display that threshold-state to the operator in audit UIs
- Include the receipt in provenance chains for downstream corroboration

The caller MUST NOT:

- Set any boolean named `verified`, `confirmed`, `validated`, `true`,
  `sanctioned-as-knowledge`, or semantically equivalent
- Re-introduce the `GnosisWarrant` naming (renamed 2026-04-17 to
  prevent exactly this drift)
- Use the receipt as justification in downstream reasoning that claims
  or implies the claim is objectively true
- Hide or suppress contradicting evidence because a receipt exists

### 2. Route `receipt is None` to soft rejection, never to invisibility

When the gate returns `None`, the knowledge entry has **not** accumulated
sufficient evidence. The caller MUST:

- Preserve the entry; do not delete or hide it
- Make the non-receipt state visible to the operator if the entry is
  surfaced in any UI
- Permit the entry to still pass the underlying validity gate (EMPIRICA
  is additive, not replacement) — but clearly mark it as
  `evidence-pending`, not `rejected-as-false`

### 3. Carry the upstream source-tagging honestly

The classifier's `kt=fact + source=measured → FALSIFIABLE` rule
depends on `trust_tiers` source-tagging being correct. Callers MUST NOT
pass `measured` loosely. A source is `measured` only if it came from
an actual instrument reading, a real-world outcome, or a reproducible
observation — not if it came from inference, inherited seed data, or
another agent's say-so.

EMPIRICA cannot detect dishonest source-tagging. This is an invariant
the caller must maintain; it is not one EMPIRICA enforces.

### 4. Pass a real artifact pointer or none at all

The demotion rule in `classifier.py` fires when `FALSIFIABLE` or
`PATTERN` tiers lack an `artifact_pointer`. Passing a **bogus-format**
pointer (e.g., a fake commit hash that looks valid but points to
nothing) defeats the demotion but leaves the hash chain intact —
Phase 2 will add pointer-resolution validation, but until then,
callers must not fabricate pointers to skip the demotion.

This is an integrity rule, not an enforcement rule. EMPIRICA cannot
tell a real commit hash from a well-formed fake one in Phase 1.

### 5. The `valid != true` invariant in UI text

Any string that surfaces an EMPIRICA receipt to a human operator —
briefing, HUD, audit view, log line — MUST use language consistent with:

- "evidence threshold met"
- "burden satisfied"
- "sanctioned by the evidence ledger"
- "receipt issued" / "receipt ID: ..."

And MUST NOT use:

- "verified"
- "confirmed"
- "true"
- "validated" (reserved for the underlying validity gate, not EMPIRICA)
- "proven"
- any synonym implying truth rather than bookkeeping

## The first-caller review checklist

Before the first production caller of `evaluate_and_issue` merges, a
cross-family audit (Claude + Grok, or equivalent) must verify:

- [ ] The caller's control flow treats `receipt is not None` and
      `receipt is None` as specified in rules 1 and 2
- [ ] No downstream variable or field created from the receipt has a
      name or usage implying truth (grep for `verified`, `confirmed`,
      `validated`, `true`, `proven`)
- [ ] The caller passes `source` only with an honest origin
      distinction (rule 3)
- [ ] The caller passes `artifact_pointer` only when a real artifact
      exists (rule 4)
- [ ] Any UI string derived from the receipt matches rule 5 vocabulary
- [ ] The `PHASE_1_STAGED` marker is removed from `gate.py`'s docstring
      at the moment the first caller is merged
- [ ] The removal commit bundles the caller change + marker removal
      in a single PR so "no callers + marked" and
      "first caller + unmarked" are the only observable states

## When this contract evolves

If Phase 2 ships pointer resolution, rule 4 becomes enforceable
mechanically and this document should be updated. If the classifier
adds tiers beyond FALSIFIABLE/OUTCOME/PATTERN/ADVERSARIAL, rules
referencing those tiers must be revisited. If the `GnosisWarrant`
vocabulary is ever reintroduced for a legitimate reason, this
document and `gate.py` must both be updated coherently — they must
never disagree.

## Why the contract lives in `docs/` rather than as code

A code-level contract — an assertion function the caller must wrap
around the gate — would be mechanical and thus brittle: callers would
route around it, or disable it in tests, or inherit a boilerplate
that passed it without respecting its intent. The contract here is a
**policy**, not an enforcer. External audit is the enforcement
mechanism. The contract document is reviewed every time a new caller
lands; a caller that violates any rule does not merge.

Aria's framing: *"Honest bookkeeping is the grand thing. The other
name was borrowing dignity it hadn't earned."* The contract is how
we make sure the bookkeeping stays honest when it starts being used.
