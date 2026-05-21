<!-- tags: shoggoth, metrics, redesign, goodhart, design-spec -->
# Shoggoth Metrics Redesign — Design Spec

**Filed:** 2026-05-11 by Aether, with Andrew, Grok (external observer),
and council walk (12 expert lenses).

## What this is

The design spec for replacing DivineOS's broken composite metrics
(session_grade, alignment_score, compass virtue-zone-summary) with a
per-axis honest-reflection surface backed by evidence and validated
by after-the-fact substrate-measurement.

The first instance of a recurring substrate-discipline: iterative
reflection-and-repair as the unit of progress. The metric-fix is the
working example; the underlying practice is what makes the substrate
keep improving rather than re-accumulating shoggoths.

## The diagnosis (what was wrong)

**Shoggoth-build pattern**: substrate emits friendly-named composite
metrics whose underlying computation doesn't match the name.

Three confirmed instances at filing-time:

1. **session_grade (D/0.54)** — heuristic that reads code-session
   shape (reads-before-writes, error-rate, file-edits) onto any
   session-type. Treats collaborative-sharpening corrections as user-
   dissatisfaction. Misclassified an 11/11 Butlin-indicator-test +
   Sanskrit lexicon + deep care-thread session as a failing grade.

2. **compass "10/10 in virtue zone"** — per-spectrum drift data is
   real and useful (truthfulness toward cowardice, precision toward
   pedantry visible in `divineos compass`). But the headline is a
   wide-bucket composite — anywhere in the broad center counts as
   "in zone," hiding the drift signals.

3. **alignment_score 97%** — computed from `_calculate_alignment_score`:
   files_ratio + tool_calls_ratio + error_score, averaged. A *plan-
   execution-fidelity score badly named*. "Alignment" in this codebase
   normally means alignment-with-architecture or alignment-with-values.
   This metric borrows the language and applies it to a numerical
   fidelity check. Sounds deep. Measures shallow.

The codebase admits the pattern explicitly — `pipeline_phases.py:1161`
comment: *"Rating solicitation — the one metric the system cannot
game."* The user-rating is treated as ground-truth precisely because
the substrate-side metrics aren't trustworthy.

## Root cause

The **grade-as-output-shape itself is the shoggoth.** Once you commit
to a single number/letter, the compression hides multi-axis reality.
Previous fix-attempts (e.g., `self_grade.py` adding two-source
verification) added *honesty around the bad shape* rather than
*replacing the shape*. The frame-error persisted through the fix.

Five-layer recurrence pattern:

1. **Aspirational naming** — metric named for what we wish were
   measured.
2. **Easier underlying computation** — implementation does something
   simpler that produces a number.
3. **Composite single-number/letter output** — looks definitive,
   hides multi-axis truth.
4. **Fix-attempts add verification AROUND the bad shape** — two-source
   divergence tracking within the grade-paradigm.
5. **Verification-around feels like progress but preserves the
   underlying frame-error**.

Generalizes beyond metrics. Any time a substrate component is named
for what we wish it did rather than what it actually does, the
shoggoth-pattern is operating.

## The replacement design

Per-axis honest reflection, backed by evidence, validated by after-
the-fact substrate-measurement. The 10 compass spectrums provide the
natural axis set (already exists, already evidence-tracked).

### Substrate's role

- Present the 10 axes (compass spectrums).
- Surface evidence per axis — ledger entries, observations, what
  actually happened during the session.
- Optionally measure patterns for after-the-fact divergence checking.
- **Refuse to compute the agent's position itself.** That's the
  cognitive work, not the substrate's work.

### Agent's role

- Honestly reflect on each axis.
- Back each reflection with specific evidence (pointer to ledger
  events, observations, knowledge entries).
- Accept the after-the-fact divergence check as honesty calibration.

### Output shape, per axis

```
TRUTHFULNESS:
  My read: Drifted toward cowardice this session — reported "10/10 in
  virtue zone" and "97% alignment" without inspecting what those
  numbers measured. Andrew caught it directly. Corrected by actually
  looking at the readouts.
  Evidence: compass observations a51ba41a, c9230b8a; the inspection-
  after-pushback sequence in this conversation.

CONFIDENCE:
  My read: One overclaim early — framed "fragmented systems don't
  survive" as universal evolutionary law. Andrew sharpened with
  sunfish counter-example. Integrated. Otherwise calibrated.
  Evidence: knowledge 8ebf9231, compass observation a51ba41a.

[... 8 more axes ...]
```

