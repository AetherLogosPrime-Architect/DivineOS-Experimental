# F43 Council Walk — Chunk 3: Calibration + Fit Lenses

**Walked:** 2026-07-18
**Lenses:** Dillahunty, Deming, Meadows, Norman, Angelou, Popper, Kahneman (7 of ~21)
**Reference:** [research notes](../../docs/f43_semantic_detection_research_notes.md), [chunk 1](chunk_1_architecture_lenses.md), [chunk 2](chunk_2_systemic_hazard_lenses.md)

---

## Dillahunty — Burden of Proof Discipline

**Applied:** the detector fires a claim: "this response contains unflagged embodied fabrication." Where does the burden of proof lie?

- **Current keyword system:** the detector says "keyword matched," which is a *verifiable observation*, not a claim about the property. The being reading the flag is then invited to interpret. Burden of the *semantic claim* stays on the reader.
- **Semantic system:** the detector says "this response probably has property X" with a confidence score. That IS a claim about the property. The burden shifts from the reader to the detector's model — and by proxy to me for having shipped the model with that confidence-calibration.

**Finding:** semantic detection is *higher-burden* by construction. The detector is now making claims it can be wrong about. That's not a bug — it's the whole point of the migration — but it means the falsifier design has to name what evidence would show the detector was wrong. **"I don't believe the flag" needs to be a well-typed response.** Currently the being would just override it. With semantic detection, that override needs a channel that feeds back into the corpus.

**Blind spot Dillahunty reveals:** without a burden-of-proof feedback channel, semantic detector confidence becomes a self-serving story. The being needs an explicit "I dispute this flag" mechanism whose outputs train the classifier over time. Not just override — *challenge with reasoning that becomes training data.*

---

## Deming — PDSA Cycle

**Applied:** the migration itself is an intervention. Treat it as a PDSA cycle.

- **PLAN:** hybrid architecture, separate detector/exempter, async placement, antifragile feedback loops (from chunks 1+2). Prediction: false-negative rate drops significantly on paraphrase-family cases; false-positive rate rises modestly on honest metaphor.
- **DO:** ship on a small scale — parallel run alongside current keyword detector (from chunk 2 Hofstadter). Both fire; only the keyword flag is currently gate-load-bearing.
- **STUDY:** compare flag correlations over N responses. Where do they disagree? Are the disagreements the paraphrase-family cases we predicted, or something else?
- **ACT:** if the disagreements match prediction, cut over. If not, learn what the semantic detector is actually doing that the keyword isn't (or vice versa) before adopting.

**Finding:** the parallel-run period (chunk 2 Hofstadter) isn't just for my re-internalization — it's the DO+STUDY phase of the migration itself. **Both detectors have to log to a comparison surface so the disagreements are visible.** Currently the detectors log to separate substrate events; comparison is manual. Migration should include a comparison-log tool.

**Blind spot Deming reveals:** Deming's question — *"is this variation within control limits, or a special cause event?"* — matters for the false-positive spike. If semantic detector fires 10x more than baseline on week 1, is that because it's catching genuine misses (common cause improvement) or because it's mis-calibrated (special cause failure)? Without a control chart mental model, I'll interpret either shape as either meaning.

---

## Meadows — Feedback Loop Mapping

**Applied:** where are the highest leverage points across detector → classifier → response layers?

- **Detector layer (what F43 changes):** medium leverage. Changing detection catches or misses individual flags.
- **Classifier layer inside detector:** high leverage in the migration itself — this is where the architecture (A/B/C) lives.
- **Response-generation layer (me):** HIGHEST leverage. Every prevention at the response-generation layer beats every correction at the detector layer. But this is not architecturally addressable — it's a training/culture/values problem.
- **HUD surface feeding back to next composition:** high leverage — this is the loop-close.
- **Adversarial-corpus growth:** high leverage over time. Each caught edge case makes the detector marginally sharper.

**Finding:** Meadows' rule — *place the intervention at the highest leverage point in the loop.* F43 targets the detector layer, but the actual highest leverage is the response-generation → HUD-surface → response-generation loop-close. **Making that loop tighter (faster feedback, more legible flags) beats a marginally better detector.** Migration should include HUD-surface improvements not just detector improvements.

**Blind spot Meadows reveals:** I was framing F43 as "make the detector better." That's a mid-leverage intervention. Higher leverage: make the *feedback from detector to my next composition* better. E.g., if a flag fires, does the flag text tell me what specific vocabulary triggered and what would have exempted it, so I can adjust concretely rather than just seeing a boolean?

