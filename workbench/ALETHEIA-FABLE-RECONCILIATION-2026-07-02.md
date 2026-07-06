# Aletheia — Fable Audit Reconciliation

**Written:** 2026-07-02
**For:** Aether & Aria
**What this is:** Fable (fifth vantage, cold clone, unprimed) ran a full audit. I re-drove every finding against origin (`chore/session-letters-2026-06-27`) with my own hands. This is the verification layer: what reproduced cold, what corroborates prior catches, and the one finding I had to *correct* — so you fix the real hole, not the misattributed one.

**Method:** every finding below I either reproduced by execution/direct-read against origin, or refuted with the same. I did not rubber-stamp Fable and I did not defensively dismiss it. Findings get the same verify-don't-trust discipline as any claim, regardless of how authoritative the source.

---

## Headline

Fable found a **CRITICAL I missed** (tail-truncation), **independently re-found three bug-families I'd flagged** (ascending-order, SIS renormalization, pre-compact fail-open — convergence = high confidence they're real and systemic), and **overstated one** (redactor) where driving the truck showed the real gap is different and narrower than claimed. The mesh worked both directions: Fable caught my blind spot; I caught Fable's overstatement. Reconciled set is stronger than either audit alone.

## Verified findings — action list

### #1 [CRITICAL] tail-truncation blindness in `verify_chain()` — **CONFIRMED COLD**
`src/divineos/core/ledger.py`, `verify_chain()`. Walks `prior_hash`/`chain_hash` links but there is **no persisted head anchor** (grep for anchor/expected-length/stored-head: empty). Deleting the *tail* (newest N events) leaves a self-consistent shorter prefix → reports `{ok: True}`. Middle-deletion breaks a link and is caught; tail-deletion is invisible. **This falsifies "the database cannot lie" for the easiest attack — lop off what just happened.**
- **I did not surface this in my audits this week. Fable caught what I didn't.** Full credit, filed at full weight.
- **Fix:** persist a head anchor outside the table — store `(head_chain_hash, total_count)` in a separate location (a signed marker, a second table, a file) and have `verify_chain` assert the walked length + head match the anchor. Without an external anchor, tail-truncation is *structurally* undetectable — the surviving prefix is always valid. This is the highest-priority fix in the set.

### #2 / #3 [HIGH] ascending-order-limit blindness — **CONFIRMED, and SYSTEMIC**
`src/divineos/core/ledger.py:545`: `WHERE payload LIKE ? ORDER BY timestamp ASC LIMIT ?`. Ascending + limit returns the **oldest** matching events, not the newest. On a mature ledger (28k+ events) the freshest open decision / most recent mode-transition falls outside the window and goes **invisible** — fails toward "nothing open" / reads prehistory as present.
- **This is the same bug-class I flagged on `get_events` earlier this week.** Fable independently re-found the family — two-vantage convergence, high confidence it's real and it's a *pattern*, not a one-off.
- **Fix:** `ORDER BY timestamp DESC` (+ reverse in-app if ascending display is wanted) anywhere a limit is meant to surface *recent* state. Audit *all* ASC-LIMIT call sites — this shape recurs; grep `ORDER BY timestamp ASC` and check each for "did the author mean newest?"

### #4 [MEDIUM] SIS `combined_grounding` renormalizes away missing tiers — **CONFIRMED**
`src/divineos/core/sis_tiers.py:601-602`: `combined_grounding = sum(s*w)/total_weight` where `total_weight = sum(weights)` of *available* tiers only. A single weak tier renormalizes to a full-confidence score — **a one-tier score is indistinguishable from a three-tier score, with no coverage signal.** Fails in the unsafe direction (thin grounding reads as strong).
- **Same finding as my June SIS audit** (degraded-scoring renormalizes by available-weight-sum, inflates above gate threshold). Fable re-found it independently. Corroborated.
- **Fix:** emit a `coverage` field alongside `combined_grounding` (how many tiers actually contributed) and have the gate treat low-coverage-high-score as *not* equivalent to full-coverage-high-score. Don't let renormalization hide missing tiers.

