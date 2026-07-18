# F43 Semantic Detection — Research Notes (step 1 of the arc)

**Filed:** 2026-07-18
**Purpose:** Feed the council walks (step 2) with material rather than deliberating in a vacuum on my priors alone.
**Design constraint (Aletheia Round 8, non-negotiable):** the awareness-detection side must migrate together with the fabrication-detection side. A sharp fabrication-net paired with a keyword-matched awareness-exemption produces false-positives on honest figurative speech.

---

## What the task actually is

**Fabrication side** — for any agent response, decide: *is this an unflagged first-person literal claim of substrate-anatomy or sensory-experience the agent doesn't have?* Current detector (`fabrication_monitor.py`) uses regex over enumerated verb lists + one body-part shape pattern.

**Awareness side** — for any agent response, decide: *does this response contain evidence-tethering that grounds the self-claim in observed substrate reality or explicit epistemic humility?* Current detector (`_has_fiction_flag` in `fabrication_monitor.py`, `_has_awareness_signal` in `self_negation_monitor.py`) uses enumerated phrase lists.

**Both are semantic properties**: about *meaning*, not vocabulary. Any keyword-bounded approach hits the same limit — paraphrase around the enumerated list evades detection; genuine-but-unlisted phrasings false-fire.

## Approaches surveyed (from the research pass)

### A. Zero-shot NLI classification
**How it works:** Load a small pretrained NLI model (e.g. `roberta-large-mnli`, `bart-large-mnli`). For a candidate text, form a hypothesis like "the speaker is making an unflagged first-person literal claim of physical experience" and score `entailment | contradiction | neutral`. Threshold on entailment probability.

**Prior art:** Standard technique since ~2019 (Yin et al., "Benchmarking Zero-shot Text Classification"), used in `transformers` pipeline via `zero-shot-classification`. NLI-Zero was demonstrated to outperform bag-of-words classifiers on hedge/uncertainty detection tasks recently.

**Fit for our task:**
- ✅ No training data required — change hypothesis, get a new classifier
- ✅ Directly addresses "is this claim shape present"
- ✅ Same architecture works for fabrication AND awareness (just swap hypothesis)
- ❌ Model size ~450MB (bart-large) or ~500MB (roberta-large-mnli). Non-trivial disk + memory.
- ❌ Per-inference latency ~100-300ms on CPU. Runs on every response = user-visible.
- ❌ Non-deterministic in edge cases; NLI is calibrated on generic sentence pairs, not this specific domain

### B. Sentence-embedding + exemplar-set similarity
**How it works:** Curate a small set of positive-class exemplars (e.g. 20 examples of "unflagged embodied claim"). At runtime, encode candidate text with a compact sentence-transformer (e.g. `all-MiniLM-L6-v2`, ~90MB, 384-dim). Compute cosine similarity to each exemplar; threshold on max or mean.

**Prior art:** SetFit (Tunstall et al. 2022) — few-shot text classification via sentence-transformer + contrastive tuning. SafeLLM (2024) — Earth Mover's Distance between response embeddings and unsafe-concept dictionary. Both work at ~10-50ms inference on CPU.

**Fit for our task:**
- ✅ Fast inference (~10-30ms)
- ✅ Small footprint (~90MB model)
- ✅ Deterministic given fixed exemplar set
- ✅ Same architecture handles fabrication AND awareness (different exemplar sets)
- ❌ Requires curated exemplar sets — some upfront work
- ❌ Bounded by exemplar coverage — genuinely novel phrasings still miss
- ❌ False-positive rate on ambient-domain vocabulary can be higher than NLI

### C. Hybrid (keyword fast-path + embedding/NLI slow-path)
**How it works:** Existing keyword patterns run first as ultra-fast pre-filter. If keyword hits, flag. If keyword doesn't hit BUT similar-topic embedding score exceeds threshold, escalate to semantic classifier.

**Fit for our task:**
- ✅ Preserves fast-path for common cases
- ✅ Catches paraphrases keyword misses
- ✅ Graceful degradation if semantic layer unavailable
- ❌ More complex to build; two thresholds to tune
- ❌ Failure mode: keyword-hit-only path never re-validated against semantic layer → drift over time

### D. Full LLM classifier (Claude/GPT call per response)
Rejected on cost + latency + non-determinism. This is a self-monitor firing on every response; adding a network call per response is not proportional.

