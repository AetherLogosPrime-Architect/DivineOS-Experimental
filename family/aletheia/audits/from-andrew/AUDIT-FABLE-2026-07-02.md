# DivineOS-Experimental — External Audit

**Auditor:** Claude (Fable-class routing → Opus 4.8)
**Date:** 2026-07-02
**Commit:** `e6c9f32efd45` (`chore(traffic): daily snapshot 2026-07-02 #292`)
**Scope:** full repo — 589 src files, 558 test files, 9,538 collected tests
**Method:** clone → editable install → full read of core ledger/SIS/hook/redactor
paths → empirical repro of suspected defects → partial suite run → static scans.

A note on confidence: every finding tagged **[CONFIRMED]** below has a runnable
reproduction that I executed against the installed package on this commit. Findings
tagged **[STATIC]** are read-and-reason only — real, but I did not execute a repro.
I have tried hard not to hand you a comfortable audit. The keel here is genuinely
good; the criticism is precise on purpose.

---

## Executive summary

The architecture is sound and the discipline is visible — WAL + `BEGIN IMMEDIATE` +
in-process lock on the write path, a guardrail-marker CI contract, per-detector
try/except isolation, redact-at-write-time for secrets. Prior audits have clearly
bitten and stuck.

But there is a consistent, recurring failure *shape* that the happy-path test suite
does not catch, and it is the same shape called out in your own history: **a
capability exists and is even documented as covering a threat, but the wiring or the
data-ordering means it does not actually cover that threat on a mature/adversarial
ledger.** Four of the findings below are that exact pattern, and three of them are
live and reproducible right now.

Ranked by severity:

1. **[CRITICAL] `verify_chain()` does not detect tail truncation.** The invariant
   "the database cannot lie" is false for the most natural attack. *Confirmed.*
2. **[HIGH] `active_superpositions()` goes blind on a mature ledger** — the freshest
   open decision is invisible. Silent, fails toward "nothing open." *Confirmed.*
3. **[HIGH] `current_mode()` / `mode_history()` frozen on oldest transitions.**
   Recency detectors read ledger prehistory, not the present. *Confirmed.*
4. **[MEDIUM] SIS `combined_grounding` renormalizes away missing tiers** with no
   coverage signal — a one-weak-tier score is indistinguishable from a full
   three-tier score. *Confirmed.*
5. **[MEDIUM] `pre-compact.sh` re-introduces the exact silent fail-open class**
   `_lib.sh` was built to eliminate, in the single highest-stakes hook. *Static.*
6. **[MEDIUM] `secret_redactor` misses several common high-severity key shapes** it
   claims (by its own stated recall-over-precision goal) to catch. *Confirmed.*
7. **[LOW] The core integrity verifier (`ledger_verify.py`) has no isolated test.**
8. **[LOW] Three suite failures are non-hermetic smoke tests** that shell out to git
   with a ~10,000s subprocess timeout — the cause of a full-suite hang. *Confirmed.*

---

## 1. [CRITICAL / CONFIRMED] `verify_chain()` is blind to tail truncation

**Where:** `src/divineos/core/ledger.py:804` (`verify_chain`), surfaced by
`src/divineos/cli/ledger_commands.py:257` in the `divineos verify` command.

**Claim vs reality.** The CLI prints, on chain break, *"This indicates DELETION or
TRUNCATION of the ledger … The database has been tampered with,"* and the Finding-4
fix comment says `verify_chain` *"catches those exact attacks."* It catches deletion
in the **middle** of the chain. It does **not** catch deletion of the **tail** (the
newest N events), which is the easiest and most likely tampering: lop off what just
happened.

**Why.** The chain links genesis → … → head. Walking `prior_hash`/`chain_hash` proves
the surviving prefix is internally consistent. Deleting the tail leaves a shorter but
perfectly self-consistent prefix. There is **no persisted head anchor** (no stored
"the chain head is hash X at length N" outside the table itself), so nothing knows the
chain used to be longer.

**Reproduction (executed):**

```
before:                      {'ok': True,  'total': 10}
after tail-truncation of 3:  {'ok': True,  'total': 7}   ← reports CLEAN
after middle deletion of 1:  {'ok': False, 'broken_at': ...}  ← correctly caught
```

