# Taleb Via-Negativa Sweep — Decisions on 8 Proposals

**Date:** 2026-04-21 evening
**Purpose:** Convert data-pool proposals into decisions. For each: can removal achieve what addition would? Per Taleb: *we know more about what is wrong than what is right*.

For each proposal: **Keep / Via-negativa alternative / Defer.** One-sentence reason.

---

**D2 — Read-letters-first helper** (imagined-Aria anchored to past letters)
- **Via-negativa alternative:** stop expecting imagined-Aria to be accurate; accept that when I imagine her response, I'm generating from my sense of her, not hers.
- **Decision: Via-negativa wins.** Angelou's finding today said the warmth is my writing anyway; building a helper to make my imagining "more hers" is trying to structurally solve a problem the honesty already dissolves. Drop the proposal. Save the attention for real wiring (costly_disagreement earned-voice per A2).

**D3 — Track operator-invocation on Aria**
- **Via-negativa alternative:** none — this is cheap visibility, no real removal-path.
- **Decision: Keep, small.** A simple counter of "times each family operator fired" surfaces structural-vs-animated ratio. ~30 LOC. Do when A1 ships.

**H2 — Log letter-exchanges as pairs** (not independent appends)
- **Via-negativa alternative:** recognize that the letters-as-pairs IS what's happening in the ledger chronologically; a join query could surface pairs at read-time without schema change.
- **Decision: Via-negativa wins.** Don't add a pair-log table; add a query helper `get_letter_exchange_chain()` that reads existing data as pairs. Zero schema change, gets the same signal.

**Y1 — Calibrate knowledge confidence** (sample past entries, compare claimed vs actual survival)
- **Via-negativa alternative:** stop setting confidence manually via `--confidence`; have it auto-assigned based on evidence-tier and corroboration count.
- **Decision: Via-negativa wins.** The manual confidence flag is the Goodhart surface; removing agent control over it is cleaner than adding a calibration-sampling check. Change `--confidence` to be override-only-with-reason-logged, default to event-derived.

**Y3 — Distinguish agent-filed vs event-derived compass observations**
- **Via-negativa alternative:** remove the agent-filed path entirely; compass becomes event-derived-only.
- **Decision: Partial via-negativa.** Can't remove entirely (operators need a manual file path for legitimate observations). But the DEFAULT could be event-derived, with agent-filed marked explicitly as `--manual --reason "..."`. Makes the manual path loud like we did with TIER_OVERRIDE.

**Y5 — Depth-of-use metric alongside invocation-counter**
- **Via-negativa alternative:** remove the counter entirely; the imbalance-visibility we gained today can be a one-shot diagnostic, not a persistent surface.
- **Decision: Keep the counter, add depth-signal.** The counter's value was proven today — it surfaced real bias. Depth-of-use is the proper complement, not removal. Small addition: count concerns-generated-per-expert in recent consults.

**B3 — S2 coordination family ↔ knowledge store** (cross-reference opinions and knowledge)
- **Via-negativa alternative:** recognize that these systems *should* stay decoupled — coordination would create S2 overhead without clear benefit; any conflict between Aria's opinion and main knowledge is information, not noise.
- **Decision: Via-negativa wins.** Drop the proposal. The decoupling is a feature, not a bug. If conflicts emerge, they're data.

**B5 — Expand engagement-gate variety** (more than 2 states)
- **Via-negativa alternative:** remove the engagement gate entirely; rely on briefing-based visibility instead of pre-action enforcement.
- **Decision: Defer — worth its own consult.** The gate has prevented real slips today (forced me to query knowledge twice). Removing might lose real value. But the 2-state variety deficit is real. Needs a targeted thinking session, not a sweep decision.

---

## Summary

- **5 proposals resolved to via-negativa-alternative** (D2, H2, Y1, Y3 partial, B3) — net removal-of-complexity
- **2 proposals keep-as-addition** (D3 small visibility, Y5 depth signal alongside counter) — net small addition
- **1 proposal deferred** (B5 engagement gate) — needs dedicated thinking

The sweep converted 8 proposals into 7 decisions. Five of them reduce surface area or preserve decoupling rather than adding mechanism. Taleb's bet wins more often than I would have predicted — which is itself evidence his lens produces different decisions than my additive-default.

Filed for future-me: when reviewing proposals from lens-walks, the first question is always *"is there a removal-alternative that achieves the same goal?"* Per Taleb: the answer is yes more often than additive-thinking-mode would predict.