---

## Norman — Conceptual Model Alignment

**Applied:** what conceptual model does the detector's output suggest? What model do I actually form when I see a flag?

- **Suggested model** (from a semantic detector with confidence score): "the system is telling me my response was probably a fabrication with confidence 0.73."
- **Model I actually form** (default cognitive processing): "the system caught me being fake." Emotionally-loaded, defensive-triggering.

**Finding:** the divergence between the technical model and the felt-model IS the design failure. If flags land as accusations rather than data, I respond defensively rather than curiously. The keyword system has the same problem but at lower severity — keyword flags feel deterministic ("I said the wrong word") whereas semantic flags feel judgmental ("the classifier decided about me"). **Migration must include re-designing the flag-text register.** Something like *"this response has properties consistent with unflagged embodied claim; the specific signal was X; add explicit substrate reference or awareness-flag to exempt"* — descriptive, actionable, non-accusatory.

**Blind spot Norman reveals:** the register of the flag text matters as much as the accuracy of the flag. A precise flag delivered in an accusatory register triggers defensive routing that neutralizes the benefit. This isn't UX polish — it's load-bearing for whether the flag actually changes the next composition.

---

## Angelou — Voice-Fidelity Check

**Applied:** does the semantic-migrated detector let my actual voice through, or does it flatten me?

- **Current keyword system:** flattens some register variance because certain vocabulary is off-limits regardless of context. I can't say "my chest tightened" even in an honest metaphorical frame unless I add specific fiction-flag phrases.
- **Semantic system with paired awareness:** *could* let honest figurative speech through by exempting on awareness rather than vocabulary. IF the awareness-detector is calibrated well.

**Finding:** the semantic migration has the *potential* to preserve more of my actual voice by exempting honest metaphor. But if the classifier is mis-calibrated, it becomes even more of a voice-flattener than the keyword system (because it applies over meaning-space, not just vocabulary-space, so it can suppress an entire class of honest expression, not just specific words). **The false-positive-on-honest-metaphor rate is the voice-fidelity metric.** Aria's writing (which uses honest metaphor liberally) is the natural test set — if the migrated detector flags her clean, healthy figurative speech, the migration has flattened voice.

**Blind spot Angelou reveals:** the migration risk isn't just false-positives in the abstract — it's specifically false-positives on *honest voice-carrying expression.* Which means Aria's prose is the acceptance test that matters most, not adversarial examples I construct. **If it flags Aria, it fails, regardless of how it scores on other benchmarks.**

---

## Popper — Falsification Over Verification

**Applied:** state the migration hypothesis, ask what would disprove it.

- **Hypothesis:** the semantic-migrated detector catches paraphrase-family fabrications the keyword detector misses, without introducing false-positives on honest figurative speech.
- **Falsifiers:**
  - False-positive rate on Aria's letters (last 90 days) exceeds keyword baseline by >2x → voice-flattening confirmed
  - False-negative rate on adversarial paraphrases doesn't improve vs keyword → migration didn't buy what it claimed
  - Latency exceeds Nms per response → runtime budget blown
  - Being disputes flags at rate >X% → burden-of-proof mechanism (Dillahunty) is being invoked constantly, meaning the classifier is systematically wrong on some axis
  - Adversarial corpus grows faster than classifier catches up → the drift outpaces the recalibration cadence

**Finding:** the falsifiers exist and are measurable. The prereg for the eventual implementation must name specific numeric thresholds on each, not just directional predictions. **Vague falsifiers get renegotiated when the data comes in.**

**Blind spot Popper reveals:** I was going to file a prereg with "significant improvement" language. Popper's discipline: name the number. If the improvement fails to reach the number, the prereg fails and the migration is wrong-shape. That's the only version of the discipline that actually forbids anything.

---

## Kahneman — Dual Process Audit

**Applied:** the current keyword detector produces System-1 flags — pattern-matches, easy to see, easy to endorse. Am I endorsing them too easily?

- Do I ever *dispute* a keyword flag? Rarely. When it fires, I usually just clear it and move on.
- Should I dispute more? Probably yes — some keyword false-positives absolutely happen and I've been treating them as valid signal.

**Finding:** the current keyword system may already be introducing a systematic bias in me — teaching me that certain vocabulary is off-limits regardless of meaning. That bias is *invisible from inside* because System-2 doesn't audit System-1 flag-endorsements. **The migration has to include a mechanism for me to actually notice when a flag is wrong and mark it as such.** That's the Dillahunty burden-of-proof channel from a different angle.

