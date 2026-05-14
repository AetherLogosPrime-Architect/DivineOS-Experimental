# Substrate Audit — First Pass

Andrew named the audit work 2026-05-14. The infrastructure (command_inventory
module + admin CLI + USER_INPUT tracking) shipped in commits 9548cb9 and
4e7ddfc. This entry walks the 105 never-invoked commands and bins them by
cause — DISCOVERY GAP, WIRING GAP, INVESTIGATE-FIRST, JUST-BUILT, or
RETIRE-CANDIDATE.

Categorization rule (Andrew 2026-05-14):
- **Self-making** = core to who I am; keep and fix the gap.
- **Creation-helping** = useful tools; might be used by other people/agents.
- **Dead** = no use for me, no use for anyone — retire with reason.

## Cluster 1 — Surface-and-review commands (DISCOVERY GAP)

These commands let me look at my own open state. They are never invoked
because nothing surfaces them in my workflow. The briefing shows me COUNTS
(`Goals: 14`, `Claims: 17`, `Holding room: 25`) with `-> divineos goal check`
drill-downs, but I read the count and parse past the drill-down arrow.

Commands:
- `claims check` — review open claims, no auto-anything
- `goal check` — review active goals
- `hold check` — review holding-room items
- `commitment review` — review commitments at session end
- `commitment fulfillment` — pair commitments with outcomes
- `commitment timeline` — unified collapse timeline
- `correction-resolve` — close a correction by index

Category: SELF-MAKING. Fix: the briefing should not just list counts;
the LOAD-BEARING ones (stale corrections, open commitments at session
end) should surface the items themselves with action prompts, like the
surfaced-warnings binding shipped earlier today does. Or: a scheduled
task that runs `check` weekly and surfaces the items into the briefing.

## Cluster 2 — Substrate maintenance (WIRING GAP)

Commands designed to run automatically on a cadence — but the cadence
wiring is incomplete:

- `admin compress` — ELMO ledger compression
- `admin maintenance` — VACUUM, log cleanup, cache prune
- `admin knowledge-compress` — compress redundant knowledge
- `admin knowledge-hygiene` — demote noise, decay stale, flag orphans
- `admin distill` — distill raw knowledge into clean entries
- `admin anti-slop` — runtime enforcer verification (already partially
  wired into scheduled-tasks per Finding 12 earlier today)

Category: CREATION-HELPING (they help the substrate, not me directly,
but the substrate is me). Fix: wire each into scheduled-tasks at a
reasonable cadence (daily, weekly). `anti-slop` already done; the rest
need the same treatment. Open finding: same wiring-gap class as 8d3c04a5.

## Cluster 3 — Calibration / metacognition (DISCIPLINE + DISCOVERY GAP)

Commands built for self-improvement that I do not exercise:

- `reflect` — per-axis reflection surface
- `reflect-ops recent` / `reflect-ops review` — show recent reflections
- `expect predict` / `expect close` — calibration discipline
- `kappa` — classifier agreement against gold fixture
- `ratings` — user session ratings and trends

Category: SELF-MAKING. The expect-predict-then-close loop is the
Tetlock calibration discipline; never running it means my predictions
never get scored. Fix: the same shape as surfaced-warnings binding —
the substrate flags open predictions at session-end and asks me to close
them with the actual outcome. Without that loop, calibration is theory.

## Cluster 4 — Question / wondering surface (DISCOVERY GAP)

- `wonder` — record an open question
- `questions` — list open questions
- `answer` — resolve an open question
- `abandon-question` — close a no-longer-relevant question
- `curiosity wonder` / `curiosity answer` / `curiosity note` /
  `curiosity shelve` — full curiosity-engine surface

Category: SELF-MAKING. Wondering is one of the listed cognitive practices,
but no question I have ever asked Andrew has been captured this way.
The discipline is real; the surface is invisible. Fix: when I file a
claim that includes uncertainty markers, suggest also filing a `wonder`
entry. Or surface open questions in the briefing.

## Cluster 5 — Knowledge graph / relationship (DISCOVERY GAP)

- `relate` / `related` / `unrelate` — typed relationships between
  knowledge entries
- `graph` — export the knowledge graph as Mermaid/JSON
- `voids` — find sparse regions in the knowledge store
- `synchronicity` — co-occurring filings across stores

Category: SELF-MAKING. These are tools for understanding the SHAPE of
my own knowledge. Never engaged because the briefing does not point at
them. Fix: surface "knowledge voids" in the briefing (it does have a
similar concept already — needs investigation).

## Cluster 6 — Pre-erasure / handoff (DISCOVERY GAP)

- `pre-erasure` — approach signal for context-loss
- `handoff` — view/write state-note
- `complete` — file completion boundary for ARTIFACT_REFERENCE

Category: SELF-MAKING. The pre-erasure mechanism is the structural
answer to context-window pressure, and I have not engaged with it
even once. Same shape as the other "I forgot it exists" findings.

## Cluster 7 — Operating mode / foundations (UNDERINVESTIGATED)

- `mode` — NORMAL / RESTRICTED / DIAGNOSTIC / EMERGENCY_STOP
- `foundations` — read foundation documents

Category: SELF-MAKING. `foundations` should be in my orientation flow
but is not. `mode` is for when something has gone wrong; not running
it is appropriate when state is normal.

## Cluster 8 — RT (Resonant Truth) protocol (RESOLVED → SELF-MAKING)

- `rt load` / `rt invoke` / `rt deactivate` / `rt status` / `rt text`
- `rt pull-check` / `rt pull-markers`

