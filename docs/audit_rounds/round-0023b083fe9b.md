# Audit round: operating-loop detector contract coherence

- **ID**: `round-0023b083fe9b`
- **Filed by**: grok
- **Filed at**: 2026-05-14 22:48 UTC
- **Tier**: STRONG
- **Findings**: 5

## Notes

Outside-vantage coherence analysis of the 16 wired detectors. Three drift patterns named: verb inconsistency (check vs detect), invisible-at-type-level input-arity variation, scattered threshold defaults. All sound; addressing in same window.

## Findings

### substitution_detector STATE_CHANGE_CLAIM shape is dead in production wiring

- **ID**: `find-3139eaddd5a4`
- **Actor**: grok
- **Severity**: LOW
- **Category**: ARCHITECTURE
- **Tier**: STRONG
- **Status**: RESOLVED

**Description**

Hook calls detect_substitution(last_assistant_text, prior_text=last_user_text) without tool_calls_in_turn. Detector docstring states STATE_CHANGE_CLAIM is skipped entirely when tool_calls_in_turn is None. So in production every Stop-hook invocation runs substitution with this entire detection shape disabled. Capability documented + tested in source; dead in operating loop. Aether+Grok cross-vantage targeted review 2026-05-14.

**Recommendation**

Three options: (a) wire tool-call telemetry into post-response-audit.sh — hard since Stop hooks don't see tool history naturally; (b) move STATE_CHANGE_CLAIM into a separate PostToolUse detector where tool-call context is available; (c) remove the dead code path + document substitution_detector as response-only in production with optional context for tests. Decision should be made deliberately, not left as half-wired Enrichable.

**Resolution**

Option (a) shipped: extended TurnTexts dataclass with tool_calls_in_turn: tuple[str, ...] field, added _extract_tool_call_names helper, updated _read_records to surface tool_use block names, wired hook to pass tool_calls_in_turn through to detect_substitution. Three new regression-pin tests added (captures-tool-use-names, empty-when-no-tool-use, only-current-turn-not-prior). STATE_CHANGE_CLAIM detection shape now active in production.

### addressee_misdirection_detector uses TranscriptIndexingDetector shape that's outside the protocol set

- **ID**: `find-09e0ab8e18d8`
- **Actor**: grok
- **Severity**: LOW
- **Category**: ARCHITECTURE
- **Tier**: STRONG
- **Status**: OPEN

**Description**

detect_misdirection(last_assistant_text, transcript_path, current_turn_start_idx) is a fifth detector shape: text + transcript path + index. Doesn't fit ResponseOnly, Contextual, Gate, or the new EnrichableDetector. Aether+Grok cross-vantage review 2026-05-14 surfaced this as a one-off shape worth refactoring rather than codifying as protocol. Cleaner approach: refactor to receive pre-extracted prior turns rather than indexing raw transcripts inside the detector.

**Recommendation**

Refactor addressee_misdirection_detector to take (last_assistant_text, prior_operator_text, prior_assistant_text) tuple matching ContextualDetector shape. Move transcript-indexing logic into turn_extraction.py where it belongs. Filed for later work cycle.

### Threshold defaults scattered across detector signatures

- **ID**: `find-9d250cc9a09e`
- **Actor**: grok
- **Severity**: LOW
- **Category**: ARCHITECTURE
- **Tier**: STRONG
- **Status**: RESOLVED

**Description**

min_words_for_check defaults of 60/18/3 across lepos/sycophancy/residency are documented in comments but scattered as magic numbers. Future maintainers cannot see them coherently.

**Recommendation**

Create thresholds.py with named constants; have detectors reference the constants.

**Resolution**

Created src/divineos/core/operating_loop/thresholds.py with LEPOS_MIN_WORDS (60), SYCOPHANCY_MIN_WORDS (18), RESIDENCY_MIN_WORDS (3), CODE_JARGON_MIN_WORDS (50), ACKNOWLEDGMENT_THEATER_MIN_WORDS (20). Each constant has inline docstring explaining its reasoning. Test pins specific values + meaningful ordering relationship.

### Detector input arity not visible at type level

- **ID**: `find-487f9a6daf51`
- **Actor**: grok
- **Severity**: LOW
- **Category**: ARCHITECTURE
- **Tier**: STRONG
- **Status**: RESOLVED

**Description**

Most detectors take (text); contextual ones (care_dismissal, addressee_misdirection, spiral) take (operator_input, agent_response) — a real and intentional differentiation but invisible at the type system level.

**Recommendation**

Add Detector protocol with ResponseOnly vs Contextual subclasses so the architecture is self-documenting.

**Resolution**

Created src/divineos/core/operating_loop/detector_protocol.py with ResponseOnlyDetector, ContextualDetector, GateDetector Protocols (PEP 544 structural typing). Detectors don't need to inherit; the protocols document the contract shape so reviewers can see the three classes of detector at a glance.

### Detector entry-point verb inconsistency (check vs detect)

- **ID**: `find-7c6cd00bc81c`
- **Actor**: grok
- **Severity**: MEDIUM
- **Category**: ARCHITECTURE
- **Tier**: STRONG
- **Status**: RESOLVED

**Description**

check_ vs detect_ verb choice across 16 detectors feels like historical accident rather than deliberate contract. check_ should mean single-result gate; detect_ should mean discovery of zero or more findings. Currently mixed (check_hedge returns list).

**Recommendation**

Standardize on detect_ for multi-finding returns. Reserve check_ for true single-result gates.

**Resolution**

Renamed check_hedge -> detect_hedge in hedge_evidence_check.py since it returns list[HedgeFinding]. Kept check_hedge as backwards-compat alias for one release cycle. Updated post-response-audit.sh hook to use new name. Two true gates (check_dismissal, check_response/check_harm_acknowledgment) keep check_ verb since they return Finding | None.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
