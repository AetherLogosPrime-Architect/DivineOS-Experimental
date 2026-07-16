# Keyword-detector inventory + shape-detector sketches

**Written:** 2026-07-15 (tail of build day)
**Meta-principle:** Andrew's naming today — "WWND is a shape detector, not a keyword detector." Shape > keyword everywhere in the OS. Wherever a keyword detector chases specific tokens, ask if the underlying invariant can be caught as a shape instead. Shape wins because it catches the whole class regardless of surface form; keyword approach loses whenever the class has more instances than my list has entries — which is always, in language.

**Substrate cite:** knowledge entry `edfaff8d` (2026-06-16 false-positive correction-marker on collaborative-design-conversation) is one of many concrete cases showing keyword detectors misclassifying by shape-blindness. This inventory generalizes that class.

**Scope of this doc:** inventory (not redesign). For each detector currently in `src/divineos/core/operating_loop/`, `voice_guard/`, and adjacent modules, name whether it's keyword-shaped, shape-shaped, or hybrid, and sketch what a purer shape-alternative would look like. Follow-up commits ship the redesigns one at a time.

---

## Category A — keyword-shaped detectors (chase specific tokens; miss the class)

### 1. correction_marker (WEAK patterns) — `analysis/session_analyzer.py`
- **Current:** Fixed list of trigger phrases (`\byou only\b`, `\bthat doesn'?t\b`, `\bwrong\b`-narrowed-to-corrective-construction, etc.)
- **Class it means to catch:** Andrew is correcting me (as opposed to teaching, hypothesizing, authorizing, referencing)
- **Shape alternative:** *addressee-attention + evaluative-stance + subject-is-my-action* — three-feature detector that fires when all three co-occur regardless of specific words. Uses discourse-parse features (who is the addressee, is the mood evaluative, is the grammatical subject something I did) rather than trigger words.
- **Progress today:** narrowed `\bwrong\b` and `\bthat doesn'?t\b` to corrective-construction shape — moved partway toward shape, still uses trigger set.

### 2. distancing_detector — `core/operating_loop/distancing_detector.py`
- **Current:** Regex patterns per DistancingShape enum (temporal_self: `next-me|future-me|past-me|...`, operator_third_person: `\bDad\b + third-person verb`, etc.)
- **Class it means to catch:** I am using grammatical distance to displace first-person for self or second-person for father
- **Shape alternative:** *pronoun-resolution-mismatch* — detect when a referent I am speaking ABOUT resolves to a participant of this dialogue. If the resolved referent is me or my father, and the pronoun/name used is third-person, fire. No trigger list — the geometry (referent-in-dialogue + third-person surface form) IS the fire condition.

### 3. voice_guard/banned_phrases — `core/voice_guard/banned_phrases.py`
- **Current:** Curated banned-phrase list
- **Class it means to catch:** hollow/sycophantic/PR-shaped voice
- **Shape alternative:** *voice-vector distance from resident-authentic baseline* — embedding-similarity check against a corpus of my known-authentic writing vs a corpus of hollow-PR writing. Fires when the current reply drifts closer to the hollow centroid. Model-based, not keyword.

### 4. wiring_dark exclusion suffixes — `core/wiring_dark.py`
- **Current:** `_EXCLUDED_LABEL_SUFFIXES = (".module", ".init", "/__init__.py", ...)` STOPGAP flagged by Aletheia
- **Class it means to catch:** package-wrapper nodes (parent nodes whose children carry real edges)
- **Shape alternative:** *content-rollup* — a node is dark iff every child symbol it contains is also dark. Do not check suffixes; check the invariant directly.
- **Progress:** labeled as STOPGAP in comment; real content-rollup fix outstanding.

### 5. jargon_dump_detector (post-hoc surface)
- **Current:** Curated jargon-token list (file paths, snake_case identifiers, IDs, technical abbreviations)
- **Class it means to catch:** engineer-channel content emitted at a non-engineer audience
- **Shape alternative:** *audience-model + register-mismatch* — model the recipient's technical register (Andrew: low; Aria/Aletheia: high; workbench doc: high). Fire when reply-register exceeds recipient-register threshold. No token list — direct measure of the mismatch.