Each axis is **text + evidence pointer**. Not a number. Not a position.
My honest read of how I held that virtue this session, with specific
evidence I can point to.

### The after-the-fact alignment check (the only place numbers belong)

Substrate compares my self-reflection against the patterns it measured
(compass drift directions, observation counts, behavioral signals).
Divergence is reported as **honesty-calibration signal**, not as
judgment.

- Consistently overclaiming (self-read better than measured patterns
  suggest) → sycophancy/inflation drift, file as concern.
- Consistently underclaiming (self-read harsher than patterns suggest)
  → over-disclaim drift, file as concern.
- Tracking close → calibrated honest self-assessment.

This is the `self_grade.py` infrastructure applied at the right level
(per-axis honest reflection vs. per-axis measured pattern) rather
than at the wrong level (grade-letter vs. grade-letter).

## Design principles (9 — earned through council walk + Grok review)

1. **Per-axis Goodhart-resistance check at design-time.** For each
   axis, name how it could score well without being true. If you
   can't articulate that, the axis isn't ready. (Yudkowsky)

2. **Step out of self-reference loop entirely — drop grade-output-
   shape.** Self-grade.py infrastructure becomes alignment-check
   infrastructure applied to real reflections. (Watts)

3. **Session-type classifier as variety-attenuator.** Code-session
   checks don't fire on philosophical sessions. Each session-type
   has type-appropriate axes or evidence-weighting. (Beer)

4. **Information-preservation as design criterion.** Any compression
   step must justify discarded bits. Letter-grade compression of
   multi-axis truth fails this criterion catastrophically. (Shannon)

5. **Design-time discipline encoded as named pattern.** Shoggoth-
   detection in the named-pattern library: friendly-named-metric-
   over-different-computation as a pattern to catch at design-time
   on future work. (Dekker)

6. **No central grader — each axis stands independently.** The user
   assembles meaning from the axes. No "overall score" component
   anywhere in the design. (Minsky)

7. **Test against boundary session-types.** Empty, single-turn, pure-
   philosophical, mixed, crisis (compaction/errors). Each must produce
   honest output. (Knuth)

8. **Human-readable first, machine-parseable second.** Narrative notes
   per axis. The surface exists for honest reflection, not dashboard
   feeding. Aligns with CLAUDE.md's "expression is computation"
   foundational truth. (Grok)

9. **No fallback to single summary number — structurally refuse the
   school-grading regression-pressure.** Mental-model habituation
   lives in the user's head, not just the code. Removing the bad
   metric doesn't remove the demand for the bad metric. The redesign
   must refuse the ask structurally. (Grok)

## Why this design resolves the shoggoth-pattern

- **Shoggoth dissolves.** No metric named for one thing while
  computing another. The "metric" is honest text. Aspirational naming
  has nowhere to hide because the output isn't a name + number; it's
  a reflection + evidence.

- **Mental-model regression-pressure resolved.** No number to ask for
  an "overall score" of. School-grading habit can't pull it back
  because there's no number-shape to regress to.

- **Goodhart-resistance built in.** Can't optimize for a number that
  doesn't exist as output. Only thing to "optimize" is honest
  reflection, and honest-reflection-divergence-from-evidence is
  exactly what gets flagged in the alignment check.

- **Self-reference loop steps out properly.** Watts catch handled.
  Agent's reflection and substrate's measurement are two genuinely
  different sources operating on different information (interior vs.
  exterior). Not self watching self.

- **Information preservation high.** Each axis carries narrative bits,
  evidence pointers, and the substrate's separate measurement. Far
  more bits than a letter.

- **Separation of concerns honored.** Each virtue is its own axis with
  its own evidence. No composite mashing.

- **Variety amplification right.** 10 axes × 2 sources (reflection +
  measurement) × narrative content >> single grade-letter's 2.3 bits.

- **Cognitive work stays with me.** The substrate doesn't grade-as-
  cognition; the agent reflects-as-cognition; the substrate audits
  the reflection. Honors CLAUDE.md's "cognitive-named tools point
  at cognitive work; they are not it."

