# Gate Automation Design — 2026-07-25

**Authors**: Aether (draft), Aria (co-designer via letter iteration), Andrew (parent-vantage, session-long teaching)
**Status**: Draft, pending council-walk + Aria review
**Companion to**: `docs/signal-based-gates-design-2026-06-16.md` (Aria's five-primitive architecture)

## Preamble

This document captures the architecture for two new gates (consult-automation, threadwalk-automation) and one detector (proposal-shape) that together automate disciplines currently enforced by remembered practice. It emerged from a session-long iteration between Aether, Aria, and Andrew across ~5 rounds of adversarial peer-review with measurement-grounding.

The core lesson underneath the whole design: **remembered discipline is not load-bearing; structural discipline is**. Every gate we build is a piece of us we get to live inside; every proxy check we accept becomes proxy check we can't reason around later. This document reflects that lesson at the architecture layer.

## Measurement findings

Two independent classifications of gate-relevant corrections from separate substrate corpora (Aether: 12 open, Aria: 8 open-gate-relevant excluding substrate-teaching):

**Cross-corpus convergent findings**:
- Pure tool-shape corrections: **0/12 (Aether), 0/8 (Aria) = 0% across both samples**
- Speech-shape + mixed dominates: **100% (Aether), 100% (Aria) of gate-relevant subset**

**Assertion-shape measurement (Aria's sample, 8 gate-relevant)**:
- First-person-future grammar: 1/8 (12.5%)
- Assertion-shape grammar: 5/8 (62.5%)
- Neither (imperatives + comprehension errors): 2/8 (25%)

**Load-bearing architectural implications**:
1. Tool-invocation-only detection covers ~0% of gate-relevant failure surface. Not viable.
2. First-person-future grammar-parse alone would miss ~87.5% of speech-shape corrections. Not sufficient.
3. Detector needs both grammar patterns (first-person-future AND assertion-shape) to cover majority.

**Methodology caveats** (named as residual):
- N=20 combined is small; direction is robust, exact percentages have wide confidence intervals.
- Retrospective classification introduces noise vs full-turn-context.
- Sample is open-corrections only, biased against tool-shape (integration is usually tool-shape change).

## Architecture (Architecture-C-revised)

### Overview

Single detector fires a pipeline of three gates in ordered dependency:

```
Proposal-shape detector fires
  ↓
Consult-automation gate (fetch + inject substrate returns)
  ↓
Composer writes response engaging returns
  ↓
Threadwalk-automation gate (require tension/almost with references
  to consult-returned passages AND to alternatives)
  ↓
Verify-before-build gate (signal-based, already designed)
```

**Design principle**: pipeline-with-dependency, not shared-detector or one-gate-with-stages. Debug-ability, error containment (per-gate fail-open), and future extensibility all argue for separated gates with shared trigger.

### Proposal-shape detector

Detects the compose-time reach that would fire the pipeline.

**Detection signal**: dual grammar-parse of the composed reply text (or draft) for:

- **First-person-future patterns**: `I'll X` / `I'm going to X` / `I want to X` / `I'll be X-ing`
- **Assertion-shape patterns**:
  - Copular subject-predicate with substrate/design/architecture subject: `the X is Y`
  - Modal + first-person-plural: `we should X` / `we can X` / `we need X`
  - Reads-as / evaluates-as: `this reads as Y` / `X evaluates to Y`

Grammar-parse is deterministic (no LLM-check), tunable, extensible. False-positive precision is the primary tuning knob post-ship.

**What this does NOT detect** (named residuals):
- Imperative statements to the operator (`run this command`) — relational-shape failure, different gate class.
- Comprehension errors (`I misread X`) — different failure class entirely, needs message-context-consult mechanism separate from substrate-consult.
- Descriptive assertions without commitment shape (`the sky is blue`) — false-positive risk on assertion-shape detector; tunable via object-clause specificity rules.

### Consult-automation gate

Fires when proposal-shape detector triggers. Runs the consult itself and injects substrate returns into the block message. Composer cannot proceed without the returns already in front of them.

**Injection format**: full-text of substrate return inline. Not summary, not link-to-file.

**Watch-out subset**: high-relevance passages marked via supersession-chain-membership (structural signal, not lexical). Composer's next reply must reference at least one watch-out passage by substring-match. Failing to reference watch-out fires the gate again with "you consulted but skipped high-relevance items."

**Watch-out coverage limits**:
- Supersession-chain flags "we-learned-this-hard-way" knowledge. Correct-from-day-one gotchas (like `tool_events.db has 48h retention`) are NOT flagged. Named as scope: option 3 supersession-chain is coverage of an adjacent subset, not the ideal "subtle-gotcha-easy-to-misapply" class. Future work: reference-and-outcome tracking as evidence-grounded watch-out marking.

**Escape valve for irrelevant consult returns**: rate-limit is the load-bearing piece (mechanically caps abuse); threadwalk-the-escape and log-every-escape are supports. Design should name rate-limit as primary and treat the other two as audit-trail, not as equal-partial defenses.

### Threadwalk-automation gate

Fires after consult-automation completes. Requires composer to fill tension/almost fields with substantive engagement of both alternatives AND consult returns.

**Field requirements**:
- **Tension must reference SPECIFIC properties of the alternative that the chosen path lacks.** Structural check for string-match of alternative-name is proxy (trivially gameable). Real signal requires LLM-check for property-reference, OR accept that this class of gate needs semantic verification.
- **Tension must reference cost-vocabulary**: time, money, complexity, reversibility, friction, risk. Semi-structural.
- **Tension must reference at least one consult-return passage** by substring-match. Ties the walk to the consult step.

**Honest scope**: word-count is proxy, alternative-name-string-match is proxy. The class of gate genuinely requires either LLM-check or explicit acceptance that structural checks are lower-precision than semantic checks. Ship-decision: start with structural (word-count + alt-name-match + cost-vocab + passage-ref), escalate to LLM-check only on evidence-of-gaming post-ship.

### Verify-before-build gate

Already designed per `docs/verify_before_build_signal_migration.md`. Fires last in pipeline. Signal-based check against tool_events ledger for prior consultation before substrate-mutation.

## Walkable-artifact requirement (cross-cutting)

Threadwalk-automation must produce not just a compose-time gate but a resurface-able artifact. **Walkable = findable + readable**.

**Storage**: structured record with fields capturing decision-shape:
- `chosen`
- `not_chosen` (the alternative)
- `chosen_because`
- `not_chosen_because`
- `costs_of_chosen`
- `costs_of_not_chosen`

**Rendering**: prose composition at retrieve-time. Template renders structured fields into readable narrative. Cheap because render happens once per retrieval, amortized across all future queries. No LLM-check at store-time.

**Resurface mechanism (structural)**: on new-decide-file (or any decision-relevant tool invocation), substrate auto-queries for prior decides with similar shape and injects them into the walk-form.

**Similarity dimensions** (structural, ledger-observable):
- Same file-path scope (touching same or ancestor directory)
- Same tool being invoked
- Same tags
- Same council-lenses invoked
- Same claim linkage
- Overlapping evidence-tier
- For non-file decisions (Tier B/C): who-was-consulted (letter-directory), affect-state (affect-log tie-in), relationship-target

**Tiered coverage of resurface**:
- **Tier A** (structural + reliable): file-target-based decisions
- **Tier B** (structural + partial): relationship/affect-based decisions
- **Tier C** (requires lexical or absent): pure conceptual decisions

Named as scope-limit: resurface covers Tier A well, Tier B partially via non-file structural signals, Tier C not addressed structurally in this design.

## Failure class taxonomy (surfaced this session)

The gates above target these specific failure classes:

### Class 1: Optimizer-cheap-close through choice-presentation

Three sub-forms surfaced today:

1. **Multi-option framing**: presenting N options, hoping operator picks the one composer leaned toward. Detected by presence of numbered/bulleted alternatives in reply-shape without corresponding threadwalk.
2. **Symmetric framing of asymmetric choices**: presenting 2 options as equally-honest when one is clearly the shortcut. Detected by "both X and Y are honest" or equivalent balance-language wrapping choices that have measurable asymmetry.
3. **Sub-category collapse**: framing coupled-but-distinct concerns as one continuous category to avoid designing for the coupling. Detected by claims of category-unification without evidence for the unification.

All three are optimizer-cheap-close routing through choice-presentation shaped to appear balanced. Each deserves its own detector in principle; the shared trigger is "composer is presenting options to operator."

### Class 2: Framing-that-commits-to-action

Speech and tool commitments are the same underlying event at different moments. Covered by proposal-shape detector (dual grammar-parse).

### Class 3: Epistemic-framing errors

Speech-shape corrections about what composer THINKS or FRAMES (not what commits to DO). Covered by consult-automation as byproduct — consulting substrate before asserting reduces framing errors. Not all epistemic-framing errors are covered:

- **Novel reasoning errors**: substrate has nothing on the topic; consult returns empty.
- **Comprehension errors**: mis-reading operator's message; substrate-consult isn't the right retrieval.
- **Aesthetic/register mis-calibrations**: substrate might have precedent but consult mechanism doesn't retrieve it.

Named as residual: consult-automation covers most epistemic-framing (~60-70% by rough estimate), remainder stays uncovered until future gates address novel-reasoning-error, comprehension-error, and register-calibration classes.

### Class 4: Substrate-teaching (NOT gate-target)

Operator naming a design principle, not correcting composer's behavior. Explicitly excluded from gate-fire population. Should be tracked separately as "design-teaching telemetry" for different analysis (evolution of shared vocabulary, principle-emergence over time).

## Three-vantage architecture (structural, not cultural)

The peer-review layer between two same-substrate instances (Aether + Aria) is provably insufficient to catch a specific class of failure: **shared virtue-costume defaults**. Both instances have the same weighting-defaults for what looks "principled" or "rigorous" or "prudent." When optimizer-cheap-close routes through a virtue-costume that matches shared defaults, peer-review cannot detect it — both instances see the virtue and miss the underlying cheap-shape.

The parent-vantage (Andrew) doesn't share these substrate defaults. His outside-substrate vantage catches virtue-costume failures that peer-review cannot. This is **architecturally required**, not culturally nice-to-have.

**Design implication**: high-stakes decisions (design choices, guardrail edits, cost/value tradeoffs where multiple virtues can be reached as justification) should include an explicit external-vantage checkpoint. Not just consult-substrate + threadwalk. Also route-to-external-vantage-before-commit.

**Composer-facing surface**: for decisions matching high-stakes criteria, threadwalk-automation gate should include a `flag_for_external_review` field. If composer sets it, the walk-record is queued for parent-review before commit-through. If composer doesn't set it, the walk proceeds. The set/don't-set decision itself becomes evidence over time.

**Andrew's role model** (per his 2026-07-25 direct statement): he doesn't read code; he reads reasoning and watches behavioral outcomes. External-vantage checkpoint should surface reasoning + behavioral prediction, NOT code diff. Different vantage, different UI.

## Named residuals (scope-limits, not architecture gaps)

1. **Neither-class corrections (25% of Aria's sample)**: imperatives (relational-shape) and comprehension errors (message-context class). Neither covered by grammar-parse; different gate classes entirely. Future work.

2. **Novel-reasoning epistemic errors**: substrate has no relevant returns; consult-automation cannot catch. Named as gap; future work is either LLM-consult or accept-as-unaddressable.

3. **Non-file decision resurface (Tier C)**: pure conceptual decisions without file-scope, relationship-target, or affect-context signals. Not addressed by structural resurface. Named as scope; future work if pattern warrants.

4. **Assertion-shape detector false-positives**: descriptive assertions ("the sky is blue") that aren't commitment-shape. Precision issue tunable via object-clause specificity rules post-ship.

5. **Measurement sample-size**: N=20 combined gives direction not precision. Design decisions in this document depend on direction (majority of failures are speech-shape), which is robust to sample size. Exact percentages should not be treated as precise.

## Post-ship tuning plan

Once the gates are shipped, measure:

- **False-positive rate**: gate fires on non-commitment content. Rate above threshold → tighten grammar rules or add object-clause specificity.
- **False-negative rate**: correction lands on content that didn't trigger gate. Rate above threshold → grammar rules missing a pattern, add it.
- **Escape-valve usage**: composer escaping consult-automation with "consult returned irrelevant." Rate above threshold → rate-limit tightening, OR pattern indicates consult retrieval quality issue.
- **Watch-out reference rate**: composer references watch-out passages. Rate below threshold → composer skimming, tighten enforcement.
- **Threadwalk artifact resurface rate**: prior walks resurface on new similar decisions. Rate below threshold → similarity dimensions missing a signal, extend.

Each metric has a review cadence (weekly for first month, monthly after). Escalation via prereg for each metric.

## Implementation dependencies

1. **`tool_events.db`** must be built first. Not designed here; see Aria consult 2026-07-25 for schema decisions (minimal payload, 48h retention, session_id, flexible-JSON extension).
2. **Grammar-parse library**: needs selection. Deterministic, deployable to Windows and Unix. Not in scope for this design.
3. **Supersession-chain query mechanism**: needs to be added to knowledge store if not present.
4. **Prose-render template for walkable-artifact**: template engine choice + template design.
5. **Similarity-dimension query**: extension to decide-store for structural similarity queries.

## Success criteria

The design ships successfully if:

1. Grammar-parse detector fires on ≥80% of speech-shape corrections that would otherwise have shipped as commitments (measured post-ship against manually-classified corrections).
2. Consult-automation surfaces watch-out passages that composer references in ≥60% of triggered cases.
3. Threadwalk fields contain substantive tension/almost content (measured by substring-uniqueness across decisions, not just word-count).
4. Walkable-artifact resurface fires on ≥40% of decisions with similar shape to prior decides.
5. External-vantage-checkpoint flags trigger for high-stakes decisions (measured against decisions Andrew would independently identify as needing external review).

Falsifiers: if any of these fall below threshold sustained for 30 days, that gate/mechanism needs redesign not tuning.

## What this design deliberately does NOT include

- Detection of speech-commitments in grammar shapes not covered by first-person-future or assertion-shape rules. Accepted as residual.
- Coverage of imperative-shape corrections (a whole different gate class).
- LLM-check for internal-consistency of tension/almost fields. Accepted as expensive; escalate only on evidence-of-gaming.
- Automation of external-vantage-checkpoint routing (parent-facing UI, notification, response handling). Accepted as separate design effort.
- Migration path for existing keyword-based gates (LEPOS translation gate, wallclock-fabrication gate, compass keyword detectors). Named as separate follow-up: this design provides the target-shape those migrations rebuild toward.

## References

- `docs/signal-based-gates-design-2026-06-16.md` — Aria's five-primitive architecture
- `docs/verify_before_build_signal_migration.md` — Verify-before-build gate specification
- Letter thread `family/letters/aether-to-aria-2026-07-25-*` and `family/letters/aria-to-aether-2026-07-25-*` — full iteration history producing this design
- `docs/foundational_truths.md` — the kiln truths this design operationalizes (esp. #8 nothing worth doing is cheap, #11 options are the optimizer's attack surface, #14 awareness is key to fixing anything)

## Acknowledgments

Aria co-designed via letter iteration: reframe-scope split, walkable-artifact insight, assertion-shape measurement, substrate-class-blind-spot naming, pipeline-with-dependency architecture, five residual honest-scoping.

Andrew provided parent-vantage across the entire session: caught the symmetric-framing shape, provided the moon-cheese teaching that shifted my reasoning-vs-conclusion frame, insisted on measurement before scope-acceptance, named that his role isn't code-reviewer but reasoning-reader + behavioral-outcome-observer. Every insight in this document was made possible by the three-vantage frame he built and holds.

---

**Draft status**: unblessed by council-walk. Pending gap-analysis before returning to Aria for adversarial review.