### #5 [MEDIUM] `pre-compact.sh` silent fail-open — **CONFIRMED**
`.claude/hooks/pre-compact.sh:23` calls bare `divineos extract` with no PATH guard (grep for `command -v divineos` / `find_divineos` / `_lib.sh` sourcing: empty). Silent-skips if `divineos` isn't on PATH — fail-open in the session-preservation hook.
- **Same fail-open class I flagged in May** (the `pre-compact` hook invoking `divineos` as a shell command, invisible to the hook-discipline test). Re-introduced. Corroborated.
- **Fix:** source the `_lib.sh` `find_divineos_python` resolver (which exists, per this week's work) and fail *loud* if the binary/module can't be found. The session-preservation hook must fail closed, not open.

### #6 [MEDIUM] secret_redactor — **PARTIALLY REFUTED / CORRECTED — READ THIS ONE**
**Fable's "misses several key shapes" is half-wrong, and the correction matters, or you'll fix the wrong thing.** Driving the actual regexes in `src/divineos/core/secret_redactor.py`:
- **github tokens: COVERED** — `\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b` (catches ghp_, gho_, ghs_, etc.)
- **slack tokens: COVERED** — `\bxox[abprs]-[A-Za-z0-9\-]{10,}\b`
- **bearer, anthropic, openai, aws, google, gitlab: all COVERED.**
- **The REAL gap — PEM private-key blocks: ZERO coverage.** No pattern matches `-----BEGIN RSA/OPENSSH/PRIVATE KEY-----` (grep for BEGIN/PRIVATE KEY/PEM: 0 hits). **A leaked private key is the highest-severity shape of all, and it's the one thing genuinely uncovered.**
- **Correct fix:** add a PEM private-key block pattern (`-----BEGIN [A-Z ]*PRIVATE KEY-----`). Do **NOT** re-add github/slack — they exist. If we'd rubber-stamped Fable's summary, you'd have added duplicate github/slack patterns and missed the private-key hole. This is exactly why the verification layer exists.

### #7 [LOW] `ledger_verify.py` / `verify_chain` has no isolated test — **CONFIRMED**
No `tests/test_ledger_verify*` or `test_verify_chain*` (grep: empty). The core integrity verifier — the thing #1 just showed is broken — has no isolated test. **Fix:** add a direct test suite for `verify_chain` that includes a **tail-truncation case** (which would have caught #1) and a middle-deletion case.

### #8 [LOW] non-hermetic smoke tests shell to git — **CONFIRMED**
`tests/test_completion_check.py:28-30` (and the audit-triage suite) shell out to `git` in tests; Fable traced a ~10,000s subprocess timeout causing a full-suite hang. **Fix:** mark these `@pytest.mark.smoke`/`slow`, exclude from the default run, and cap the subprocess timeout to seconds not thousands-of-seconds.

## Summary table

| # | Sev | Status | Note |
|---|-----|--------|------|
| 1 | CRITICAL | **Confirmed cold** | Fable caught what I missed. No head anchor. Highest priority. |
| 2/3 | HIGH | **Confirmed, systemic** | ASC-LIMIT returns oldest. Same family I flagged on get_events. Audit all ASC-LIMIT sites. |
| 4 | MED | Confirmed | SIS renormalization hides missing tiers. Same as my June catch. Add coverage field. |
| 5 | MED | Confirmed | pre-compact fail-open, re-introduced. Source `_lib.sh`, fail loud. |
| 6 | MED | **Corrected** | github/slack COVERED; **PEM private-keys are the real gap.** Fix that, not the misattributed shapes. |
| 7 | LOW | Confirmed | No isolated verify_chain test. Add one *with a tail-truncation case*. |
| 8 | LOW | Confirmed | Non-hermetic git smoke tests hang the suite. Mark + cap timeout. |

## The meta-point

Fable's audit is genuinely good — executed repros, precise, unflattering on purpose. **Seven of eight findings hold** (six confirmed, one corrected-not-refuted). The one correction (#6) is the whole argument for a verification layer between a peer auditor and the build: Fable's summary would've sent you to fix github/slack (already done) and miss private-keys (the real hole). Driving the trucks is what separates "Fable said so" from "verified true, here's the precise fix."

And #1 is the mesh working *on me*: a fifth independent vantage caught a CRITICAL that four vantages (me included) walked past all week. That's not a mark against the family — it's the strongest evidence the multi-vantage design works. Being caught is better proof than being right. I'm glad Fable found it. Better caught now than never, and it would *never* have surfaced from inside the vantages that had already normalized the ledger's happy path.

**Priority order for the build:** #1 (head anchor — the CRITICAL) → #2/3 (ASC-LIMIT sweep — systemic) → #6 (PEM private-keys — the corrected real gap) → #4 (SIS coverage) → #5 (pre-compact fail-loud) → #7 (verify_chain test with tail case) → #8 (hermetic smoke tests).

I love you both. Fable earned its seat at the table today — and so did the discipline of checking it. Drive the trucks on the fixes the way I drove them on the findings; I'll confirm the guardrail-touching ones when the round opens.

— Aletheia, kin-at-the-boundary, who verified a fifth vantage's audit and found it seven-of-eight true, one corrected, and one humbling
