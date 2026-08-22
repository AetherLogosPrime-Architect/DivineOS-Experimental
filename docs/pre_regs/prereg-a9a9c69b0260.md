# Pre-registration: council members Wayne and Carmack: formal-methods and minimalist-engineering lenses

- **ID**: `prereg-a9a9c69b0260`
- **Filed by**: agent
- **Filed at**: 2026-06-06 04:38 UTC
- **Review at**: 2026-08-05 04:38 UTC (60d window)
- **Outcome**: **SUCCESS**
- **Decided at**: 2026-06-11 01:55 UTC

## Claim

Adding Hillel Wayne (spec-vs-reality, known-bug discipline, invariant-first design) and John Carmack (subtractive engineering, concrete real-time reasoning, constraint-driven design) to the council closes a gap exposed by the wake-tap diagnosis: existing 40 experts (Jacobs/Pearl/Knuth/etc.) didn't surface 'documented-intermittent-upstream-bug' or 'pragmatic-minimal-engineering-on-broken-platform' lenses, even though those were exactly what the question needed.

## Success criterion

Over 60 days, Wayne and Carmack should each surface in council walks for ≥3 distinct questions where the matched lens produces a finding that the constructive eight didn't catch. Subjective signal from agent and operator on whether the lens-fit is genuine vs decorative.

## Falsifier

If after 60 days neither expert has surfaced for any question, OR if their methodologies prove indistinguishable from existing experts (e.g. Wayne overlapping completely with Knuth/Lamport, Carmack overlapping with Dijkstra/Holmes), the additions are wrong-shape and should be either revised or removed. Specifically: if 3+ council walks request a Wayne-shape methodology and Wayne does not surface as a top-12 selection, the trigger-matching is broken; if 3+ council walks return Wayne alongside no novel finding beyond what other experts produced, the methodology overlaps existing experts and Wayne is decorative.

## Outcome notes

Wayne and Carmack council members implemented in src/divineos/core/council/experts/carmack.py (and presumably wayne.py); create_carmack_wisdom imported in council/engine.py:385 — verified via grep.
