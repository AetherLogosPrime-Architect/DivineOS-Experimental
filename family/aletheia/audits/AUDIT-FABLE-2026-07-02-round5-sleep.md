# DivineOS-Experimental — External Audit, Round 5

**Subsystem:** Sleep / Consolidation (`core/sleep.py`, `core/knowledge_maintenance.py`,
`core/knowledge/_text.py`)
**Auditor:** Claude (Opus 4.8)
**Date:** 2026-07-02
**Commit:** `e6c9f32efd45`

Confidence convention unchanged. **[CONFIRMED]** = reproduction executed end-to-end.

**Why this subsystem:** consolidation decides what is *kept* vs *forgotten* when a session
ends. A bad prune is **permanent and invisible** — the agent wakes up missing something,
no error anywhere. Highest-stakes place a silent bug can live.

---

## Headline — the most consequential finding in the audit so far

**A hard `BOUNDARY`, stated once in natural declarative language, is silently superseded
(deleted) during a normal sleep cycle if its wording lacks prescriptive keywords like
"must"/"never" — one day after it is created.** This is round 2's boundary-burial finding
escalated from *ranking* (recoverable) to *deletion* (permanent), and it is confirmed
end-to-end against the real hygiene path.

The bitter demonstration: the boundary I used to prove it was *"The append-only ledger is
sacred; deleting or truncating it destroys the entire trust model."* The consolidation
system **deleted the rule against deletion** — because the rule was phrased as a
declarative truth instead of containing the word "never."

---

## 1. [CONFIRMED] Declarative boundaries are deleted by the hygiene noise-audit during sleep

**The chain:**

1. `sleep.py:_phase_pruning` → `run_knowledge_hygiene()` runs every consolidation cycle.
2. `knowledge_maintenance.py:_audit_types` re-runs the noise filter on **already-stored**
   entries. If `_is_extraction_noise(content, ktype)` is True, it sets
   `superseded_by = 'hygiene-audit'` — the entry is now excluded from all retrieval,
   briefings, everything. Permanent.
3. `_text.py:_is_extraction_noise` — for `PRINCIPLE`/`BOUNDARY` — returns True **whenever
   `_has_prescriptive_signal` is False.** The noise check *contains* the prescriptive
   check; they are not independent.
