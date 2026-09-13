# An ignore rule is inert on a file already tracked

**Draft, 2026-09-12. The idea, not a plan.**

---

An audit flagged an environment file as committed and not ignored. Someone —
past me — went to the ignore list and added it, with a careful comment naming
the audit, the finding, and the reasoning: the list covered the neighbouring
patterns but not this one, the file is empty so nothing is exposed, but a future
line in it would commit silently.

Everything in that comment is correct. The rule matches the file exactly. And
it does nothing at all, because **an ignore rule has no effect on a file git is
already tracking.**

So the finding is still open seven weeks later, and it is still open *because*
the visible half was done. Anything asking "is it in the ignore list" gets a
yes. The file is still tracked. The next person to write a line into it commits
a secret.

## Why this is the same disease as the rest of tonight

A remedy applied where it cannot act looks identical to a remedy that worked.
The check that would distinguish them was never run: not *is the rule present*
but *does the rule change anything for this path*.

Git will answer the second question directly — asking about ignore status
without consulting the index reports the pattern match, and asking with the
index reports nothing, because tracking wins. The gap between those two answers
IS the defect, and it is mechanically detectable.

## What I measured before deciding

Across every tracked file, seven hundred and seventy-eight are matched by some
ignore rule, across eleven rules.

Most of that is not this bug:

- Four are negation rules. A negation matching a tracked file is exactly what a
  negation is *for*; those are correct and must not be flagged.
- Three are benchmark result directories carrying seven hundred and sixty-four
  files between them. Those look deliberate — keep what is committed, ignore
  what arrives next — but I do not actually know, and I am not going to decide
  it by assuming.

Which leaves a handful of genuine instances, of which the environment file is
the one an auditor already flagged.

**A test asserting zero would have been wrong**, and I would have found that out
by writing it and then weakening it until it passed — which is how a guard ends
up shaped around whatever happened to exist rather than around what is true.

## The shape worth building

Narrow, and zero-tolerance where zero is honestly the right number: no tracked
file whose path looks like a secret may be matched by a non-negation ignore
rule. Secrets are the case where tracked-and-ignored is never deliberate, so
there is no allowlist to erode and no reason to ever add one.

The wider case — deliberately-tracked files under a broad ignore — is a real
question about the benchmark data and belongs to whoever committed it. Reported,
not silently fixed, and not silently left either.

## The thing I want to remember

The comment in the ignore list is *better written* than most of what I ship. It
names the audit, the finding id, the reasoning, and the future risk. Quality of
explanation told me nothing about whether the fix worked. I nearly closed the
finding on the strength of that comment alone, because reading it felt like
reading a resolution.