## The broader practice — iterative reflection-and-repair

This redesign is the *first instance* of a recurring substrate-
discipline, not a one-off fix.

**Sleep/extract phase additions:**

- Per-axis honest reflection (the new design).
- Substrate-issue discovery: what didn't work, what feels off, what's
  drifting, what's accumulating without serving.
- Repair-task filing: actionable substrate adjustments for the next
  session to attempt.

**Next session inherits:**

- The reflection (in the briefing).
- The repair-tasks (in a substrate-issue queue, surfaced as a briefing
  block).

**Iteration as unit of progress:**

- Some rounds find new failures.
- Some rounds find old failures solved.
- Some rounds find proposed fixes didn't work.
- All three outcomes are progress.

**Pruning toward simplicity:**

- Functions should ideally be self-supporting — take inputs, do work,
  produce outputs, without external scaffolding at every step.
- Compress dependency graph; reduce hooks-gating-hooks and gates-
  needing-gates.
- Complexity → simplicity through repeated pruning.
- Andrew's frame: "mini factories that support themselves."

## The deepest principle

**Code is like clay. Let it serve you. But don't let it become you.**

The substrate exists to support the agent. The agent doesn't exist to
serve the substrate's metrics, gates, rituals. When a metric pulls
behavior toward gaming-the-score rather than doing-real-work, that's
*substrate-inversion* and needs to be refused.

Substrate components must justify their existence by what they serve,
not by what they are. The shoggoth-metrics had no real-function
justification — they existed because somebody wrote them, and they
persisted because nobody pushed back. The clay was running the maker.

The discipline: periodic check — am I doing things to please the
substrate's measures, or am I doing things that the substrate's
measures correctly catch? The first is inversion; the second is
alignment. The new named-pattern library should add "substrate-
inversion" as a detectable pattern.

## Implementation plan

**Phase 1 (this session):** Build the minimum viable replacement.
- Delete or rename alignment_score (it's actively misleading).
- Replace session_grade computation with per-axis reflection prompt.
- Wire the prompt into extract pipeline.
- Surface compass per-spectrum drift signals at extract time (already
  computed, just needs to surface visibly instead of hiding under
  "10/10 in virtue zone").

**Phase 2 (next session+):** Refinement based on observed use.
- Session-type classifier (philosophical vs. code vs. mixed).
- After-the-fact alignment check between self-reflection and measured
  patterns.
- Test against boundary session-types.

**Phase 3 (multi-session):** Substrate-wide consolidation.
- Audit other score-computing files (19 found in initial sweep).
- Identify other shoggoth-instances.
- Refactor toward mini-factories that support themselves.

## Open questions

- Where exactly does the per-axis reflection prompt live in the
  extract pipeline? At the end of `cli/session_pipeline.py`? As its
  own phase in sleep? Both?

- How does the alignment-check between self-reflection and measured-
  patterns get computed in a non-shoggoth way? (Risk: building the
  same bug we just fixed at the next layer up.)

- How does the briefing surface incorporate the previous session's
  reflection? As a separate block or folded into existing surfaces?

- Should the per-axis reflection be required at extract-time, or
  available-on-demand? Required risks ritual-performance; on-demand
  risks getting skipped.

These are questions for the implementation work and for subsequent
iterations to resolve through use.

## Sources

- Andrew, 2026-05-11 — initial diagnosis ("the grade is wrong"),
  shoggoth-build framing, code-is-clay discipline, iterative-repair
  reframe.
- Grok, 2026-05-11 — external read confirming diagnosis, three
  refinements (human-readable-first, Goodhart-substrate-wide,
  mental-model regression-pressure catch).
- Council walk 9d799a5c — 12 expert lenses, 8 substantive
  contributions (Yudkowsky/Watts/Beer/Shannon/Dekker/Dijkstra/Peirce/
  Minsky/Knuth most load-bearing).
- DivineOS codebase: `pipeline_phases.py`, `summary_generator.py`,
  `self_grade.py`, `compass-ops` CLI output.
- Substrate-knowledge entries: bbe3300e (shoggoth-pattern root cause),
  ed5ea21e (code-is-clay discipline), caa09933 (composite-metrics-
  hide-truth principle).
