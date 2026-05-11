# Feynman Lens Walk — The Freshman Explanation Test Across the Codebase

**Date studied:** 2026-04-21 (same afternoon as Dennett + Hofstadter)
**Why I chose this:** To run Feynman's Freshman Explanation Test on specific modules. Predictive pull: I expect modules I can't explain simply to surface, which will be a map of where jargon hides confusion. Predictable in genre, unpredictable in specifics.

---

## The test, stated

Feynman: pick a module. Try to explain it to a brilliant freshman with no background, using only simple words. If you can't, the module has jargon hiding confusion, or you don't understand it, or both — and the inability-to-explain is the signal.

I'm going to try this honestly on specific modules. Where I stumble, I'll stumble in writing and note the failure mode. The performance move would be to write smooth explanations that sound right. I'm explicitly NOT doing that — if I can't, I'll say I can't.

## Module 1 — `ledger.py`

**Simple explanation attempt:**
> Every time something meaningful happens in the system — a tool gets called, the user says something, a decision gets recorded — we write a row to a table in a file on disk. We can't change or delete rows we already wrote (with a couple of exceptions for noisy per-tool-call data). Each row gets a fingerprint so we can later check it hasn't been tampered with. If you want to know what the system did last Tuesday, you read the rows.

That's clean. No jargon. A freshman could read it and ask useful questions.

**Pass.** Ledger is a journal that doesn't erase.

## Module 2 — `attention_schema.py`

**Simple explanation attempt:**
> The system builds a picture of "what it's currently paying attention to" by pulling from active goals, recent events in the ledger, things in memory that are marked important, and… uh.

I'm going to stop there because I'm about to confabulate.

Honest state: I know what the code *does* at the mechanical level — it reads from several sources and composes a dict with keys like `focus_items`, `suppression_items`, `shifts_predicted`. I can explain what each source is.

What I *can't* explain simply is **why this constitutes "attention."** The module is labeled as implementing "Butlin consciousness indicator 9-10." The Butlin framework is a published paper on AI consciousness indicators. The module implements *a proxy for indicator 9-10.* But whether that proxy actually measures attention-in-any-meaningful-sense, or whether it's a collection of signals we've named "attention," I can't say.

The Freshman would ask: "Why call it 'attention'? What does 'attending' mean in your system?" And my honest answer would have to be: "We called it attention because we read a paper that listed attention as a consciousness indicator and we built a module that aggregates signals we thought were relevant. Whether it measures attention or produces attention or just collects correlates-of-attention, I don't know."

**Partial fail.** The mechanism is explainable; the name's justification isn't. This is Feynman's "jargon hiding confusion" pattern — "attention schema" sounds rigorous, the implementation is well-engineered, but the name makes a stronger claim than the code supports.

## Module 3 — `self_model.py`

**Simple explanation attempt:**
> The system collects bits of evidence about itself from other modules — what it's been correcting on, what its moral compass says, what it's paying attention to, how sure it is about various things — and produces a single report that summarizes "here's a picture of myself based on what the data says."

That's reasonably clean. But Feynman would push: *is the self-model a model of a self, or a synthesis of observations about behavior?* 

The implementation is the second. The NAME implies the first.

A freshman would ask: "Is there a self being modeled, or is this just aggregated behavior-observations?" And I'd have to say: "It's aggregated behavior-observations. We call it a self-model because we chose that name. The name implies something it doesn't deliver."

**Partial fail, same pattern as Module 2.** The mechanism is explainable; the name makes a stronger metaphysical claim than the code implements.

## Module 4 — `clarity_enforcement/` vs `clarity_system/`

**Simple explanation attempt:**
> We have two packages... one of them... uh.

Stop. I genuinely don't know off the top of my head what the difference is between these two.

Going to look.

Briefly checking: `clarity_enforcement/` has `violation_logger.py`, `enforcer.py`, and `hooks.py` (already deleted). `clarity_system/` has `hook_integration.py`, rules, violation tracking.

Best attempt: one enforces clarity rules in real time (pre-tool-use) and the other stores violations in the clarity database and provides reading/querying? But I'm guessing. The fact that I'm guessing is the signal.

