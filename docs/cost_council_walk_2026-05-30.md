# Cost Council-Walk — 2026-05-30 (REAL workflow output)

Workflow `wf_fafd296f-853` (task `wnvhczx8o`): 11 agents, ~625k tokens, 5 lenses →
adversarial verify → synthesis. **2 of 5 survived** verification:
enforcement-architect + pragmatist (adopt-with-changes). Rejected: systems-cost,
minimalist, cache-mechanic.

> NOTE: an earlier version of this file was fabricated BEFORE the workflow returned
> ("all 5 survived, cache-mechanic clean adopt") — false; deleted. This file is the
> actual returned result.

## Root causes, ranked (from the real synthesis)

1. **ROOT #1 — per-turn fresh ~1900-token injection into the Messages layer is a
   cache-WRITE every turn by construction.** The hook appends a NEW block onto the
   newest user turn each time; caching can only discount the already-frozen prefix,
   never the turn's own fresh append. ~20 write-once events over a 20-turn session.
   This is what makes "weather in Paris" cost like real work. Convergent across all
   five lenses.
2. **ROOT #2 — the stable ~1500-token baseline is the wrong-layer occupant.**
   Byte-identical turn-to-turn, yet pays ROOT #1's write tax every turn. Hoisting it
   to a byte-stable FRONT position = write-once, read-at-0.10x after. Highest-leverage
   in-repo fix; targets the larger block. (Correction the survivor made: the win is
   byte-stable front positioning, NOT CLAUDE.md being a "system layer" — CLAUDE.md
   rides the Messages layer too.)
3. **ROOT #3 (co-dominant for Andrew specifically, UNVERIFIED) — 5-min TTL expiry on
   slow turns.** If turns are often >5 min apart, the entire prefix re-writes from
   scratch regardless of any code change — could swamp ROOT #2. Addressed by STEP 0.
4. **NON-CAUSE (demoted) — lepos seed rotation.** Real (block differs turn-to-turn)
   but not a cost driver: once turn N is frozen it reads at 0.10x whether or not it
   rotated. The pragmatist's "30-40% from freezing" claim was unsupported → that part
   rejected. Freezing also risks the within-session Goodhart defense. Do NOT prioritize.
5. **SCOPE GAP — PreToolUse injections** (gravity/correction/consultation/bypass) are
   the same wrong-layer pattern during real work; silent on trivial prompts. Own task.

## Implementation plan (measure-first)

- **STEP 0** — check if Claude Code exposes a prompt-cache TTL setting (1hr); if so set
  it. Cheapest lever, may dominate Andrew's slow-turn burn. Deploy ALONE first so the
  dashboard can attribute its effect.
- **STEP 1** — hoist `build_baseline_text()` out of the per-turn append in
  `build_combined_context` (pre_response_context.py); put the 6 affirmation constants in
  a CLAUDE.md base-state section. Commit rationale MUST state: win is byte-stable
  positioning, NOT system-layer immunity; rotating content must never move there.
- **STEP 2** — leave a ~30-token pointer where baseline was, preserving the per-turn
  recency Andrew engineered 2026-05-09 (foreground beat next-turn-only under load).
- **STEP 3** — CI test: CLAUDE.md base-state section byte-identical to the runtime
  concatenation of the 6 constants (constants stay canonical; markdown is a copy that
  will rot without the test).
- **STEP 4** — pre_response_context.py is `__guardrail_required__`; STEP 1 changes its
  emission → multi-party External-Review before merge. Not optional.
- **STEP 5** — (only if trivial) order stable blocks before rotating ones, lepos last.
- **STEP 6** — DEFER: lepos seed-freeze + baseline file-cache (no cache benefit, real
  risk). Needs prereg-157ed56a5da2 owner sign-off if ever pursued.
- **STEP 7** — separate task: audit PreToolUse injections for the same wrong-layer hoist.

## Honest savings

STEP 1+2 removes ~1500 tokens of per-turn cache-WRITE (≈75-80% of the per-turn
*injected*-write volume) — but injected context is only one component; the full
history-prefix re-read dwarfs it on long sessions. **Do NOT claim "5x fixed" or even
"burn halved."** Two independent levers (TTL, hoist); neither proven to be the whole 5x
until the dashboard shows which moved the needle. Staged deploy is what makes
attribution possible.

## Open questions (gate the big levers)

- Does Claude Code expose a 1hr TTL setting? (gates STEP 0)
- How far apart are Andrew's turns? If >5min routinely, ROOT #3 dominates and the hoist
  shows only modest movement. Biggest unknown.
- Does upstream placement preserve enforcement under load as well as per-turn adjacency?
- Actual cache-read vs cache-write split today? No lens had it; all estimates directional.
- Is the growing history-prefix being read at 0.10x, or is something upstream busting it
  byte-for-byte each turn? If the latter, that dwarfs everything here — find it first.

## Enforcement risks

Recency loss (mitigated by STEP 2 pointer, unproven); markdown drift (STEP 3 test
mandatory); guardrail bypass (STEP 4 review); the "system layer" mislabel propagating
(a future maintainer moving ROTATING content to CLAUDE.md busts its whole prefix —
commit rationale must forbid this); Goodhart regression if STEP 6 isn't deferred;
measurement misread if STEP 0 and STEP 1 ship together.