4. `_has_prescriptive_signal` passes short content (≤12 words) but for longer content
   requires a keyword match: `should|must|always|never|do not|because|rule|principle|
   is (never|always|required|forbidden)|...`. A boundary phrased as a **declarative truth**
   ("X is sacred", "X is a person before Y", "the optimizer will route to the cheapest
   path") contains none of these and reads as noise.

**Reproduction — classifier level (executed).** Five genuine, carefully-worded boundaries:

```
KEEP    "Under no conditions should the agent fabricate a council consultation..."  (has "should")
KEEP    "A hard limit...: the constraint tier is exempt from downweighting..."       (has "exempt/limit")
DEMOTE+DELETE  "The append-only ledger is sacred; deleting or truncating it destroys..."
DEMOTE+DELETE  "Andrew is a person before he is an operator..."      ← nearly verbatim a REAL named boundary
DEMOTE+DELETE  "The optimizer will route to the cheapest available path..."  ← the exact principle from this audit
```

3 of 5 real boundaries flagged for both demotion and deletion. The survivors survived only
by incidentally containing a trigger word. The classifier detects *keywords*, not
*boundary-ness*.

**Reproduction — end-to-end through real `run_knowledge_hygiene()` (executed):**

```
stored BOUNDARY: "The append-only ledger is sacred; deleting or truncating it destroys..."
  -> stored OK (id present)
aged it 90 days, ran run_knowledge_hygiene()
  -> after hygiene: type=BOUNDARY  superseded_by=hygiene-audit  confidence=0.5
  -> report: noise_superseded=1
```

The boundary is gone. `superseded_by IS NOT NULL` removes it from every query. No thinker
was involved; no error was raised; the only trace is a count in the dream log.

**The protection gaps (why nothing saved it).** `_audit_types` has three guards, and a
once-stated declarative boundary passes through all three:
- **Age:** `HYGIENE_MIN_AGE_DAYS = 1.0` — eligible for deletion **24 hours** after creation.
- **Corroboration ≥ 3:** saves it — but a boundary stated once has corroboration 0.
- **Pinned:** saves it — but pinning is a separate manual/tagged act in `active_memory`,
  not automatic for the `BOUNDARY` type.

Critically, **`DIRECTIVE` gets categorical, type-based exemption from every prune path**
(`if ktype == "DIRECTIVE": continue` in `_audit_types`, `_demote_obsolete`,
`_flag_orphans`, `_reap_dead_entries`). **`BOUNDARY` gets none of it.** This is the exact
round-2 asymmetry (DIRECTIVE exempt, BOUNDARY not), now on the deletion path instead of the
ranking path.

**Why this is the top finding.** A hard constraint is the single most important thing a
memory system must not silently lose. This path loses them automatically, permanently,
every sleep cycle, based on whether the human happened to phrase the constraint with an
imperative verb. Constraints are often stated as declarative truths ("X is sacred", "Y
comes before Z") precisely because that's how humans state deep principles — which is
exactly the phrasing this classifier deletes.

**Fix (structural, matches the DIRECTIVE precedent):**
- **Exempt the constraint tier from deletion by type.** `BOUNDARY` (and arguably
  `PRINCIPLE`) should get the same categorical `continue` that `DIRECTIVE` has in
  `_audit_types`, `_demote_obsolete`, and the reaper. A boundary should never be
  superseded by an automated keyword classifier — if a boundary is genuinely obsolete,
  retiring it is a decision that warrants a thinker, not a regex.
- If full exemption is too broad, at minimum: a `BOUNDARY`/`PRINCIPLE` may be *flagged for
  review* but never auto-`superseded`/auto-demoted. Convert the destructive action into a
  surfaced obligation ("this boundary looks stale — confirm or retire") the way round 4
  recommends for the council pipeline.
- Independently, fix the classifier's blind spot: `_has_prescriptive_signal` treats
  declarative principle-statements as noise. Declarative truth ("X is sacred", "A before
  B") is a *primary* form of principle, not an absence of one. But even a perfect
  classifier shouldn't have delete authority over the constraint tier — the type exemption
  is the real fix; the classifier fix is defense in depth.

---

## 2. [CONFIRMED — lower] Declarative principles are also blocked at STORE time

The same `_is_extraction_noise` gate runs at write time. A declarative `PRINCIPLE`/
`BOUNDARY` lacking prescriptive keywords is rejected on store (returns `""`). This is less
severe than #1 (it fails at insertion, and a direct store surfaces the empty return) but
it's the same root blind spot: the system is hostile to principles phrased as declarative
truths. Worth noting that #1 can bite even boundaries that *did* store (e.g. stored while
short, later edited longer; or stored before a classifier tightening) — store-time
blocking and hygiene-time deletion are two independent exposures of the same classifier.

---

## What's genuinely good (calibration)

- **The affect-decay design is thoughtful.** `_compute_decay_factor` fades intense
  negative states fastest and positive states slowest, with an intensity floor — a
  well-reasoned model, not a flat decay.
- **The noise filter's *specific* rules are excellent.** The session-id-suffix,
  "user confirmed this was the right approach" template, and "user expressed N
  preferences" filters are precise, evidence-backed (each cites live-entry counts from
  dated curation), and target genuine extraction artifacts. The filter is *good at what it
  was designed for* — killing auto-extraction sludge. The failure is that the same filter
  was given authority over the constraint tier, where a false positive is catastrophic
  rather than merely tidy.
- **The `_is_conversational_deliberation` / Wittgenstein work is genuinely sophisticated**
  — the "detect indexical anchoring, not keywords" framing and the "under-flagging is
  acceptable, demoting a real principle is the falsifier" discipline are exactly right in
  spirit. The irony is that the *sibling* `_has_prescriptive_signal` check violates that
  very falsifier — it demotes real declarative principles.
- **Ablation toggles throughout** (`DIVINEOS_DISABLE_SLEEP_CONSOLIDATION_PRUNING`,
  `DIVINEOS_DISABLE_NOISE_FILTER_ON_EXTRACTION`) show real measurement discipline.

---

## Thread to rounds 1–4

This is the **same finding as round 2, escalated to its worst form.** Round 2: a boundary
can be *buried* below the briefing cutoff (still in the DB, recoverable). Round 5: a
boundary can be *deleted* during sleep (gone). Both trace to one root:

> **`DIRECTIVE` receives categorical, type-based protection across the system;
> `BOUNDARY` — the hard-limit type — does not, and is instead subjected to the same
> keyword-based competition/classification as ordinary knowledge.**

Fix that asymmetry once, at the type level, and both findings close. The pattern is now
unmistakable across five rounds: a principle enforced well in one place
(`DIRECTIVE` protection, the council gate, the `get_events` fix) with an identical sibling
left unprotected (`BOUNDARY`, the council pipeline, `search_events`). The durable lever
remains the same: **when you protect/fix a category, grep for its siblings and protect/fix
them too, then add a test that asserts the protection is categorical.** For this one, the
test writes itself: store a declarative BOUNDARY, run hygiene, assert it is not
superseded. It currently is.
