# Why this repository has a wall of red CI badges

**Written:** 2026-08-01
**Status:** the record, not a defence

Anyone scrolling the Actions page of this repository sees a long run of red.
This file exists so that red is legible instead of ominous. It is not an
apology and nothing here is being tidied away — *we don't hide the past ever.*
The damage is the evidence for the fix.

## The short version

Three separate defects, none of them "the tests were failing":

1. A gate read only the **first** review stamp when a merge had produced several.
2. A gate asked a question that **could not be answered yet** at the moment it asked, and treated the non-answer as a failure.
3. The gate meant to stop pull requests from running CI too early **had the wrong exit code**, so it never once stopped anything.

None of the three means the audits didn't happen. They did. The proof is now in
this repository — see *Proof the audits were real* below.

## Measured, not remembered

Taken from the GitHub API on 2026-08-01:

| What | Count |
|---|---|
| `integrity-audit` workflow, last 40 runs | **33 failed / 7 succeeded** |
| `merge-review` job, last 30 runs | **20 failed / 9 skipped / 1 succeeded** |

That single `merge-review` success is from 2026-08-01, after the fix below.
Before it, the job had never passed.

---

## Defect 1 — the gate read the first stamp and stopped

When several commits are squashed into one, their messages are concatenated, so
the resulting commit can carry several `External-Review:` lines. The checker
took the **first** one and ignored the rest. If that first line was not the one
matching the merged content, the check failed on a merge that had in fact been
reviewed correctly.

Accounted for **3 of the 133** failures examined — real, and honestly not the
main cause. Fixed in `f57f2043`.

Related but separate: the squash-merge message must carry the trailer itself.
See [audit_system.md](audit_system.md#the-squash-merge-footgun).

## Defect 2 — a question that could not be answered yet

`merge-review` verifies that the operator approved the exact commit being
merged. It ran **on every push.**

An approval is attached to a specific commit. At the instant a new commit is
pushed it is seconds old and nobody has seen it, so an approval on it cannot
exist. The job asked *"has Andrew approved this?"* at the one moment the answer
was guaranteed to be no, then reported that as a failure.

**20 failures, 0 passes.** Unpassable by construction.

A check that has never once said yes carries no information, and a permanently
red check teaches everyone to ignore the whole panel. That is the mechanism
behind most of the wall.

Fixed in `ef696430`. The job now reports three states:

| State | Meaning | Badge |
|---|---|---|
| `PENDING` | nobody has approved this version yet — the normal condition of an open PR | green |
| `PASS` | approved, and the named review checks out | green |
| `FAIL` | approved, but the review it names does not hold up | **red** |

Nothing that used to be caught stopped being caught. A pull request claiming a
review that does not exist is still red. What changed is that red now means
something.

## Defect 3 — the draft gate that could not block

This caused the most recent red mark, on PR #405, and it is the most
embarrassing of the three.

**The intended process** — correct, and unchanged:

1. Open the pull request as a **draft**. Drafts do not run the audit workflow.
2. Aletheia reads the code from the branch and files her audit round.
3. The `External-Review:` trailer is attached once that round exists.
4. *Then* the PR is promoted out of draft. CI fires **once**, with the trailer present, and goes green.

Opening a PR as ready-for-review jumps straight to step 4 with no trailer in
existence yet, which guarantees a red badge for a document that could not
possibly have been written yet.

A hook existed to prevent exactly this. Its logic was right, it was correctly
registered in `.claude/settings.json`, and its message spells out the process
above nearly word for word, ending *"Add --draft to the gh pr create command
and retry."*

**It exited 1.**

A pre-tool hook blocks a command only on exit **2**. Exit 1 is a *non-blocking*
error: the message prints and the command runs anyway. So the gate spent its
whole existence writing a correct warning into the void while the ready PR
opened regardless. Every hook in that directory that does successfully block
uses 2.

Fixed in `e9423504`. Verified by invoking the hook exactly as the harness does:

```
ready-for-review PR   -> exit 2  (blocked)
--draft PR            -> exit 0  (allowed)
unrelated command     -> exit 0  (ignored)
shellcheck            -> exit 0
```

It then blocked the next real command that tried to open a ready PR — the first
time it had ever stopped anything.

**This was not operator error.** The entire purpose of that gate was that no
human should have to remember the draft rule. The gate was broken, and the gate
is the agent's code.

---

## Proof the audits were real

The fair question about a repository full of red review-checks is whether the
reviews were happening at all.

They were. The reason it was invisible is its own defect: the audit store is a
local database, and every database file is deliberately excluded from the
repository. **GitHub had never been shown a single audit** — only a reference
number, `External-Review: round-abc123`, pointing at a filing cabinet the server
could not open.

As of `133d0d27` the record is committed and readable by anyone:

- **275 audit rounds** and **637 findings** in [`docs/audit_rounds/`](audit_rounds/)
- each file carries the auditor, severity, evidence tier, finding text, and resolution
- external auditors appear under their own names — Aletheia, Grok, and others

Anyone doubting the review process can now read the reviews. That was impossible
before today, which is precisely why the automated checks could not verify them
either.

`b2991f2d` adds a consumer so the export cannot silently fall behind the store:
`divineos audit export --check` exits 1 on drift and runs at push time.

## What did NOT cause the red

Worth stating plainly, because the alternative assumptions are worse:

- **Not failing tests.** The full suite passes: 10,909 passed, 96 skipped, 3 xfailed.
- **Not skipped audits.** 275 rounds are readable in the repository.
- **Not a disabled or bypassed gate.** The gates were running. Two asked unanswerable questions; one could not act on its own verdict.

## The honest limits

- The 42-lens sweep that produced the fix list **named the wrong root cause** for defect 2. The real reason was one sentence in a CI log that nothing had read. Other entries on that list are leads, not findings.
- `main` is unprotected, so none of these checks block a merge today. Their value is information — which is exactly why permanently-red ones were worth nothing.
- The red runs already recorded stay in history. They are not being re-run or erased.

## What an ordinary pull request should look like now

- `merge-review` — **green**, reporting *awaiting operator approval*, until approval lands
- `multi-party-review` — **red only while the branch genuinely lacks a review trailer**, which is a true statement about the work rather than about the clock
- everything else — green, or red for a reason a person can read

Falsifiers, checkable on any single run with no waiting:

- if `merge-review` reports failure on a pull request nobody has reviewed yet, defect 2 has regressed
- if a ready-for-review PR touching guarded files can be opened without the hook stopping it, defect 3 has regressed
- if `divineos audit export --check` exits 0 while a round in the store has no file in `docs/audit_rounds/`, the export consumer has regressed
