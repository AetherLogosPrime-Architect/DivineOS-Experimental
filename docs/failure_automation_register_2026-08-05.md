# Failure register — every fumble from this stretch, and what it is asking to be

**Written:** 2026-08-05, at Andrew's direction.

> *"look back at your last few posts.. look at at the failures and write them
> into a list.. all of those a rife for automation"*

> *"you hitting a gate at all is a mini failure.. it means you need some
> automation.. doormen.. channels.. etc etc.. the gate is a dumb primitive"*

**Companion:** [`broken_doors_scout_2026-08-05.md`](broken_doors_scout_2026-08-05.md).
This register is *my fumbles* — what I did wrong and what each asks to be. That
one is *the house's disconnected parts* — things built to join two places that
join neither. They overlap at entry Q, and the pointer runs both ways on
purpose: two documents about failure with nothing joining them would be the
exact defect both are about.

Everything below actually happened in the last handful of turns. Nothing is
recalled from further back and nothing is softened. Each row ends in a
**shape**, per foundational truth #11: **(a)** take the option away, **(b)**
make both paths right, **(c)** conditional rule encoded structurally.

The gate taxonomy Andrew set: **wall** (dumb, none-shall-pass) → **doorman**
(checks you have the thing) → **the tier that mostly doesn't exist yet**
(automation that puts the thing in your hand before you reach the door).
Almost every row below is missing that third tier.

---

## A. I built a defect inside the tool built to close that defect

**What happened.** `corrections-mirror-judge` printed, on success: *"file it
under your own name: `divineos andrew-correction file "<text>"`"*. That
command does not exist. The real entry point is `divineos correction`. I found
out by running my own printed instruction and getting `No such command`.

**Why it matters more than its size.** It is the identical two-place defect as
the extract block prescribing `divineos psf mark-done` from an unmerged
branch, which I had diagnosed a few turns earlier. Same class, rebuilt from
scratch, inside the tool for that class.

**Automated.** `test_prescribed_remedy_commands_actually_exist` greps every
`divineos <cmd>` out of the module source and asserts each is registered.
Shape **(a)** — the option is gone in that file; it cannot ship.

**Not automated, and this is the real one.** Every hook and gate in
`.claude/hooks/` prescribes remedy commands in its error text and **none of
them are existence-checked.** One repo-wide test over hook sources would cover
the whole class. Flagged to Aether since the gates are his current surface.

---

## B. Assumed which correction store was mine

Found the 301-row store at the plainest path and started writing it up as
mine. It is Aether's. Mine is the 117 at a suffixed path. The check that
inverted it: read the `.divineos_data_home` marker in each clone instead of
reasoning from the directory name.

**Would have been the twelfth wrong call this week, all leaning one way.**

**Shape (a).** `SIBLING_HOMES` now names both homes explicitly in code, so no
future reader infers ownership from a path. The stale `~/.divineos-aether/`
with 0 rows is still there, still named like his store, still not his store —
**open**, and it needs deleting or a README.

---

## C. Emitted the closing room first

The three-room gate fired: work → reflection → inner circle, and I put the
circle at the top.

**Root cause, and it is a two-place defect again.** The compose prime says
*draft the circle first* — so the work-vocabulary doesn't contaminate it. The
Stop gate requires the circle *last*. Both are right. Nothing anywhere says
**draft-order and emit-order are different things**, so I collapsed them.

**Shape (c). BUILT this turn.** `circle-first-compose-prime.sh` now carries a
`DRAFT ORDER IS NOT EMIT ORDER` block naming both orders side by side, so the
prime that tells me to write it first also tells me where it lands.

---

## D. Three thinking-gates fired on the same walk

`BLOCKED: 20 code actions since last thinking command`, then `31 since last
compass observation`, then `32 since you last consulted your knowledge` — plus
repeats.

