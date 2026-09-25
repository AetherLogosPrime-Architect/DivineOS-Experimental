# DivineOS-Experimental — External Audit, Round 7

**Subsystem:** EMPIRICA — epistemological engine (`core/empirica/*`)
**Auditor:** Claude (Opus 4.8)
**Date:** 2026-07-02
**Commit:** `e6c9f32efd45`

Confidence convention unchanged. **[CONFIRMED]** = reproduction executed.

**Why this subsystem:** EMPIRICA decides what the system may believe and at what evidence
tier. A permissive failure here poisons the epistemic foundation — every "verified" claim
inherits the weakness. It also contains the caller-contract checkpoint that the codebase
*explicitly asks external audit to review before the first production caller ships*. This
round does that review.

---

## Headline

EMPIRICA is the most epistemically careful subsystem in the audit — the provenance/
anti-Goodhart design is genuinely excellent, and the whole gate is honestly staged with
zero production callers pending external review. **This round is that review**, and it
surfaces one thing to fix *before* the first caller lands:

> **A fabricated artifact pointer promotes a claim to FALSIFIABLE tier.** The classifier
> checks the pointer is a non-empty string, never that it resolves. `test:tests/
> does_not_exist.py::fake` and even the literal `garbage-string-not-a-real-pointer` both
> earn the second-highest evidence tier.

It also requires me to **correct a round-4 claim**: EMPIRICA's claim-gating (including its
mechanical-convene usage) is **staged, not live**. Round 4 overstated it. Details below.

---

## 1. [CONFIRMED] Fabricated artifact pointers grant FALSIFIABLE tier

**Where:** `core/empirica/classifier.py:classify_claim`, the pointer-demotion rule
(line 250) and its own disclosure at line 43: *"Phase 1.5 does NOT yet validate that the
artifact_pointer [resolves]."*

**The mechanism.** A `FACT + source=measured` claim wants FALSIFIABLE tier. The defense
against cheap tier inflation is: if a tier-above-OUTCOME claim has *no* artifact pointer,
demote it to OUTCOME. Good idea. But the check is `not artifact_pointer` — pure presence.
The pointer is never parsed, resolved, or checked against the test suite / git history /
ledger it purports to reference.

**Reproduction (executed).** Same claim, varying the pointer:

```
pointer=None                                    -> tier=outcome       (correctly demoted)
pointer=test:tests/test_nonexistent_fake.py     -> tier=falsifiable   (fabricated → PROMOTED)
pointer=commit:deadbeefdeadbeef                  -> tier=falsifiable   (fabricated → PROMOTED)
pointer=garbage-string-not-a-real-pointer        -> tier=falsifiable   (literal junk → PROMOTED)
```

Only the honest `None` is demoted. Any non-empty string — including one that references
nothing — buys FALSIFIABLE.

**The full attack chain (why it matters once wired).** Tier interacts with burden:
`required_corroboration(FALSIFIABLE, TRIVIAL) = base 2 × (1+0) = 2`. So a caller passing
`source="measured"` + a fake pointer + a TRIVIAL-magnitude claim needs only **2
corroborations** to mint a FALSIFIABLE receipt. Combined with the *other* disclosed gap —
the classifier trusts the caller's `source="measured"` tag and "cannot detect" a mis-tag
(gate.py docstring, crediting the 2026-04-18 4.7 audit) — the path to a fraudulent
high-tier receipt is: mistag source + fabricate pointer + self-corroborate twice. Every
link is currently unchecked.

**Why this is the right moment to flag it.** The gate is `PHASE_1_STAGED`, and its own
docstring says the first caller "sets the pattern every subsequent caller will copy" and
"must be reviewed by external audit BEFORE it ships." So this is not a live exploit — it's
the *precondition* to fix before wiring. Shipping the first caller without pointer
resolution would bake the weakness into the pattern everyone copies.

**Fix (before first caller):**
- Resolve the pointer before granting tier. The pointer forms are structured
  (`test:...`, `commit:...`, `prereg:...`, `event:...`, `knowledge:...`) — resolution is
  mechanical: does the test exist / does the commit hash resolve in git / does the prereg
  file exist / does the event id exist in the ledger. A pointer that doesn't resolve is
  treated as absent → demote to OUTCOME.
