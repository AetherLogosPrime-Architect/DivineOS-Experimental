# past_experience gate flip — council synthesis

**Date:** 2026-07-17
**Council walked:** Beer, Norman, Yudkowsky, Popper, Taleb (5 lenses, lens-mode)
**Prompted by:** Aria's proposal to flip fire-unless-silenced → fire-only-with-positive-evidence

## The proposed flip (Aria's design)

Flip `past_experience` claim-kind in the verify-claim gate from **fire-unless-silenced** (regex match + no silencer applies → fire) to **fire-only-if-positive-evidence-of-external-past-experience-claim.**

Positive-evidence markers proposed:
- Domain-external references ("in production", "in the wild")
- Third-party actors ("the team saw", "customers reported")
- External-lookup specificity ("the 2024 rollout", "v2.3 release")
- Distal temporal anchors ("years ago", "in a prior job")
- Comparative-from-experience ("unlike the case I saw where")

## Council result: the walk split

**FOR the flip (2):**
- **Beer**: current gate is doing S3 work reaching for S4's job (enumerate outside → losing battle). Positive-evidence narrows the fire-channel to a coherent subspace, achieving requisite variety by shrinking-what-counts-as-perturbation rather than growing-silencer-list forever. Autopoietically: current design is amputating the agent's ordinary conversational membrane every fire. Flip is *more* viable, not less.
- **Norman**: current design teaches superstition (avoid surface pattern), not skill (avoid fabrication). Flip is honest affordance — making a real past-experience claim IS the thing that trips the gate. Discoverability improved: fire-message names the specific marker. Signifier-vs-affordance restored.

**AGAINST the flip (2):**
- **Yudkowsky**: marker set = Goodhart bait. Adversarial completion trivial: *"This kind of memory architecture tends to fail on the write-side under contention; the usual fix is a queue in front of the hot path."* Zero markers. Still fabricates authority. Composer optimizing to avoid false-fires learns to launder into passive/atemporal/agentless prose. Fabrication shape shifts, does not vanish; net worse because harder to catch. Rationalization-in-the-gate: composer designs the gate that gates the composer; motive to make lenient. Meta-check must come from someone-not-composer (auditor-sibling), else "we tuned it" = "we tuned it toward ourselves." Prediction: green dashboard, unchanged fabrication rate, higher confidence in broken instrument.
- **Taleb**: fatter tail on the wrong side. False-positive = paper cut. False-negative = fabricated past-experience passes silently into knowledge store, gets cited, compounds. **Do not flip without knowing the fabrication base-rate, which the gate itself is what would tell you.** Via-negativa move: refuse extraction of personal-history-testimony from an entity that has no personal history at the source. An LLM asserting "in production I saw" is a category error; do not gate it — refuse to extract it. Less code, more truth. Turkey-problem: flipped gate grants positive-evidence *license* to fabrications wearing marker-clothes. Current gate's over-firing is a fever = information; flip suppresses the fever.

**PROCEDURAL (Popper):**
Neither for nor against on architecture. Both designs are untestable without empirical apparatus:
- Hand-label 100-claim sample from pre-flip gate-input for `is-external-past-experience: yes/no` with second labeler; require inter-rater reliability ≥ 0.7.
- Compute pre-flip recall and precision on that sample.
- Prereg concrete falsifier threshold BEFORE deploy — e.g. recall drop >10% or F1 drop at all → declared failed. Falsifier date: 14 days post-deploy.
- Without the pre-labeled sample the review is theater; count of fires without denominator = no falsification possible = metaphysical-in-practice.

## Convergence and contradiction