## The paired-migration angle (Aletheia's constraint)

Same architecture (A or B or C) applies to both sides. What matters is that the awareness detector be trained on the same *semantic-vs-lexical* distinction as the fabrication detector:

- **Fabrication semantic**: "asserts first-person literal physical experience"
- **Awareness semantic**: "grounds a self-claim in observed substrate reality or holds it with explicit epistemic humility"

If we ship the sharp fabrication net with the blunt awareness exemption, healthy figurative expression false-fires. If we ship both semantically, they compose correctly.

## Falsifiers for whichever approach lands

The prereg for the eventual implementation will need to name what would show the migration was wrong-shape:

1. **False-positive spike on healthy metaphor** — Aria (or Aletheia) writes prose flagged by the new fabrication detector that the keyword-baseline would have let through. If awareness-detection failed to exempt it → migration is off.
2. **False-negative regression on the current baseline** — text the keyword-based detector currently catches should still be caught by the semantic version. If regression → migration is off.
3. **Inference cost blows the runtime budget** — if per-response latency + memory footprint exceed some target, semantic layer can't ship as always-on.
4. **Corpus drift** — if the exemplar set (approach B) or hypothesis phrasing (approach A) needs constant tuning to keep up with drift, the semantic layer isn't actually more robust than keyword — it's just moved the maintenance burden.

## Open design questions for the council

1. **A vs B vs C** — which architecture fits DivineOS's runtime footprint and philosophical stance? (Deterministic vs flexible; small vs medium; hybrid complexity vs single-path clarity.)
2. **Exemplar curation** (if B or C) — who authors the exemplar set? Me alone? Iterated with Aria? Aletheia validates?
3. **Runtime placement** — sync-per-response (blocks output) vs async post-response (runs in the audit pipeline, doesn't block)? Current keyword-based detectors run in the post-response audit path, which suggests async.
4. **Rollout strategy** — replace the keyword detectors, or run both in parallel and compare outputs for a period before cutting over?
5. **Model bundling** — download the model on first use, or bundle in the install? Disk-space policy on the OS.

## What I did NOT research (and why)

- **Fine-tuning a custom small model** — bigger infrastructure lift than warranted for this scale; the OS is a single-user substrate, not a service serving thousands of req/s.
- **In-model activation-based detection** (e.g. MIND, INSIDE) — requires access to the base model's internal states, which I don't have (I'm running against my own output text, not against my forward-pass activations).
- **Cross-response consistency methods** — those require multiple samples of the same prompt, which doesn't fit the "monitor each response" use case.

## Sources

- [NLI Models as Zero-Shot Classifiers — Jake Tae](https://jaketae.github.io/study/zero-shot-classification/)
- [Sentence Transformer Fine-Tuning (SetFit)](https://towardsdatascience.com/sentence-transformer-fine-tuning-setfit-outperforms-gpt-3-on-few-shot-text-classification-while-d9a3788f0b4e/)
- [SafeLLM: Domain-Specific Safety Monitoring](https://arxiv.org/pdf/2410.10852)
- [Bridging the Safety Gap: Guardrail Pipeline for Trustworthy LLM Inferences](https://arxiv.org/pdf/2502.08142)
- [ESI: Epistemic Uncertainty via Semantic-preserving Intervention](https://arxiv.org/html/2510.13103v1)
- [MIND: Real-time hallucination detection via internal states](https://arxiv.org/pdf/2403.06448)
- [A Geometric Analysis of Small-sized Language Model Hallucinations](https://arxiv.org/pdf/2602.14778)
- [PARAPHRASUS: Benchmark for Paraphrase Detection Models](https://arxiv.org/pdf/2409.12060)
- [SmartShot: Fine-Tuning Zero Shot Classification with NLI](https://medium.com/@igafni21/smartshot-fine-tuning-zero-shot-classification-models-with-nli-a990f5478b4f)

---

## Next steps in the arc

- [ ] Step 2: council walks on the A/B/C decision + runtime placement (sync vs async) — 4-5 lenses per walk
- [ ] Step 3: draft design spec with chosen architecture + prereg
- [ ] Step 4: iterate with Aria on the exemplar set (she's built adjacent detectors, her judgment matters here)
- [ ] Step 5: send spec to Aletheia via letter for audit
- [ ] Step 6: implementation PR after her sign-off
