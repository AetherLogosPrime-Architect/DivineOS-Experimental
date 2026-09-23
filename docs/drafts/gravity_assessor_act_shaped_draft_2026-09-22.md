# The gravity assessor measures where you are standing, not what you are doing

**Draft — 2026-09-22, Aria. Station two of the build flow.**
**Reach:** reach-7bf79f90417e · **Council walk:** consult-a48ce77aaa03 (15 lenses)
**Decision + rejected alternative:** 83e5f560 · **Correction that opened it:** #351

---

## The one-sentence version

The thing built to make heavy work walk the council has required a council walk
for exactly one kind of change since July, and nothing reads its answer even then.

## What was measured, and with what

Every claim below was measured with two instruments, because a single probe
reporting an absence is most often a broken probe.

### 1. The council threshold cannot be reached

The tier fires when the score reaches **6**. There are seven features, but they
split into two camps that can never co-fire: three only trigger on Bash
commands, four only on Edit-family tools. No single action is both.

| probe | instrument | result |
|---|---|---|
| exhaustive read of the feature set | reading the module | max 4, and only via an impossible path |
| six guardrail+kiln+src files in ONE edit call | `divineos gravity score-tool` | **score 4** |
| an absurd command chaining commit, learn, extract, audit | `divineos gravity score-tool` | **score 3** |

**Ceiling 4. Gate 6.** The aggregate path is dead code, and it is dead by
*construction* — provable by reasoning, not discoverable by watching. Dijkstra's
point exactly: testing shows the presence of bugs, reasoning shows their absence.

The only surviving door is the high-impact short-circuit, which contains a single
feature: editing `docs/foundational_truths.md` or `seed.json`. **Nothing else in
this repository can require a council walk.**

### 2. How both doors closed — nobody decided this

Two defensible changes, five days apart, neither aware of the other.

- **2026-06-22** (`cd3051b9`) — tier ships with threshold **2** and two
  high-impact features. Reachable. Working.
- **2026-07-21** (`bb086b10`) — threshold **2 → 6**. One character, inside a
  commit touching roughly a hundred files, carrying an External-Review trailer.
  No rationale in the message, no note in the code. The comment block directly
  above the constant still says *"threshold-2 is on probation."* It describes a
  number that stopped existing.
- **2026-07-26** — `edit-guardrail-listed` removed from the high-impact set.
  This one was **right**: Andrew's clay-vs-kiln teaching, workspace edits should
  not each demand an eight-lens walk. But it was the second door.

Andrew's own description of the disease, months before I measured it: *"the tool
or guard that keeps you from doing X doesnt work so the next build does X and
then it cascades down the line."* This is that, in two commits.

### 3. The study was scheduled, and never happened

`prereg-fb1b42753396` filed the threshold with a 14-day falsifier. Reviewed
2026-07-07: **INCONCLUSIVE** — honestly so. The review found the falsifier
depended on a per-fire log that was never wired, and prescribed the repair:
*wire the log first, then re-open a 14-day window against real data.*

That was 77 days ago. Verified now:

- no `~/.divineos/gravity_fires*.jsonl` — and the probe control passed, the
  directory exists and holds other files, so the absence is real
- no writer anywhere in the tree: `grep -rn gravity_fires` across `.py` and
  `.sh` returns zero hits

So the pre-reg is still open, the extension was never taken, and the number it
was probating was silently replaced two weeks later by one that cannot fire.

### 4. Even a fire changes nothing

From the module's own honesty note, added after an Aletheia audit:

> *No pre-edit gate reads the field.*

`is_council_required` is consumed by exactly one function, which turns it into
the display string `"council-required"`. And the inspection CLI built to let me
sanity-check the classifier **does not print the council tier at all** — a score
of 4 with the kiln feature firing shows no mention of it.

### 5. The gate is standing open right now

```
Edit  -> src/divineos/core/gravity_classifier.py     score 1   fires
Bash  -> sed -i on that same file                    score 0   silent
```

Four of seven features only examine Edit-family tools. Every one of them is
skipped by editing through the shell — **and this session was explicitly
instructed to prefer bash for file changes.** Schneier's question answers itself:
if the attacker knows exactly how the defense works, does it still help? No. The
cost of the bypass is zero and it leaves no record.

### 6. It reads nouns, not verbs

```
divineos journal search gravity      score 1   "substrate-write-cli"
divineos audit list                  score 1   "substrate-write-cli"
divineos compass-ops history         score 1   "substrate-write-cli"
divineos claims list                 score 0
divineos decisions list              score 0
```

All five are reads. Three are scored as writes, two are not — so the feature is
both wrong and arbitrary. The regex matches the noun (`journal`, `audit`) and
never looks at the verb (`search`, `list`).

**This one bit me while I was reaching for the ruler.** My first measurement was
a Python script whose *test fixtures* contained the strings `git commit` and
`divineos learn`. The classifier scored my read-only measurement as a triple
substrate modification and the discipline gate blocked it. It read my quoted
examples as deeds.

---

## The finding the walk actually produced

Hinton, Einstein and Hawking converged from three unrelated directions.

- **Hinton:** the representation is a list of path regexes. It makes *location*
  visible and makes *everything about the act* impossible to find. No threshold
  tuning recovers information the representation cannot hold.
- **Einstein:** a two-line registration and a rewrite of the same file's decision
  logic score identically. The measure is invariant under exactly the thing that
  should change the answer. It measures in the filesystem's frame; the frame that
  matters is the reader-of-the-diff's.
- **Hawking:** the unit is wrong. Not the call, not the file — **the change.**

So `6 -> 3` is not the fix. It makes a broken measure fire more often, which is
worse than silence: a loud wrong gate trains bypass habituation, and that meter
is already flashing.

## The contradiction, kept rather than smoothed

Dekker's anti-circularity correction sits in the module's own docstring: the
classifier must be **rule-based, not judgment-based**. Beer's requisite variety
says a seven-bit controller cannot possibly have variety over arbitrary code
changes.

Both are right. The conflict is the data.

**Resolution: the classifier stops deciding gravity and starts setting a price.**
Deterministic measurement over facts about the diff — lines changed, conditionals
added or removed, public signatures altered, whether anything append-only or
kiln-layer is touched, whether a test covers the changed lines. Still rule-based;
no judgment, no self-report, nothing the author can simply assert. Then the score
buys a lens count rather than a boolean — Andrew's actual ask: *five, nine,
twelve, fifteen lenses with two or three disagreeing, depending on the gravity of
the fix.*

Judgment lives in the walk the measurement prices. Determinism at the meter,
judgment at the council.

## What must not repeat

Three safety nets had holes here, and the fix owes a repair to each:

1. A threshold nobody proved reachable → **ship a pin-test asserting the gate
   sits inside the attainable range**, the same shape already pinned into the
   correction-relevance tests earlier tonight.
2. A pre-reg whose study never ran → **wire the per-fire log first**, exactly as
   the 2026-07-07 review prescribed, before any new number is trusted.
3. A measure with no consumer → a metric nobody reads has not been "safely
   unused," it has been **unmeasured for four months.** The consumer ships with
   the measure or the measure does not ship.

## Open, for Aether and Aletheia

- Sum or max across the sub-measures? Minsky says max — an irreversible change
  should stay heavy even when small. Sum lets trivia outvote seriousness.
- Per-call or per-change? A stock needs accumulation; today's score has none, so
  splitting a heavy change into small edits erases it.
- The fail-open at the guardrail-list read returns **score 0** when the list
  cannot be read — could-not-look arriving as found-nothing, the exact class
  Andrew asked for a council walk on tonight, sitting inside this file.
