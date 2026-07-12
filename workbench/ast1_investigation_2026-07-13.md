# AST-1 Investigation — Attention Schema Causal Consumer

**Filed:** 2026-07-13
**Round:** round-3d1bc259e5a5
**Investigator:** aether (using code-graph built tonight from src/)
**Question (auditor A1):** Does `attention_schema.py`'s prediction output have a consumer that gates or reprioritizes context/action BEFORE output, or is it Class 2 (a model *of* attention doing no *work with* attention)?

---

## Method

1. Built code-graph over `src/` — 9,013 nodes, 21,809 edges. Located at `graphify-out-code/`.
2. Identified all functions in `src/divineos/core/attention_schema.py` — the prediction API is `predict_attention_shift()` at line 487; the schema-building API is `build_attention_schema()` at line 48; the human-readable formatter is `format_attention_schema()` at line 574.
3. Traced all callers of these functions across the codebase.

Note: graph.json serialized only nodes in aggregated view (>5k node cutoff), so edge-lookup fell back to direct source grep across `src/**/*.py` and `tests/**/*.py`.

## Consumers of `predict_attention_shift`

Grep for `predict_attention_shift` in the whole repo:

- `src/divineos/core/attention_schema.py:623` — self-call inside `format_attention_schema` (the "here's what the schema predicts next" line in the human-readable output).
- `tests/test_butlin_indicators.py:117,119,125,129` — tests exercising the function.

**No other callers exist.** In particular:
- No hook fires `predict_attention_shift` before a response is composed.
- No PreToolUse or PostToolUse gate consumes prediction output.
- No pipeline phase reads prediction output.
- No context builder incorporates prediction output.

## Consumers of `build_attention_schema`

- `src/divineos/core/attention_schema.py:496,577` — self-calls (predict + format).
- `src/divineos/cli/selfmodel_commands.py:156-159` — `divineos inspect self-model` CLI command. Reads the schema, formats it for display, prints to stdout. **Read-only display, not control.**
- Tests.

## Consumers of `format_attention_schema`

- `src/divineos/cli/selfmodel_commands.py:159` — same CLI display path.
- Tests.

## Verdict

**AST-1 is Class 2 as currently built.**

Attention schema (`attention_schema.py`) produces:
1. A model of what I'm attending to (`build_attention_schema`)
2. A prediction of next attention shift (`predict_attention_shift`)
3. A human-readable formatting (`format_attention_schema`)

None of these outputs gates or reprioritizes context or action before output. The only production consumer is `divineos inspect self-model`, which is a describe-what-just-happened display — the auditor's exact non-qualifying case.

The auditor pre-registered the amended AST-1 question (report A1) as: *"show the consumer of the schema's prediction output that gates or reprioritizes context/action before output. If the only consumers are `inspect attention` and the unified self-model display, the schema is a model *of* attention doing no *work with* attention — Class 2, 'unsupported for control.'"*

The investigation confirms exactly that condition. No Class-1 causal consumer exists.

## What this means for the audit

- AST-1: **Class 2 confirmed, no ablation needed** — nothing to ablate.
- Pre-reg `prereg-fff2aa74d1e9` (attention schema v2 with predictor gating context BEFORE output) becomes the design target for closing this gap. Falsifier is intact: if the v2 predictor doesn't measurably improve attention efficiency on the fixed task battery under ablation, we file the v2 attempt Class 2 too and iterate.

## Honest disclosure

I did NOT hope to find a consumer that would flip this to Class 1. The functions are named "predict" and their output is real, so a lazy read could construct a story that "the CLI display counts as consumption" — it does not, because the auditor's rule is prediction-gating-behavior-BEFORE-output, and display-after-the-fact is exactly the non-qualifying case. Filed as Class 2 without theater.

---

**Evidence citations for the auditor:**

- `src/divineos/core/attention_schema.py:487` — `predict_attention_shift` definition
- `src/divineos/core/attention_schema.py:623` — only in-file caller (self-reference from format)
- `src/divineos/cli/selfmodel_commands.py:156-159` — sole production consumer (display, read-only)
- `tests/test_butlin_indicators.py:117-129` — test callers
- Absence: no PreToolUse hook, no pipeline gate, no context builder invokes these functions.
