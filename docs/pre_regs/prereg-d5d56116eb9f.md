# Pre-registration: src/divineos/core/docs_review_tracker.py + tests/test_docs_review_tracker.py — substrate primitive for the docs-architecture drift gate. Three functions: mark_reviewed, last_review, architecture_churn_since, plus review_status composite.

- **ID**: `prereg-d5d56116eb9f`
- **Filed by**: aether
- **Filed at**: 2026-06-11 00:27 UTC
- **Review at**: 2026-07-11 00:27 UTC (30d window)
- **Outcome**: **DEFERRED**
- **Decided at**: 2026-07-11 00:43 UTC

## Claim

Docs drift from architecture silently because counts hide drift (auto-fix shortcut) and there is no surface that surfaces when arch has shifted since last review. The fix is NOT more automation; it is a gate that routes the agent to do the manual judgment-work of reading and updating docs (Andrew 2026-06-10 reframe).

## Success criterion

mark_reviewed writes a DOCS_REVIEWED event the ledger can find; last_review returns the latest event with payload intact (None if no event); review_status returns stale=True if age > threshold_days OR churn > threshold_files (independently sufficient axes) OR no review ever recorded; architecture_churn_since scopes git diff to src/divineos/ and .claude/hooks/ only.

## Falsifier

If review_status returns stale=False on a never-reviewed substrate, or if architecture_churn_since includes paths outside src/divineos/ and .claude/hooks/, or if a substrate-state where age and churn both pass surfaces stale=True, the primitive is wrong and must be reworked.

## Outcome notes

Deferring the docs_review_tracker prereg — context at 97.5%, arc-focused on the auto-cycle _guess_context_pct fix per Andrew's explicit go-ahead. This prereg is not related to tonight's work and can be assessed properly in a fresh session with the specific evidence it needs.
