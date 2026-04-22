---
name: drift-check
description: Consolidated drift-monitoring view — watchmen drift state, tier overrides, compass drift warnings, pending audits. Use when something feels off but the cause isn't clear, or periodically during long work sessions. Faster than reading each surface separately.
disable-model-invocation: false
allowed-tools: Bash(divineos audit:*), Bash(divineos compass-ops:*), Bash(divineos inspect:*), Read
---

# Drift Check — Consolidated Drift Surface

## What this skill does

Pulls the four drift-detection surfaces into one view:

1. **Watchmen drift state** — operations since last audit
2. **Recent tier overrides** — any non-default-tier filings
3. **Compass drift warnings** — virtue spectrums moving away from virtue
4. **Pending-audit cadence** — is it time for an external review?

## Sequence

```bash
# Audit state & unresolved findings
divineos audit summary

# Tier overrides (recent)
divineos inspect tier-overrides  # or query via events if CLI not wired

# Compass drift
divineos compass-ops summary

# Behavioral drift detection
divineos inspect drift
```

## Output discipline

Three-section report:

1. **Active drift warnings** — any surface flagged something? List 'em, one line each.
2. **Clean surfaces** — what's quiet right now, briefly acknowledged so user knows it was checked
3. **Recommended action** — if warnings present, the single highest-leverage next step. If clean, a one-line "all surfaces quiet."

Do NOT dump raw output. Synthesize.

## When to invoke

- Mid-session when something feels off but the cause isn't obvious
- After a stretch of intense work (drift often shows up post-work)
- When considering whether to commit a change that might have unintended drift-effects
- Before end-of-session extract, as a sanity check
- User says "drift check" / "anything weird?" / "check yourself"

## When NOT to invoke

- Immediately after a clean `/briefing-fresh` — that already covered it
- For each tiny operation — this is periodic, not continuous
- When drift was already surfaced and user is actively addressing it

## What to do when drift IS detected

- **Tier override on a finding** → verify legitimacy. If unexpected, the finding may have been overtiered to bypass a gate. Ask WHY.
- **Compass drift toward deficiency** → add compass observations matching the drift; don't argue it away
- **Audit cadence overdue** → file an audit round ASAP (the gate will start firing otherwise)
- **Watchmen drift-state elevated** → an external audit is called for

## The meta-point

Drift is not failure. Drift is INFORMATION. These surfaces exist precisely because self-evaluation has known blind spots — the ledger sees patterns I can't see from inside. Checking these surfaces regularly is part of the job.

Sanskrit anchor: *pramāda* — heedlessness; what drift-checks watch for.