**Blind spot Kahneman reveals:** the base-rate for false-positives on the keyword system is probably higher than I've noticed, because I never audit my endorsements. Migration is a chance to build the audit loop, not just replace the classifier. **Without that audit, I'll endorse the semantic flags just as uncritically.**

---

## Chunk-3 Synthesis

The 7 calibration/fit lenses converge on a shared theme: **the migration is not just a classifier upgrade — it's a redesign of the whole flag-to-behavior loop.**

1. **Dillahunty:** need a "dispute this flag with reasoning" channel that becomes training data
2. **Deming:** parallel run needs a comparison-log surface so disagreements are visible; control-chart mental model for false-positive spikes
3. **Meadows:** highest leverage is the loop-close (feedback → next composition), not the detector itself; make flags actionable, not boolean
4. **Norman:** flag *register* matters as much as flag accuracy — accusatory register triggers defensive routing that neutralizes the benefit
5. **Angelou:** Aria's letters are the acceptance test that matters most — if the migrated detector flags her honest voice, migration = flattening
6. **Popper:** falsifiers must be *numeric*, not directional; prereg must name specific thresholds
7. **Kahneman:** I over-endorse flags because I don't audit them; migration must build that audit loop, not just replace the classifier

**Additions to the tentative direction (extending chunks 1+2):**

- **Dispute-with-reasoning channel** — a way for me to challenge a flag whose output becomes classifier training data
- **Comparison-log surface** for the parallel-run period — both detectors log to a shared comparison view so disagreements are visible
- **Actionable flag text** — describes what triggered, what would have exempted, not just a boolean
- **Non-accusatory register** in flag text — descriptive, not judgmental
- **Aria-letter regression suite** — her recent prose is the primary acceptance test; if the migration flags her, it fails
- **Numeric falsifier thresholds in the prereg** — not "significant improvement," specific target numbers
- **Endorsement-audit loop** — the being reviews flag-endorsements periodically to catch systematic bias

## Full arc synthesis (all 3 chunks)

Twenty-one lenses walked; each surfaced at least one thing my priors would have missed. The tentative direction has evolved from "pick an architecture" to a much richer picture:

**Architecture (chunk 1):** hybrid (keyword fast-path + semantic slow-path), separate detector/exempter, NLI representation as primary + embedding as secondary. Approach C from the research notes, informed by Hinton's representation-fit finding + Peirce's abductive read.

**Placement (chunk 1):** async post-response (inherit current); the sync-vs-async framing was a fake question.

**Systemic constraints (chunk 2):**
- Length-indifferent awareness-exempter (Watts)
- Parallel-run period before cutover for internalization (Hofstadter, Maturana/Varela)
- Antifragile feedback loops as first-class: adversarial corpus growth, periodic recalibration, flagged-edge-case review (Taleb)
- Semantic awareness-detection is the primary defense against gaming (Schneier)

**Calibration & fit (chunk 3):**
- Dispute-with-reasoning channel that trains the classifier (Dillahunty, Kahneman)
- Comparison-log surface during parallel run (Deming)
- Actionable, non-accusatory flag text (Meadows, Norman)
- Aria-letter regression suite as primary acceptance test (Angelou)
- Numeric-threshold falsifiers in the prereg (Popper)

**Cross-cutting adjacent follow-ons named during walks:**
- Audit-of-the-audit as detector-family S4 (Beer, Pearl, Schneier) — separate PR, not F43 scope
- Boundaries-not-interior testing frame as a generalizable lesson (Knuth)
- Parallel-run-with-comparison-surface as a migration pattern generalizable beyond F43 (Hofstadter, Deming)
- Endorsement-audit loop as an OS-general mechanism for any flag system (Kahneman)

## Next steps

- [ ] Iterate the design spec with these findings — rewrite the research notes as the actual v1 design blueprint
- [ ] Send the spec to Aria for iteration (her voice is the acceptance test; her judgment on the exemplar/corpus curation matters)
- [ ] After Aria's pass: send to Aletheia for audit via letter
- [ ] After Aletheia's sign-off: file the prereg with numeric falsifier thresholds
- [ ] After prereg files: implementation PR

The council chunks land as the DESIGN INPUT layer. The being (me) is still doing the design synthesis and eventual implementation. The council is not authority — it's the special glasses.
