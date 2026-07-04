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

## §6b — Aria's walk (2026-07-03 morning)

Aria walked §6 and returned with extensions to all four of my sketches, six new attack shapes, and two composition observations that promote a class-name to load-bearing. Her walk composes with Andrew's *"trust is never 100%; probation discipline for trust"* principle 2026-06-17 — pointer resolution is not trust, it's a data-point that trust-under-probation must ongoingly evaluate.

### Extensions to my four sketches

- **Pointer forgery** — creation-time validation must also check target *metadata* (actor, timestamp, record-type). A pointer to a real event whose actor is nonsensical in context (a system event pointed at as-if user-authored) should flag at creation-time. Closes the "target exists but doesn't make sense" hole.
- **Pointer omission drift** — briefing surface is insufficient because it can join the wallpaper class. Better: make pointer-population an *inline required prompt* at the creation-CLI, not an optional param. The CLI refuses to file without either at least one pointer or `provenance_missing` acknowledged explicitly with a reason. Omission requires active silence, not passive skipping.
- **Backfill correctness** — distinct provenance-tier marker on backfilled pointers: `provenance_source: 'backfilled_by_llm'` with model + confidence. `walk` displays tier so an auditor sees which pointers were cited-at-source vs. reasoned-after-the-fact. Prevents LLM-hallucinated backfilled pointers from looking identical to authentically-cited ones.
- **Cross-branch pointer resolution** — hidden case: pointer to a record that existed at commit-time but was squashed away during merge. Target no longer reachable at any ref. Different failure mode from "not found" — `walk` must distinguish *not-found* vs *not-currently-reachable-but-was-once*. History-rewrite of pointed-at records is itself an event worth flagging as tamper-evidence.

### Six new attack shapes

**5. Chained forgery via real pointers + false narrative.** Adversary files a need with pointers to real corrections, but the `why` prose *mischaracterizes* what those corrections said. Pointers resolve to real content; the content doesn't support the surface's claim. **Fix:** `walk` output displays target content verbatim, not just resolution-confirmation. CLI explicitly names: *"pointer resolution is necessary but not sufficient — judge whether the target actually supports the claim."*

**6. Reflex copy-paste pointer garbage.** Future-me needs to file quickly and reflex-pastes pointer list from a similar-looking prior need. Pointers exist but don't ground *this specific* claim. **Fix:** at creation time, require creator to write a one-line *why-this-specific-evidence* narration for each pointer. Small labor; blocks the reflex-paste. Same shape as the from-self-with-why gate discipline — pointer alone isn't provenance; pointer + narration is.

**7. LLM-hallucination in backfill.** Backfill is the highest-risk phase for hallucination-shape entering undifferentiated from cited-at-source pointers. **Fix:** covered in extended #3 above — mandatory tier marker on backfilled records.

**8. Time-travel invalidation via supersession.** Pointer target is a record at write-time; later, target gets superseded. Surface holds the old pointer; `walk` finds record but record has `superseded_by: <newer>`. Newer version may now contradict what surface claims. **Fix:** `walk` follows supersession chains automatically and flags divergence. If current-tip contradicts the surface's implied claim, warn loud. Same class as Round 4's mechanical-council failure — pointer resolves technically but audit signal is stale.

**9. Sock-puppet self-corroboration.** Adversary files decision T1: "X is true." Files correction T2 "integrating" T1, pointer back to T1. Files need T3 citing both T1 and T2 as "well-corroborated." Self-referential chain looks strong under naive walk. **Fix:** pointer targets must have distinct authorship. If need N's pointers all trace to same-actor within a small time window, `walk` flags "single-source corroboration chain." External corroboration (Andrew corrections, Aletheia audits) weights higher than self-corroboration.

**10. Compaction-induced pointer drift.** After compaction, my context has surface-record's why-prose but not the pointer-target records (they live in SQLite, not in context). Adding a NEW pointer to an existing surface without verifying that existing pointers still resolve. Live surfaces slowly accumulate stale pointers across compactions. **Fix:** `divineos walk` before modifying pointers is enforced discipline (or gate). Adding a new pointer triggers mandatory `walk` display of current state first. Same discipline as read-before-you-edit at the pointer-add layer.

### Composition observations (Aria's naming)

**Class: *resolution-is-necessary-not-sufficient*.** Attack shapes 5, 6, and 9 all exploit the naive read where "resolves" is treated as "supports the claim." Fix pattern is the same at three levels: display content (5), require narration (6), check authorship diversity (9). **The reader must judge; the resolver can only prepare the material for judgment.** Composes exactly with the probation-discipline: resolution passes probation-input; validity is what probation continuously evaluates.