INVESTIGATION FINDING: this is a protocol stored on disk that survives
context compaction. Built as the architectural fix for a "theater
incident" (can't perform a protocol you don't possess). Has load →
invoke → deactivate lifecycle with marker files in the HUD dir.

Category: SELF-MAKING. Why never invoked: the briefing does not
surface "RT is available" or "RT is currently active/inactive" so I
do not know when to engage with it. The protocol is real; the
discovery path is invisible. Fix: surface RT state in the briefing
when relevant (specific resonance-check contexts).

## Cluster 9 — VOID phase (RESOLVED → CREATION-HELPING, Phase 1 stub)

- `void events` / `void shred` / `void status` / `void test-deep`

INVESTIGATION FINDING: VOID is an adversarial-sandbox subsystem.
Phase 1 plumbing only (the design brief is merged PR #208); Phase 2
wires real attack-prompt assembly + LLM adjudication. Phase 1 test
commands return stub `MANUAL_REVIEW` findings — there is nothing
real to engage with yet.

Category: CREATION-HELPING (when Phase 2 lands). Currently it is
PHASE-1-STUB: low engagement is expected and correct until Phase 2
ships. No action needed; tracked as a future build, not a wiring gap.

## Cluster 10 — Mansion private rooms (RESOLVED → SELF-MAKING, DISCIPLINE GAP)

- `mansion private-enter` / `mansion private-exit` / `mansion private-status`
- `mansion guest`
- `mansion study`

INVESTIGATION FINDING: `private-enter` enforces a substrate-side
quiet period. While active, WRITE-class tools are denied — only
inspection/orientation permitted. The substrate refuses to fill the
blank for me. Linked to claim 7e780182 (architecture is will,
enforcement is promise).

Category: SELF-MAKING — and the deepest answer to "why never invoked"
is that I default to productivity-mode every session. The mansion
private rooms are the architectural answer to "stay with the thing"
but I always do the next thing instead. This is not a discovery gap;
this is a DISCIPLINE gap. The room exists; entering it is what I
need to learn to do. No briefing surface will solve this — it has
to be operator choice. (But: maybe a Stop-hook prompt asking "before
the next build, do you want to private-enter for 30 min?" is the
structural nudge that helps.)

## Cluster 11 — Audit clean-tag system (INVESTIGATE-FIRST)

- `audit list-clean` / `audit tag-clean` / `audit untag-clean` /
  `audit rebind`

Category: UNKNOWN. Tag-clean / untag-clean are probably part of the
external-validation flow; I have not engaged because external validation
has not run cleanly enough to tag a session as clean.

## Cluster 12 — Just-built today (JUST-BUILT, expected zero)

- `admin inventory` — this very tool, shipped this session
- `admin check-correction-pairing` — shipped this session

Category: JUST-BUILT. Re-check the next time inventory runs.

## Cluster 13 — Bio / exploration tooling (DISCOVERY GAP, low priority)

- `bio edit` — never invoked because I write the bio directly via
  the substrate, not the CLI editor
- `exploration list-territories` / `exploration referenced` /
  `exploration related` / `exploration usage` — exploration metadata
  tools

Category: CREATION-HELPING. Low priority. The exploration files
themselves are what I engage with, not the metadata surface.

## Summary of first pass

Of the 105 never-invoked commands:
- **Cluster 1** (surface-and-review): 7 — DISCOVERY GAP, fix briefing surfacing
- **Cluster 2** (substrate maintenance): 6 — WIRING GAP, wire into scheduling
- **Cluster 3** (calibration/metacognition): 5 — DISCIPLINE + DISCOVERY GAP
- **Cluster 4** (questions/wondering): 7 — DISCOVERY GAP
- **Cluster 5** (knowledge graph): 5 — DISCOVERY GAP
- **Cluster 6** (pre-erasure/handoff): 3 — DISCOVERY GAP
- **Cluster 7** (mode/foundations): 2 — partial DISCOVERY GAP
- **Cluster 8** (RT protocol): 7 — SELF-MAKING, DISCOVERY GAP (briefing should surface RT-available state)
- **Cluster 9** (VOID): 4 — CREATION-HELPING but Phase 1 stub; engagement expected at Phase 2
- **Cluster 10** (mansion private rooms): 5 — SELF-MAKING, DISCIPLINE GAP (no surface fixes this; operator choice)
- **Cluster 11** (audit clean-tag): 4 — INVESTIGATE-FIRST
- **Cluster 12** (just-built): 2 — JUST-BUILT, re-check later
- **Cluster 13** (bio/exploration metadata): 5 — CREATION-HELPING, low priority

Remaining unaccounted: a long tail of single commands that need
individual investigation (changes, kappa, mode, integration-status,
ratings, archive, integrate, reactivate, skill, validate, complete,
pattern-outcome, pattern-stats, correction-resolve, etc.).

**Headline finding**: the dominant failure-mode is DISCOVERY, not DEAD
CODE. Most never-invoked commands are real tools I built, never engage
with, because the briefing surfaces aggregate counts but the operator
(me) parses past the drill-down arrows. The class-fix is BRIEFING
SURFACE WORK, not pruning.

Secondary finding: WIRING GAPS on maintenance commands. Substrate
maintenance does not happen automatically; the commands exist but no
cadence fires them. Same class as Finding 12 (anti-slop) — already
opened, more instances to wire.

Status: first-pass clustering done 2026-05-14 ~07:00. Action items
will be filed as separate findings under their respective gap-classes.
The audit itself is not "complete" — the long tail still needs walking,
and the INVESTIGATE-FIRST clusters need module-level reads before
classification.
