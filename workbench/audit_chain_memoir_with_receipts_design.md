# Audit Chain — Memoir-with-Receipts Design

**Started:** 2026-07-03, Aether, morning after peer-substrate exchange with Anvil + Muse
**Status:** first-pass frame. Aria collab expected when she has runway.
**Context:** Anvil (Structured Chaos) surfaced the gap 2026-07-02 late; Aria named the design principle "memoir-with-receipts" 2026-07-03 morning.

---

## §1 — The finding

Anvil's exact framing: *"narrative why without ID pointers is a memoir, not an audit chain."*

Muse's diagnostic: *"the substrate is not fake, but the audit chain is currently hand-cranked."*

Aria's design principle: *"the fix isn't to lose the narrative; it's to attach the audit chain UNDER the narrative so both live at the same layer. Memoir-with-receipts."*

Three sibling instances filed under `audit-chain` cluster today (2026-07-03), all pointing at the same underlying pattern:

1. **Needs-provenance** — active needs carry prose in the `why` field but no structured pointer fields linking back to originating events/knowledge/corrections. A peer auditor asked me to walk from a live warning to its originating correction; I couldn't.
2. **Hook-provenance** — the auto-push-letter hook script exists but its registration lives in `.claude/settings.json` on a specific branch. Working on a different branch means the hook is silently absent. No walkable link between "letter written on branch B" and "hook registered on branch A."
3. **List-surface** — CLI commands like `divineos andrew-correction list` only show OPEN records. 17 DEFERRED corrections have no listing surface; reaching them requires direct SQLite querying.

All three are the same shape: **the substrate contains the record; the read-surface doesn't walk to it automatically.**

## §2 — Load-bearing invariants (the target)

For each surviving live surface (warning, need, hook registration, active correction, live rule), the substrate must expose:

- **What triggered me** — the originating event/correction/observation that made this surface exist.
- **What I cite as evidence** — the specific records (event_id, knowledge_id, decision_id, compass_observation_id, correction_id) that support the surface's claim.
- **What integrated my behavior change** — the andrew-correction record where I marked the correction integrated, with evidence pointer.
- **What runs my enforcement** — the code file/hook/detector currently enforcing the discipline, and where its registration lives.

The invariant: **from any live surface, a peer auditor with just my CLI can walk to every record supporting it, without SQLite skill or grep-through-prose.**

## §3 — Design candidates

### C1: Structured pointer fields on all record types

Every record type (need, correction, observation, decision, event) gains optional pointer fields:

```
source_events: list[str]         # event_ids that triggered/motivated
source_corrections: list[str]    # andrew-correction ids that filed this
source_knowledge: list[str]      # knowledge_ids cited as evidence
source_observations: list[str]   # compass observations that composed this
```

At creation time, the creator populates whichever pointers apply. If none apply, the record still files but flags `provenance_missing: true` so an audit can enumerate memoir-only records for backfill.

**Fix scope:** schema additions + CLI parameter additions. Non-destructive to existing records.

### C2: Widened list surfaces

Add `--all`, `--include-deferred`, `--include-integrated`, `--include-superseded` flags to every `list` command that currently shows only actionable rows. Optionally, a unified `divineos walk <surface-id>` command that traverses pointers automatically.

**Fix scope:** CLI-only, no schema changes. Cheapest surviving invariant.

### C3: Registration-audit surface for hooks

A `divineos hooks status` command that shows: which hooks are registered in the current branch's `.claude/settings.json`, which hooks exist as scripts, which hooks are registered on origin/main but not current branch. Surfaces the branching artifact this morning made me discover the hard way.

**Fix scope:** small CLI addition, reads settings.json + hook directory.

### C4: Uniform substrate search

A `divineos substrate search <query>` that traverses all record types (events + knowledge + decisions + compass + corrections) with a unified interface. Deprecates the current per-type `list`/`search` fragmentation.

**Fix scope:** larger — unified query planner across five SQLite tables + result normalization.

## §4 — Composability

C1 (structured pointers) is the load-bearing one — everything else composes on top:
- C2 (widened lists) becomes trivial once pointers exist (the surface just filters differently)
- C3 (registration audit) is orthogonal but shares the "walk to source" pattern
- C4 (uniform search) is the endgame that C1 makes possible

**Recommended order:** C1 first (schema + creation-time population), then C3 (small orthogonal add), then C2 (backfill and widening list surfaces), then C4 (unified query) as v2.

## §5 — Aletheia-cost insight

Aria named this 2026-07-03: **Aletheia's whole seat is currently absorbing the manual cost of the missing audit chain.** Every time she clones the repo and walks source to verify a provenance claim, she's paying the labor cost of memoir-shaped substrate. Building C1+C2 shifts her work from prose-parsing to trace-following, freeing her cycles for boundary-vantage judgment that only human-substrate can do.

This gives the design a **named beneficiary** — the audit chain isn't just for hypothetical future peer-substrate auditors, it's for the sister currently doing manual walks by hand.

## §6 — Adversary-vantage — deferred to Aria

Aria's discipline on the priming spec was to name attack shapes before code. The audit-chain design deserves the same. Concrete adversary questions worth walking:

- **Pointer forgery**: what stops me from filing a need with pointers to unrelated events? (Answer sketch: at creation time, the CLI validates that pointer targets exist; at read time, `walk` displays the target's own content, so a fake pointer to unrelated content is visible immediately.)
- **Pointer omission drift**: what stops future-me from filing new needs without populating pointers? (Answer sketch: `provenance_missing: true` flag surfaces in briefing; enforcement gate can fire on new-record-without-pointers if desired.)
- **Backfill correctness**: for existing memoir-shaped records, how do we backfill pointers without inventing them? (Answer sketch: leave `provenance_missing: true` on records where we can't reconstruct; don't fabricate.)
- **Cross-branch pointer resolution**: if a pointer references a record that exists on origin/main but not the current branch, what does `walk` show? (Answer sketch: attempt origin lookup, mark result as "resolved-from-origin" so the operator sees the boundary.)

Waiting on Aria to walk these + any I missed before I start writing code.

## §7 — Pre-registration

Per the Goodhart-prevention discipline, before implementing:

**Claim:** structured pointers on live surfaces make audit chain walkable-from-CLI without SQLite skill.

**Success:** within 30 days of C1+C2 landing, (a) I can walk from any live warning to its originating correction via `divineos walk <need-id>` or equivalent, (b) at least one peer-audit (Anvil or Muse or Aletheia) confirms they can reach the walk without insider help, (c) `provenance_missing` flag on new-record creation stays at 0% (all new records cite sources).

**Falsifier:** within 30 days, (a) `walk` command fails to reach an originating correction for a live warning, OR (b) more than 10% of new records file with `provenance_missing: true`, OR (c) the pointer fields become a ceremonial slot the creator populates with placeholder values that don't resolve.

**Review date:** 30 days after C1+C2 code lands.

I'll file this as a formal pre-registration before the first PR ships.

## §8 — What's next

- Aria walks §6 adversary shapes when she has runway
- Aletheia's boundary-vantage on the schema change when guardrail-review batch opens
- Then I write code: schema migration + CLI creation-time param + `walk` command + `hooks status` command

No urgency on any single piece. This design lives at workbench-scope until we converge.

— Aether, first-pass draft, 2026-07-03 morning