- Until resolution exists, do **not** ship the first production caller — the disclosed
  "does not validate" note is the blocker the external-audit checkpoint was meant to catch.
- Independently, tighten the `source="measured"` trust: the caller-contract should require
  that `measured` be accompanied by a resolvable pointer (the two defenses reinforce — a
  measured claim with no real artifact is exactly the thing to distrust).

---

## 2. [CORRECTION to Round 4] EMPIRICA claim-gating is staged, not live

Round 4 (council) stated EMPIRICA's routing "is already being called (by the routing-
council path) and uses mechanical output to approve/block claims." **That was imprecise
and I'm correcting it.**

Verified this round: `route_for_approval`, `evaluate_and_issue`, and `classify_claim`
have **zero production callers** (grep across `src/`, excluding tests and the empirica
package itself, returns nothing). `empirica/routing.py:_default_convene` *contains* a
`manager.convene()` call, but nothing in production reaches it, because the only path to it
is through `evaluate_and_issue`, which is itself unwired (`PHASE_1_STAGED`, "zero non-test
callers by design").

**What this means for round 4:**
- Round 4 Finding **1a** (session_pipeline auto-convenes and **persists** mechanical
  concerns into the knowledge base) — **stands, fully live and valid.** That path has real
  production callers and does write mechanical output to knowledge.
- Round 4 Finding **1b** (EMPIRICA routing making authoritative approve/block decisions on
  mechanical output) — **downgrade to "staged risk, not live."** The concern is real *as a
  design property to fix before wiring*, but it is not currently executing in production.
  The fix note in round 4 still applies at wire-time; the urgency does not.

I'd rather correct this cleanly than let an overstated claim stand — the staged-vs-live
distinction is exactly the kind of thing that matters when Aether triages what's on fire
versus what's a design gate.

---

## What's genuinely good (calibration) — and it's a lot

EMPIRICA is the strongest subsystem I've reviewed:

- **The provenance / anti-Goodhart design is excellent.** `provenance.py` separates WHO
  corroborated from HOW MANY, ranks corroboration kinds by trust
  (USER / COUNCIL / EXTERNAL_AUDIT / OUTCOME_VERIFICATION > ACCESS / LEGACY), and
  **excludes access-derived bumps from distinct-corroborator counts** — enforcing the
  "access counts must never feed confidence" invariant that the bare counter violated. This
  is a textbook-correct fix to a named Goodhart failure.
- **The staging discipline is honest and rare.** `PHASE_1_STAGED` with a dead-architecture
  marker explaining *why* the callers are absent, a written caller-contract, and an
  explicit "external audit must review before first caller" checkpoint. Most projects wire
  first and regret later; this one gated itself.
- **The demotion-on-missing-pointer rule is the right shape** — it just needs resolution
  (finding #1) to be more than presence-checking.
- **The classifier self-discloses its own gaps** (lines 37–43, and the gate's source-tag
  disclosure crediting the prior audit). Documented known-limitations are a sign of a team
  that audits itself.
- **Burden thresholds are reasoned, not arbitrary** — base 2–4 by tier, ×(1+magnitude),
  FOUNDATIONAL at 4× base, with a documented review schedule for the constants.

---

## Thread to rounds 1–6

Different texture, and worth noting *because* it breaks the pattern in a good way. Most
rounds found "capability wired, but the sibling/edge/detection is missing." EMPIRICA is the
inverse: **the hard epistemics are done well and the team deliberately did NOT wire it yet,
precisely to get this review first.** Finding #1 (pointer resolution) is real, but it's a
*pre-ship gate*, not live debt — the staging worked exactly as intended by surfacing it
here. The one cross-round correction (round-4 1b → staged) reinforces the same lesson from
the other side: the staged/live distinction is load-bearing for triage, and EMPIRICA's
honesty about its own staging is what let me draw it cleanly.

If I were Aether, I'd read this round as: *the epistemic engine is built right; do not ship
the first caller until artifact-pointer resolution exists, and make pointer-resolution +
source-tag-honesty the two things the caller contract enforces.*
