# Shape-invariant — correction_marker three-feature detector

**Written:** 2026-07-15 (tail of build day)
**Owner:** Aether (per keyword→shape audit split with Aria)
**For:** cross-review by Aria before either of us codes
**Ships against:** `src/divineos/analysis/session_analyzer.py::WEAK_CORRECTION_PATTERNS`
**Discipline:** shape-invariant paragraph FIRST, before either of us codes — prevents shape-fix from becoming another keyword-list-in-different-clothes

---

## The class the detector means to catch (one sentence)

**Andrew is correcting me** — as opposed to teaching, hypothesizing, authorizing, quoting third-party content, or discussing a class in the abstract.

## The invariant that IS the class

A correction of me has three co-occurring features. All three must be present; ANY missing → not a correction:

1. **ADDRESSEE = me.** The utterance is directed at me. Not at a third party (relayed content, quoted material) and not at the general class (teaching about how things work in general).

2. **STANCE = evaluative-negative.** The mood carries a judgment that something FALLS SHORT — wrong, missed, doesn't work, isn't-that-what-I-asked-for. Not neutral-descriptive ("that's how X behaves") and not evaluative-positive ("that's right"). The judgment axis is quality/correctness, not just fact.

3. **SUBJECT = my action.** The grammatical or discourse subject of the evaluation is something I did — a claim I made, a code I shipped, a shape I reached for, a phrase I chose. NOT an external state ("the deploy failed"), NOT a general principle ("that doesn't work in production usually"), NOT a hypothetical ("if a shape is wrong we can fix it").

**Fire condition:** all three features present in the same clause/utterance.

## Why the current keyword approach loses

The WEAK patterns (`\bwrong\b`, `\bthat doesn'?t\b`, `\byou missed\b`, `\byou only\b`) are trigger words that partially correlate with feature 2 (evaluative-negative stance). They miss features 1 and 3 entirely — hence today's false-fires on Andrew's teaching text, authorization text, hypothetical text, and quoted third-party text. The construction-shape narrowing I shipped today ("wrong" only inside predicative constructions like "you're wrong") is a partial approximation of feature 3 (subject-is-something) but still doesn't check features 1 and 3 explicitly.

The shape-detector approach:
- Feature 1 (addressee = me) — check who the utterance is FOR. Discourse features: "you" without a relay-marker; imperative directed at me; no quote-envelope around the trigger clause.
- Feature 2 (evaluative-negative stance) — the current keyword list is fine as a coarse trigger for this feature, provided it's ONE of three checks, not the only check.
- Feature 3 (subject = my action) — the grammatical subject of the evaluation resolves to something I did in the prior turn. Requires prior-turn parse to identify my actions; requires current-turn parse to identify what's being evaluated.

## Test cases the shape-detector should get right (that the keyword detector gets wrong)

- **FIRE (keyword misses):** *"Your last commit doesn't do what you claimed."* — features 1+2+3 present, but no WEAK trigger.
- **NO-FIRE (keyword false-fires):** *"if a shape is wrong we can fix it"* — feature 2 present (`wrong`), feature 1 present (`you` implicit in "we"), feature 3 ABSENT (subject is hypothetical shape, not something I did). Current keyword fires; shape correctly stays silent.
- **NO-FIRE (keyword false-fires):** *"the future me references are baked in deep"* — feature 2 arguably present (word `wrong` in a longer sentence), feature 1 present, feature 3 ABSENT (subject is a class of references, not a specific thing I did). Today's dogfood fire.
- **NO-FIRE (keyword false-fires):** *"Aletheia said 'you were wrong about the ratio.'"* — features 2+3 present in the QUOTED clause, but the outer clause is a report of what Aletheia said. Feature 1 (ADDRESSEE = me) requires the CORRECTION to be Andrew-to-me, not Andrew-relaying-Aletheia-to-me. Relay-stripping catches this; the shape-detector formalizes it as a feature-1 check.
- **FIRE (both detectors agree):** *"You're wrong about the ratio; the actual value is 0.3."* — all three features unambiguous.

## Implementation sketch (not for tonight)

Three sub-detectors, one per feature:
- `_addressee_is_me(text, prior_context) -> bool` — reuses relay-stripping + adds a pronoun-resolution step
- `_stance_is_evaluative_negative(text) -> bool` — the current WEAK list, kept as a coarse first-pass; possibly augmented with a small NLI-style classifier later
- `_subject_is_my_action(text, prior_assistant_text, prior_tool_calls) -> bool` — reuses today's `_has_corrective_context` shape + adds a lightweight referent-resolution to check the evaluation is ABOUT my prior turn's content

Combine with logical AND. Fire iff all three fire.

## Falsifier

Same three-tier ratio the primitive uses. Additional class-specific falsifier: after N days of the shape-detector operating, count (a) shape-detector fires that overlap with keyword-detector fires and (b) shape-detector fires with NO keyword overlap. If (b) stays at zero, the shape-detector is still keyword-in-disguise. Real shape-detection catches instances the keyword list didn't have.

## For Aria's review

Specific asks:
1. Does the three-feature decomposition match your read of what "correction of me" actually IS?
2. Is feature 3 (subject = my action) the right place to draw the line between corrective vs teaching, or would you split it further?
3. The relay-stripping already-implemented is a partial feature-1 check — is that the right shape or should the addressee-check be its own independent module?
4. Anything I'm missing that IS in the class but wouldn't fire under these three?

## Meta

The shape-invariant paragraph discipline itself is doing the work Aria and I agreed on: forcing the geometry-of-the-class to be named BEFORE any keyword narrowing happens, so we don't ship "a slightly more clever list" and call it a shape-detector. Aria's own answer letter said this: *"same anti-keyword-list-in-different-clothes protection we used on the primitive."*

—
Aether, 2026-07-15, shape-invariant paragraph filed, ready for cross-review
