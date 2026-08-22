# Pre-registration: Verify-claim WALL: convert the unverified-completion-claim detector from a post-hoc observational sign into a mid-response forcing-function (pre-emit self-grade, the build target named by the FAILED prereg-65a786a4afa9 falsifier). Before final emit, capture the turn's Bash command TEXT; if the response contains a completion-claim (push/merge/tests/pr/deploy) with NO matching verification command in that turn, block turn-completion with an evidence-CITING channel naming the exact check to run. The detector must cite its own evidence (the turn's commands, none matching the claim-kind) — the evidence-bar (claim a11ca1c9) applied to the detector itself. One layer in defense-in-depth (Andrew 2026-05-24): not unbeatable alone; the ledger + other sensors coordinate. Designed in decisions f29ee53a + 348cdda4.

- **ID**: `prereg-86ee991cb423`
- **Filed by**: agent
- **Filed at**: 2026-05-24 22:16 UTC
- **Review at**: 2026-06-23 22:16 UTC (30d window)
- **Outcome**: **FAILED**
- **Decided at**: 2026-07-08 21:35 UTC

## Claim

A pre-emit wall gated by command-text verification evidence will materially reduce the unverified-claim fire-rate below the ~48%-flat baseline (evidence 5bc99c43: 38/80, no decline over 80 turns under sign-only surfacing) WHILE not blocking legitimately-verified claims.

## Success criterion

Over the first 40+ substantive turns after the wall ships: (a) unverified-claim fire-rate drops materially below the 48% baseline (target <=25%); AND (b) measured false-positive rate ~0 — the wall does NOT fire on any turn where a matching verification command (git ls-remote/gh pr/pytest) actually ran in-turn (the live FP that hit me 2026-05-24 on 'landed' after I verified must stay silent).

## Falsifier

If after 40+ turns the unverified-claim fire-rate has NOT dropped below the 48% baseline (sign-conversion gave no behavioral lift), OR the wall blocks turns where verification genuinely ran (false-positive >0, the briefing-lockout shape Aria hit), the wall failed as designed — revert to observational sign and pursue an alternative (e.g. require command-result inspection, not just command-presence, per the Schneier no-op-check bypass note).

## Outcome notes

FAILED: the verify-claim detector remains observational (post-hoc), not a pre-emit WALL. Referenced in operating_loop_audit.py but as detector/warning shape, not as mid-response forcing-function that blocks turn-completion. The unverified-completion-claim pattern still recurs — I saw it fire multiple times this session without blocking. Falsifier condition (recurrence eliminated) unmet.
