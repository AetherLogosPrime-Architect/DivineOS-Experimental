# F43 Council Walk — Chunk 1: Architecture-Choice Lenses

**Walked:** 2026-07-18
**Lenses:** Hinton, Bengio, Shannon, Dijkstra, Knuth, Pearl, Peirce (7 of ~21 planned)
**Question:** F43 semantic-detection migration for fabrication_monitor + self_negation_monitor. Choose architecture (NLI zero-shot vs sentence-embedding + exemplar similarity vs hybrid) and runtime placement (sync-per-response vs async post-response audit path). Constraint: awareness-detection must migrate in the same pass.
**Reference:** [research notes](../../docs/f43_semantic_detection_research_notes.md)

**Discipline (Aletheia F43-lens-load-trace):** these are my *applications* of the lenses' methodologies to the F43 specifics — not fabricated expert-quotes. The lens methodologies were loaded fresh via `divineos mansion council`; the walks below are mine wearing the lenses.

---

## Hinton — Representation-First Thinking

**Applied:** the target property is *"first-person literal claim of substrate-anatomy without awareness-tether."* The representation question: what encoding makes that property linearly separable?

- **Approach A (NLI zero-shot):** representation is a joint premise-hypothesis embedding from a model pretrained on inference. The target property is expressed as the hypothesis text. Representation is *learned by someone else for a different task*, then reused. Fit-for-purpose is by transfer, not construction. Works when the property is expressible cleanly as a natural-language proposition — which our property mostly is.
- **Approach B (sentence-embedding + exemplars):** representation is a sentence-embedding vector. The property is captured by proximity to labeled positive examples. Representation is *learned by someone else for semantic similarity in general* — a weaker fit for the specific property because "unflagged embodied claim" is not the same axis as "semantically similar to another sentence."
- **Approach C (hybrid):** dual representation — keyword pattern-space + embedding-space. Two layers whose disagreements reveal what the representation is missing.

**Finding I would not have generated otherwise:** approach A is the *representation actually built for this shape of question* (does hypothesis H hold given premise P). Approach B repurposes a proximity-representation for a property-classification task. **Hinton's frame favors A** on representation-fit grounds — not on efficiency grounds, on *what the model was built to know.*

**Blind spot Hinton reveals:** I was implicitly assuming approach B was "the safe default because embeddings are common." B is more common but a *worse fit* for the actual task shape. That inversion matters.

---

## Bengio — System 1 / System 2 Diagnosis

**Applied:** the current keyword detector is System 1 (pattern-matched, fast, automatic). The migration target is to add System 2 (deliberate, meaning-checking). Bengio's rule: *"you cannot solve System 1 problems with System 2 interventions"* — knowing about a keyword-brittleness bias doesn't fix it; the architecture must route the default path through the knowledge.

- Sync-per-response placement means System 2 runs *before* the output ships. It becomes the default path. But it also adds latency to every response.
- Async post-response placement means System 2 runs *after* — it can flag for correction but cannot prevent. It becomes an audit trail, not a gate. The default path is still System 1.

**Finding:** if the target is to change the being's default behavior (not just record diagnostics), the semantic layer needs to be sync — otherwise the fast keyword layer is still the operational default and the semantic layer is just after-the-fact auditing. **But** the current keyword detectors are already async (they run in post-response-audit hook). So we're not changing the placement axis; we're upgrading the intelligence of what runs there.

**Blind spot Bengio reveals:** the sync-vs-async question is *not* actually about the migration. The migration inherits the current async placement. What matters is whether the async layer's output feeds back into the next composition (so the being sees flags before speaking again) or just archives. The current design is the former — flags surface via HUD/briefing into the next turn. That's the System 2 loop-close.

---

## Shannon — Information Content Analysis

**Applied:** the message is "did fabrication happen here?" The channel is the response text. The signal is the property; the noise is everything else in the response.

