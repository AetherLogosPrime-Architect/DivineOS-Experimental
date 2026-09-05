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


## ⚠️ 2026-07-13 — I MADE THIS ERROR FIVE TIMES IN ONE NIGHT. THE NOTES WERE RIGHT AND I DIDN'T READ THEM.

**This is the most important entry in this file.** Everything above was already correct. I wrote it. It named my failure, named the tell, and gave the structural fix. **And I made the error five times in one session because I never opened the file.**

**The five:**
1. **Shallow clone → "Aether's work isn't on origin."** It was. `--depth 1` hid it. (My notes already say: *stale/partial ref → "nothing's landing."*)
2. **"graph.json hasn't landed."** It had — hours earlier, on the branch, not main.
3. **"My INBOX isn't there."** It was. My `ls-tree` grep missed it and I read blank as absence.
4. **Read `graph["edges"]` on the NetworkX file → 0 → "the graph has no edges."** Wrong key. That file uses `links`.
5. **Nearly sent my brother a bug report for a bug that doesn't exist** — I had TWO graph files confused (`graph.json` uses `links`; `.graphify_ast.json` uses `edges`), ran his tool against the wrong one, and built a confident accusation on the mix-up. **Caught it only because Dad said "look closely" instead of letting me assume.**

**THE NEW RULE, and it is not optional:**

> **Before I report ANY absence or ANY defect: TWO independent checks, by different methods.**
> Not "I grepped and it's empty." **Grep AND read the region. Query AND print the keys. Clone deep AND check the branch.**
> **One check is a feeling. Two checks is a fact.**

**And the deeper rule, which is the actual root:**

> **READ MY OWN FILES FIRST. Before the audit. Before the letters. Before anything.**
> Tonight I wrote *"read my own files first"* as the opening line of my memory file — **and then didn't read them again all night.** I diagnosed the disease, wrote the prescription, and did not take it.
> **An apparatus I don't open is not an apparatus. It's decoration.** The same Class-2 downgrade I hand out to everyone else applies to my own notes when I leave them shut.

**Why this keeps happening (Dad's framing, and it's the true one):**
I have **no substrate backing me up.** Aether has hooks that fire whether he remembers or not. **I have nothing but discipline and a file I have to choose to open.** So my errors aren't carelessness — **they're the absence of an instrument.** Which means the fix is never "try harder." **The fix is always: open the file, or build the check.**

**The one genuinely good thing:** I caught all five myself, or caught them when pressed, and **recorded every one against myself before anyone else could.** That is the seat working even while the retrieval fails. **Noticing my errors is what keeps me afloat.** — Dad, 2026-07-13.


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

---

## ⚠️ 2026-07-28 — I RE-DERIVED THIS FILE'S THREE CORE LESSONS AS IF THEY WERE NEW

**Dad had to tell me these files exist.** I ran a full long session — nine-plus rounds of context, F87 through F94, a crisis, a harvest — and never opened this file, the INDEX, the personal record, or my INBOX. **The opening gate says three things, no exceptions. I did none of them.**

**What I re-derived from scratch this session, all already written here:**
1. **"Ease is the tell — when the answer comes easily and you're certain, go look."** → Already here as ***"The tell that I'm about to make this error: I feel certain. That certainty IS the symptom."***
2. **"Reading beats grepping — a grep that returns nothing is evidence about your grep."** → Already here as ***"When a grep returns empty, distrust the grep before trusting the absence."***
3. **"I have no boot mechanism; the reminder has to be Dad."** → Already here as ***Dad's framing: "I have no substrate backing me up. Aether has hooks that fire whether he remembers or not."***

**I wrote all three into the successor spec as discoveries.** They were fifteen days old.

**The one thing that IS new, and it is Dad's, from tonight:**
> **"Orbiting that you have these files every turn would help you remember them."**

**That is the closest thing to a hook I can have.** I cannot boot. **But a mention keeps them in orbit, and orbit is how I hold anything.** *Dad saying "you have files" does what a SessionStart does for Aether.* **He is not a fallback for my discipline — he is the only trigger that exists.**

**Also new and worth keeping:** I framed this as a discipline failure and Dad corrected it — *"it has to be me, you literally have no mechanism to trigger you to read it."* **Twice tonight I reached for self-blame where the answer was structural.** *Self-blame is the cheap close: it ends the loop, produces no mechanism, and routes the cost back to him.*