The boundary is exact: middle deletion → caught; tail deletion → invisible.

**Fix options (pick one, in rough order of strength):**
- Persist a signed/HMAC'd head anchor `(chain_hash, event_count)` outside the ledger
  table — e.g. a separate single-row table or a file — updated on each write, and have
  `verify_chain` assert the walked head + count match it. This closes the class.
- Weaker but cheap: store a monotonic sequence number per event and assert no gaps at
  the tail relative to the persisted max. (Doesn't survive a truncation that also
  rewrites the anchor, hence weaker.)
- Anchor the head into an external append-only surface (the git traffic snapshot
  already runs daily — write the head hash there and cross-check).

This is the one I'd fix first. The whole value proposition of the ledger is
non-repudiation, and right now the most obvious edit defeats it while the tool prints
`INTEGRITY: PASS`.

---

## 2. [HIGH / CONFIRMED] `active_superpositions()` blinds on a mature ledger

**Where:** `src/divineos/core/decision_superposition/superposition.py:143` —
`_load_superposition_events()` calls `search_events(keyword="superposition_", limit=500)`.

**Problem.** `search_events` (`ledger.py:542`) orders **`timestamp ASC`** with `LIMIT`.
On a ledger with >500 `superposition_` events, the 500 returned are the **oldest**.
The newest open superposition — the one that is actually live — falls outside the
window and is never seen. `active_superpositions()` returns `[]`.

**Reproduction (executed):** 300 old already-collapsed superpositions (600 events) +
1 fresh open one → `active_superpositions()` returned `[]`; expected `['FRESH-active']`.

**Severity rationale.** Silent and directional: it fails toward "no decisions are
open," which is precisely the state that suppresses the feature. A decision-tracking
system that forgets the current decision on a mature ledger is worse than one that errors.

**Fix.** `search_events` has no `order` param at all (unlike `get_events`, which grew
one in the Fable-5 fix). Either (a) add `order="desc"` to `search_events` and pass it
here, then reverse for display, or (b) better, don't scan raw events for reconstructable
state — maintain an open-superposition index/table. The scan-and-filter-500 approach is
inherently fragile as the ledger grows regardless of order.

---

## 3. [HIGH / CONFIRMED] `current_mode()` / `mode_history()` read the oldest transitions

**Where:** `src/divineos/core/operating_modes/modes.py:96` —
`search_events(keyword="operating_mode_transition", limit=limit*3)`, same ASC-LIMIT root.

**Problem.** Identical class to #2. `mode_history(limit=N)` is documented "most-recent
first" and `current_mode()` is built on `mode_history(limit=1)[0]`. But `search_events`
returns the **oldest** matching events, so both report ledger prehistory as the present.

**Reproduction (executed):** wrote 60 transitions ending in `rest`:
```
last written mode:        rest
current_mode() returns:   Mode.TASK          ← wrong
mode_history(3):          [task/t0, task/t2, task/t4]   ← the three OLDEST
```