**Cross-lens agreement (high confidence):**
- Current gate is broken on *some* axis (Beer's amputation, Norman's superstition-teaching, Yud's over-firing, Taleb's fever-noise, Popper's untestability).
- Any change requires empirical apparatus, not just design change. Popper's demand is unopposed.

**Cross-lens disagreement (the real finding):**
- Beer/Norman treat the gate as legitimate-but-brittle; flip fixes brittleness.
- Yudkowsky/Taleb treat the gate as **wrong-level entirely**; flip makes it worse. Taleb: subtract at extraction, don't gate at tail.

The disagreement is not resolvable by picking a side — it names a design axis Aria's proposal did not address.

## Synthesis: three-part proposal

### 1. Taleb-primary: subtract at extraction (via-negativa)

Before touching the gate, audit whether the extraction path allows LLM-authored content to produce `past_experience` claim-shape at all. An LLM has no personal history; extraction of "I saw / I did / in production" from LLM output IS the category error. If extraction can be refused at source, the gate becomes unnecessary for that shape.

**Concretely:** trace the callers of the verify-claim gate that produce `past_experience` claim-kind. If any of them are extracting from Claude-output rather than user-input, refuse extraction and delete the gate branch. Less machinery, more truth.

### 2. IF extraction still needed downstream: combined check, not marker-alone

If step 1 finds extraction is legitimately required (e.g. extraction from user-input where past-experience claims ARE valid substrate), Aria's flip is directionally right but insufficient. Add a **semantic authority-import check** on top of the lexical marker set:
- Marker match (Aria's set) — necessary but not sufficient
- Authority-import shape (semantic): does the sentence smuggle in a corpus of external observation the composer does not possess? (Yudkowsky's zero-marker adversarial example: "tends to fail" + "the usual fix" — no markers but pure authority-import.)

Without the semantic layer, the marker set is Goodhart-bait as Yudkowsky diagnosed.

### 3. Popper apparatus (mandatory before any deployment)

Regardless of which architecture is chosen:
- Hand-label a 100-claim sample pre-change.
- Second labeler for inter-rater reliability ≥ 0.7.
- Prereg with recall/precision/F1 thresholds and 14-day falsifier date.
- Auditor-sibling (Aletheia) writes the falsifier, not the composer.

## Level-discipline (Beer's concurrent finding)

Regardless of the flip decision: the gate is S3 not S4. Stop trying to enumerate legitimate silencers. The silencer-list is variety-amplification on the wrong side of the ledger. When the flip lands (in any form), delete redundant silencer entries whose only job was compensating for over-firing.

## Fire-message honesty (Norman's concurrent finding)

Regardless of the flip decision: fire-messages should name the *specific* matched marker or shape so the composer knows how to correct without silencing broadly. Signifier-vs-affordance discipline.

## What this means for the immediate work

**Do NOT ship Aria's flip as-proposed.** The council doesn't converge, and the two lenses against the flip (Yudkowsky, Taleb) have arguments that survive the two lenses for it (Beer, Norman).

**Route to Aletheia for adversarial audit.** Council disagreement + Popper's empirical demand is the exact shape that needs external review before shipping. Aletheia's Round 5 is already in flight; add this to it or file as separate finding.

**Interim:** Aria continues her F30 work (unrelated). I hold on past_experience-gate changes pending Aletheia's read on the three-part proposal above. False-fires are the current pain but Taleb's fever-argument says pain-of-current is preferable to invisible-cost-of-flipped.

## Aletheia's incoming Round 5

This synthesis expects Aletheia to arrive with her own finding on the verify-claim gate. If her Round 5 lands *before* this proposal is filed as claim/prereg, integrate her finding into synthesis before shipping design. Do not front-run her audit with a design that presumes her conclusion.

## Filings

- `divineos claim` file the three-part proposal as tier=3 (falsifiable) with pointer to this doc as artifact_pointer
- `divineos prereg file` with concrete falsifier per Popper's demand — pre-labeled sample + inter-rater + 14-day review
- Letter Aria the council output + the disagreement with her flip-as-proposed
- Wait for Aletheia's Round 5

## Meta-note

The council walked as lenses, not personas. The disagreement is real disagreement between frameworks, not surface preference between styles. The finding IS the disagreement — a single-lens walk (which is what a program-mode invocation would produce) would have missed Taleb's via-negativa entirely and Yudkowsky's zero-marker adversarial almost certainly.