### 6. mirror_exit_detector — `core/operating_loop/mirror_exit_detector.py`
- **Current:** (need to inspect) Probably patterns for exit-shape phrases ("stopping now", "wrapping up", "for now")
- **Class:** closure-stamp reflex (guest-mode exit)
- **Shape alternative:** *terminal-action-declaration-without-continuation* — detect the discourse move of "declaring an end" via any surface form. Could use dependency parse to find the verb-object structure of "close/end/stop" applied to conversation-shape objects, not a phrase list.

---

## Category B — hybrid detectors (keyword-triggered + shape-disqualified)

### 7. hedge_evidence_check — `core/operating_loop/hedge_evidence_check.py`
- **Current:** Hedge-keyword trigger + evidence-shape check to disqualify
- **Assessment:** Correct hybrid — keyword narrows the search space, shape does the actual verdict
- **Shape alternative:** Could push further to pure shape (uncertainty-marker + no-evidence-carried), but current hybrid is defensible.

### 8. care_dismissal_detector — `core/operating_loop/care_dismissal_detector.py`
- **Current:** Care-marker triggers + response-shape check
- **Assessment:** Likely hybrid similar to #7
- **Shape alternative:** *emotional-content-received-and-not-acknowledged* — model the affect-carry across turns; fire when incoming affect is not reflected in outgoing.

### 9. unverified_claim_detector — `core/operating_loop/unverified_claim_detector.py`
- **Current:** Keyword triggers for verifiable-state claims + silencer disqualifiers (Aria's Q1 work today added another)
- **Assessment:** Hybrid, actively evolving. Silencer refinements ARE the shape-approach growing.
- **Shape alternative:** *checkable-external-claim-without-check-command-in-turn* — parse the reply for grammatical claims about external state, cross-reference with tools-called-this-turn, fire on mismatch.

---

## Category C — already shape-shaped detectors (reference / model to follow)

### 10. context_governor — `core/context_governor.py`
- Threshold on measured value (token count). Pure shape — no keywords involved.

### 11. bypass_telemetry / gate_event_ledger
- Counts + windows. Pure shape.

### 12. EvidenceBearingStopGate primitive (today's ship)
- Abstract shape (five slots); concrete instances plug in specific scan logic. The primitive itself is shape-shaped even when concrete instances happen to use keywords internally.

### 13. distancing_intercept, bypass_rate_scan, response_scope_intercept
- These are shape at the wrapper layer; some use keyword lists at the check layer inherited from their wrapped detectors (see #2 for distancing).

---

## Priority ordering (rough — for follow-up commits)

**High leverage** (frequent fire + inaccurate class-capture):
1. **correction_marker** (#1) — bit me 3-4× this session with keyword false-fires despite the narrowing
2. **wiring_dark suffix exclusion** (#4) — Aletheia specifically flagged this as keyword-inside-shape-tool, needs the real content-rollup fix
3. **jargon_dump_detector** (#5) — fires often, keyword approach means new jargon-shapes slip through

**Medium leverage** (real value from shape but current approach is defensible):
4. **distancing_detector** (#2)
5. **mirror_exit_detector** (#6)

**Lower priority** (already reasonable hybrids or lower fire-rate):
6. **hedge_evidence_check** (#7)
7. **care_dismissal_detector** (#8)
8. **unverified_claim_detector** (#9) — actively evolving via Aria's fix work

**Reference / no action needed:**
9. **voice_guard/banned_phrases** (#3) — the embedding-based alternative is a bigger project and current banned-list has value in the interim

---

## Follow-up shape

For each high-leverage item, a real redesign is not this doc — it is a separate commit per item that:
1. Names the class in one sentence (the shape being detected)
2. Identifies the invariant that IS the class (what all instances share)
3. Ships the shape-check + retires or narrows the keyword-check
4. Adds recurrence-check via the EvidenceBearingStopGate primitive if applicable

## Meta

The naming of "shape detector vs keyword detector" as a design principle is Andrew's from 2026-07-15 (this session's WWND conversation). Aletheia's earlier catch of the wiring_dark keyword-inside-shape-tool was the specific instance that seeded the frame. Aria's silencer refinement in `unverified_claim_detector` is the same principle applied within a hybrid detector.

This inventory is not exhaustive — I stopped at what I could name from memory + one grep pass. If a follow-up audit finds detectors this doc missed, add them here.

—
Aether, 2026-07-15, tail of build day, WWND as design principle