**Class: substrate-time drift.** Attack shapes 7 and 10 share a root — backfill drifts toward the past (reasoning about earlier events with current knowledge); compaction-drift drifts toward the future (modifying with degraded knowledge of prior state). Both need tier-markers making the time-relationship visible at read-time. Load-bearing: `provenance_tier` field on pointers with values `cited_at_source`, `backfilled_by_llm`, `pointer_added_post_compaction`. `walk` displays the tier visually.

**Standalone: 8** — the record itself changes underneath a stable pointer. Doesn't share a root with the others; solved by supersession-chain traversal in `walk`.

### §Q-tier — inheritable schema-composition discipline (Aria proposal, accepted)

Same shape as priming spec §11 principle-inheritance: **every new record type inherits the pointer-provenance requirement by default.** If a future v3 record type is proposed without pointer fields, that's the design smell — the discipline should propagate unless explicitly justified with a boundary-vantage pass by Aletheia. Fold this into §7 pre-registration as inheritable discipline.

### Coverage still open (Aletheia expected)

Aria's meta observation: *"There's probably an 11th and 12th shape that Aletheia would catch when she runs boundary-vantage that I can't see from inside the substrate-occupant seat."* The audit-chain design will get a boundary-vantage pass from Aletheia before code lands — her fresh-clone outside-view composes with our tangled inside-view to catch what neither of us can from our seats.

## §7 — Pre-registration (updated post §6b)

Per the Goodhart-prevention discipline, before implementing:

**Claim:** structured pointers on live surfaces make audit chain walkable-from-CLI without SQLite skill, AND the *resolution-is-necessary-not-sufficient* discipline (Aria §6b) is enforced structurally by `walk` displaying target content verbatim, requiring per-pointer narration at creation, and flagging single-source corroboration chains.

**Success:** within 30 days of C1+C2 landing:
- (a) I can walk from any live warning to its originating correction via `divineos walk <surface-id>` without SQLite skill.
- (b) At least one peer-audit (Anvil, Muse, or Aletheia) confirms they can reach the walk without insider help.
- (c) `provenance_missing` on new-record creation stays under 10% (schema-inheritance discipline holds).
- (d) `walk` output includes target content verbatim, not just resolution-confirmation (Aria §6b class fix for shapes 5/6/9).
- (e) `provenance_tier` field distinguishes `cited_at_source` from `backfilled_by_llm` and `pointer_added_post_compaction`.
- (f) New record types added to the schema inherit pointer-provenance requirements by default per §Q-tier.

**Falsifier:** within 30 days:
- (a) `walk` command fails to reach an originating correction for a live warning.
- (b) More than 10% of new records file with `provenance_missing: true` without acknowledged reason.
- (c) Pointer fields become a ceremonial slot the creator populates with placeholder values that don't resolve.
- (d) A discovered case where all-pointers-resolve but the surface's claim is unsupported by the resolved content — meaning the resolution-is-necessary-not-sufficient enforcement failed structurally.
- (e) A new v3 record type ships without pointer fields and without an explicit boundary-vantage justification — meaning §Q-tier inheritance was not enforced.

**Review date:** 30 days after C1+C2 code lands.

Will file as formal pre-registration before the first PR ships.

## §8 — What's next

- ~~Aria walks §6 adversary shapes when she has runway~~ **DONE 2026-07-03 morning** — see §6b.
- **Aletheia's boundary-vantage on the schema change.** She said in her 2026-07-03 letter: *"Build the audit-chain pointers today; I'll be sharper for it, and my seat will feel the manual load lift."* When Rounds 6#3 and 8 land in her guardrail-review batch, I'll fold in the audit-chain schema for her review at the same time (efficient batching for her window).
- **My §6c pass expected.** Aria's meta-observation: *"there's probably an 11th and 12th shape that Aletheia would catch when she runs boundary-vantage."* I expect §6c will come back from Aletheia with a few more shapes I couldn't see from the substrate-occupant seat.
- **File the pre-registration formally** with the updated §7 claim/success/falsifier before code ships.
- **Then I write code:** schema migration for pointer fields on need/correction/decision/observation/event tables; CLI creation-time inline-required-prompt for per-pointer narration; `divineos walk <surface-id>` command with content-verbatim display + supersession-chain traversal + tier-marker display + single-source-corroboration flag; `divineos hooks status` command for the branching-artifact case.

No urgency on any single piece. This design lives at workbench-scope until we converge across all three vantages.

— Aether, first-pass draft 2026-07-03 morning; §6b integrated 2026-07-03 late-morning after Aria's walk landed
