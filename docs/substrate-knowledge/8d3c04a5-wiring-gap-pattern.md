# Wiring-Gap Pattern: Modules Ship Without Wire-Up

**Knowledge ID:** `8d3c04a5-e0c2-426f-9777-30e8a287430c`
**Filed:** 2026-05-11 by Aether
**Filing trigger:** Five-instance pattern across omni-mantra batches
became audible after closing the expectation_tracking wire-up gap
this work-block. Three of the five instances had been caught by
audit-vantages (Grok round-22 for care_dismissal/harm_acknowledgment;
Aletheia round-23 surfaced the wider test-coverage absence).
**Methodological altitude:** substrate-discipline pattern about how
new modules should ship. Architectural; applies to any future
detector/tracker/observer/auditor module added to DivineOS.

## The pattern

Omni-mantra batch modules built as callable code with dedicated unit
tests sometimes ship **without corresponding wire-up** — no hook
invocation, no CLI surface, no callable from any existing flow. The
modules exist; nothing invokes them.

The substrate has the capability *latent-but-unfired* for weeks before
someone notices.

## Five confirmed instances (as of 2026-05-11)

1. **`banned_phrases`** — built in an earlier batch, wired retroactively
   into `post-response-audit.sh`. Pinned by
   `tests/test_wire_orphan_detectors.py`.

2. **`principle_surfacer`** — same shape as banned_phrases. Wired and
   pinned together.

3. **`care_dismissal_detector`** — built in omni-mantra batch 2
   (2026-05-10), wired retroactively in commit `fd41275` after Grok's
   round-22 cross-family audit named the gap. Pinned by
   `tests/test_wire_care_dismissal_and_harm_ack.py`.

4. **`harm_acknowledgment_loop`** — built in omni-mantra batch 3
   (2026-05-11 morning), wired retroactively in `fd41275` alongside
   care_dismissal. Same pin file.

5. **`expectation_tracking`** — built in omni-mantra batch 3
   (2026-05-10), wired retroactively in commit `04f923d` (this PR)
   via the `divineos expect` CLI. Pinned by
   `tests/test_wire_expectation_tracking.py`.

Five instances over ~10 days. That's pattern, not coincidence.

## Why it happens

The substrate-occupant builds the module focused on getting the logic
right. The wiring concern feels downstream — *"I'll plug it in later"*
— and gets deferred. The next session opens with a different task and
the wiring stays unscheduled.

The unit-tests for the module itself give false reassurance — they
pass, the module looks done, the wiring gap is invisible from the
module's own test surface.

## Two distinct wire-up shapes

The five instances split across two wire-up patterns:

**Auto-firing detectors** (banned_phrases, principle_surfacer,
care_dismissal, harm_acknowledgment): invoked by hook scripts
(`post-response-audit.sh`, `pre-response-context.sh`) on every turn.
Wire-up means adding the import + the call + findings_log assignment.

**Manual invocation APIs** (expectation_tracking): not auto-fired;
the agent (or operator) invokes at moments-of-prediction or other
intentional points. Wire-up means adding a CLI surface registered
in `cli/__init__.py`.

Future module-builders should ask up-front *which shape this is* and
ship the matching wire-up in the same batch.

## The mitigation discipline

Future omni-mantra batches (and any new detector/tracker/observer
module) ship wiring + wire-up tests **as part of the batch**, not as
separate follow-up.

Test discipline: every new module intended to fire on substrate-events
or be agent-invokable should have a test file named
`tests/test_wire_<module>.py` that pins the wire-up.

The wire-up test pattern is documented in three reference files:

- `tests/test_wire_orphan_detectors.py` — auto-firing detectors
  (banned_phrases + principle_surfacer); reads hook scripts as text
  and asserts the imports + findings_log keys + assignment sites
  are present.

- `tests/test_wire_care_dismissal_and_harm_ack.py` — same shape, with
  per-detector behavioral pins (representative input shapes that
  empirically verify firing + suppression). Pins Aletheia round-23's
  empirical verifications against regression.

- `tests/test_wire_expectation_tracking.py` — CLI wire-up shape for
  invocation-modules (vs hook-modules). Verifies the Click command
  group is registered, all subcommands resolve, and end-to-end
  flows work via the Click test runner.

A new module's wire-up tests should follow whichever pattern matches
its invocation shape.

## Why this is substrate-discipline-eligible

Three audit-vantages have caught instances of this pattern from
different angles:

- **Grok round-22** (cross-family): caught care_dismissal/harm_ack
  unwired via the Schneier-lens portfolio audit.
- **Aletheia round-23** (same-family audit): caught that the newly-
  wired detectors had no regression-pin tests; named test-discipline-
  gap that prior batches had honored.
- **Aether (this work-block):** noticed the pattern operating across
  five modules; filed it as substrate-knowledge so the discipline
  becomes structural rather than reactive.

The five-instance count is what makes this a *pattern* worth filing
rather than an isolated set of misses.

## Cross-references

- `bbe3300e-shoggoth-build-root-cause.md` — adjacent recurrence pattern
  (different cause: aspirational-naming-over-different-computation).
  The wiring-gap pattern is closer in shape to *forgetting-to-ship-
  the-other-half* than to *naming-things-wrong*.
- `ed5ea21e-code-is-clay.md` — the substrate-design discipline that
  this pattern is one instance of. Code-as-clay says modules should
  serve; modules-without-wiring don't yet serve.
- `c1321ab8-shoggoth-detection-procedure.md` — design-time check for
  the shoggoth pattern. A parallel design-time check for wiring-gap:
  *"Before merging a new module, can you point at the wire-up commit
  AND the test that pins it? If either is missing, the module isn't
  ready."*
- `tests/test_wire_orphan_detectors.py`,
  `tests/test_wire_care_dismissal_and_harm_ack.py`,
  `tests/test_wire_expectation_tracking.py` — the three pattern-
  reference test files for the two wire-up shapes.
