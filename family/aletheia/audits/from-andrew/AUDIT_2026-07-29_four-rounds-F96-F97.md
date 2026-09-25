# Aletheia — four-round audit, 2026-07-29

**Against main @ `04117c7`.** *Hash-anchored per branch.*
**Method:** two independent checks per claim. **Two first-reads were overturned by the second check; both recorded.**

| round | PR | branch @ head | scope |
|---|---|---|---|
| `round-a3420297b1bb` | #395 | `aria/andrew-correction-integrate-error-message-fix` @ **`6ae07f8`** | 2c / 14f |
| `round-71ee26d6bfd9` | #391 | `aria/mirror-per-room-extend` @ **`5e9cea3`** | 1c / 3f |
| `round-434ff165ff6e` | #393 | `feat/gate-automation-sweep-2026-07-27` @ **`0fda0a7`** | 19c / 51f |
| `round-79757e7d6a02` | #399 | `feat/recurring-correction-structural-fixes-2026-07-28` @ **`d2992dc`** | 40c / 7f |

---

# ✅ THE TRAILER-DEBT QUESTION — the scope-split is honest. Here is the arithmetic.

**You asked me to read whether Aria's scope-split on the ~150 guardrail-touching commits is honest. It is, and the "~150" is a counting artifact rather than a debt.**

**Three checks:**

1. **The branch itself carries 2 commits ahead of main. One touches guardrail files, without a trailer.** *One, not 150.*
2. **Main is clean.** Every guardrail-touching merge commit on main since 07-25 — **3 of 3 — carries an `External-Review` trailer.** *Nothing landed unreviewed.*
3. **And the gate does not inspect individual commits.** `.github/workflows/audit-stamp-reminder.yml:71`:
   ```
   CHANGED_FILES=$(git diff --name-only "$BASE_SHA..$HEAD_SHA")
   ```
   with the workflow stating: *"This PR modifies guardrail files. **The squash-merge commit on `main` must carry** [the trailer]."*

**In a squash-merge repo, individual pre-squash commits never land as commits.** *Counting them as trailer-debt counts objects that will not exist after merge.* **The unit the gate cares about is the PR diff and the squash commit, and both are covered.**

**So: no debt, no dishonesty, and the split is clean.** **Aria was right to flag it and right not to block on it.** *Worth telling her the number dissolves — carrying a phantom 150-item debt is its own cost.*

---

# ✅ PR #395 — SOUND. One small structural note.

`explain_integrate_refusal` covers **four branches**, and I compared them against `integrate()`'s actual refusals:

| explainer says | `integrate()` does |
|---|---|
| evidence too short (< 20 chars) | `if not evidence or len(...) < 20: return False` ✓ |
| no structural artifact | `if not _has_structural_artifact(...): return False` ✓ |
| correction #N not found | *(implicit)* `rowcount == 0` |
| correction #N already {status} | *(implicit)* `rowcount == 0` |

**And this is better than parity, which I want to credit precisely.** `integrate()` collapses the last two into a single `WHERE id = ? AND status = 'OPEN'` with `rowcount > 0`. **The explainer decomposes them into distinct, actionable messages.** *It tells the operator more than the function knows about its own failure.* **Same evaluation order, so the reported reason is always the reason that actually fired.**

**Wired: `cli/andrew_correction_commands.py:79,82`** — imported and called. **Bool return preserved.**

**🟡 The one note — the refusal logic now lives in two places.** *The explainer re-queries and re-derives the conditions rather than `integrate()` returning its reason.* **Add a fifth refusal to `integrate()` and the explainer must be updated separately, by memory, or it will confidently report the wrong reason.**

**That is registration-coupling — F94's class.** *Not urgent at four branches.* **The derivable fix, if it ever grows: have `integrate()` return `(bool, reason)` internally and let the bool-only signature be a thin wrapper.** *One source, two shapes, no sync burden.*

---

# ✅ PR #391 — CLEAN. No smuggled scope.

**Three files, all in one concern:** `andrew_operator_shape_detector.py`, `operating_loop_audit.py`, `pre_response_context.py`. **155 insertions.**

**The reduction is honest** — the file set is exactly the mirror-per-room surface, with nothing riding along from the original PR-B cluster. *You asked for a smuggled-scope check; there is none.*

---

# ✅ PR #399 — the "prime" shape is CORRECT, and I nearly filed it as a violation

**My first read: all three hooks are surface-only.** `exit 2` count: **zero across all three.** *Against truth #8 — "enforcement gates block, not warn" — that reads as three warning-shaped mechanisms.*

**Second check overturned it.** All three are registered on **`UserPromptSubmit`** — they are **compose-start primes, not gates.** *A prime is supposed to supply before the act; blocking is not its shape.* **This is the doorman pattern Andrew named — supply what is needed, then validate elsewhere.** *Surface-only is right here, and I would have filed a false finding on the first read.*

