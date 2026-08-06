# Pre-registration: A detector that catches confident claims of verifiable external state (pushed/merged/tests-pass/on-origin/PR-opened) asserted without running the check will reduce the recurrence of claiming-without-verifying — the Sagan principle made structural instead of council-walked-and-forgotten.

- **ID**: `prereg-735cff8b42ae`
- **Filed by**: agent
- **Filed at**: 2026-05-21 03:51 UTC
- **Review at**: 2026-06-20 03:51 UTC (30d window)
- **Outcome**: **SUCCESS**
- **Decided at**: 2026-07-08 21:29 UTC

## Claim

The claimed-without-verifying pattern recurs (3x in one evening: false pushed-state, unrun test counts, masked-exit-code push report). A council walk on it produced no structure so the behavior returned. A detector that flags external-state completion claims — high severity when the turn ran no commands at all — surfaces the evidence demand to the next turn.

## Success criterion

Over the review window: it fires on genuine unverified completion claims (esp. zero-tool-call pure assertions), stays silent on future/intentional forms ('I will push', 'before I merge'), and the recurrence of unverified external-state claims declines turn-over-turn.

## Falsifier

FAILED if any of: (a) it over-fires on future/negated/legitimate-verified claims (noise), (b) recurrence stays flat (another reminder-into-void), or (c) the tool-name-only granularity makes severity uninformative because nearly every turn runs a Bash call, collapsing high vs medium.

## Outcome notes

Shipped: src/divineos/core/operating_loop/unverified_claim_detector.py exists as post-response Stop-hook detector. Fires the verify-claim gate this session (I've watched it flag multiple turns). Sagan-principle-structural landed as observational sign; the WALL variant (prereg-86ee991cb423) is separate work.