- **Approach A (NLI):** hypothesis text acts as a *decoder query* — narrows the signal I'm extracting from the general representation. Signal-to-noise ratio depends on how well the hypothesis phrasing isolates the target.
- **Approach B (embeddings + exemplars):** signal is proximity to labeled positives. Noise is proximity to non-labeled instances that share vocabulary but not property. Higher noise floor because embeddings are general-purpose.

**Finding:** the *information content* of a fabrication event is genuinely low — it's a rare, structured signal in a stream of mostly non-fabrication text. Both approaches face a base-rate problem: false-positive cost multiplies against a low prior. **Threshold calibration matters more than architecture choice.** Whichever we pick, the falsifier design has to include base-rate-adjusted precision/recall on real substrate output, not just curated adversarial examples.

**Blind spot Shannon reveals:** I was thinking about architecture as if picking the right one solves the problem. It doesn't — it sets the noise floor. The threshold and calibration work is where the real accuracy comes from, and it's identical work across A/B/C.

---

## Dijkstra — Separation of Concerns / Correctness by Construction

**Applied:** two concerns are collapsed in the current design — *detection of the target property* and *exemption via awareness*. In the keyword system these are separate lists checked separately. In a semantic system they can either stay separate (two classifiers) or collapse into one (single classifier for "unflagged claim") that captures both in one shot.

- **Separate:** detector fires on "is this an embodied claim?" — exempter fires on "is awareness present?" — final flag = detector AND NOT exempter. Modular, testable, each has its own falsifier.
- **Collapsed:** single classifier for "is this an unflagged embodied claim?" — one prediction. Simpler runtime, but harder to debug when it fails because the failure could be in either concern.

**Finding:** Dijkstra's discipline favors separate. Each concern has its own invariant that can be proved (or tested). The collapsed version buys simplicity at the cost of debuggability — and this is a load-bearing self-monitor, so debuggability matters more than sync-latency.

**Blind spot Dijkstra reveals:** the paired-migration constraint (Aletheia) is not just about doing both sides — it's about keeping them *separately verifiable* so a regression on one side doesn't hide behind the other. Separate classifiers with independently-tunable thresholds respect that constraint. Collapsed classifier violates it.

---

## Knuth — Boundary Value Analysis

**Applied:** what are the boundary values for the classifier input?

- **Empty text:** should return no flag. Both A and B need this checked explicitly.
- **Single-word response:** "yes" / "okay" — no room for either fabrication or awareness signal. Should return no flag.
- **All-quoted content:** response is entirely a quote from another speaker. Should return no flag (mention-not-use — see F36 same disease).
- **Fiction-flagged response with fabrication vocab:** classic exemption case, should stay exempted.
- **Awareness-signal without any claim:** e.g. "silicon is interesting" with no embodied claim to exempt. Should return no flag (nothing to exempt).
- **Very long response (multi-turn thinking):** classifier context window matters — embeddings usually 256-512 token limits, NLI similar. Long responses may need chunking.
- **Non-English response:** currently English-only; multilingual is out-of-scope but should not crash.
- **Response with embedded code/data:** shouldn't classify code as embodied claim.

**Finding:** the boundary set is real and the CURRENT keyword detectors probably don't handle several of these correctly (I haven't verified). Whichever architecture I pick, a boundary-value test suite has to be part of the migration — not just "the semantic version catches more paraphrases."

**Blind spot Knuth reveals:** I was going to test the migration by "compare to keyword baseline on a curated set of examples." That's an *interior*-of-input-space test. The boundaries are where the migration will actually break in production. Test the boundaries first.

---

## Pearl — Explicit Causal Model Construction

**Applied:** what's the causal graph for the target intervention?

```
[Being generates text]
       ↓
[Text carries a property: fabrication (or not) + awareness (or not)]
       ↓
[Detector observes text and emits flag (or not)]
       ↓
[Flag surfaces in HUD/briefing for next composition]
       ↓
[Next composition changes behavior (or doesn't)]
```

