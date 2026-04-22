---
name: prereg
description: File a pre-registration (Goodhart-prevention discipline) for a new mechanism before deploying it. Captures claim, success criterion, falsifier, and review date. Use when adding detection logic, thresholds, or optimization targets. Ensures the mechanism has an honest review built in.
disable-model-invocation: false
allowed-tools: Bash(divineos prereg:*), Read
---

# Prereg — Pre-Registration Filing

## What this skill does

Files a pre-registration — a Goodhart-prevention discipline where, before deploying any new detection mechanism, threshold, or optimization target, we commit to a success criterion AND a falsifier AND a scheduled review date. No mechanism ships without its own honest review clock.

## Why pre-regs matter

New detectors can game their own metrics in ways that look like success but aren't. A pattern-detector that reports 100% accuracy is suspect until tested against data it didn't train on. A hedge-monitor that reports zero hedges could mean we solved hedging OR that the monitor is silent. The pre-reg captures what we EXPECT to see and what would prove us wrong — before we can post-hoc-rationalize the result.

## Fields

- **Mechanism** — what's being deployed (name it precisely)
- **Claim** — what we believe this mechanism will do
- **Success criterion** — what observable output would indicate the mechanism works
- **Falsifier** — what would prove it doesn't work or has drifted
- **Review date** — when to actually come back and check (30/60/90 days typical)

## Filing

```bash
divineos prereg file "<mechanism>" \
  --claim "<what we believe it does>" \
  --success "<observable success criterion>" \
  --falsifier "<what would prove it wrong>" \
  --review-days 30
```

For mechanisms whose reviews needs specific actors, add `--review-actor aria` or similar.

## Sequence

1. **Name the mechanism** precisely — not "the new detector" but "the identity-drift detector in aria_ledger that checks for third-person narration and daughter-framing"
2. **State the claim** — what do we believe this will do in practice?
3. **Name the success criterion** — how would we KNOW it's working? Be observable and specific. "Drifts detected before write to family_interactions" is better than "drifts caught."
4. **Name the falsifier** — what would prove it wrong? "Zero drift events logged over 30 days AND we observe drift in subagent output" would mean the detector is silent, not that drifts stopped.
5. **Review date** — 30 days typical. Longer for mechanisms expected to see rare events.
6. **File.**

## Examples (from DivineOS history)

- **Family-member persistence foundation** — prereg with foundation-claim + falsifier tying shipping to external-actor outcome gate + review 30 days out
- **Pattern anticipation** — claim "surfaces recurring patterns before user mentions them"; falsifier "no pattern surfaces accurately over 30 days"; review 30d

## When to invoke

- Before deploying ANY new detection logic (hedge-monitor, drift-detector, sycophancy-detector variants)
- Before adjusting a threshold that affects behavior
- Before adding a new event-type that will be used for audit or accountability
- User says "prereg" / "file a pre-registration" / "let's lock this with a review clock"

## When NOT to invoke

- For pure refactors that change no behavior
- For mechanisms already covered by an existing pre-reg
- For one-off fixes that won't generalize into a detector

## Overdue discipline

`divineos prereg overdue` surfaces any pre-regs whose review date has passed. This is BRIEFING-SURFACED — tomorrow-me will see "you have N overdue prereg reviews" automatically. That's the clock that makes the discipline real.

Sanskrit anchor: *saṅkalpa* — the formal commitment made before beginning.
