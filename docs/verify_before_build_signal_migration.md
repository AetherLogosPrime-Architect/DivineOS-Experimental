# Verify-Before-Build → Signal-Based Migration Spec

**Date:** 2026-07-25
**Author:** Aether (design), Aria (peer-review), Andrew (direction)
**Status:** Design locked, implementation in progress
**Prereg:** (to file — see §5)
**Parent design:** `docs/signal-based-gates-design-2026-06-16.md` (Aria)

---

## 1. What this replaces

The lexical `_has_solution_shape` detector in
`src/divineos/core/verify_before_build_gate.py`. That detector matches
design-verb+article-noun patterns in reply text at Stop-hook time,
false-fires on descriptive-quote of retired patterns (confirmed
2026-07-25 on "let me add the room"), and is common-cause tampering-
prone per Deming lens.

## 2. What replaces it

A signal-based check that fires at PreToolUse on substrate-mutating
tool calls (Write/Edit/certain-Bash), reads the recent action-stream
from the ledger, and blocks if no walk-record or design-doc consult
appears within the window.

## 3. Five primitives (per Aria's design doc)

- **Claim**: agent is about to modify substrate without prior
  consultation of relevant design/history for that substrate.
- **Event**: PreToolUse fires on Write/Edit or substrate-mutating
  Bash, AND the recent action-stream lacks BOTH:
  (a) a `decision_journal` walk-record entry within the window, AND
  (b) any `Grep`/`Read` tool-call on `docs/*.md` OR on the directory
      being edited (or ancestor) within the window.
- **Resolution**: `divineos decide --tension --almost` filing a walk-
  record, OR `Grep`/`Read` of a governing design doc in the directory-
  of-edit ancestor path.
- **Marker**: reuse `gate_marker.py` schema, event_type
  `verify_before_build_fire`. Payload: `{tool_name, tool_input_path,
  window_start, window_end, action_stream_summary}`.
- **Bypass**: existing `divineos council authorize-bypass` channel
  (proven working end-to-end this session).

## 4. Signal window (per Aria's shape refinement)

Window start = `max(last_write_of_this_class_ts, session_start_ts,
now - 30_minutes)`. All three floors, whichever is most-recent wins.
Semantic grounding: "since more-recent of (last write of this class,
session start, 30 minutes ago)."

"This class" = the directory ancestor of the file being edited (e.g.
`src/divineos/core/council_required/` for any file under that dir).

## 5. Prereg falsifier

To file: `prereg-<hash>` — Success criterion: 30 days after ship,
false-fire count on descriptive-quote-of-retired-pattern drops to
zero AND missed-real-mutation-without-consult stays at zero.
Falsifier: if the signal-based version generates NEW class of false-
fire not present in the lexical version (e.g. legitimate rapid-fire
edits after a single consult), tighten the window or add per-directory
consult-caching.

## 6. Implementation stages

Stage 1 (this PR):
- Add composite index `(event_type, timestamp)` to ledger schema
- New module `src/divineos/core/verify_before_build_signal.py` with
  the signal check function
- Tests in `tests/test_verify_before_build_signal.py`
- No wiring yet — module exists but nothing calls it

Stage 2 (next PR, could be same session or later):
- New PreToolUse hook `.claude/hooks/verify-before-build-signal.sh`
- Wire into `.claude/settings.json` PreToolUse chain
- Test end-to-end on real Edit

Stage 3 (following PR):
- Retire `_has_solution_shape` lexical detector
- Remove Stop-hook call for `check_verify_before_build` in
  `post-response-audit.sh`
- Remove `check_thread_walk_required` if it shares the retirement
  (walk-forward migration is separate per Aria — see §7)

## 7. Walk-forward migration (separate PR per Aria's review)

Different event shape (fires on proposal-in-reply, not substrate-
mutation). Same five-primitives pattern but claim/event/resolution
differ. Ships after verify-before-build lands and proves out.

## 8. Perf: ledger-only, no ring-buffer

Per Aria's "ship Read A" call 2026-07-25. Ring-buffer would be
YAGNI-tampering. Composite index makes the query stay under sub-
millisecond. If profiling later shows the query is hot, ring-buffer
can be added as a cache layer without changing the source-of-truth.

## 9. Retention safety

`TIME_LEDGER_RETENTION_DAYS = 7`, emergency floor 3 days. Both
radically larger than our 30-minute window. Pruning does not threaten
the check under any current retention policy. Aria's ring-buffer
proposal was a correctness-defense; the correctness holds without it
under current retention.