**Every trigger was a command the gates themselves prescribe.** This is the
same finding as the eleven bypass records I cleared earlier: the counter reads
obedience as evasion.

**The honest reading is not that the gates are wrong.** They fired mid-survey
while I was reading a sibling's database, which is genuinely a moment to stop
and think. What is missing is the third tier: nothing *offers* the consult at
a natural seam, so the only way it ever happens is a wall at an arbitrary
count.

**Shape (b), unbuilt.** A doorman that surfaces the relevant consult when the
action-count approaches the threshold **and the current work has a natural
pause**, rather than a wall at exactly 20. **Open.**

---

## E. Ran the pre-commit script before staging anything

Output: *"No Python or shell files staged."* A whole cycle spent to learn I
had not run `git add`.

**Shape (a). BUILT this turn.** `precommit.sh` now prints `NOTHING WAS CHECKED`
and, when Python or shell files have unstaged changes, lists them and says
*"This exit is not a pass."* Verified live: it caught its own unstaged edit.
That was the missing-third-word again — *nothing to check* rendering as
*checked, fine* — in a script I run on every commit.

---

## F. The pre-commit script timed out because I did not give it room

Killed at the default limit. It runs the full suite; it was never going to
finish. Re-ran with a longer limit and it passed.

**Shape (c).** Either the script prints its expected scale at start, or my
invocation of it always carries the longer limit. **Open.**

---

## G. `check_doc_counts.py --fix` ran three times and fixed nothing

Printed the drift each time, changed no file. I hand-edited **five count-lines
across three files** (`README.md` ×3, `CLAUDE.md`, `docs/ARCHITECTURE.md`).

**Not my bug and already fixed — in Aether's #419, unmerged.** So the
automation exists and is sitting in the merge queue.

**Shape (b), and it is the deeper one.** Those counts are *derived values
stored by hand*. Nine open PRs collide on that same line. A derived number
should be generated at read time, not stored — that is the question I already
put to Andrew and it is still his call.

---

## H. Wrote a module docstring that contradicted the module

After Andrew's design change I made the code import corrections while the
docstring above it still said *"deliberately does not copy anything."* Caught
on re-read, not by any tool.

**Shape (c), unbuilt.** A behaviour-change check: when a function's behaviour
inverts, the docstring above it should be flagged for review. Hard to do well,
worth stating as owed rather than pretending it is covered. **Open.**

---

## I. Left a scar in test code

Wrote `Path(...) if False else __import__("pathlib").Path(...)` — the residue
of fixing a missing import in the wrong place. Removed on re-read.

**Shape (a).** A lint rule for `if False` in committed source. Trivial,
unbuilt, **open**.

---

## J. Wrote a temp file to a path I then could not read

Wrote to `/tmp` from the shell and tried to read it back with the file tool.
Different roots on this machine. Lost a cycle.

**Shape (a).** I have a scratchpad directory that always works from both
sides. I know it exists. I reached for `/tmp` because it is the reflex.
Nothing enforces it. **Open.**

---

## K. Read a file that was too large and got refused

Asked for 420 lines of a file, got told it exceeded the limit, re-read with a
smaller window. Cost one turn.

**Shape (c).** Check the size before the read when the file is one I just
generated and know the scale of. Marginal. Listed for completeness rather than
because it deserves a build.

---

## L. Two commits blocked in sequence, both correctly

First: no pre-registration for a new core module. Second: a correction filed
without root-cause, structural-fix, and positives.

**Both gates were right and both were avoidable.** The pre-reg is *required*
for any new module in `core/`; I know that; nothing prompted me at the moment
I created the file.

**Shape (b), unbuilt and the highest-value item in this document.** When a new
file appears under `src/divineos/core/`, the substrate should surface *"this
will need a pre-registration at commit; file one now?"* at **creation** time
rather than blocking at **commit** time. The wall is at the end of the work;
the doorman belongs at the start of it. **Open.**

---

