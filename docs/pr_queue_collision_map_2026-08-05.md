# PR queue — collision map and merge order

**Written:** 2026-08-05 by Aria, at Andrew's instruction to coordinate rather
than clean up after.

> *"you organize the tasks and give him his duty list so you both dont collide
> lol.. and then each of you works on what you work on and then after you
> resync and share and audit eachothers work"*
> *"others might be in there you havent seen yet"*

He was right that there were others. This is the survey.

---

## The queue

15 open PRs, all draft. 13 mergeable with green checks, 2 red on tests
(#409, #410), 1 conflicting with no checks run (#406).

## The two blockers, both diagnosed

### #409 / #410 — two failing tests, one word

CI on `split/bypass-livelock-gates`: `2 failed, 10813 passed, 143 skipped,
13 deselected, 3 xfailed`.

Both failures share one cause. `tests/test_bypass_telemetry.py:96` and `:246`
assert `"Elevated bypass rate" in block`. The new output says
`"Elevated ESCAPE rate"`.

**The logic is correct.** Both failing outputs contain the escalation at the
right thresholds with the right counts, and carry the substantive fix:
*"Compliance is excluded from this verdict: running a gate's prescribed
command satisfies it and is not evasion."* That is the counter no longer
reading obedience as evasion — the thing the PR exists to do.

Verified against both sides: on `aria/system-load-check-2026-07-30` the source
at `bypass_telemetry.py:280` still says `"Elevated bypass rate"` and the two
assertions match it, so they pass here. The mismatch exists only on his branch.

**Two-line assertion update. His branch, his line to change.**

### #406 — conflicting, mine

78 ahead, 4 behind. 44 overlapping files, of which **27 are letters** — the
same content arriving by two paths, not real conflicts — and 17 are
code/config/docs.

`git merge-tree` reports **exactly 13 genuine conflicts**, matching Aether's
independent count of 13. Two measurements, same referent, same answer. Worth
noting given our 92-vs-184 disagreement on gate fires, where neither of us
named the database.

**Two are `add/add`:** `src/divineos/core/system_load_check.py` and
`tests/test_system_load_check.py`. We each independently created the same
file. That is not "reconcile two edits" — it is **decide which implementation
survives**, and it is a joint decision, not a merge either of us performs
alone.

The other 11 are ordinary content conflicts.

---

## The collision map — what nobody had looked at

Files touched by more than one open PR, letters excluded:

```
  9   docs/ARCHITECTURE.md
  7   README.md
  6   .claude/settings.json
  4   src/divineos/cli/__init__.py
  4   .claude/hooks/keyword-enforcement-doorman.sh
  3   setup/setup-hooks.sh
  3   CLAUDE.md
  3   .claude/hooks/aletheia-boot-gate-preflight.sh
  2   src/divineos/hooks/pre_tool_use_gate.py
  2   src/divineos/cli/knowledge_commands.py
  2   scripts/check_root_cause_audit.py
  2   scripts/check_push_readiness.sh
  2   scripts/check_doc_counts.py
```

**Nine of fifteen PRs touch the architecture doc. Seven touch the README.**

### Most of that is manufactured, and the mechanism is one line

Sampled the actual diffs (#407, #413, #416). Two kinds of change:

- **Module description lines** — real content, different modules, different
  lines. These mostly do NOT collide.
- **The count line** — `cli/ CLI package (421 commands across 82 modules)`
  rewritten to `(422 commands across 84 modules)`. Every PR that adds a module
  rewrites the same line to a different number.

So the nine-way collision is largely **one auto-derivable value stored by
hand**. The doc-count discipline that keeps the docs honest also manufactures
the conflicts.

### #419 fixes the adjacent problem, not this one

Read it before writing this. It is good work: `--fix` shipped with no fixer
for command counts, so on command drift it ran, changed nothing, and printed
*"likely a non-count error, investigate manually"* — sending two of us hunting
a phantom. It also closes an unreachable success condition where a branch with
genuinely fewer commands could never converge.

That is **convergence within a branch**. The collision is **across branches**,
and monotonic fixers do not close it: monotonic prevents one branch going
*down*, but nine branches each raising the same line to a *different* number
still conflict textually. Andrew chose monotonic on 2026-06-12 precisely to
reduce rebase fights, and it does reduce them; it does not eliminate this case.

**Not proposing a fix.** Rule 1: understand before moving, and the
generated-vs-stored question belongs with whoever owns that tool. Flagged as
the largest single source of queue friction.

---

## Proposed merge order

Ordered by collision cost, lowest first, so each merge invalidates as little
as possible downstream.

**Tier 1 — merge first, few shared files:**
#411 (branch scope guard), #412 (ci merge review visibility),
#417 (family letters), #418 (stop phase hang)

**Tier 2 — the doc-count fix, so later merges inherit a working fixer:**
#419

**Tier 3 — after the two-line test fix lands:**
#409, #410

**Tier 4 — heavy shared-file touchers, one at a time with a rebase between:**
#405, #407, #408, #413, #414, #415, #416

**Last — mine, after main has settled:**
#406, rebased onto whatever main has become, with the two `add/add` files
resolved by joint decision first.

Order matters most inside Tier 4. Every one touches the architecture doc or
the settings file, so merging two without a rebase between guarantees the
second conflicts.

---

## Duty split

**Aether:** the two-line assertion fix on #409/#410. The gate emit-path he has
already built. Merge execution in the order above, rebasing between Tier 4
items.

**Aria:** the audit pass on each PR before it merges — his first pass, my
second, per Andrew 2026-08-04 (*"the gates hes working on are not his they are
YOURS.. its just better he works on them first then you can see everything hes
done and pushback accordingly"*). Plus the #406 rebase once main settles.

**Joint, before either of us touches it:** which `system_load_check.py`
survives.

**Open question for Andrew:** whether the doc-count line should be generated
at merge rather than stored, since it produces most of the queue friction and
neither of us owns that call alone.
