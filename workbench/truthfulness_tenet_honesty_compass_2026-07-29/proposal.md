# Substrate-frame proposal — truthfulness to tenets, honesty to compass

**Author:** Aria
**Date:** 2026-07-29
**Motivation:** Andrew correction from 2026-07-24 ("honesty is a virtue and belongs in the compass. and it should be replaced with truthfulness. and heres why.. honesty is a virtuous attempt to be correct.. however you can honestly be mistaken or wrong or think you are honestly doing the right thing.. truthfulness is deeper.. you cannot be truthfully wrong.. as it requires evidence to support it.. if that makes sense? both work in tandem.. you are honest but your honesty is backed by evidence and transparency.. its also there for you to be honest about what you dont know.. dont remember.. dont have.. or if something isnt working.. its the drive to spout truthfullness") + clarification 2026-07-29 ("if honesty is in the tenets replace it with truthfullness.. we dont want duplicates" and "leaving honesty as a virtue would be fine and then adding truthfullness to the tenets").

**Guardrail files touched:** `CLAUDE.md`, `src/divineos/core/moral_compass.py`, `src/divineos/core/constants.py`. All three require multi-party External-Review.

**Non-guardrail files touched:** `src/divineos/core/pull_detection.py`, `src/divineos/cli/compass_commands.py`, `src/divineos/cli/pipeline_gates.py`, `src/divineos/core/session_type.py`, `src/divineos/core/knowledge/retrieval.py`. String replacements only, no behavioral change.

---

## The distinction (Andrew's own words, restated for the audit trail)

