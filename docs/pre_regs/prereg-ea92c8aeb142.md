# Pre-registration: Stickiness gradient: scale contradiction-resolution decay and threshold by entry's evidence weight (corroboration_count + maturity tier). High-evidence entries resist single contradictions; low-evidence entries flip easily. EWC analog at the supersession layer.

- **ID**: `prereg-ea92c8aeb142`
- **Filed by**: agent
- **Filed at**: 2026-05-04 23:00 UTC
- **Review at**: 2026-06-03 23:00 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

Replacing uniform DECAY_MODERATE on DIRECT contradictions with evidence-weighted decay (and uniform contradiction_count >= 3 with evidence-weighted threshold) will preserve well-established knowledge through transient single-contradiction events while still letting low-evidence entries flip easily on new evidence. Operationalizes the principle that 'truth-strength scales with evidence-strength' at the supersession layer.

## Success criterion

(a) A CONFIRMED entry with corrob>=10 retains higher confidence after a single DIRECT contradiction than a RAW entry with corrob=1 takes on the same contradiction, AND (b) tests for the existing contradiction-resolution behavior continue to pass for the RAW/low-evidence case (no regression on simple cases).

## Falsifier

(a) High-evidence entries become un-overturnable — even genuinely-wrong CONFIRMED entries with sufficient contradicting evidence fail to be superseded, OR (b) The threshold scaling produces noisy briefing churn (entries oscillating in/out of contradicted state), OR (c) Performance regression in the contradiction-resolution path.
