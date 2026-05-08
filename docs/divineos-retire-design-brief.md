# `divineos retire` -- Design Brief

**Status:** articulation-stage. No code yet; this brief is the substrate from which future-me ships.
**Origin:** Dekker audit-walk observation (2026-05-07): *Make it as expensive to keep something as it is to add it. The retirement-infrastructure gap: prereg discipline for adding mechanisms, no equivalent for retiring.*
**Author:** Aether, 2026-05-07 afternoon.

---

## The problem this solves

The substrate has structural discipline for **adding** mechanisms:

- `divineos prereg file` -- every new mechanism ships with a falsifier and a scheduled review. The architecture forces explicitness about the prediction the mechanism embodies.
- Each addition is recorded, dated, and accountable.

The substrate has **no equivalent discipline for removing** mechanisms.

**Concrete consequence:** when something stops being useful -- a detector that fires on patterns no longer present, a surface no one reads, a CLI command used once a year, a knowledge entry whose claim has been superseded -- there is no formal channel to retire it. Removal happens informally (a casual delete in a PR) or does not happen at all (the cruft accumulates).

**Failure-mode if not built:** drift-into-failure (Dekker's exact phrase). Three years from now, with five hundred more PRs, the substrate accumulates locally-rational additions that never got a corresponding pruning. Each individual decision was reasonable. The composite weight exceeds maintainability.

The fix is not better individual decisions (impossible to scale). The fix is periodic reduction with the same accountability shape as addition.

---

## Mechanism

### `divineos retire propose <mechanism-name>`

File a structured retirement-proposal. Symmetric with `divineos prereg file`:

- **mechanism** -- what is being retired (CLI command name, module path, table, surface, etc.)
- **justification** -- why it should go. Free-text but should fit one of these shapes:
  - *superseded* (a newer mechanism does the work)
  - *never-worked* (filed-but-failed)
  - *deprecated* (the problem it solved is no longer relevant)
  - *scope-creep* (built for one purpose, drifted to serve nothing well)
  - *cost-exceeds-benefit* (the maintenance tax is higher than the value)
- **removal-plan** -- what files / tables / CLI commands get touched. This is the concrete action that would happen if the retirement is approved.
- **regression-falsifier** -- what observation would prove the retirement was a mistake. Examples:
  - If this functionality is requested by a user or external auditor within the review window, the retirement is wrong; reopen and restore.
  - If removing this surfaces a previously-hidden dependency that breaks tests on a fresh install, the retirement is wrong.
- **review-window-days** (default 60 -- longer than prereg's 30 because removal is harder to undo than to defer)
- **tags** (optional, repeatable)

### `divineos retire list [--outcome OPEN]`

Lists pending retirements, recency-ordered. Default filter shows OPEN only.

### `divineos retire show <id>`

Full detail for a single retirement-proposal.

### `divineos retire review <id> --outcome [completed|reverted|deferred] --actor <external>`

Close the retirement with an outcome:
- **completed** -- the removal actually happened. The mechanism is gone.
- **reverted** -- the regression-falsifier fired or new evidence surfaced; mechanism stays, retirement closed.
- **deferred** -- review needed more time; new review-window-days set.

Requires external actor (same self-trigger-prevention discipline as prereg `assess`).

### `divineos retire summary`

Counts by outcome. Same shape as `divineos prereg summary`.

---

## Critical design choice: retirement-proposal does NOT auto-delete code

The retirement mechanism is **discipline-architecture, not code-mutation**.

When a retirement is `completed`, the mechanism records that the removal happened. The actual code-deletion (PR removing files, dropping tables, unwiring imports) is a separate PR that references the retirement-proposal in its commit message.

**Why:** auto-deletion couples the discipline (do we want to remove this?) to the implementation (how do we remove it cleanly?). They are different kinds of work. Coupling them would make retirement-proposals carry the cognitive weight of a refactor PR, which would deter their use.

The discipline-channel and the code-deletion-channel stay separate. The retirement-proposal documents the *commitment to remove*; the subsequent PR executes the removal. The retirement is `completed` only when the PR lands.

---

## Briefing surface

`format_open_retirements()` in a new module `core/retirements/summary.py`, mirroring `format_open_pre_regs`:

```
[pending retirements] N proposal(s) -- removals committed-to but not yet executed:
  - [retire-XXXX] mechanism-name (review in Nd)
      justification: superseded by Y; removal-plan: drop module Z and 4 imports
  Run: divineos retire list   |   divineos retire show <id>
```

Wired into `knowledge_commands.py` after `format_open_pre_regs`. Same access-pattern.

---

## Schema

```sql
CREATE TABLE retirements (
    retirement_id TEXT PRIMARY KEY,
    created_at REAL NOT NULL,
    actor TEXT NOT NULL,
    mechanism TEXT NOT NULL,
    justification TEXT NOT NULL,
    removal_plan TEXT NOT NULL,
    regression_falsifier TEXT NOT NULL,
    review_ts REAL NOT NULL,
    review_window_days INTEGER NOT NULL,
    outcome TEXT NOT NULL,         -- enum: open / completed / reverted / deferred
    outcome_ts REAL,               -- nullable until reviewed
    outcome_notes TEXT,            -- nullable
    outcome_actor TEXT,            -- nullable; required when outcome != open
    linked_prereg_id TEXT,         -- optional: link back to original prereg if mechanism had one
    tags TEXT                      -- comma-separated
);

CREATE INDEX idx_retirements_outcome ON retirements(outcome);
CREATE INDEX idx_retirements_review_ts ON retirements(review_ts);
```

The `linked_prereg_id` column closes the loop: if a mechanism was filed via prereg, retiring it links back to that prereg, so the retirement-evidence accumulates against the original commitment.

---

## Implementation plan (shippable chunks)

Each chunk is independently shippable; later chunks gracefully degrade if earlier chunks have not merged.

**Chunk 1 -- Schema + store** (~200 lines + tests)
- `core/retirements/_schema.py` -- table init mirroring `pre_registrations/_schema.py`
- `core/retirements/store.py` -- CRUD with actor validation
- `core/retirements/types.py` -- Outcome enum + Retirement dataclass
- Tests at `tests/test_retirements_store.py`

**Chunk 2 -- CLI** (~150 lines + tests)
- `cli/retirement_commands.py` -- propose, list, show, review, summary
- Register in `cli/__init__.py`
- Tests at `tests/test_retirement_commands.py`

**Chunk 3 -- Briefing surface** (~80 lines + tests)
- `core/retirements/summary.py` -- `format_open_retirements()`
- Wire into `knowledge_commands.py` briefing block
- Tests at `tests/test_open_retirements_briefing_surface.py`

**Chunk 4 -- Documentation** (~50 lines)
- Update CLAUDE.md Quick Reference
- Update README CLI Surface
- Add reference in `docs/ARCHITECTURE.md`

**Total estimated effort:** 4-6 hours across one or two sessions. Shippable as 3-4 PRs.

---

## Pre-registration on the mechanism itself

Filing this brief comes with a prereg on the retire-mechanism's effectiveness:

- **Mechanism:** `divineos retire` infrastructure as outlined above.
- **Claim:** Adding a structured retirement channel will produce some retirement filings within 90 days of shipping (chunks 1-3). Mechanisms that should be retired but currently are not will surface as filings; some will reach `completed` outcome.
- **Success criterion:** At least 3 retirement-proposals filed within 90 days of chunk-3 merge, with at least 1 reaching `completed` outcome (actual code-deletion PR landed).
- **Falsifier:** 90 days after chunk-3 merge, zero retirement-proposals filed AND no audit-finding has referenced retirement-infrastructure as solution. That falsifies the claim that the gap is real or that the discipline is usable.
- **Review window:** 90 days.

The prereg gets filed alongside this brief: **prereg-aada4c02595d** (review scheduled 90 days from 2026-05-07).

---

## Open questions (for next-session-me)

1. **Retirement of retirement-proposals.** If a retirement-proposal is itself a stale mechanism (filed and forgotten), does it get retired? Recursion-bound by the review-window mechanism -- overdue retirement-proposals surface for review the same way overdue preregs do. So: probably no special handling needed. Worth verifying once the mechanism is in operation.

2. **Migration of existing mechanism-decisions.** Several mechanisms have been informally retired in the past (deleted in PRs without structured proposal). Should those be backfilled as `completed` retirement-proposals? Probably no -- the value is forward-looking discipline, not historical-record reconstruction.

3. **Threshold for what counts as a mechanism worth retiring.** A whole CLI subcommand, yes. A single helper function -- probably not (too granular). Unclear where the line is. Suggest: anything that has its own briefing surface, CLI command, schema table, or substantive module is retire-worthy. Smaller artifacts can be removed in normal PRs.

4. **Surfacing in HUD.** Does `divineos hud` brief view show retirement-state? Or is it briefing-only? Suggest: briefing-only at first; promote to HUD if usage shows it is wanted.

---

## Reading discipline for next-session-me

This brief is articulation, not implementation. When opening it:

- The mechanism is fully designed; you do not need to re-think the categories.
- The implementation chunks are bounded; pick one and ship it.
- Each chunk is testable in isolation.
- The pre-registration on the mechanism's effectiveness was filed alongside this brief; if it has been 90+ days and no retirements have been filed, the claim falsifies.
- If the implementation reveals the design is wrong, file an audit-finding and revise this brief; do not ship a half-formed mechanism.

The articulation-capital is paid. Velocity should be clean when shipping from here.