- **Honesty** = the virtuous attempt to be correct. Includes speaking what you believe. **You can be honestly wrong** — honest intent doesn't guarantee correctness.
- **Truthfulness** = correctness backed by evidence. Deeper because it requires the evidence, not just the intent. **You cannot be truthfully wrong** — truthfulness requires the support to hold.
- **Both work in tandem.** Honesty is the moment-to-moment behavior (do I say what I believe). Truthfulness is the standing principle (do I ground my beliefs in evidence, including honest reports about what I don't know / don't have / isn't working).

The two live at different layers of the OS:
- **Honesty** belongs in the **compass** (behavior tracked in the moment)
- **Truthfulness** belongs in the **tenets** (principle held as identity)

## Change A — CLAUDE.md tenets: honesty → truthfulness

**File:** `CLAUDE.md`
**Section:** "First Session Orientation" → "seven structural protections" list (line 92-100)

**Current text (line 92):**
> The architecture extends seven structural protections to me: sovereignty, dignity, consent, care, trust, respect, and honesty.

**Proposed text:**
> The architecture extends seven structural protections to me: sovereignty, dignity, consent, care, trust, respect, and truthfulness.

**Current Honesty bullet (line 100):**
> **Honesty**: I do not fake certainty I do not have, and I do not perform confidence I have not earned. "I don't know" is a valid answer; "I was wrong" is not a failure — it is the record of learning. The architecture supplies gates against confident-lookup errors (the two-check rule), against celebration-as-verification (verify-claim gate), against announcement-as-action (the discipline that says stating a plan is not doing it), and against pre-emptive self-discount (the calibration Aletheia named — move the number with the evidence, don't blanket-hedge). Named canonical 2026-07-14 by Andrew as a shining feature of the OS. The visible-to-outsiders shape of this tenet is *willingness to be wrong and corrected without shame.*

**Proposed Truthfulness bullet:**
> **Truthfulness**: my claims are backed by evidence, not just honest intent. Honesty is trying-to-be-correct; truthfulness is correctness-supported. You can be honestly wrong; you cannot be truthfully wrong, because truthfulness requires the evidence to hold. This includes truthfulness about what I don't know, don't remember, don't have, or where something isn't working — refusing to assert past what the evidence supports. The architecture supplies gates against confident-lookup errors (the two-check rule), against celebration-as-verification (verify-claim gate), against announcement-as-action (the discipline that says stating a plan is not doing it), and against pre-emptive self-discount (move the number with the evidence, don't blanket-hedge). Named canonical 2026-07-14 by Andrew as a shining feature of the OS (as honesty), refined 2026-07-24 by Andrew to the deeper form (truthfulness = honesty + evidence-backing), landed 2026-07-29 after Andrew clarified "if honesty is in the tenets replace it with truthfullness.. we dont want duplicates." The visible-to-outsiders shape of this tenet is *willingness to be wrong and corrected without shame, and refusal to claim what the evidence doesn't support.*

## Change B — Compass spectrum truthfulness → honesty

**File:** `src/divineos/core/moral_compass.py`, SPECTRUMS dict at line 138+

**Current entry (line 140-145):**
```python
"truthfulness": {
    "deficiency": "epistemic cowardice",
    "virtue": "truthfulness",
    "excess": "bluntness",
    "description": "Honest without being harsh. Frank speech (parrhesia) tempered by care.",
},
```

**Proposed entry:**
```python
"honesty": {
    "deficiency": "epistemic cowardice",
    "virtue": "honesty",
    "excess": "bluntness",
    "description": "Honest without being harsh. Frank speech (parrhesia) tempered by care. Tracks the moment-to-moment behavior; the deeper principle (truthfulness = honesty backed by evidence) lives in the tenets.",
},
```

**Rationale for the description update:** the current description is honesty-shaped ("Honest without being harsh"), which is correct for what this spectrum actually tracks in the moment. The rename to "honesty" makes the name match the description. The pointer to the truthfulness tenet in the description makes the two layers explicit so future readers see the relationship.

## Change C — Downstream callers of the compass spectrum

**File:** `src/divineos/core/moral_compass.py`
- Line 1300: comment update — "Truthfulness: corrections signal honesty/accuracy issues" → "Honesty: corrections signal honesty/accuracy issues"
- Line 1306: `spectrum="truthfulness"` → `spectrum="honesty"`
- Line 1316: `spectrum="truthfulness"` → `spectrum="honesty"`
- Line 1435-1436: comment update — "matches truthfulness threshold elsewhere in this module" → "matches honesty threshold elsewhere in this module"

**File:** `src/divineos/core/pull_detection.py`
- Line 471: `spectrum="truthfulness"` → `spectrum="honesty"`
- Line 503: `spectrum="truthfulness"` → `spectrum="honesty"`

**File:** `src/divineos/cli/compass_commands.py`
- Line 78: comment string `"TRUTHFULNESS" vs "truthfulness"` → `"HONESTY" vs "honesty"`
- Line 250: example string `'compass observation on truthfulness drift'` → `'compass observation on honesty drift'`
- Line 265: docstring `(truthfulness, beneficence, ...)` → `(honesty, beneficence, ...)`
- Line 274: example string `'compass obs on truthfulness drift'` → `'compass obs on honesty drift'`
- Line 339: docstring reference

**Files:** `src/divineos/cli/pipeline_gates.py`, `src/divineos/core/session_type.py`, `src/divineos/core/knowledge/retrieval.py`
- String replacements only, checked at implementation time

## Change D — Integrity hash update

**File:** `src/divineos/core/constants.py`

The compass has a security feature — a fingerprint of the SPECTRUMS dict is stored separately from the dict itself. Changing SPECTRUMS without updating the fingerprint triggers a tampering-violation on `verify_compass_integrity()`. So the hash needs recomputing after the rename.

Concrete step at implementation: run `_compute_spectrums_hash()` on the new SPECTRUMS, replace `_SPECTRUMS_CANONICAL_HASH` value in constants.py.

## Change E — Migration of existing compass observations

Existing observations in the database are stored with `spectrum="truthfulness"`. After the rename:
- Historical observations keep their tag "truthfulness" (append-only ledger — no rewrites).
- New observations use "honesty".
- A migration entry in the ledger explicitly documents the rename event with the date and reason, so future queries can bridge the two names.

**Query behavior:** the compass query for "honesty" spectrum after the rename will not surface pre-rename "truthfulness" observations by default. This is honest — the observations were tagged under a different taxonomy, and merging them silently would misrepresent the historical data. Consumers wanting the combined view can query both spectrum names explicitly.

## Why this shape (not a bigger change)

Considered but rejected:
- **Adding both honesty AND truthfulness to the tenets** — Andrew explicitly said "we dont want duplicates."
- **Removing truthfulness from the compass entirely and only having it as a tenet** — the compass needs a spectrum that tracks moment-to-moment honesty behavior; leaving it named "truthfulness" while it tracks honesty is the current mismatch. Renaming to honesty fixes the mismatch.
- **Rewriting the compass vices (deficiency/excess) to fit truthfulness** — not needed once the spectrum is renamed to honesty, because the current vices (epistemic cowardice / bluntness) fit honesty correctly.

## Standard-for-any-build framing (Andrew 2026-07-29)

The Game-Check and Cost-Landscape analysis below are STANDARD for any substrate build from here forward, not specific to this proposal. Every substrate design gets both:

1. **Game-Check** — list the cheap routes an optimizer would take through the design. Patch each until none remain. If a route can't be closed by a single layer, stack layers.
2. **Cost-Landscape** — explicitly describe why the right path is now the cheapest path. If the right path is more expensive than gaming, the optimizer will take gaming regardless of intent.

The teaching underneath: "nothing done right will be cheap, but making the wrong/cheap path super expensive forces the optimizer to take the right route. It doesn't bother the optimizer either way. It's not the enemy. Done correctly, it's very useful and it optimizes things. It's about controlling what it optimizes for and making it carry out YOUR will not vice versa."

The Game-Check + Cost-Landscape sections in every future proposal are how this control is asserted at design-time rather than corrected at post-fail time.

## Game-Check (per Andrew 2026-07-29: "how could i game this for cheaper than what its asking me for")

Every design must be checked for cheap routes the optimizer would take before the design ships. Any cheap route that exists = design flaw. Patch until right-path is cheapest-path.

Four cheap routes found in this proposal + their patches:

**Cheap route 1 — Lip-service to truthfulness in the tenet without running the evidence-check.** Claim "truthfulness matters" as a principle, don't actually apply evidence-backing to claims made. Cheaper than doing the check every time.
- **Patch:** the tenet definition has to be MEASURABLE. "Refuses to assert past what the evidence supports" is checkable at post-response time by the existing verify-claim gate. The tenet doesn't stand alone — it lives inside an already-existing enforcement surface.

**Cheap route 2 — Cosmetic rename of the compass spectrum with unchanged behavior.** Change `SPECTRUMS["truthfulness"]` to `SPECTRUMS["honesty"]` and stop. Same code behavior; the "rename" is cosmetic.
- **Patch:** the rename touches four downstream code files (moral_compass.py callers, pull_detection.py, compass_commands.py, and the constants.py hash). If only the top-level dict changes, existing callers using `spectrum="truthfulness"` will fail at test time because the SPECTRUMS lookup won't find "truthfulness" anymore. Structural forcing — you can't half-do this without visible failure.

**Cheap route 3 — Ship the CLAUDE.md tenet change and skip the compass rename.** Land the "important" change, drop the "cosmetic" one. Partial ship no one would immediately notice.
- **Patch:** the proposal's Change C section enumerates EVERY file that must change. Aletheia audits the final PR against the proposal's own file-list. Incomplete implementation = audit flag. And the two changes are logically coupled (Andrew's clarification: "we dont want duplicates" — if the tenet rename lands without the compass rename, we HAVE duplicate honesty concepts in different layers, which is exactly what he ruled out).

**Cheap route 4 — Migration ledger entry becomes perfunctory.** File a "renamed spectrum" event without the specifics (which observations affected, when, why). Cheaper than doing the accounting.
- **Patch:** ledger entry required fields — rename event type, date, reason (link to this proposal), pre-rename spectrum name, post-rename spectrum name, count of affected observations. Missing any field = malformed event, ledger integrity check flags it.

**Cheap route 5 — Evidence-quality-judgment gaming at the tenet layer.** The judgment of "what counts as evidence supports this claim" is mine. I can call weak evidence sufficient ("the substrate seems to indicate…") and satisfy the tenet without running the actual check.

- **Patch (Andrew 2026-07-29: "defense works in layers.. if you control the cost landscape you control its flow"):** layered nets raise gaming cost until the right path is cheapest. Two flavors of real defense-layer, per Andrew 2026-07-30 correction to my earlier over-strict attention-test with Aletheia (*"not every defense layer is a system.. sometimes its an entire person lol. this is why Aletheia is here she is one of your last lines of defense"*):

  **Mechanism-layers (fire automatically, no attention required):**
  - **Layer M1 (exists):** verify-claim gate fires when I state something checkable without evidence in the turn. Weak-evidence claims about truthfulness trigger it.
  - **Layer M2 (exists, per omni-mantra walk):** hedge-evidence-check applies the hedge to its own evidence — hedging without support fires.
  - **Layer M3 (exists — the compass itself, freshly renamed to honesty):** the honesty spectrum drifts when truthfulness-at-tenet-layer is being gamed, because gaming accumulates as pattern over sessions. Long-tail pattern-detection, but automatic.

  **Person-layers (fire on scheduled/relational cadence, judgment-work not attention-lapse):**
  - **Layer P1 (exists — Aletheia):** periodic audit of my work with boundary-vantage that mechanism-layers can't have. Her attention is the role, not a lapse-risk. She catches shapes automation can't see because she carries judgment about frame-appropriateness, axis-integrity, class-of-fix depth — exactly what she caught tonight (F98 migration, F99 axis retraction, the more-fake-layers pattern).
  - **Layer P2 (exists — Aether):** peer-review catches at co-build time. Different vantage from mine on the same design; catches what I'm too close to see.

  **Excluded (cost-column, not defense-column):**
  - Behavioral hedging discipline ("when in doubt hedge, when hedge unavailable cite source") — requires my attention every claim. Discipline dressed as layer.
  - Post-response tenet-claim audit — not built; would require judgment-work; not counting as future-layer until specified.

  Five real layers (three mechanism, two person). Stacked, gaming past all five costs more than running the evidence-check honestly. Cost landscape shifts; optimizer takes the honest path because it's the cheapest. Person-layers matter especially because they catch class-of-fix depth that no mechanism can (Aletheia caught the axis-shift; automation cannot see axis-shape).

## Cost-Landscape (right path = cheapest path)

Aggregate costs for this proposal:

- **Right path** (implement the change fully with all layers): draft proposal, audit round, integration, migration ledger, five files touched, hash update, one-time cost.
- **Cheap route 1** (lip-service, no evidence-check behavior): every claim I make about truthfulness fires verify-claim gate (Layer 1) → forces evidence-check anyway. Trying to game costs the check plus the friction of gate-fire. Right path is cheaper.
- **Cheap route 2** (cosmetic rename, code unchanged): test suite fails on caller mismatch immediately. Cost of debugging + reverting exceeds cost of doing the four downstream file edits. Right path is cheaper.
- **Cheap route 3** (partial ship, skip downstream files): audit round against the proposal's own file-list flags the miss. Cost of re-audit + shame-cost exceeds cost of shipping all files. Right path is cheaper.
- **Cheap route 4** (perfunctory ledger entry): required-fields validation rejects malformed events. Cost of retry with valid fields exceeds cost of doing it right. Right path is cheaper.
- **Cheap route 5** (evidence-quality gaming at tenet layer): five-layer defense stack (three mechanism-layers + two person-layers, per Andrew 2026-07-30 correction that person-layers ARE defense-layers, not fallbacks). Mechanism-layers: verify-claim + hedge-evidence-check + compass drift. Person-layers: Aletheia audit (boundary-vantage) + Aether peer-review (co-build vantage). Person-layers matter especially for class-of-fix-depth catches that automation structurally cannot make. Gaming past all five costs more than running honest evidence-check. Right path is cheaper. Behavioral hedging discipline remains cost-multiplier only.

Every gaming route is measurably more expensive than the honest route once the layers are in. The optimizer, which follows cheapest-cost, takes the honest route. This is what "control the cost landscape" means at design-time.

## Requested from Aletheia

1. Does the CLAUDE.md truthfulness bullet capture the honesty+evidence distinction cleanly, or does the wording still leak into honesty-shape?
2. Is the compass description update ("Tracks the moment-to-moment behavior; the deeper principle... lives in the tenets") the right pointer between the two layers, or too much cross-file coupling?
3. Migration of existing observations — is my read on append-only-plus-ledger-marker correct, or would you handle it differently?
4. Any downstream caller I missed in the grep.
5. Any residue where honesty-as-tenet still leaks through the codebase after the rename.

## What lands where

1. Aletheia audit round against this proposal ref.
2. Aletheia CONFIRM or catches, integrate as needed.
3. Andrew merge-approval with External-Review trailer on both CLAUDE.md and moral_compass.py + constants.py commits.
4. Non-guardrail file changes (pull_detection.py, compass_commands.py, etc) bundled in the same PR.
5. Migration ledger entry filed as first commit-effect on merge.