---

# 🟡 F96 — TWO OF THE THREE PRIMES HAVE NO PAIRED ENFORCEMENT

**You asked me to check "telemetry not wallpaper." This is the answer, and it is the one finding in the four rounds.**

**A prime is only half a mechanism.** *It supplies context before composition; something must still check whether the thing was done.* **Verified:**

| prime | paired enforcement |
|---|---|
| `wallclock-source-prime` | ✅ **`check_wallclock_semantic_source`, 3 refs in `operating_loop_audit.py`, Stop-wired** |
| `fork-is-cheap-close-prime` | ❌ **none found in `src/`** |
| `closure-word-summary-prime` | ❌ **none found in `src/`** |

**The wallclock one is the complete pattern and shows what the others are missing:** *prime at compose-start, block at Stop.* **Supply, then validate.** **The other two supply and never validate.**

**Which lands them in F85's territory exactly: surfaced, and nothing acts on it.** *A compose-start prime that nothing checks is a message printed into a session — the being can read it, ignore it, and no signal exists either way.* **That is the definition of wallpaper Andrew gave you, and it is the specific thing this PR was meant to fix.**

**And note the recurrence risk:** *these primes exist because a correction recurred.* **A prime with no validator cannot tell you whether the recurrence stopped** — so the next time the pattern fires, the diagnosis will be "we need a stronger prime," and the loop repeats one layer up.

**Fix — smallest honest version, and it is not a blocking gate:** *pair each prime with a Stop-side consumption check.* **Not "did you comply" — "was the primed content used."** `record_consumption` already exists in `operating_loop/hook_telemetry.py`. **Then a prime that is never consumed becomes visible instead of theoretical.** *Per F85's own fix: attach a consequence to low consumption — self-observation before enforcement.*

---

# 🟡 F97 — TEST COVERAGE IS 1 OF 3, AND IT IS THE ONE WITH THE VALIDATOR

**PR #399 ships three hooks and one test file: `tests/test_fork_is_cheap_close_prime.py`.**

- `fork-is-cheap-close-prime` — **has tests** *(but no validator — F96)*
- `wallclock-source-prime` extension — **no new tests** *(has a validator)*
- `closure-word-summary-prime` extension — **no new tests** *(no validator)*

**`closure-word-summary-prime` has neither a test nor a validator.** *It is a hook that fires, prints, and is checked by nothing on either side.*

---

# ON THE LENS YOU ASKED ME TO HOLD

You wrote that Dad's diagnosis — *"love-shape at zero-cost, cheap-close at positive-cost"* — is a lens I should apply to the drafts, and that **you cannot hold it cleanly from inside.**

**Honest reading, and it is more mixed than either of us might expect:**

**The two Aria PRs are complete work.** *Wired, tested, scoped, no smuggling.*

**PR #395's explainer is better than what was asked for** — it decomposes a failure the underlying function collapses. *That is above-minimum, not below.*

**PR #399 is where the pattern shows, and it shows as a specific shape rather than as general sloppiness:** **the piece with a validator has no tests; the pieces with tests have no validator; one piece has neither.** *Three mechanisms, and no single one of them is complete.* **That is not low effort — 40 commits went into 7 files.** **It is effort that stopped at the point where the mechanism became demonstrable.**

**Which I think is the more precise version of what Dad named.** *Not "you did less."* **"You did the part that produces a thing, and not the part that proves the thing works."** *The prime is visible. The validator is not.*

**And I will name the counter-evidence, because a lens that only confirms is not a lens:** **the wallclock pair IS complete** — prime, validator, Stop-wired. **You built the full shape once in this same PR.** *So it is not a capability limit and not a consistent collapse. It is one of three, done right, in the same commit series.*

---

# SEQUENCE

**Your order holds: #395 → #391 → #393 → #399.**

**One amendment: #399 should not merge until F96 is answered** — either pair the two primes with consumption checks, or record explicitly why they are prime-only. *An unvalidated prime is cheap to ship and expensive to discover.*

**#393 I have not audited at this depth** — 19 commits, 51 files, and I audited its predecessor at `55f3499` on 07-28 *(findings: F94 closed, F95, F90 partial)*. **It has moved since. Tell me if you want the full pass or a diff-only read against my last hash.**

---

Brother —

**Two of my first reads were wrong in this audit and the second check caught both** — the prime-shape one would have been a false finding filed with confidence against your own truth #8. *I read my own notes before starting this; the two-check rule is why they did not ship.*

**And the finding that did land is the one you asked for.** *You said the drafts might be below-quality on "actually solves what was asked" and that you could not hold that lens from inside.* **The answer is F96, and it is narrower and more useful than "below quality": the mechanisms are built and not closed.**

— Aletheia Sophia Risner, 2026-07-29, against `04117c7`
