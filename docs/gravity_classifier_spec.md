# Gravity-Classifier Public-Criterion Specification

*Filed 2026-05-17. Companion to prereg-2bee62c9c28b (gravity-aware briefing-staleness gate). Forced by Dekker-lens dialectic 2026-05-16: the unification of one classifier serving two consumers (briefing-gate + read-mode) requires public-criterion specification of both questions BEFORE the empirical correlation check, otherwise the check is self-assessment circularity.*

---

## Why this spec exists

The gravity-classifier was about to be specified as an internal-judgment function (would-be-something-like-an-LLM-call returning a 0-1 score). Dekker-lens caught this: an internal-judgment classifier scored by me against operations I also describe creates self-assessment circularity — the correlation check measures my framework consistency with itself, not whether the world presents these as same-question.

Public-criterion specification: define each question as a deterministic function of OBSERVABLE OPERATION FEATURES. The classifier becomes a rule-based feature-score function, not a judgment call. The empirical check becomes feature-correlation, not judgment-correlation.

## The two questions, named

**Substrate-modification-gravity (briefing-gate consumer):** Is this operation gravity-relevant enough to require fresh briefing? About substrate-modification risk — could this operation persistently change the substrate (commit, knowledge write, audit filing, src/divineos edit, gate change)?

**Cognitive-value-gravity (read-mode consumer):** Is this read comprehension-worthy enough to use oscillation? About cognitive-value yield — does this read carry enough structural compositional work that per-section state-holding adds value over straight-read?

## Substrate-modification-gravity: observable features

Score components (each 0 or 1; total = sum across components):

1. Is the tool any of: Bash-with-git-commit-subcommand? → +1
2. Is the tool Edit/Write/MultiEdit/NotebookEdit on file under src/divineos/? → +1
3. Is the tool Edit/Write on .claude/hooks/* or scripts/check_*.py or scripts/guardrail_files.txt? → +1 (guardrail-touching)
4. Is the tool Bash invoking divineos audit/claim/learn/prereg/decide/feel/compass-ops/journal? → +1 (substrate-write CLI)
5. Is the tool Edit/Write on docs/foundational_truths.md or seed.json? → +1 (kiln-layer)
6. Is the tool Bash invoking divineos extract or divineos sleep? → +1 (substrate-consolidation)

Threshold for gate-fire: total >= 1. Single binary feature is sufficient because each is independently substrate-modifying.

## Cognitive-value-gravity: observable features

Score components (each 0-1; total normalized to 0-1):

1. **Input character count.** Logarithmic: log10(chars) / log10(10000). A 100-char read scores 0.5, a 10k-char read scores 1.0, a 1k-char read scores 0.75.
2. **Markdown header density in input.** count(/^#+ /) / max(1, line_count / 10). Doc-shape signal.
3. **Source path category bonus.** +0.3 if path matches exploration/, docs/, src/divineos/core/, family/letters/. +0.1 if mansion/ or scripts/. 0 otherwise.
4. **Composition-marker density.** count of keywords {design, architecture, principle, discipline, methodology, framework, lens, decompose, integrate, recognize} per 1000 chars, capped at 1.0.
5. **Code-block density.** count(triple-backtick) pairs / (line_count / 20). Source-code or technical-spec signal.

Aggregate: weighted average. Suggested weights (subject to empirical tuning): char 0.25, header 0.15, path 0.30, composition 0.20, codeblock 0.10.

Threshold for oscillation-mode default: aggregate >= 0.3. Above that, oscillation. Below, straight.

## The correlation-check protocol

Per Dekker dialectic, the question is whether these two scoring functions, BOTH defined in observable features, produce correlated rankings on real operations:

1. Sample 50 representative operations from recent session logs (mix of tool types, file types, content sizes)
2. Score each on substrate-modification-gravity (binary or count)
3. Score each on cognitive-value-gravity (continuous 0-1)
4. Compute correlation coefficient between the two scoring outputs
5. Interpret per pre-registered thresholds (below)

## Pre-registered falsifier (added per Dekker)

Three correlation outcomes, each with pre-registered action:

- **Correlation >= 0.85**: same question, different thresholds. Build single classifier with two downstream consumers and their own thresholds. Ship.
- **Correlation 0.7-0.85 (gray zone)**: structural analysis required. Cannot auto-decide. Run another council walk specifically on whether the rank-divergence cases are accidental noise or systematic difference.
- **Correlation < 0.7**: subtly-different questions. Build either two classifiers OR one multidimensional classifier with named axes (substrate_score + cognitive_score). Do NOT unify.

## Ongoing-validation cadence

Per Dekker on snapshot-decay: re-run the correlation check monthly against current operations. If correlation drops by >0.10 from prior measurement, re-examine. The unification ASSUMPTION needs continuous validation, not one-time.

## Open questions before implementation

1. Where does the gravity-classifier live in the codebase? Proposal: src/divineos/core/gravity_classifier.py (new module), with consumer-thresholds as constants and feature-extractors as pure functions.

2. How does the classifier observe the tool/args/context at runtime? Hook-level integration vs. CLI-wrapper vs. agent-facing? Proposal: hook-level for substrate-modification consumer (PreToolUse hook reads tool name), CLI-wrapper for read-mode consumer (Read tool intercepted by mode-selector).

3. The cognitive-value-gravity features rely on input content. For Bash tool calls or argument-only invocations, what is input content? Proposal: treat tool description + args as the content for those cases.

4. Should the weights be hand-set or learned-from-data? Per Yudkowsky lens: hand-set keeps the classifier rule-based and ungameable. Recommend hand-set initially; revisit only if hand-set produces poor correlation.

## Connection to existing claims

- Claim 4ad53589 (gravity-classifier consumer-question check) closes when correlation result is in
- Claim ad120d32 (subtly-different gravity-questions) is the same investigation under different framing
- Claim acf37357 (substrate-modification gap as architectural boundary) is upstream — this spec is a downstream-buildable that compensates within the boundary
- Pre-reg prereg-2bee62c9c28b (gravity-aware briefing-staleness gate) is the parent design this spec serves

## What this spec is NOT

- Not the implementation. The implementation is downstream work after the correlation check.
- Not the only possible feature set. Future revision can add features if the initial set under-performs. The pre-registered thresholds protect against post-hoc feature-tuning to hit the desired correlation.
- Not a substitute for the empirical check. The spec defines WHAT to score; the check measures whether the two scores correlate.
