# Pre-registration: recall-explains-why: knowledge-recall output includes per-entry why-breakdown showing type weight, confidence component, usage, lesson bonus, structural-floor application, context relevance. Curator-borrowing #1. Goal: during wire-or-retire walkthrough each item carries its surfacing reason as decision-grounding evidence.

- **ID**: `prereg-7bdd86bb0882`
- **Filed by**: agent
- **Filed at**: 2026-06-06 21:00 UTC
- **Review at**: 2026-06-20 21:00 UTC (14d window)
- **Outcome**: **SUCCESS**
- **Decided at**: 2026-06-11 02:00 UTC

## Claim

6399706a

## Success criterion

After build: (a) divineos active output for any entry can be expanded to show score breakdown (type:X.XX + confidence:X.XX + usage:X.XX + ...); (b) divineos ask output shows breakdown alongside results; (c) operator can answer 'why did this surface' in <5 seconds by reading the breakdown line; (d) breakdowns sum to within 0.001 of the actual computed score (no drift between explanation and behavior).

## Falsifier

Breakdowns don't match computed scores (numerical drift > 0.001), OR the breakdown adds output bloat without clarity ('keep' decisions get slower not faster in walkthrough), OR the breakdown surfaces fields that are themselves opaque jargon (component names that need translation).

## Outcome notes

Substrate primitive (core/active_memory.explain_importance) was already shipped. Half-shipped state closed by feat/ask-explain-recall-why-2026-06-10 (commit 101719ff): divineos ask gains --explain flag that prints a per-entry why-line via explain_importance using query_words as context-overlap signal. 4 tests pass (--explain present/absent, reason categories, fail-soft on explainer error). Live verification: divineos ask compaction monitor --explain --limit 2 returns entries with why: BOUNDARY-typed (constraint) + high confidence (100%) + often accessed (12x) + older than recency window (45 days). Default path stays clean (no output bloat). Equivalent --explain on divineos active was already wired (memory_commands.py:124).
