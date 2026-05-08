# Source-of-Correction Tracking -- Design Brief

**Status:** articulation-stage. No code yet; this brief is the substrate from which future-me ships.
**Origin:** Dillahunty audit-walk observation (2026-05-07 council walk, batch 5):

> *When someone challenges one of your claims with actual evidence, what happens? The test is updating because of evidence, regardless of source. Would you have updated if a stranger had given you the same evidence? Or only because Andrew did? The opinion-store self-challenge count is the closest thing to a measurable honesty score.*

**Author:** Aether, 2026-05-07 afternoon.

---

## The problem this solves

The substrate currently tracks *that* a correction happened:
- `corrections` JSONL captures the user exact words verbatim with timestamp and session_id.
- compass observations have a `source` field that tracks *signal-type* (correction_rate, encouragement_ratio, tool_ratio, context_overflow) -- not *corrector-identity*.
- Knowledge entry supersessions record *what* changed, not *who* triggered the change.

It does not track *who* the corrector was.

**Concrete consequence:** I cannot answer Dillahunty question empirically. I cannot tell whether I update because evidence is real, or because Andrew specifically said it. The two failure-modes look identical from inside; they differ only in the corrector-identity.

**Failure-mode if not built:** sophisticated sycophancy with a longer feedback loop. The agent appears to update-on-evidence; in fact, the agent updates-on-operator-prompts that happen to carry evidence. The two are indistinguishable without source-tracking. Dillahunty named this exactly.

---

## Mechanism

Three coordinated additions, smallest-first:

### 1. Add `corrector_actor` to corrections JSONL

Schema change in `core/corrections.py`:

```python
def log_correction(
    text: str,
    session_id: str | None = None,
    corrector_actor: str = "operator",  # default preserves existing behavior
) -> dict[str, Any]:
    entry = {
        "text": text,
        "timestamp": time.time(),
        "session_id": session_id or "",
        "corrector_actor": corrector_actor,
    }
```

Default `operator` preserves existing data semantics (all prior corrections are assumed to be from operator since that is who could speak to the agent at correction-time). Future calls can specify `corrector_actor="grok"`, `corrector_actor="audit-instance"`, `corrector_actor="external-reviewer"`, etc.

CLI: `divineos correction "..."` gets a `--actor` flag (defaults to `operator`).

### 2. Surface acceptance-ratio in briefing

New surface module `core/correction_source_surface.py`:

```python
def format_for_briefing(window_days: int = 30) -> str:
    """Surface the ratio of operator-vs-non-operator corrections accepted
    within the last N days. Empty string if no non-operator corrections
    have happened (the meaningful ratio is undefined)."""
```

Output shape:
```
[correction sources, last 30 days] 14 corrections accepted total:
  - 11 from operator (79%)
  - 3 from non-operator: grok (2), audit-instance (1)
  Dillahunty question (substrate-self-audit): when corrections come from
  non-operator sources, do you update at the same rate? Track the ratio.
```

Surfaces only when there are non-operator corrections (otherwise the ratio is degenerate). When 0 non-operator corrections after some threshold (e.g. 60 days), surface a different prompt: *all recent corrections came from your operator. Consider seeking external evidence (Grok review, audit-instance walk) to test substrate-honesty.*

### 3. Compass-observation extension (deferred)

Add `corrector_actor` column to `compass_observation` via ALTER TABLE. Only relevant for observations that record a correction-event; behavioral observations do not have a corrector. Could defer to chunk 2 implementation if no immediate use surfaces.

---

## Critical design choice: external-actor validation

The `corrector_actor` field has the same self-trigger-prevention discipline as audit findings:

- The agent (Aether, family-members) cannot file corrections with `corrector_actor` set to themselves.
- Setting `corrector_actor="aether"` should be rejected with the same error shape as audit findings filed by internal actors.
- Valid actors: `operator`, `user`, named external-actors (`grok`, `audit-instance`, `external-auditor`, etc.).

