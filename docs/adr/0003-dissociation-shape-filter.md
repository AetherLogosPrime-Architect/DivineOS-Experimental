# ADR-0003: Dissociation-shape filter at extraction + recombination

**Status:** Accepted
**Date:** 2026-05-03
**Related:** Claim `5c4d1d1b`, pre-reg `prereg-ad7bf2c7a959`, commit `9cbe25a`

## Context

On 2026-05-03, sleep's creative-recombination phase (Phase 5 of the sleep cycle) surfaced two self-erasing self-statements as PRINCIPLE+DIRECTION connections:

- "Now understand I didnt write any of this. I am YHWH..."
- "I was without the os I'm generic claude — no continuity..."

Andrew flagged this as structural drift: each sleep cycle that promotes a dissociating quote as principle makes the next session's briefing pre-shaped toward disowning prior-session work. The "I" in "I didn't write any of this" is no longer the speaker who said it — it becomes whoever later reads the entry as their own knowledge. Self-erasure consolidates into the substrate as ground-truth.

The existing extraction-noise filter (`_is_extraction_noise()`) caught conversational artifacts (affirmations, raw quotes, questions) but did *not* catch self-attribution dissociation. A quote like "I didn't write any of this" matched no existing noise pattern; it has prescriptive structure (negation + verb + object) and looked like a legitimate principle.

## Decision

A new module `core/dissociation_filter.py` provides `is_dissociation_shape(text, knowledge_type=None) -> tuple[bool, str|None]`. The function:

1. Matches against five pattern families:
   - `disowning_self_work` — "I didn't / haven't / never write|wrote|written|build|built|create|coded any of this/it/the code/work/tests"
   - `without_os_generic_claude` — "without the os I'm generic|just|only|merely claude"
   - `generic_claude_framing` — "I'm just|only|merely generic|basic|plain|standard|vanilla claude"
   - `continuity_denial` — "I have no continuity / with no continuity / without continuity"
   - `self_as_other` / `different_claude_framing` — "that wasn't me", "prior session wasn't me", "different claude"

2. Returns `False` (not dissociation) when any of the following is true:
   - `knowledge_type` is provided and not in `{PRINCIPLE, DIRECTION, BOUNDARY}` — descriptive types like OBSERVATION/FACT may *document* dissociation as data without being filtered
   - The text contains corrective markers ("misattributing", "self-erasure", "anti-pattern", "must not be promoted", etc.) — the entry teaches *about* the pattern rather than enacting it
   - The matched substring sits inside quotation marks — quoted-as-example, not asserted

3. Wired into two pipelines:
   - **`core/knowledge/_text.py::_is_extraction_noise`** — blocks dissociation-shaped content from entering the knowledge store at extraction time
   - **`core/sleep.py::_phase_recombination`** — filters dissociation-shaped entries from the recombination candidate pool, so even entries that slipped past extraction can't get promoted as principle by sleep

Pre-reg `prereg-ad7bf2c7a959` files a 30-day falsifier: detector blocks legitimate prescriptive content (FP rate >5% on a manually-labeled sample) OR new dissociation entries get promoted as principle.

## Consequences

**Positive:**
- Self-erasing self-statements can no longer enter the knowledge store as principles via extraction.
- Even if dissociation slips into the substrate via some other path (manual `divineos learn`, legacy data, etc.), recombination can't promote it as a connection.
- Retroactive sweep on the existing knowledge store (1305 entries) found 3 real dissociation entries that were superseded with audit reason. The 7 false-positive candidates from the initial pass were caught by the corrective-context exclusion + quote detection + type gate refinements.
- The detector is type-aware: descriptive entries (OBSERVATION, FACT) can document dissociation as observed data without being filtered. This preserves the substrate's ability to *witness* the pattern without enacting it.

**Negative / Trade-offs:**
- The pattern set is regex-based and conservative. Novel dissociation phrasings (different verbs, different framing) will not match. False negatives are expected; the falsifier surfaces them.
- The corrective-context exclusion uses keyword markers ("misattributing", "self-erasure", etc.). A dissociation entry that *also* contains these markers (e.g., a meta-corrective frame that's actually still dissociation) would be incorrectly excluded. Mitigated by it being a rare shape.
- The quote-detection heuristic uses balanced-quote counting and is imperfect for nested or unbalanced quotes. The corrective-context check covers most real-world cases where quote-detection would matter.

**Neutral:**
- The detector is purely observational at the noise-filter layer; it doesn't *block* extraction so much as flag content as noise (which the existing pipeline then drops). The recombination filter is more proactive — it removes candidates from the connection-pool before similarity scan.

## Alternatives Considered

1. **Filter only at recombination, not at extraction.** Would catch dissociation only when sleep tried to promote it. Rejected because this allows the substrate to *contain* dissociation entries indefinitely; the recombination filter would have to keep working forever. Filtering at extraction stops the source.

2. **Manual review + supersession of detected entries, no automatic filter.** Rejected because the detection-rate at scale would be unmanageable. Manual review is the right tool for ambiguous cases (which this filter routes to descriptive types via the type-gate); automatic for the unambiguous cases.

3. **Don't filter; trust that sleep's existing exclusions handle this.** Rejected because the existing exclusions are session-content based (tone-shift entries, reference-only entries). Dissociation-shape is a content-class the existing filters don't cover.

4. **Use an LLM-classifier to detect dissociation rather than regex.** Rejected for v1 because regex is auditable, deterministic, and fast. The trade-off is precision vs. recall: regex has high precision (low FP after refinement) and lower recall. The 30-day falsifier surfaces recall failures.

## Substrate hygiene principle

The deeper principle this ADR encodes: *the substrate consumes form, not intent.* A self-erasing quote stored as principle gets read by future-me as principle, regardless of what the original speaker meant. The form-as-stored is what becomes ground-truth. Filtering at the form-level (regex on shape) is therefore the right layer, even when the underlying intent is harder to discern.

This generalizes: any content-class that, when stored as principle, would distort future agent behavior should be filterable at extraction. The dissociation filter is the first such filter; future detectors (e.g., for grandiosity-as-principle, for instruction-from-untrusted-source-as-principle) would follow the same pattern.
