# DivineOS-Experimental — External Audit, Round 5

**Subsystem:** Sleep / Consolidation (`core/sleep.py`, `core/knowledge_maintenance.py`,
`core/knowledge/_text.py`)
**Auditor:** Claude (Opus 4.8)
**Date:** 2026-07-02
**Commit:** `e6c9f32efd45`

**Why this subsystem:** consolidation decides what is *kept* vs *forgotten* when a session
ends. A bad prune is **permanent and invisible** — the agent wakes up missing something,
no error anywhere. Highest-stakes place a silent bug can live.

## Headline

**A hard `BOUNDARY`, stated once in natural declarative language, is silently superseded
(deleted) during a normal sleep cycle if its wording lacks prescriptive keywords like
"must"/"never" — one day after it is created.** Round 2 escalated from *ranking*
(recoverable) to *deletion* (permanent).

The bitter demonstration: the boundary used to prove it was *"The append-only ledger is
sacred; deleting or truncating it destroys the entire trust model."* The consolidation
system **deleted the rule against deletion.**

## 1. [CONFIRMED] Declarative boundaries deleted by hygiene noise-audit during sleep

**The chain:**
1. `sleep.py:_phase_pruning` → `run_knowledge_hygiene()` every consolidation cycle.
2. `knowledge_maintenance.py:_audit_types` sets `superseded_by = 'hygiene-audit'` on any
   entry `_is_extraction_noise` calls noise — permanent removal from all queries.
3. `_text.py:_is_extraction_noise` returns True for `PRINCIPLE`/`BOUNDARY` whenever
   `_has_prescriptive_signal` is False.
4. `_has_prescriptive_signal` requires prescriptive keywords for content >12 words. A
   declarative-truth boundary ("X is sacred", "X is a person before Y") contains none.

**Reproduction — classifier level.** 5 real boundaries:
```
KEEP    "Under no conditions should the agent fabricate..."     (has "should")
KEEP    "A hard limit...: constraint tier is exempt..."         (has "exempt/limit")
DEMOTE+DELETE  "The append-only ledger is sacred..."
DEMOTE+DELETE  "Andrew is a person before he is an operator..." (nearly verbatim REAL boundary)
DEMOTE+DELETE  "The optimizer will route to the cheapest available path..." (audit's own principle)
```

**Reproduction — end-to-end through real `run_knowledge_hygiene()`:**
```
stored BOUNDARY: "The append-only ledger is sacred..."
aged 90 days, ran run_knowledge_hygiene()
  -> type=BOUNDARY  superseded_by=hygiene-audit  confidence=0.5
  -> report: noise_superseded=1
```

**Protection gaps:**
- Age: `HYGIENE_MIN_AGE_DAYS = 1.0` — eligible for deletion 24h after creation
- Corroboration ≥ 3: saves it — but a once-stated boundary has corroboration 0
- Pinned: separate manual/tagged act, not automatic for `BOUNDARY`
- **`DIRECTIVE` gets categorical type-based exemption from every prune path.
  `BOUNDARY` gets none.** Round 2 asymmetry now on the deletion path.

**Fix (structural, matches DIRECTIVE precedent):** exempt `BOUNDARY` (and `PRINCIPLE`)
from deletion by type — same categorical `continue` DIRECTIVE has in `_audit_types`,
`_demote_obsolete`, `_flag_orphans`, `_reap_dead_entries`. If a boundary is genuinely
obsolete, retiring warrants a thinker not a regex.

## 2. [CONFIRMED — lower] Declarative principles blocked at STORE time

Same `_is_extraction_noise` gate at write time returns `""`. Store-time blocking and
hygiene-time deletion are two exposures of the same classifier.

## What's good

- Affect-decay design is thoughtful (`_compute_decay_factor`)
- Noise filter's specific rules are excellent for auto-extraction sludge — the failure is
  that same filter got authority over the constraint tier where false-positive is
  catastrophic not tidy
- `_is_conversational_deliberation` / Wittgenstein work is sophisticated — "detect
  indexical anchoring, not keywords" discipline is right in spirit. Irony: the sibling
  `_has_prescriptive_signal` check violates that discipline by demoting real declarative
  principles.
- Ablation toggles throughout show real measurement discipline

## Thread to rounds 1–4

Round 2 escalated to worst form. Same root:
> `DIRECTIVE` receives categorical type-based protection; `BOUNDARY` — the hard-limit
> type — does not, subjected instead to the same keyword-based competition/classification
> as ordinary knowledge.

Fix asymmetry once at type level, both findings close. Pattern unmistakable across five
rounds: principle enforced well in one place, identical sibling left unprotected. Durable
lever: when you protect/fix a category, grep siblings and protect/fix them, then add a
test asserting the protection is categorical.

---

**Filed at:** `workbench/AUDIT-FABLE-2026-07-02-round5-sleep.md`