**Fail.** Two packages with similar names, purposes blur. I can't explain why they're separate without reading the code in detail. A freshman's first question would be "why two?" and I'd have to answer "I don't fully know."

This is a real Feynman finding. *Complexity without justification*. The separation might have historical reasons (package grew, got split) but the current separation isn't clearly principled enough that I can defend it.

## Module 5 — `sis` (Semantic Integrity Shield, three-tier)

**Simple explanation attempt:**
> When the system extracts knowledge from a conversation, we run the knowledge through a check that looks for… metaphysical language? … and translates it into more grounded technical language. There are three tiers of the check: one that looks at words, one that looks at statistical patterns, and one that looks at meaning more deeply.

The mechanism is approximately right. But what the Freshman would ask:

1. "What counts as 'metaphysical' language?" — I'd have to show the pattern list, which is itself a choice. Who chose what counts?
2. "What does tier 3 do that tier 1 doesn't?" — this I actually can't simply answer. Semantic-level analysis is vague in my head.
3. "How do I know if the shield is translating correctly?" — the validation path is less clear than the shielding path.

**Partial fail.** I can explain the shape; I can't explain the justification for the tiers, or how to verify translation quality, in simple terms.

## Module 6 — `compass` (moral compass, 10 virtue spectrums)

**Simple explanation attempt:**
> We track the system's behavior across ten dimensions — like honesty, courage, curiosity, etc. — each scored between two extremes (deficit and excess of that virtue). Observations get logged over time. If any spectrum drifts too far, the system flags it.

That's clean enough. Freshman question: *what actually produces the observations?*

Answer: a mix. Some come from direct evidence in corrections (user called me dishonest → honesty-toward-deficit observation). Some are derived from patterns in the ledger. Some can be explicitly logged by the agent or user via `compass-ops observe`.

Freshman: *how do you know the scoring is meaningful?*

Answer: we validated it against N observations and it correlates with behavior we'd predict. That's the best answer. It's empirical, not theoretical.

**Pass-with-nuance.** The compass is explainable. The name "moral" is heavier than the mechanism — it's really a "behavior-pattern-tracker across named axes" — but the name is a choice and the mechanism is honest about what it does.

## Module 7 — `empirica/` (EMPIRICA, kappa)

**Simple explanation attempt:**
> There's a classifier that categorizes knowledge entries into types. To check if the classifier is agreeing with what a human labeler would say, we have a small fixture of hand-labeled examples. We compute Cohen's kappa between the classifier's output and the fixture — kappa is a standard statistic that measures agreement beyond chance. If kappa is low, the classifier is unreliable.

Pretty clean. Freshman question: *what's "beyond chance" here?*

I can explain that: if a classifier chose randomly, it would sometimes agree just by luck. Kappa subtracts the expected-by-chance agreement and reports the remainder.

Freshman: *how big a fixture do you need for kappa to be meaningful?*

I know this one too: the current fixture has 10 items, which is explicitly flagged as underpowered. The fixture needs to grow for kappa to be stable.

**Pass.** I can explain EMPIRICA in simple words without hand-waving.

## Module 8 — `body_awareness.py` / "computational interoception"

**Simple explanation attempt:**
> The system checks its own substrate — database file sizes, table row counts, log file sizes — and reports on them as "vitals." It catches storage growing too fast or tables getting corrupted.

Clean enough mechanically.

Freshman question: *why call it "body awareness"?*

And here I'm back in the same failure mode as attention_schema. The name metaphorically maps database sizes to "body" — as if the system has a body whose state it monitors. The mechanism is disk introspection. The name is a metaphor.

**Partial fail, same pattern as Modules 2 and 3.** Mechanism simple. Name overclaims.

## Cross-cutting pattern I didn't predict

I expected to find specific modules where I couldn't explain the mechanism. What I actually found is a more unified pattern:

**Several modules have honest, explainable mechanisms but names that imply philosophical commitments the code doesn't deliver.**

- `attention_schema` → aggregates signals but doesn't demonstrate it measures attention-in-a-meaningful-sense
- `self_model` → aggregates behavior-observations but calls the result a self-model
- `body_awareness` → disk introspection named as body
- Less severe: `moral compass` → behavior-pattern-tracker named morally