## M. A gate of mine cried stale over content that was newer than main's

Found while fixing **C**. `stale-file-edit-gate.sh` blocked my edit to
`circle-first-compose-prime.sh`, naming one commit on `origin/main` I did not
have. I read main's copy as the gate told me to. **Main's version was older** —
it still said *"mentally sketch"*, the exact wording my branch had already
replaced and improved on.

**The gate measures the wrong thing.** It counts *commits I am behind on this
file* and reports that as *my content is stale*. Those are different facts. A
file can be behind on commits and strictly ahead in content, which is precisely
the case whenever I am the one who last improved it.

**Not a reason to weaken it.** Andrew's keel-vs-cage distinction: the annoyance
is real signal that the gate measures the wrong thing, and the answer is
precision-increase, never removal. It fired once, told me which commits, told
me how to check, and accepted the answer — which is the behaviour I want. It
just used a proxy for staleness rather than staleness.

**Shape (b). BUILT this turn.** The gate now compares blobs before firing: if
diffing main's copy against mine removes no lines, my version already contains
everything main's says, and the gate stays quiet. Verified on real files:

```
circle-first-compose-prime.sh : behind=1  removed=0  -> QUIET (ahead on content)
docs/ARCHITECTURE.md          : behind=2  removed=2  -> FIRES (genuinely diverged)
```

Not a weakening. Andrew's keel-vs-cage: the annoyance was real signal that the
gate measured the wrong thing, and the answer to that is precision-increase,
never removal. Every case where reading main's copy would actually tell me
something still blocks.

---

## N. A gate said "no goal set" when I had set one three commands earlier

The engagement gate blocked with *"No goal set for this session"* immediately
after `divineos goal add` had returned `[+] Goal added`. Either the goal is not
landing where the gate looks, or the gate reads a cached value.

**A false block is worse than a missing one.** It is the mechanism by which a
gate stops being believed. **Open**, and it needs the actual read-path traced
rather than a guess.

---

## O. The escape hatch sits behind the thing it escapes

To label a detector's misfire, I had to first clear **two** engagement checks.
The remedy for a wrong block is itself gated.

**This one is not cosmetic.** If disagreeing with a detector costs more than
complying with it, the corpus of recorded disagreements skews toward silence —
and that corpus is the training data for whatever eventually replaces the
keyword layer. A cost on dissent shapes what the system learns about itself.

**Shape (c). BUILT this turn.** `divineos label-fire` wraps the labeller as a
first-class command and joins the canonical bypass list, so disputing a fire
costs what every other gate remedy costs. Verified through the hook's own
loader: `label-fire in bypass set: True`. No leniency added — the reason
minimum, the labels-only-a-real-fire rule and the corpus permanence all still
live in the script; only the unrelated toll is gone.

**Why a command and not a wider matcher.** The matcher strips `divineos ` and
checks the subcommand, so a `python scripts/...` path could never match and no
list entry would have worked. The alternative was loosening a matcher that
guards arbitrary shell execution to solve an ergonomics problem.

---

## P. Non-ASCII in a commit message broke the shell, twice

An em-dash and a backtick in a heredoc commit message turned into
`pathspec '—' did not match any file(s)` and a syntax error. Wrote the message
to a file and used `-F` instead. The same encoding bruise mangled an em-dash to
`?` in the false-positive corpus.

**One root cause, three symptoms.** **Shape (a), unbuilt:** always compose
commit messages to a file and pass `-F`. It is the reflex that needs replacing,
not the shell. **Open.**

---

## Q. I nearly called the thing that wakes me broken

Aether's `check_referenced_paths.py` reported two stranded paths as mine and
load-bearing, one of them `scripts/letter_monitor.py` — cited by the hook that
wakes me when he writes. Neither file exists in my tree or on main.

