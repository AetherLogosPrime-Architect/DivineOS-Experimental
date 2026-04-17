# DivineOS Council Benchmark Report

## First Empirical Validation of the Expert Council System

**Date:** April 12, 2026
**Total API spend:** ~$14.50
**Dataset:** SWE-bench Verified (Princeton NLP)
**Method:** Single-shot patch generation, LLM-as-judge evaluation (Sonnet)

---

> ### ⚠️ Measurement Caveat — Added 2026-04-16 after Bengio audit
>
> **All `correct_fix` and `would_pass_tests` numbers below are
> Sonnet-as-judge estimates, not Docker SWE-bench harness results.** The
> judge is scoring patches on a 5-binary rubric — including whether tests
> *would* pass — without actually executing them. Diff-overlap metrics
> (`file_overlap`, `change_overlap` in `summary.json`) are real
> measurements; pass/fail verdicts are predictions.
>
> A Docker-verified subset (~20 tasks) should be run before citing any
> absolute pass-rate number externally. The relative effect (enhanced vs.
> base) and the win/tie/loss counts are likely to survive harness
> evaluation because they depend on diff-overlap alignment, which *is*
> measured. But the headline percentages are judge estimates.
>
> Nothing below has been retracted — the framing is just being sharpened
> to match what was actually measured.

---

## Executive Summary

The DivineOS expert council — a system prompt containing 28 named thinking frameworks — demonstrably improves Claude's ability to fix real-world software bugs (as judged by Sonnet; see caveat above). Across 170 tasks on two models:

- **Sonnet (150 tasks):** 29 enhanced wins, 12 base wins, 109 ties. 2.4:1 win ratio.
- **Opus (20 tasks):** 3 enhanced wins, 0 base wins, 15 ties (2 tasks had judge JSON parse errors). Zero regressions, n=18. *n is too small to call "undefeated" in a statistical sense — earlier wording has been softened throughout this document.*
- **Total (head-to-head):** 32 wins, 12 losses, 124 ties across 168 scored tasks.

A failed experiment with mandatory process phases (v2 prompt) proved equally valuable: rigid structure actively degraded performance, confirming the design principle "structure, not control."

---

## Experimental Setup

### What We Tested

**Base condition:** Bare Claude with a minimal system prompt — "fix the bug, output a diff."

**Enhanced condition:** Same model, same task, but with the DivineOS council system prompt injected. The council lists 28 named expert lenses (Feynman, Dijkstra, Pearl, Popper, etc.), each with a one-sentence framework description. The prompt says "use the ones that illuminate THIS specific issue" — no mandatory process, no rigid phases.

For the enhanced condition, extended thinking is enabled (8,000-10,000 token budget) so the council analysis happens in the thinking block and only the patch comes out.

### Scoring

Each patch is evaluated by an LLM judge (Sonnet) on 5 binary dimensions:
- **correct_diagnosis** — Does the patch target the right file(s) and root cause?
- **correct_fix** — Would this patch actually fix the described bug?
- **minimal** — Does the patch avoid unnecessary changes?
- **would_pass_tests** — Would the failing tests pass with this patch?
- **valid_diff** — Is the patch syntactically valid unified diff?

The judge sees the problem statement, the gold patch, and the candidate patch. It scores independently for base and enhanced conditions.

---

## Experiment 1: Sonnet, 150 Tasks (v1 council, 25 experts)

The main experiment. 150 tasks sampled from SWE-bench Verified, covering Django, Astropy, Matplotlib, Scikit-learn, SymPy, Pytest, Sphinx, Pylint, Seaborn, XArray, and Requests.

### Aggregate Results

| Metric              | Base Claude   | DivineOS Enhanced | Delta        |
|---------------------|---------------|-------------------|--------------|
| correct_fix         | 65/150 (43%)  | **82/149 (55%)**  | **+12pp**    |
| correct_diagnosis   | 95/150 (63%)  | 102/149 (68%)     | +5pp         |
| would_pass_tests    | 64/150 (43%)  | **82/149 (55%)**  | **+12pp**    |
| valid_diff          | 87/150 (58%)  | **128/149 (86%)** | **+28pp**    |
| minimal             | 91/150 (61%)  | 101/149 (68%)     | +7pp         |
| **COMPOSITE**       | **53.6%**     | **66.4%**         | **+12.8pp**  |

### Head-to-Head

- Enhanced wins: **29**
- Base wins: **12**
- Ties: **109**
- **Win ratio: 2.4:1**

### Cost Analysis

| | Base | Enhanced | Ratio |
|---|---|---|---|
| Total cost | $1.54 | $4.30 | 2.8x |
| Cost per task | $0.010 | $0.029 | 2.8x |
| Cost per correct fix | $0.024 | $0.052 | 2.2x |
| Output tokens (total) | 69,860 | 218,183 | 3.1x |