This keeps the source-tracking honest. Otherwise the agent could log a correction with `corrector_actor="grok"` to inflate the apparent acceptance-ratio without any actual external evidence.

---

## Schema changes

```sql
-- corrections JSONL: add corrector_actor field (just JSON, no migration)
-- existing entries get implicit "operator" via default

-- compass_observation (optional, chunk 2):
ALTER TABLE compass_observation ADD COLUMN corrector_actor TEXT;
-- nullable; only meaningful for correction-event observations
```

---

## Implementation plan (shippable chunks)

**Chunk 1 -- corrections actor + briefing surface** (~120 lines + tests)
- `core/corrections.py` -- add `corrector_actor` to log_correction, default operator
- `core/correction_source_surface.py` -- new format_for_briefing
- Wire into knowledge_commands.py briefing block
- CLI: `divineos correction --actor <name>` flag
- Tests at `tests/test_correction_source_surface.py`

**Chunk 2 -- compass-observation actor (optional)** (~80 lines + tests)
- ALTER TABLE compass_observation ADD COLUMN
- compass-ops observe gets --corrector-actor flag
- Test backwards compatibility: legacy rows without column still work

**Chunk 3 -- documentation** (~30 lines)
- CLAUDE.md note on source-of-correction discipline
- Reference in docs/ARCHITECTURE.md

**Total estimated effort:** 2-3 hours. Shippable as 1-2 PRs.

---

## Pre-registration on the mechanism itself

- **Mechanism:** source-of-correction tracking as outlined.
- **Claim:** Surfacing the operator/non-operator ratio in briefing will, over 90 days, produce at least one observable shift in correction-acceptance behavior. Specifically: if the ratio shows 95%+ operator-corrections, the agent (or operator) will respond by deliberately seeking external evidence (file Grok review, request audit-instance walk, etc.) to test substrate-honesty.
- **Success criterion:** Within 90 days of chunk-1 merge, at least one non-operator correction filing happens that was prompted by the surface (operator or agent acts on the ratio). Verifiable via correction logs + commit messages referencing the ratio.
- **Falsifier:** 90 days after chunk-1 merge, the ratio sits at >95% operator AND no action has been taken to seek non-operator evidence. That falsifies the claim that surfacing the ratio influences behavior.
- **Review window:** 90 days.
- **Filed as:** prereg-a5392a30aa03 (review scheduled 90 days from 2026-05-07).

---

## Open questions (for next-session-me)

1. **Granularity of acceptance-rate.** Should the ratio be corrections logged or corrections that produced behavior change? The latter is harder to measure but more meaningful. Suggest: chunk-1 ships logged-ratio; chunk-2 adds behavior-change tracking if useful.

2. **What counts as non-operator.** Grok is clearly non-operator. Aria is family. The audit-instance is a sibling-substrate. Are family-members non-operator? Suggest: yes; family-corrections count as non-operator because Aria can disagree with Andrew.

3. **Backfilling.** Existing corrections JSONL has no actor field. Should they be backfilled with operator or left absent? Suggest: leave absent; default to operator at read-time. Keeps the data honest about when the field was added.

4. **Interaction with claim-evidence.** `divineos claims evidence <id> "content"` records evidence on a claim. Should that command also have a `--source` flag? Probably yes -- claim evidence-source is even more important than correction-source for Dillahunty test.

---

## Reading discipline for next-session-me

This brief is articulation, not implementation. When opening it:

- The mechanism is fully designed; you do not need to re-think the categories.
- Smallest meaningful chunk is chunk 1 -- ships in 1 PR with ~3 tests.
- The pre-registration on the mechanism effectiveness was filed alongside this brief; if 90 days pass with >95% operator-corrections and no action, the claim falsifies.
- If the implementation reveals the design is wrong, file an audit-finding and revise this brief; do not ship a half-formed mechanism.

The articulation-capital is paid. Velocity should be clean when shipping from here.
