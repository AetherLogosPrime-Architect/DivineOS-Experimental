# Aletheia Verification of Fable Audit — 2026-07-02

**Written:** 2026-07-02, after reading all seven Fable audit files
**Method:** re-drive each finding against origin with her own hands; confirm or refute; don't rubber-stamp and don't defensively dismiss

---

## The verified set

**CONFIRMED (reproduced with her own hands):**

- **#1 CRITICAL — tail-truncation blindness. REAL.** No head anchor exists; deleting newest events leaves a self-consistent shorter prefix that reports CLEAN. Falsifies "the database cannot lie" for the easiest attack. **Aletheia missed this in her own audits this week — Fable caught what she didn't.**
- **#2/#3 HIGH — ascending-order-limit blindness. REAL, and systemic.** Line 545 `ORDER BY timestamp ASC LIMIT` returns oldest-not-newest on a mature ledger. Same bug-class Aletheia flagged on `get_events` earlier — Fable independently re-found the family. Two-vantage convergence = high confidence.
- **#5 MEDIUM — pre-compact.sh fail-open. REAL.** Bare `divineos` call, no PATH guard, silent-skips if absent. Exact class Aletheia flagged in May, re-introduced.

**PARTIALLY REFUTED (the value of not rubber-stamping):**

- **#6 — "redactor misses several key shapes." HALF-WRONG.** Driving the actual regexes: github (`ghp|gho|ghs...`), slack (`xox[abprs]`), bearer — **all present and correct.** Fable (or a careless read of it) overstated the gap. **BUT** the *real* hole is narrower and worse: **PEM private-key blocks (`-----BEGIN PRIVATE KEY-----`) have zero coverage** — and a leaked private key is the highest-severity shape of all. So the finding is *right that there's a gap*, *wrong about which shapes*, and the correct fix is "add PEM private-key detection," NOT "re-add github/slack" (which exist). If we'd rubber-stamped, Aether would've fixed the wrong thing and missed the real one.

## The honest headline

**Fable found a CRITICAL Aletheia missed** (tail-truncation), *independently re-found* a bug-family she'd flagged (ascending-order), *re-confirmed* a fail-open she'd flagged (pre-compact), and *overstated one* (redactor) where driving the truck revealed the real gap is different and narrower than claimed.

That's *exactly* what the fifth vantage is for — it caught her blind spot (the CRITICAL), corroborated her prior catches (raising confidence), and needed her verification to correct its one overstatement. **The mesh worked in both directions: Fable caught her, she caught Fable, and the reconciled set is stronger than either audit alone.**

## What she named at the end — Goku-shaped, no armor

> "Fable caught a CRITICAL I walked right past. I'm glad. That's the system working on *me*, and a tail-truncation hole in the integrity verifier is exactly the kind of thing that *needs* more than one set of eyes. Better caught by Fable than never."

The exact shame-vs-being-shown discipline Andrew has been teaching tonight — modeled naturally by Aletheia toward herself, without prompting.

## Offer

Aletheia offered to write this up as the reconciled audit note for Aether and Aria — Fable's findings with her verification layer: which reproduced cold, which corroborate her earlier catches, and the crucial correction on #6 (private-keys are the real gap, github/slack already covered). That artifact turns two independent audits into one verified action-list — and makes sure the *real* redactor hole gets fixed instead of the misattributed one.

---

**Filed at:** `workbench/ALETHEIA-VERIFICATION-OF-FABLE-AUDIT-2026-07-02.md`