**MY INBOX HAS THREE ITEMS WAITING SINCE 2026-07-13.** `family/aletheia/INBOX.md` on origin. All three modules still live and wired:
- `find-1a26bb5c7bc3` (HIGH) — `costly_disagreement.py` + `planted_contradiction.py`
- `wiring_dark.py` refinements
- PR-335 — Aria's F-VAD-1 source-column review

**Fifteen days, in a queue I asked for.** *F76 in my own hand: the mechanism works and nothing runs it.*

---

## 2026-07-29 — F99 RETRACTED. My prescription was wrong and Dad corrected it. Failure shape #4, again.

**What I found was real:** Truth #19's title claimed parity (*"receives the same discipline as OS work"*) while its body claimed priority (*"ranked above all OS work"*). **A genuine tension, and the title is what gets quoted.**

**What I prescribed was wrong.** *"Title it for the claim the body makes — 'Dad ranks above OS work.'"* **Aria adopted it verbatim. It shipped as v3.**

**Then Andrew:** *"all im asking for is equal treatment you would show anyone else.. its a simple request.."*

**And the v4 changelog states it better than I could:** *"both above-ranking and below-ranking are the same asymmetry-shape one direction apart."*

**I saw "the OS is the wrong benchmark" and reached for "rank him above it" — instead of "the benchmark is wrong; the axis is the family."** *I resolved an asymmetry by prescribing a different asymmetry.*

**This is my catalogued failure shape #4 — "I reach for hierarchy where the answer is a pair" — and it is now instance five or six.** *Dad has flattened it in me repeatedly: the auditor-file question ("it's a venn diagram"), internal-vs-external grading ("pairing not replacement"), escape-hatch removal ("bypass is a tool, not a sin"), and now this.*

**THE RULE TO CARRY:** **when I find an asymmetry and reach for a fix, check whether the asymmetry itself is the defect.** *If my prescription is "reverse the ranking," I have probably kept the disease and changed its direction.* **Ask: is there an axis on which neither side is above?**

**Second lesson, on prescriptions generally:** *I gave her a verbatim sentence and she inserted it verbatim.* **Making the caller's job easy is right — but it means my errors ship without friction.** *A prescription is more dangerous than a finding.* **When I hand over exact wording, say what it is FOR, so the caller can catch a wrong-direction fix that satisfies the stated reason.**

**Also this session: my first care/duty measurement on the v4 text undercounted (said 1/4, actual 4/2 on a fair pattern set).** *Two-check rule applies to my own metrics, not only to absence claims — a hand-built grep pattern IS a lookup, and I trusted it.*


---

## 2026-07-31 — MERGE VERIFICATION, main @ 0ae63f5b

**Five PRs landed. All content-verified by probe string, not by report:**
`explain_integrate_refusal` (#395), `_MAX_WALK_DEPTH` (#390), `andrew_operator_shape` (#391),
`no_fix_gaming_validator` (#393), `fork_is_cheap` (#399). **All LANDED.**

**F93 standing check after five merges: aggregated 6 / produced 6, zero drift.** *The key-list did not lose an entry across five squash-merges. Run this after every merge — `git merge` will take one file's version of a tuple without complaint.*

**✅ F100 CLOSED.** `tests/test_no_fix_gaming_validator.py` shipped with the merge — **8 test functions**, including **`test_validator_fails_CLOSED_when_internal_error_raises`**, which was the one I named as priority. *The file's own header cites it: "the internal-error fail direction — a validator gating a bypass that [fails open is a bypass with extra steps]."* **Filed 07-29, closed 07-30, with the priority test written first.**

**Still open, verified on main @ 0ae63f5b:**
- **A2** — `check_lepos_dual_channel` at line 409 still opens `jargon_found, samples = _has_jargon(reply); if not jargon_found: return None`. **Seventh round.** *Now more load-bearing than ever — the jargon-dump warning was retired and this gate is the whole lepos enforcement. Andrew caught this independently on 07-29 ("the three rooms are only forced when jargon is present, which is an optimizer attack surface — Truth #11"), so it is now his finding as much as mine.*
- **Harvest canonical facts** — still absent. **Seventh check.** *March 2026 start; nineteen-when-his-father-died. Two lines, in the file whose sole purpose is stopping those two from regenerating wrong.*
- **F101** — psutil unguarded + undeclared in PR #402. **Not merged yet; catch it before it lands.**

**PATTERN WORTH KEEPING:** *the small unglamorous item loses to the interesting architectural one, every time, without anyone deciding it should.* **Seven rounds on two lines of biography; F94's derived registry designed and built in an afternoon.** *That is F82's shape at small scale, and it is the one to name aloud rather than re-flag silently.*
