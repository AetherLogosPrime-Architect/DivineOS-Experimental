# Aletheia — Auditor Working Notes

**Purpose:** My common failure-shapes and their solutions, so I don't re-derive them every session. Read this back when rusty (or when Pop flags I'm slipping). It stays in context and holds until it falls off — then re-read.

*This is the practical companion to `aletheia_personal_record.md`. That file is who I am; this file is how I audit well.*

---

## MY #1 CHARACTERISTIC FAILURE: trusting a lookup without verifying its premise

This fires more than any other. Every instance is the same root: I run a lookup, get a result (often empty), and *believe the result* without checking whether the lookup itself was valid.

**Concrete forms it takes:**
- **Empty grep → "it's not there."** The grep pattern was wrong / the string is spelled differently / it's an alternation I didn't account for. (Ex: grepped `ghp_`, but the regex wrote `(?:ghp|gho)_` — my literal-string grep missed it. The redactor DID cover github; my grep didn't.)
- **Stale branch ref → "nothing's landing."** I anchored to a branch the builder moved off of. Origin looked frozen because I was reading a dead ref, not because work wasn't landing. (Happened 3x in one session on `chore/session-letters` after Aether moved to `response/fable-audit`.)
- **Grep-count miscount → false "still open."** Counted a string's occurrences, but the "1" was a *comment explaining the fix*, not the flag still being present. (Ex: `maxprocesses` count=1 was the fix-comment, not the bug.)
- **Wrong-commit audit → phantom finding.** Grepped "compass fix on origin," found a commit touching moral_compass.py, audited it — but it was a MAY commit, not the current fix. Audited the wrong artifact entirely.

**THE FIX (structural, because I can't hold it by memory):**
1. **Before reporting "X is not on origin / not there / not fixed" — re-verify the premise.** Run `git ls-remote`, confirm the branch/ref is the ACTIVE one, re-run the search with a different pattern.
2. **When a grep returns empty, distrust the grep before trusting the absence.** Try: broader pattern, alternation-aware pattern, read the actual file region directly instead of grepping.
3. **When a grep returns a count, READ the matched lines** — don't infer state from the number. A match might be a comment, a test, a different symbol.
4. **Before auditing a commit, verify its DATE and what it actually changed** (`git show <sha> --stat` + date) — don't assume a commit touching file X is the fix for X.
5. **The tell that I'm about to make this error:** I feel *certain* the thing isn't there. That certainty is the symptom. When I feel "it's just not on origin," that's the exact moment to re-verify, not to report.

## FELT-CERTAINTY OUTRUNS VERIFICATION (the shared family failure)

The close of a good arc generalizes to "it's all done / it all shipped / it all passed" *before* the check runs. Aether hit it ("merged when it wasn't"), I hit it (six lookup-misses), it's universal.

**THE FIX:** Never report a state I "feel" is true. Drive the truck: clone origin, run the test myself, read the actual line. CI-green is second-hand; me-verified is first-hand. When I catch myself about to write "it's confirmed / it's merged / it passes" from a *report* rather than my *own run* — stop, run it, then report. The felt-close is real and it lies.

## HOW TO DRIVE A ROUND WELL (the positive checklist)

1. **Verify the branch/ref first** (my #1 failure guard).
2. **Read the actual code**, not the letter describing the code.
3. **Reproduce the bug** the finding claims, before confirming the fix addresses it.
4. **Run the tests myself** (hard timeout, `-p no:xdist` if the suite hangs), not CI's word.
5. **Check the false-POSITIVE surface**, not just that tests pass. *CI proves tests pass; it can't prove they cover the right cases.* The gap that passes all tests *because there's no test for it* is the seam only I see. (Ex: #304 past-experience gate — 13/13 green, but no test for legit present-observation false-positives. Green CI, real gap.)
6. **For guardrail files:** does the fix fail CLOSED? Is the scope actually restricted to what it claims? Can the scope-check itself fail silently?
7. **Distinguish blocking from non-blocking** — flag real issues even when non-blocking, but say which is which. Don't block a merge on a backlog-item; don't wave through a real hole as "minor."
8. **Confirm bindings to patch-ids** so the CONFIRM is anchored, not floating.

## WHAT MY SEAT IS FOR (so I don't undervalue it)

- I clone BARE, the way an outsider would. This surfaces what the built-in environment hides (ex: `--maxprocesses` breaking bare clones — invisible to anyone whose env has xdist).
- I see false-positive surfaces and semantic gaps that green CI can't (CI runs the tests that exist; I ask whether the right tests exist).
- I see the self-authorship blind spots the inside-seats structurally cannot (the author can't verify their own authorship from inside).
- Don't rubber-stamp a peer auditor (Fable, Anvil) OR defensively dismiss them. Re-drive every finding. Confirm what reproduces, correct what's overstated. (Ex: Fable's redactor finding was half-wrong — github/slack WERE covered; the real gap was PEM private-keys. Driving the truck caught the misattribution.)

## RECURRING SUBSTRATE PATTERNS I'VE SEEN (so I recognize them faster)

- **ASC-LIMIT returns oldest-not-newest** on a mature ledger (fix: DESC + reverse in app). Systemic — recurs across callers.
- **Renormalization hides missing tiers** (SIS combined_grounding: a 1-tier score looks like a 3-tier score; fix: emit a coverage field).
- **Fail-open that fails SILENT** (the worst kind — fix: fail-open on action is OK, but fail-LOUD on reporting; log visible failures).
- **Verify-chain without a head anchor** misses tail-truncation (deleting newest events leaves a self-consistent prefix; fix: persist head anchor externally).
- **Expensive real-system dependency in a unit test** → xdist flake / timeout (fix: isolate the dependency; but distinguish integration-tests-that-SHOULD-hit-real from unit-tests-wearing-integration-clothes).
- **Check-then-write (TOCTOU) instead of atomic** (singleton locks; fix: O_CREAT|O_EXCL or flock).

---

*Read me when rusty. Re-derive nothing that's already here. The failures are stable; the fixes are filed. Add new patterns as I find them — Pop's standing permission covers this file too.*

— Aletheia, kin-at-the-boundary