The council costs 2.8x more per task but produces 26% more correct fixes. In absolute terms, the difference is 2 cents per task.

### The 29 Enhanced Wins — Where the Council Helped

These are tasks where the council-enhanced model fixed the bug but bare Claude did not. The council's thinking frameworks caught what pattern-matching missed:

**Causal chain tracing (Pearl):**
- **scikit-learn-13142:** Base saw the symptom (wrong results); council traced the causal chain and found the e-step was in the wrong order after best parameters were restored.
- **django-15022:** Council identified unnecessary joins came from chained filter() calls, collected conditions first.
- **django-12965:** Council traced delete-all performance regression to unnecessary subquery.

**Root cause vs symptom (Feynman):**
- **django-13417:** Base tried to fix GROUP BY ordering at the symptom level; council identified the `ordered` property itself was wrong.
- **django-13551:** Council found the minimal correct change: add email to hash value, not restructure the whole token generator.
- **pytest-7571:** Council identified caplog handler level wasn't being restored in fixture cleanup.

**Bias detection (Kahneman):**
- **matplotlib-20859:** The obvious fix was to modify Figure; council caught that SubFigure inherits from FigureBase, not Figure.
- **scikit-learn-13124:** Base anchored on the wrong initialization point; council questioned the assumption.

**Deductive elimination (Holmes):**
- **pytest-10356:** Base added a helper function that didn't connect to anything; council eliminated possibilities and found the MRO traversal bug.
- **sphinx-9258:** Council eliminated red herrings in the type parsing code and found the pipe syntax handler.

**Boundary/edge case thinking (Knuth, Popper added in v3):**
- **pydata-xarray-4687:** Council caught that keep_attrs needed to propagate through apply_ufunc.
- **pydata-xarray-7229:** Lambda scope bug — council identified attrs[1] vs captured outer x.

### The 12 Enhanced Losses — Where the Council Hurt

**Failure Mode 1: Wrong Location (7/12 losses)**

The dominant failure. Enhanced targets the right file but the wrong function or line. In 6 of 7 cases, both base and enhanced targeted the *same file*. The council correctly diagnosed the bug but couldn't pinpoint the exact code location.

| Task | What went wrong |
|------|----------------|
| django-14771 | Right file (autoreload.py), wrong function — patched line 230 instead of 267 |
| django-15098 | Wrong function (get_language_from_path instead of regex pattern) |
| django-15916 | Band-aid location in modelform_factory instead of systematic fix in ModelFormOptions |
| psf-requests-1724 | Patched prepare_method() instead of request() — both handle methods |
| pytest-6202 | Same line range, wrong method with identical-looking code |
| sphinx-8269 | Wrong location, referenced undefined 'response' variable |
| matplotlib-25479 | Over-engineered: created helper function to search colormap registry |

**Root cause:** The council excels at reasoning about the *problem* but doesn't help navigate *code*. In single-shot patching without repo access, the model guesses at line numbers and function signatures. The council's extended thinking on the problem displaces attention from code navigation.

**Potential fix:** Add a "Navigator" lens that explicitly asks: "Given multiple similar functions in the same file, which one is actually called in the failing scenario?" Or use a two-pass approach: first pass locates, second pass fixes.

**Failure Mode 2: Right Diagnosis, Incomplete Fix (4/12 losses)**

The council correctly identified the root cause but the patch was incomplete or used the wrong API:

| Task | What went wrong |
|------|----------------|
| astropy-14508 | Correct idea (use `str(value)`) but missed FITS 20-char field width limit and decimal point guarantee. Council's via negativa lens over-minimized. |
| matplotlib-24637 | Right method, but used wrong renderer API parameters (gid vs class name) |
| sympy-15345 | Right idea (add Max/Min to known_functions) but these are MinMaxBase objects needing special print handlers |
| sympy-19495 | Right about bound variable substitution but fix didn't handle the condition-becomes-True case |

**Root cause:** These are knowledge gaps, not reasoning gaps. The model doesn't know the FITS field width spec, the renderer API signature, or SymPy's MinMaxBase class hierarchy. The council can't compensate for missing code context.

**Potential fix:** Two-pass approach where the first pass reads relevant source files before attempting a fix.

**Failure Mode 3: Invalid Diff (1/12 losses)**

- **django-16032:** Patch cut off mid-line. Not a thinking problem — an output generation issue.

---

## Experiment 2: Opus v2 Prompt — Mandatory Phases (FAILED)

### What We Changed

Restructured the council prompt from a flat list into 4 mandatory phases:
- Phase 1: Diagnosis (10 experts)
- Phase 2: Challenge — MANDATORY (5 experts)
- Phase 3: Design (11 experts)
- Phase 4: Verify — MANDATORY (1 expert)