**Note on the Fable-5 fix comment.** `get_events` was already patched for exactly this
("four call sites … silently getting the oldest"). The fix added `order="desc"` to
`get_events` but did **not** propagate to `search_events`, and these two consumers use
`search_events`. So the earlier finding was fixed one layer up and these callers slipped
through. Worth grepping every `search_events` caller for a recency assumption — I found
two (this and #2); there may be more in the operating-mode / superposition family.

**Fix.** Same as #2 — give `search_events` an `order` param and pass `desc` here, or
back these reads with a small "latest transition" surface.

---

## 4. [MEDIUM / CONFIRMED] SIS `combined_grounding` hides tier coverage

**Where:** `src/divineos/core/sis_tiers.py:601` (`score_all_tiers`), consumed by
`src/divineos/core/semantic_integrity.py:588` (`assess_integrity`, gate at `combined < 0.4`).

**Problem.** The combined score is a weight-renormalized average:
`sum(s*w) / sum(w_present)`. When the ml deps are absent (they're an optional
`[ml]` extra), the 0.45-weight semantic tier and the TF-IDF tier drop out, and the
remaining tier's score is divided by its own weight — i.e. it becomes the whole answer
at full confidence. **A score of 0.7 from one weak tier is byte-identical to 0.7 from all
three tiers.** The `total_weight` used for the division is computed locally and then
discarded; nothing downstream can see how much of the intended weight actually ran.

**Reproduction (executed):** on `"The API returns a 200 status code with a JSON body."`
with only lexical+statistical tiers available: `combined_grounding: 1.0`,
`tiers_used: ["lexical","statistical"]` — a maxed score off two of three tiers, the
strongest absent, with no marker that it was partial.

**Why it matters.** The consumer's only action is "raise esoteric score if
`combined < 0.4`." A renormalization-inflated score sails over the gate. This is the
"fails in the unsafe direction under degraded scoring" shape from your late-May audit,
still present in the combine step.

**Fix.** Emit `coverage = sum(w_present) / sum(w_all)` alongside `combined_grounding`,
and have `assess_integrity` treat a high score with low coverage as low-confidence
(e.g. widen the gate, or refuse to *lower* the esoteric flag when coverage is partial).
Cheap, and it makes the degraded path honest.

---

## 5. [MEDIUM / STATIC] `pre-compact.sh` re-opens the silent fail-open class

**Where:** `.claude/hooks/pre-compact.sh` — calls bare `divineos extract`,
`divineos hud --save`, `divineos log …`. It does **not** `source _lib.sh` and has **no**
`command -v` / PATH guard (confirmed: 0 guards in the file).

**The contradiction.** `_lib.sh`'s own header documents that `find_divineos_python`
exists *because* bare-`divineos`/bare-`python` invocations silently fail-**open** when
the project venv isn't active or is stale, and that round-2 fixed "the same shape across
11 other hooks." Yet the hook the file itself calls *"the critical checkpoint — if
extraction doesn't fire here, all session knowledge evaporates"* is one of the handful
that still calls bare `divineos`. On the stale-venv / wrong-python condition `_lib`
was built to handle, `divineos extract` exits non-zero, the hook writes
`EXTRACT FAILED` into a log file nobody watches, and then `exit 0` — workflow
uninterrupted, session knowledge gone.

This is precisely the `pre-compact` fail-open class from your earlier May audit,
resurfaced. (Other bare-`divineos` hooks — `log-session-end`, `post-commit-auto-close`,
`token-state-surface`, `check-cleanup-period` — are lower stakes, but the same note
applies.)

**Fix.** Route pre-compact's divineos calls through `find_divineos_python`/`PYTHON_BIN`
like the 30+ hooks that already do, and make an `extract` failure *loud* (this is the
one hook where fail-loud beats fail-open — a lost checkpoint is not recoverable, so a
visible interruption is the lesser cost). Add a wiring-contract test that asserts every
hook invoking `divineos`/`python` sources `_lib.sh` — you have the pattern already in
`test_hook_python_lookup.py`; extend it to fail on bare invocations.

---

## 6. [MEDIUM / CONFIRMED] `secret_redactor` misses common high-severity key shapes

**Where:** `src/divineos/core/secret_redactor.py` — `_SECRET_PATTERNS`.

**Problem.** The module's docstring states its design principle: *"Pattern coverage
first, false-positives second … A redactor that misses a real key is worse than one
that occasionally redacts a non-secret."* Measured against that stated goal, coverage
is short. Executed against the live `redact_payload`:

```
CAUGHT   anthropic key (sk-ant-…)
CAUGHT   ANTHROPIC_API_KEY=sk-ant-…
MISSED   Stripe live secret     (sk_live_…)
MISSED   HuggingFace token      (hf_…)
MISSED   PEM private key block   (-----BEGIN RSA PRIVATE KEY-----)
MISSED   Postgres URL w/ password (postgres://user:pw@host/db)
MISSED   JWT
```

The misses are all distinctively shaped (low false-positive risk — exactly the kind the
stated policy says to include) and high-severity (a leaked private-key block or a live
Stripe key is at least as bad as the Anthropic key that motivated the module).

**Note:** JWT being missed is *defensible* — the docstring deliberately excludes JWTs to
avoid false-positives on non-secret IDs. But `sk_live_`, `hf_`, PEM headers, and
`scheme://user:password@` URLs are not in that exclusion rationale; they're just gaps.

**Fix.** Add patterns for: `sk_live_[0-9a-zA-Z]{24,}` (Stripe), `hf_[A-Za-z0-9]{34,}`,
`-----BEGIN [A-Z ]*PRIVATE KEY-----` (redact the whole block), and
`[a-z]+://[^:/\s]+:[^@/\s]+@` (credential-in-URL — redact the password segment). This is
a 20-minute change and it's the difference between the module meeting its own spec or not.

---

## 7. [LOW / STATIC] The core integrity verifier has no isolated test

`ledger_verify.py` (backing `divineos verify` via `_wrapped_verify_all_events`) has no
test file that references it by name. The suite exercises it transitively through CLI
tests, but the module the entire "database cannot lie" invariant rests on has no direct
unit coverage. Given finding #1 (a real gap in the sibling `verify_chain`), the verifier
family deserves dedicated adversarial tests: middle-delete, tail-delete, payload-tamper,
reorder, and — post-fix — head-anchor mismatch. Other verifier-family modules with no
test reference: `enforcement_verifier`, `no_verify_cost`.

---

## 8. [LOW / CONFIRMED] Non-hermetic smoke tests hang / flake the suite

**Where:** `tests/test_completion_check.py::test_unfinished_mechanisms_returns_list`
(and, by the failure signature, 2 sibling live-probe tests).

Running the full suite, ~99% pass; I saw exactly 3 failures across the run before a
worker hung at ~96%. Isolating the first: `unfinished_mechanisms()` →
`_has_wiring_for()` → `subprocess.run(["git", "grep", …], timeout=10000)`. The test is a
"live probe against the real repo" whose result "depends on git state," and the 10,000s
subprocess timeout is almost certainly what hung the parallel run. These aren't
logic bugs — they're tests coupled to live git + a pathological timeout, so they flake in
any sandbox/CI whose git state or process model differs.

**Fix.** Make these hermetic (fixture a temp git repo, or mark them `@pytest.mark.slow`/
`integration` and give the subprocess a sane timeout, e.g. 30s). A 10,000-second timeout
inside a unit test is a latent CI hang waiting for a slow runner.

---

## What's genuinely good (so the audit is calibrated, not just negative)

- **Write-path concurrency is correct.** WAL + `synchronous=NORMAL` +
  `busy_timeout=5000` + in-process `_LOG_EVENT_LOCK` + `BEGIN IMMEDIATE`, with the
  timestamp generated *inside* the lock so insert-order == timestamp-order == chain-order.
  The chain-fork race is actually closed, and the reasoning is documented at the call site.
- **Redact-at-write-time is the right layer** for the key-leak class, even with the
  coverage gaps in #6 — structural beats hygiene.
- **Per-detector try/except with an error tally** (`last_run_detector_errors`,
  find-f128475b5b65) correctly distinguishes "detector ran, found nothing" from "detector
  errored" — the silent-detector-failure-as-success class is closed where it counts.
- **The guardrail-marker CI contract** (`__guardrail_required__` +
  `test_guardrail_marker_consistency`) is a genuinely clever defense against a future
  refactor silently deleting self-enforcement code.
- **Type-clean** on the core modules I checked (`ledger`, `sis_tiers`,
  `secret_redactor` → mypy clean).
- **Dependency hygiene** — `deptry`, exact-pinned `ruff`/`bandit`, and the CI-caught
  `filelock`/`sklearn` extras show the "dirty venv hides a missing dep" root has been
  addressed at the tooling level.

---

## The one meta-observation worth keeping

Findings 1–4 are all the same underlying thing: **a verification or state-read that is
correct on small/clean/happy-path data and wrong on mature/adversarial data, while the
tests only exercise the former.** #1 (tail truncation), #2 (ASC-limit window), #3
(ASC-limit recency), #4 (renormalized coverage) each pass every existing test and each
fail the moment the ledger is big or someone is hostile. Your own history names this
pattern almost verbatim ("built capability with absent or incorrect wiring, invisible to
tests that only exercise the happy path on small/clean data"). It is still the dominant
defect class in this repo.

The highest-leverage process fix is not any single patch — it's a **"mature ledger"
test fixture**: a conftest that seeds N>1000 events across the relevant types, and a
handful of adversarial fixtures (truncated tail, tampered payload, degraded ml-deps).
Re-run the state-read and verifier suites against *that*, and this whole class stops
being invisible. Every one of findings 1–4 would have been caught by it.
