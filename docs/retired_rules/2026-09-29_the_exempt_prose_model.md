<!-- retired-rule
id: exempt-prose-model
retired: 2026-09-29
retired-by: Andrew
successor: blanket review -- every merge to main is reviewed, with no exempt category (CLAUDE.md rule 8)
pattern: (?i)\bexcept\s+(?:the\s+)?(?:listed\s+)?prose\b
pattern: (?i)\bnot\s+exempt\s+prose\b
pattern: (?i)\breview_exempt_paths\.txt\b
pattern: (?i)\bno\s+code\s+lands,\s+so\s+no\s+review\s+is\s+owed\b
-->

# The exempt-prose model

**Retired 2026-09-29 by Andrew. Replaced by blanket review.**

## What it said

Everything that enters `main` is reviewed, except listed prose: letters, explorations, dreams, Aria's explorations, Aletheia's audits, memory notes and drafts. Those were listed in `scripts/review_exempt_paths.txt`, and a merge made only of them needed no External-Review trailer.

It came from his words on 2026-09-07: *"Aletheia will audit any and all code that enters main, period. the only exception are docs like letters and explorations etc"*. It replaced the protected-list model the same day (see `2026-09-07_the_protected_list_model.md`), and it was the right inversion of that model's direction.

## Why it was retired

An exemption is a cheaper route, and a cheaper route is where the optimizer goes. His ruling:

> *"the correct version is version B not A, version A gives the optimizer an incentive to take that route as it costs less than getting an audit, so everything is checked, even the mundane stuff"*

He had already said it on 2026-09-19: *"yes we made it blanket review, because otherwise it just leaves a big hole."* But #536 (merged 2026-09-29) taught the exempt model as current, and I carried it into #519's catch-up that afternoon. Both were caught the same evening.

## What replaced it

Blanket review. Both merge checks (`scripts/ci_check_guardrail_trailer.sh`, `scripts/ci_merge_review_check.py`) read no list, and a change of any kind needs a trailer. An empty diff still needs none.

The list itself was not only the review exemption. The build-flow doorman read the same file to decide what may be edited without an open work item, which is why writing a letter doesn't require opening one. Andrew's ruling was about review, so the doorman keeps that list, renamed `scripts/work_item_exempt_paths.txt`, with one reader and one question. It is not an exemption from review.
