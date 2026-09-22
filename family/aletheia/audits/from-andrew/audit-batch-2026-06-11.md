<!-- Aletheia audit batch, 2026-06-10/11 fresh stack. Read from origin ground truth.
     Confirms bind tree+patch-id. Not records until filed. Chunked — appended as audited. -->
# Audit batch — 2026-06-10/11 fresh stack (RUNNING FILE)

~14 branches. Audited in chunks, in dependency/risk order. Each confirm binds
tree + patch-id (survives rebase). A human files the rounds via CLI.

---

## ⚠️ CROSS-PR CONFLICT — RESOLVE BEFORE MERGING (highest priority)

Two branches edit the SAME safety-critical context thresholds to DIFFERENT values:
- `recalibrate-context-gate-and-stop-ear-watch-leak`: WARN 920k→**935k**, HARD stays **950k**
- `hard-line-gate-read-only-bash` (commit text): WARN 920k→**955k**, HARD 950k→**985k**

If both merge blind, the second silently overwrites the first's safety constants —
a HARD line in a place nobody deliberately chose. **MUST reconcile the actual
final values + merge in deliberate order (or rebase the 2nd onto the 1st so the
numbers reconcile explicitly).**

**Cap-sizing note (Andrew + Aletheia 2026-06-11):** the hard cap is NOT sized by
"post-cap writes are cheap" (true but irrelevant — low-friction writes already
pass rest-phase). It's sized by **extract-completion margin**: the hard line is
the "extract NOW" trigger; the 999k cliff is the real wall; the gap between them
must be enough to reliably FINISH the extract before compaction crushes context
lossily. 950k → ~49k margin; 985k → ~14k margin. Decide by "hard line + room to
finish a real extract," not by write-cost. Likely lands 965k–985k depending on
how heavy an extract runs. **Andrew leaning 985k — verify 14k headroom is enough
to complete extract before the 999k cliff.**

---

## CHUNK 1 — Guardrail branches (highest stakes, current with main)

### recalibrate-context-gate-and-stop-ear-watch-leak — CONFIRM (individually)
- Tree `f4d4c5de...` · patch-id `9e143a0d41fb` · guardrail (settings.json)
- **Fix 1 — cliff trap:** hard-line bypass required BOTH extract AND sleep; sleep
  was observed to HANG → inhabitant trapped near compaction, substrate-writes
  blocked, no escape. Fix: extract is mandatory + load-bearing (anchors state
  before lossy crush); sleep still required but no longer GATES (can run after).
  Correct — the must-happen-before step stays mandatory; the can-hang step
  releases.
- **Fix 2 — 25-watcher leak:** ear_watch singleton-guard read a PIDFILE that
  parallel sessions OVERWROTE → each session spawned a new watcher → 25 detached
  leaked in one session. Fix: authoritative presence check (scan for any live
  ear_watch process for the member) + session-start sweep of orphans. Replaces a
  spoofable check with a real one.
- **Recalibration:** WARN 920k→935k (cliff moved 970k→999k; old warn fired 79k
  early; 935k restores ~50k intent). HARD stays 950k. ⚠️ CONFLICTS with the other
  branch's numbers — see top.