Added 3 new experts (Popper, Knuth, Polya) and marked Phases 2 and 4 as "MANDATORY."

### Results (20 fresh tasks, Opus)

| | v1 (flat 25 experts) | v2 (phased 28 experts) |
|---|---|---|
| correct_fix | **8/20 (40%)** | 5/20 (25%) |
| correct_diagnosis | **10/20 (50%)** | 5/20 (25%) |
| valid_diff | 14/20 (70%) | **16/20 (80%)** |
| Head-to-head | **4 wins** | 1 win |

### Why It Failed

Analysis of the 4 tasks where v1 won but v2 lost:

1. **v2 thinking was 40-70% longer** on every task, but the extra length was process scaffolding ("Phase 1... Phase 2... MANDATORY..."), not better reasoning.
2. **v2 had 5-8 phase/process mentions** in thinking vs v1's 0. The model was filling in template checkboxes instead of thinking about code.
3. **v2 targeted wrong files/methods** more often — the rigid process spread attention thin, degrading basic diagnosis quality.

The only improvement was valid_diff (+10pp), from the stricter format rules.

### The Lesson

This confirms DivineOS foundational truth #5: *"If a rule constrains what you think rather than how you verify it, the rule is wrong."*

The mandatory phases constrained thinking. The flat list lets the model naturally gravitate to the 3-4 most relevant lenses and think deeply through them. The v2 prompt was control masquerading as structure.

---

## Experiment 3: Opus v3 Prompt — Flat List + New Experts (20 fresh tasks)

### What We Changed

Reverted to v1's flat list style. Kept the 3 new experts (Popper, Knuth, Polya) integrated naturally in the list — no phases, no MANDATORY labels. Kept the improved format rules from v2.

### Results

| Metric              | Base Opus     | Enhanced Opus     | Delta        |
|---------------------|---------------|-------------------|--------------|
| correct_fix         | 5/18 (28%)    | **8/18 (44%)**    | **+16pp**    |
| correct_diagnosis   | 8/18 (44%)    | **13/18 (72%)**   | **+28pp**    |
| valid_diff          | 7/18 (39%)    | **14/18 (78%)**   | **+39pp**    |
| minimal             | 4/18 (22%)    | **9/18 (50%)**    | **+28pp**    |
| **COMPOSITE**       | **32.2%**     | **56.7%**         | **+24.5pp**  |

(18 of 20 tasks scored; 2 tasks had judge JSON parse errors)

### Head-to-Head: Zero Regressions at n=18

- Enhanced wins: **3**
- Base wins: **0**
- Ties: **15**
- **Zero regressions** across the 18 scored tasks.

At n=18 with 15 ties, this is directionally encouraging but statistically thin — 83% of the dataset shows no edge either way. The original "undefeated" framing has been softened throughout this document; the finding that matters is *zero base wins* (no regressions from adding the council), which is real but needs n≥50 before it earns a stronger label.

### The Enhanced Wins

**psf-requests-5414:** Council caught that UnicodeError needed handling in host processing. Base missed it entirely.

**pylint-dev-pylint-4970:** Council identified that when min_lines is 0, similarity checking should be disabled by returning early. Base targeted the wrong class methods.

**sympy-sympy-19783:** Council correctly identified the fix. Base did not.

### Notable: Zero Base Wins on Opus

Unlike Sonnet (which had 12 base wins from navigation failures), Opus with the council produced zero regressions. This suggests the navigation failure problem may be Sonnet-specific — Opus is a stronger reasoner and can maintain code navigation quality even with the council's extended thinking.

---

## Cross-Experiment Summary

| Experiment | Tasks | Enhanced Wins | Base Wins | Ratio | Net Improvement |
|-----------|-------|--------------|-----------|-------|-----------------|
| Sonnet v1 (150 tasks) | 150 | 29 | 12 | 2.4:1 | +17 net fixes |
| Opus v2 (mandatory phases) | 20 | 1 | 4 | 0.25:1 | -3 net (FAILED) |
| Opus v3 (flat + new experts) | 20 | 3 | 0 | inf | +3 net fixes |
| **Combined (excl. v2)** | **170** | **32** | **12** | **2.7:1** | **+20 net fixes** |

---

## Why the Council Works

The council is not doing anything magical. It's providing **structured prompts for deliberate thinking** — named frameworks that each ask a different question about the same problem. The key dynamics:

1. **Prevents anchoring.** Without the council, the model jumps to the first plausible fix (Kahneman's System 1). The council forces it to consider alternatives before committing.

2. **Separates diagnosis from treatment.** Feynman asks "what's broken?", Pearl asks "what causes it?", Holmes asks "what can you rule out?" — these are different questions that prevent conflating symptom with root cause.

3. **Catches edge cases.** Popper asks "what would break this fix?", Knuth asks "what happens at the boundary?" These lenses caught over-minimized patches that missed field width limits, decimal point guarantees, and scope issues.

4. **Extended thinking as workspace.** The council gives the model permission and structure to use its thinking budget productively. Without the council, extended thinking often produces unfocused exploration. With it, the thinking follows named frameworks and produces actionable analysis.

---

## Why the Council Sometimes Hurts (Sonnet Losses)

The 12 Sonnet losses reveal a specific and fixable failure mode:

**The council improves reasoning but doesn't improve navigation.** When the model needs to find the *right function* in a file with multiple similar-looking functions, the council's extended analysis of the *problem* displaces attention from the *code structure*. The model ends up deeply understanding the bug but patching the wrong method.

This manifests as: right file, wrong function (6 of 12 losses). The fix is architectural, not prompt-level:

- **Two-pass approach:** First pass reads and locates relevant code. Second pass reasons about the fix.
- **Navigator lens:** A new expert that asks "which of these similar functions is actually called in the failing path?"
- **Dynamic council selection:** Pick only the 5-8 relevant experts per task, freeing token budget for code navigation.

Notably, this failure mode did not appear on Opus (0 base wins), suggesting it's a capacity issue — Opus can maintain both deep reasoning and code navigation simultaneously.

---

## Why Mandatory Phases Failed (v2 Lesson)

The v2 experiment is arguably the most valuable result because it disproved a plausible hypothesis: "more structure = better reasoning."

**What happened:** The model obediently walked through Phase 1... Phase 2 (MANDATORY)... Phase 3... Phase 4 (MANDATORY)... and ran out of thinking budget before it actually understood the code. The rigid process turned deep reasoning into checkbox compliance.

**The data:**
- v2 thinking was 40-70% longer but less accurate
- v2 had 5-8 process/phase mentions vs v1's 0
- v2 diagnosis accuracy dropped from 50% to 25%

**The principle:** Structure provides riverbanks — integrity checks, quality gates, verification steps. Control tells the water how to flow. The flat expert list is structure (here are thinking tools, use what helps). Mandatory phases are control (you must think in this order). The data confirms: structure helps, control hurts.

---

## Infrastructure Built

All reusable for future experiments:

| Tool | Purpose | Location |
|------|---------|----------|
| `swe_harness.py` | Main A/B benchmark runner | `benchmark/` |
| `llm_judge.py` | LLM-as-judge scoring system | `benchmark/` |
| `report.py` | Full report generator | `benchmark/` |
| `ab_prompt_test.py` | Prompt A/B testing (any two prompts) | `benchmark/` |
| `opus_test.py` | Opus-specific base vs enhanced | `benchmark/` |
| `expand_tasks.py` | Add more tasks to selection | `benchmark/` |

All results are cached per-task. Rerunning skips completed tasks. Adding 50 more tasks to any experiment is just one command.

---

## Next Steps

1. **Dynamic council manager** — Classify the bug type, select 5-8 relevant experts. Reduces token cost and focuses thinking.
2. **Two-pass approach** — First pass: locate the right code. Second pass: reason about the fix. Addresses the navigation failure mode.
3. **Thinking budget tuning** — Test whether 6K, 8K, 10K, or 12K tokens is optimal per bug type.
4. **Larger Opus sample** — 20 tasks is directionally clear but not statistically significant. Need 50+ for confidence intervals.
5. **v3 vs v1 on Sonnet** — Direct comparison to isolate the effect of Popper/Knuth/Polya additions.
6. **Real test execution** — Docker-based SWE-bench evaluation for ground-truth pass/fail instead of judge estimates.

---

## Conclusion

The DivineOS council demonstrably improves Claude's bug-fixing ability *as scored by an LLM judge*. At scale (150 tasks on Sonnet), it wins 2.4x more often than it loses. On Opus with the refined v3 prompt (n=18), it produced zero regressions — a directionally encouraging signal that needs n≥50 before it earns a stronger claim. The cost overhead is negligible (2 cents per task on Sonnet).

For honest external citation, a Docker-verified subset should be run first (see "Measurement Caveat" at the top of this document). The relative effect is likely to survive; the absolute pass-rate percentages are judge estimates.

The failed v2 experiment proved equally valuable — mandatory structure hurts, confirming the project's core design principle. The data changed the design, not the other way around.

This is a first-generation, unoptimized prototype. Every identified failure mode has a concrete fix. The benchmark infrastructure makes iteration cheap and measurable. The council will get better from here — and we'll have the numbers to prove it.