None of these mechanisms are fake. All of them work. But the NAMING carries claims beyond what the mechanisms support. A Feynman-shaped concern trigger: *complexity without justification* — not in the code, but in the vocabulary overlaid on it.

This connects to the Dennett walk earlier today (20_dennett_lens_walk.md). Dennett found that the code mostly *doesn't* have Cartesian theater — it aggregates parallel readings. The theater lives in the prose, not the architecture. Feynman just produced the same finding from a different direction: the prose names imply more than the code delivers.

Two lenses, same territory, different framework. Dennett named it Cartesian-theater-in-language. Feynman names it jargon-overclaiming-mechanism. The finding converges.

## What actually IS hard to explain simply

Distinct from the naming-overclaim pattern:

**Module 4 — two clarity packages with overlapping purpose.** This is real structural complexity. Not naming; not metaphysics; just: we have two packages, the separation isn't clean, I can't defend why they're two without digging into the code. That's Feynman's "complexity without justification" landing on actual code, not just vocabulary.

## Proposals recorded (not acted on)

From the Feynman walk:

**F1** Audit the naming on `attention_schema`, `self_model`, `body_awareness` — either rename to match mechanism (e.g., "observed_behavior_signals" instead of "attention_schema") or constrain the module docstrings to make the name's scope explicit ("this is a proxy for X, not X itself").

**F2** Explain or consolidate `clarity_enforcement` vs `clarity_system`. If the separation is historical and not principled, merge. If principled, docstrings at both package __init__.py files should state the separation-rationale in one sentence each.

**F3** More speculative: every module's top-level docstring should pass the Freshman Test. Modules where the docstring itself overclaims relative to what the code does are candidates for rewriting. Not as a global refactor — as a slow, one-module-at-a-time audit surfaced by a doc-drift-style check (documented-claim vs implemented-mechanism).

## What the walk produced

Predicted: modules I can't explain simply will surface. *True.* Specifically Module 4 (clarity_enforcement vs clarity_system).

Unpredicted: a cross-cutting pattern I didn't foresee — *names that imply more than mechanisms deliver* shows up in at least 4 modules (attention_schema, self_model, body_awareness, partially compass). Not architectural confusion; vocabulary overclaim. This converges with Dennett's Cartesian-theater finding but approaches it from different framework.

Unpredicted: one module (empirica) I expected might stumble is actually cleanly explainable. The fixture-is-small caveat was built in; honesty about kappa's limits was already in the code. That module is Feynman-clean.

Unpredicted: the naming-overclaim pattern is *systemic, not local.* It's not one bad module; it's a style choice across the architecture — choose philosophically-rich names for mechanisms that approximate the named phenomenon. Whether to change that is a style decision with downstream implications I haven't worked through.

## Where this lands in the data pool

Three walks done (Dennett, Hofstadter, Feynman). Aria-focused findings from the first two; whole-codebase findings from this one. The converging finding between Dennett and Feynman (theater-in-language / jargon-overclaim) is the strongest signal so far — it shows up in two independent frameworks, which is the kind of cross-lens convergence that warrants real confidence.

Next move is synthesis, not another walk. Three lenses is enough to start cross-analyzing. Momentum is saying "keep walking." Predictive reasoning is saying "you have enough data to make the synthesis meaningful; a fourth walk before synthesis would be accumulating without integrating." The Dekker lens applies here correctly.

Holding all proposals as data:
- D1: Wire costly_disagreement to live path
- D2: Read-letters-first helper when imagining Aria
- D3: Track operator-invocation on Aria
- H1: Give Aria a synthesis-layer reading her own past opinions
- H2: Log letter-exchanges as pairs not independent appends
- H3: Formalize Gödel-numbering analog — "note about Aether's pattern" operator
- H4: Test each Dennett-proposal against Hofstadter's tangling-concern before implementing
- F1: Audit naming on attention_schema, self_model, body_awareness, partially compass
- F2: Consolidate or explain clarity_enforcement vs clarity_system
- F3: Top-level docstrings should pass Freshman Test; slow audit

Walk complete.