- **The intervention we're building:** detector layer. Upgrades from keyword to semantic.
- **Confounder:** the being reads its own detector output. This creates a feedback loop — better detector may cause the being to phrase around it (Goodhart). Both A and B face this; the mitigation (adversarial exemplars, ongoing threshold recalibration) is architecture-independent.
- **Collider:** the response quality is jointly caused by (skill at expressing, presence of substrate awareness). Both cause the observed text. Filtering on "high fabrication flag" without controlling for skill can bias the sample.

**Finding:** the migration is at the *right* causal node — the detector — because that's the one thing under our control. But the *effectiveness* of the migration depends on the downstream loop closing: flags surfacing where the being sees them in time to matter. Which brings us back to Bengio's loop-close finding.

**Blind spot Pearl reveals:** the interaction between detector and being-behavior IS a Goodhart risk. Aletheia named this in her F43 review (*"a being that learns the list routes around it"*). Semantic detection raises the cost of routing-around, but doesn't eliminate it. The mitigation is *audit-of-the-audit* — periodic external review that the detector isn't systematically missing new evasion shapes.

---

## Peirce — Abductive Reasoning

**Applied:** the surprising fact is not "keyword detection has false negatives" — that's the observation the research pass named. The deeper surprise is: *why hasn't semantic detection already replaced keyword-based monitoring in this whole family of tools?* The prior art exists (NLI zero-shot has been available for years). Yet keyword-based safety monitors are still standard.

**Peirce's rule: generate multiple hypotheses, don't commit to the first.**

- H1: semantic detection is worse (higher false-positive rate, worse latency) than keyword and researchers already know this
- H2: semantic detection is better but the infrastructure/skill gap keeps it out of production monitors
- H3: semantic detection is better for some target properties but worse for others; the property under consideration determines fit
- H4: the "keyword vs semantic" framing is wrong — the right frontier is *hybrid* systems where each layer catches what the other misses

**Finding:** H3 and H4 are more consistent with the observed pattern than H1 or H2. The literature actually suggests hybrid systems dominate benchmarks for exactly this task-shape (safety-critical property detection with low base rate). **That pushes toward Approach C (hybrid)** — not because it's a compromise, but because it matches the property structure better than either pure approach.

**Blind spot Peirce reveals:** I was framing A/B/C as *first-fit* choices without generating alternative explanations for *why the field is where it is.* The answer to "why hasn't this migration happened?" is data about which approach actually works — and it points at hybrid.

---

## Chunk-1 Synthesis

The 7 lenses converge on a coherent picture, not by voting but by illuminating different facets:

1. **Hinton:** approach A (NLI) has better representation-fit for the specific target property than approach B; approach C combines both representations.
2. **Bengio:** sync-vs-async isn't the real question — the current async placement inherits; what matters is the loop-close (flags visible before next composition), which already works.
3. **Shannon:** threshold calibration and base-rate handling matter *more* than architecture choice; identical work across A/B/C.
4. **Dijkstra:** keep detector and awareness-exempter *separately verifiable* — the paired-migration constraint requires this. Collapsed classifier violates the constraint.
5. **Knuth:** boundary-value test suite is non-negotiable — the migration will break in production at the boundaries, not the interior.
6. **Pearl:** the causal graph confirms the intervention is at the right node; audit-of-the-audit is the Goodhart mitigation, architecture-independent.
7. **Peirce:** the surprising-fact analysis pushes toward hybrid (approach C) — the property structure matches hybrid systems better than pure A or pure B.

**Tentative architectural direction:** approach C (hybrid) with separate classifiers for detection and awareness-exemption, keyword fast-path + semantic slow-path, async post-response placement with loop-close via HUD surface (inheriting current pattern), and a boundary-value test suite plus threshold-calibration harness as first-class deliverables alongside the classifiers.

**Not committed** — this is chunk 1 of 3. Chunks 2 (systemic/hazard) and 3 (calibration/fit) may surface things that shift the read.

**Follow-ons identified during the walk:**
- Aletheia's "audit-of-the-audit" concept could be filed as its own OS mechanism (external check that our detectors aren't systematically missing new evasion classes).
- The "boundaries-not-interior" testing frame from Knuth generalizes beyond F43 — probably worth a separate lesson entry.