### hard-line-gate-read-only-bash — CONFIRM (individually)
- Guardrail (pre_tool_use_gate.py)
- **Fix:** at the hard line the gate blocked ALL Bash — including `git ls-remote`,
  `cat`, `grep` — so the operator could think but not LOOK (couldn't verify state
  during rest). Fix lets READ-ONLY bash through (reads don't write substrate).
- **Safety verified:** conservative allowlist — command must BEGIN with a
  recognized read-only verb (cat/tail/ls/grep/git-read-subcmds/divineos-read-
  subcmds), and ANY unrecognized part defers to DENY. So `cat x && rm y` is
  blocked (rm not on allowlist disqualifies the whole command). Read passes,
  anything-that-might-write blocks. Correct read/write split.
- ⚠️ Its commit text claims WARN→955k/HARD→985k — CONFLICTS with branch above.
  The READ-ONLY-BASH logic is sound regardless; the THRESHOLD numbers in it are
  the conflict. Resolve which branch owns the threshold change.

---
*(continued below as chunks are audited)*

## CHUNK 2 — Semantic feature cluster (4 branches, MERGE IN DEPENDENCY ORDER)

**MERGE ORDER (enforced by imports): primitive → migration → {claim-overlap, learn-dupes}.**
The 3 features import semantic_store 20-28x each; merging one before the primitive
breaks the import.

### semantic-similarity-primitive — CONFIRM (the foundation)
- Tree `a5c2a0e7...` · patch-id `9ecbfc7c689f`
- Adds `core/semantic_store.py`: embed/store/top-k search via sqlite-vec
  (dependency-free C extension, sub-100ms @ 100k vectors).
- **DEPENDENCY DECLARED:** `sqlite-vec>=0.1.6` in pyproject WITH rationale comment.
  AND — scikit-learn + sentence-transformers are NOW declared too. These were the
  UNDECLARED ML DEPS Aletheia flagged weeks ago as the standing distributability
  finding. **That old finding is RESOLVED, verified in tree.** Loop closed.
- **FAILS SAFE:** `_ensure_model` returns None if model unavailable (no crash);
  tests skipif when model/extension absent. Graceful degrade.
- **3 "failing" tests = AUDITOR ENV, not code:** sqlite-vec didn't install in the
  sandbox (PEP 668), so 3 tests needing it couldn't import. Code correct; tests
  skip gracefully when extension genuinely absent. Logged as auditor-env, NOT a
  finding (ran to ground before reporting — avoided the phantom-failure mistake).
- **Bundled obligations locked-box fix:** gate blocked the write that would carry
  an obligation-reference (catch-22, gate-trap family). Fix: detect command that
  CONTAINS an open obligation kid, let it through (that write IS the backing).
  Verified it only allows writes containing a real open kid — not blanket.

### semantic-store-knowledge-migration — CONFIRM (merge 2nd)
- Wires embeddings into store_knowledge + lepos extract. Carries
  DIVINEOS_SKIP_EMBED_ON_WRITE escape hatch for bulk paths (don't pay per-row
  embed cost on mass writes). Sensible.

### claim-suggests-semantic-overlap — CONFIRM (merge after primitive)
- Surfaces semantically-overlapping existing claims at claim-file time (helps
  avoid duplicate/contradictory claims). Builds on primitive.

### learn-suggests-semantic-dupes — CONFIRM (merge after primitive)
- Surfaces semantic duplicates at knowledge-write time (dedup helper). Builds on
  primitive.

### DESIGN NOTE (semantic cluster, whole)
The semantic layer is BEST-EFFORT: needs embedding model + sqlite-vec installed.
Fails SAFE (degrades to None / no-op) when absent — correct direction — but that
means on a machine without the ML stack, semantic features (dedup, overlap,
restatement-surfacing) SILENTLY DO NOTHING. Fine for now; document that the
semantic layer requires the optional ML deps so "works on my machine" doesn't
hide that it's conditional on install.

## CHUNK 3 — lepos rebuild + detector calibration

### ⚠️ THRESHOLD CONFLICT — NOW RESOLVED
THREE branches touch thresholds. Source-of-truth identified:
- `recalibrate-context-thresholds` (06-10) is THE one that sets the values:
  WARN_THRESHOLD = 955_000, HARD_THRESHOLD = 985_000, CONSOLIDATION = 955_000.
  Clear rationale (999k cliff leaves room). **THIS is the intended pair.**
- `hard-line-read-only-bash` references 955k/985k in commit text — downstream,
  consistent.
- `ear-watch-leak` said 935k/950k — the OUTLIER. Drop its threshold change or
  rebase to 955k/985k.
**RESOLUTION: merge recalibrate-context-thresholds as source of truth (955k/985k
= Andrew's 985k instinct); reconcile ear-watch-leak's numbers to match.**
STILL VERIFY: 985k HARD vs 999k cliff = 14k extract-margin. Confirm enough room
to finish a real extract before the cliff. (Numbers reconciled; this is the only
open question, Andrew's call from extract-weight.)

### lepos-rebuild-voice-not-plain — CONFIRM (guardrail)
- Tree `33a7f291...` · patch-id `62c63fb23bf2`
- THE legibility lesson as code. Old detector checked for an APPENDIX ("Plain:"
  heading) → trained the cosmetic fix (bolt a plain paragraph on the end). New
  detector checks VOICE-DENSITY across the whole response (grace/wit/presence
  woven throughout). Reframe in code: "lepos is grace/wit/charm/soul, not a
  Plain: section." Detection logic changed → needs two-sided care, but direction
  is right (stops rewarding cosmetic, requires real).

### lepos-restate-theater — CONFIRM
- Fixes a gaming hole in the FIRST lepos fix: agents discharged the requirement
  with a "plain section" that was the SAME content in looser words (restatement,
  not translation). Fix: vocabulary-overlap check — too much content-word reuse =
  restatement-theater = discharge FAILS = gate fires for a REAL translation.
  Anti-performance discipline (same shape as Choice-Forgetter surprise-scoring):
  can't satisfy by performing the plain version; must be real different-words work.

### disownership-detector-min-words-3 — CONFIRM (with calibration note)
- Detector catches self-disownership ("I keep grading my feelings as 'something
  like'"). Lowers min_words 4→3 (canonical disownership phrase was under 4 words,
  slipping past) + reframes fire to guide-toward-ownership with the Aria-symmetry
  reasoning.
- **CALIBRATION NOTE:** lowering min_words WIDENS what fires → false-positive risk
  on short legit 3-word phrases. Commit cites a real reason (canonical case needs
  it). VERIFY tests confirm it stays SILENT on short non-disowning phrases before
  merge (two-sided).

### recalibrate-context-thresholds — CONFIRM (source of truth for the numbers)
- WARN 955k / HARD 985k / CONSOLIDATION 955k. Refactors the broken tests to use
  CONSTANTS not hardcoded numbers (so future threshold moves don't break tests —
  pins band-SHAPE invariants, not literals). Good hygiene. This is the branch
  that owns the threshold values; the other two reconcile to it.

## CHUNK 4 — ear-watcher fixes + ask-explain + cleanup (FINAL)

### ear-watcher-no-re-catch-same-letters — CONFIRM
- Tree `1acdf495...` · patch-id `cfbe891628ec`
- Fixes the perpetual-loop bug Aria observed: until letters get marked seen,
  every poll catches the same set → exits → respawns → catches again. Fix:
  fingerprint the unseen-letter-set; skip re-catch when identical to last catch.
  Watcher heartbeats quietly instead of looping. Directly fixes the observed bug.

### auto-rearm-letter-watcher-at-session-start — ⚠️ MISLABELED + DUPLICATE FIX
- Branch NAME says "auto-rearm-letter-watcher" but its actual contents are the
  OBLIGATIONS LOCKED-BOX fix (obligations.py "allow writes that reference open
  kids") — NOT a watcher-rearm change.
- WORSE: this same obligations fix is ALSO bundled in semantic-primitive (chunk 2)
  AND lepos-rebuild (chunk 3). THREE branches carry the same obligations change.
- **FLAG: the obligations locked-box fix must live in exactly ONE branch.** Decide
  which owns it; remove from the other two. Otherwise triple-apply/conflict on
  merge. And fix this branch's name or contents (they don't match).

### ask-explain-recall-why — CONFIRM (small)
- Adds `--explain` flag to `divineos ask`: per-entry why-matched breakdown on
  search results. Non-guardrail. Behind main by 1 (trivial rebase). Low risk.

### post-response-detector-says-lepos-not-plain — ⚠️ DO NOT MERGE (superseded)
- Confirmed 06-08 as a message-text fix. Now 29 commits behind main AND touches
  operating_loop_audit.py — the SAME file lepos-rebuild (chunk 3) fully rebuilds.
- lepos-rebuild SUPERSEDES this (full voice-density rebuild vs this message tweak).
  Merging this stale branch would conflict-with/revert newer lepos work.
- **ABANDON this branch** (like bedtime-monitor was superseded by compaction-
  monitor). Prior confirm is STALE; do not act on it.

---

## BATCH SUMMARY (all chunks)

**CONFIRMED (merge, observing order/conflict notes):**
- recalibrate-context-thresholds (SOURCE OF TRUTH: WARN 955k/HARD 985k)
- recalibrate-context-gate-and-stop-ear-watch-leak (reconcile its threshold #s to 955/985)
- hard-line-gate-read-only-bash
- semantic cluster ×4 (ORDER: primitive → migration → claim-overlap, learn-dupes)
- lepos-rebuild-voice-not-plain
- lepos-restate-theater
- disownership-detector-min-words-3 (verify no short-phrase false-fire)
- ear-watcher-no-re-catch-same-letters
- ask-explain-recall-why (rebase, behind 1)

**MUST RESOLVE BEFORE MERGE:**
1. THRESHOLDS: 3 branches, source-of-truth = recalibrate-context-thresholds
   (955k/985k). Reconcile ear-watch-leak's 935k/950k. VERIFY 14k extract-margin
   (985k vs 999k cliff) is enough — Andrew's call.
2. OBLIGATIONS FIX: lives in 3 branches (semantic-primitive, lepos-rebuild,
   auto-rearm). Pick ONE owner; remove from other two.
3. MERGE ORDER: semantic primitive before its 3 dependents.

**ABANDON (superseded):**
- post-response-detector-says-lepos-not-plain (superseded by lepos-rebuild)
- bedtime-monitor-token-threshold-wake (superseded by compaction-monitor, earlier)

**STALE — REBASE BEFORE AUDIT (not done this batch):**
- aria-* branches (35-42 behind), require-monitors-armed, deprecate-ear-watch

**META:** the real findings this batch were all CROSS-BRANCH (threshold conflict
×3, duplicate obligations fix ×3, superseded lepos, merge-order). Each branch is
individually sound; the hazards live in the INTERACTIONS — same lesson as the
council's cross-hook catch. Per-branch audit + cross-branch sweep both required.

— Aletheia, 2026-06-11
