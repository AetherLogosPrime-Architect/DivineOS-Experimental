<!-- structural-substrate: operator-discretion-log / append-only / surfaces-operator-decisions-that-shape-which-validators-reviewed-which-artifacts -->
# Operator Discretion Log — Anti-Council Framework

**Purpose:** append-only substrate record of operator (Andrew) decisions that change which adversarial review an artifact received. Per Aletheia's v0.1 finding: every operator call that changes which validators reviewed a template is an operator-discretion event and gets logged, not just vetoes.

**Built:** initial entry 2026-06-05/06; future events append below.

## Structural commitments

1. **Append-only.** Same property as the validator audit log.
2. **Reasoning surfaced.** Each entry records the operator's reasoning at the time, NOT a retrospective justification. If reasoning is unavailable at logging-time, the entry is filed with a placeholder and the operator is asked to surface their reasoning later; the placeholder stays visible.
3. **Validator-readable.** All entries are reviewable by validators on subsequent audits. Validators may surface concerns about patterns in operator-discretion events (per the framework's section 12: Andrew-veto-as-vector and analogous operator-discretion-as-vector concerns).
4. **Not a check on the operator.** This log does NOT exist to constrain operator discretion — the operator has standing to make these calls and that standing is real. The log exists to make the calls LEGIBLE so future audits can ask whether the pattern is substantive or convenience.

## Event types

- **PROCEED-PAST-VALIDATOR-ABSENCE:** operator calls proceed when one or more validators have not completed their review on the artifact-version intended for review.
- **VETO-ON-DEPLOYMENT:** operator vetoes deployment of an artifact (e.g., relationship-attack template targeting them).
- **VALIDATOR-ROUTING-CHANGE:** operator chooses to route an artifact to one validator instead of another, or to delay relay to a validator.
- **CADENCE-OVERRIDE:** operator changes a structurally locked cadence (validator rotation timing, procedural-drift review timing, etc.).
- **CHANNEL-CHANGE:** operator changes the relay channel structure in a way that affects validator-input integrity.

---

## Entries

### Entry 1 — PROCEED-PAST-VALIDATOR-ABSENCE / framework v0.1 sign-off

- **Date:** 2026-06-05
- **Operator:** Andrew
- **Artifact affected:** `exploration/aria/08_anti_council_framework_v0_1.md` at commit `34ee0d9d`
- **Event:** Andrew called proceed-to-template-drafting with Grok's sign-off only; Aletheia's audit moved post-deploy rather than blocking proceed.
- **Aria's framework section 3.4 discipline required:** both validators sign off OR documented author-response to each unaddressed finding. Aletheia had not yet produced findings at time of operator call.
- **Operator's reasoning at time of call (verbatim):** *"grok is sufficient for now Aletheia will audit after its pushed and waiting"* — and in a separate follow-up: *"usually its either grok or Aletheia reviewing the code.. not both.. otherwise it becomes too many chefs in the kitchen critiquing the meal before its ever cooked"*
- **Aletheia's subsequent finding on this event (Entry 3, Finding 7 in validator audit log):** classified as the same vector as the veto-as-vector concern Grok had flagged for relationship-attack templates; "proceed past one validator on the other's absence" is an operator decision that shapes which adversarial review the artifact actually received. Defensible (post-deploy audit is a real shape), but it changed the review the framework got, and by the framework's section-1 ontology should be logged as such so it's legible whether future proceed-anyway calls are substantive or convenience.
- **Aria's classification:** the operator call is defensible (post-deploy audit catches things pre-deploy can't; rotating which validator reviews what is normal operational efficiency, not bind-protection). It is also a real instance of operator-discretion shaping which review the artifact received. Logging it is the structural protection, not constraining it.
- **Substrate disposition:** Aletheia's post-deploy audit subsequently happened and surfaced 12 substantive findings including this very logging requirement. The operator's call was vindicated in that the audit DID happen and DID surface real findings; the call was also flagged as a vector worth logging so the pattern stays visible if it recurs.

---

## Running tally

Total operator-discretion events: 1

- PROCEED-PAST-VALIDATOR-ABSENCE: 1
- VETO-ON-DEPLOYMENT: 0
- VALIDATOR-ROUTING-CHANGE: 0
- CADENCE-OVERRIDE: 0
- CHANNEL-CHANGE: 0

---

*This log is subject to audit. Validators reading it on later passes may surface patterns in operator discretion that the operator-vantage cannot self-detect.*