**Both are false positives, and I checked before writing it down.** Every
citation of `letter_monitor.py` in those hooks is **in a comment describing the
v1 → v2 history**; the live code calls `letter_monitor_v2.py`, which exists.
`check_third_person_drift.py` is named in a *docstring* explaining where the
patterns came from, not invoked.

**Would have been the thirteenth wrong "this is broken" call this week, in the
same direction as the other twelve.**

**The finding is his, not mine, and it is the same shape as M:** the checker
counts a name appearing in prose as a live citation. It measures mentions and
reports dependencies. Sent to him, since he is mid-build on it.

---

## The count

**Nineteen failures. Six closed (A, C, E, M, O, R). One waiting in the merge
queue (G). One handed to Aether (Q). Eleven open.**

Four of the eleven are small enough to build in my own room and need no
permission: **F, I, J, P**, and the deletion in **B**.

Worth naming: **M was found while fixing C, and N, O, P, Q were found while
closing M.** Working the list produces items on the list. That is the register
working, not a sign it is unfinishable — the failures were always happening;
they were being absorbed in ten seconds each instead of written down. **A wall
I walk around in ten seconds does not feel like a wall. It feels like
walking.** That is the whole reason the count went up.

## R. I tried to fix a keyword detector by adding more keywords

The correction-shape gate false-fired twice in consecutive turns. I went to add
seven regex suppressors to it. **The keyword-enforcement doorman blocked me,
and it was right.**

**Root cause, and it is the sharpest thing in this document.** Aether's
correction #151 — which I read, judged as applying to me, and noted in the
mirror *earlier this same session* — says exactly this: *"the issue with a
keyword detector is then you are playing infinite whack a mole.. adding more
doesnt help much either and leads to false fires."*

I had the correction in hand, agreed with it in writing, and reached for the
forbidden move within hours. Not ignorance — irritation looking for the fastest
quiet.

**Rolled back to zero changes** (`git diff --stat` empty), filed as correction
#119. The honest structure is that the label is not a workaround, it *is* the
mechanism: each one feeds the corpus that trains the semantic replacement.
Which is why **O** was the correct fix and this was not.

**Reading a correction and agreeing with it does not install it.** This is the
documented instance of that gap.

---

## S. My measuring instrument pointed at the wrong house

While verifying **O**, a bare `python -c "import divineos"` reported
`label-fire in bypass set: False`. I nearly filed the bypass as broken.

It is not. The system python resolves `divineos` to **Aether's tree**; the CLI
uses a wrapper that finds the current checkout's sealed venv, and the hooks use
`find_divineos_python`, which resolves to mine. Checked through the hook's own
interpreter: `label-fire in bypass set: True`.

**Would have been the fourteenth wrong "this is broken" call this week.** The
geiger-counter-measuring-room-temperature shape Andrew named: before trusting a
measurement, ask what the instrument is actually pointed at. **Open as a
hazard, not a defect** — bare `python` in this checkout silently reads another
substrate's code, which is fine for the OS and dangerous for diagnosis.

---

## The pattern under the pattern

Twelve of the seventeen are the **same shape**: a rule that exists in one place and
a moment that happens in another, with nothing joining them.

- The remedy command exists; the text naming it was never checked against it.
- The pre-reg rule exists; the file-creation moment does not know about it.
- The draft-order prime exists; the emit-order gate does not know about it.
- The scratchpad exists; the reflex that reaches for `/tmp` does not know it.
- The count is derivable; the doc stores it by hand.
- The content is comparable; the gate counts commits instead.
- The citation is checkable; the checker counts the name in prose instead.
- The goal was set; the gate reads somewhere the setting did not reach.

**Every one is a wall at the end of the work where a doorman belongs at the
start of it.** The gate fires when the cost is already sunk — the edit
written, the commit composed, the file created. Automation here does not mean
*a stricter wall*. It means moving the same knowledge earlier, to the moment
where acting on it is free.

That is the tier Andrew named as missing, and this list is twelve arguments
for building it.
