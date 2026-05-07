# Pre-registration: Reflexion structured failure memory: add failure_shape and preventive_action columns to lesson_tracking, plus a shape-indexed retrieval surface, so when the same failure-shape recurs the substrate surfaces the relevant preventive-action proactively rather than relying on prose description matching

- **ID**: `prereg-f55843b9d1fd`
- **Filed by**: agent
- **Filed at**: 2026-05-04 23:09 UTC
- **Review at**: 2026-06-03 23:09 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

Adding structured (failure_shape, preventive_action) pairs to lessons and a shape-matched retrieval surface will allow the substrate to recognize when a current situation matches a known-failure-shape and surface the pre-existing preventive action before the failure recurs. Today's lessons (botched-rebase, half-fix shape, etc.) become structurally retrievable rather than prose-search dependent.

## Success criterion

(a) Lesson can be filed with explicit (failure_shape, preventive_action) pair AND retrieved by shape via a query function, AND (b) Existing free-form lessons continue to work unchanged (NULL shape/action backward-compatible).

## Falsifier

(a) Shape-matching produces too many false positives — retrieval surfaces unrelated lessons because string-overlap is too loose, OR (b) Operators stop using free-form lessons and feel forced into structured-only — losing the prose nuance that captures lessons that don't fit shape/action format, OR (c) Schema migration breaks existing lesson queries.
