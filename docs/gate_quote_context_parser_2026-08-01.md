# Quote-context parser for the bypass matcher

**2026-08-01.** Andrew: *"its a lego on the floor you keep stepping on because
you refuse to pick it up.. brat lol.. the gate needs a doorman and you know
this."*

He was right and the diagnosis was exact: I had already filed the claim, and
filing had felt like discharge.

## The failure

The overdue-prereg gate **hard-blocks all substantive tool use** and names
`divineos prereg assess` as its own remedy. `prereg` is on the canonical
bypass list. `divineos prereg overdue` passed. The `assess` call was **denied
three times** — because its notes value happened to describe shell syntax.

The identical command with a short note passed. So the discriminator was
**argument content**, which meant the matcher was deciding on the raw command
string rather than on shell structure.

Worst possible failure curve: the gate refuses its own remedy exactly when the
remedy needs a detailed note. A trivial outcome files fine; a considered one
cannot.

## The fix

`_has_compound_shape` was `any(marker in cmd for marker in CHARS)` — a
substring scan. It is now an explicit quote-state scanner.

| context | chaining operators | substitution / backtick |
|---|---|---|
| unquoted | **dangerous** | **dangerous** |
| single-quoted | inert | inert |
| double-quoted | inert | **dangerous** |

That bottom-right cell is the whole reason this is not trivial. It is real
shell behaviour and it is the F31 exploit: `cd "$(rm -rf /)" && ...` runs the
substitution as part of `cd`'s argument evaluation. The prior fix encoded that
rule for the `cd` prefix specifically; this generalises it.

Unterminated quote → **fail closed.**

## Why an explicit scanner and not shlex

Aletheia recommended shlex at F31. I deviated, and flag it because departing
from an auditor's named recommendation should be visible rather than quiet.

`shlex` in posix mode gives token boundaries but **discards the quoting
context** — it cannot tell me whether a substitution sat inside double quotes,
which is the only case that matters here. Non-posix mode keeps quotes but
stops tracking escapes correctly. The decision is per-quote-context, so the
parser has to model quote context.

## Why this is a different call from the silencer that was REJECTED

Consulting the knowledge store before building surfaced a prior decision that
looks like a precedent against this one, and it deserves an answer rather than
a silent override.

The `unverified_claim_detector` carries a design note (2026-06-02, Schneier
lens) that **rejects** silencing on descriptive/quoted context:

> the tempting fix — silence when a stative adverb like "already" precedes the
> trigger — is REJECTED: it opens a false-negative loophole ... for this gate
> a missed real claim is far worse than a harmless re-check.

Two things distinguish the present change, and if either failed I should not
have shipped it:

**1. The cost asymmetry is inverted.** There, a false positive is a harmless
re-check and a false negative is an unverified claim reaching Andrew. Here, a
false positive **hard-blocks every tool call including the remedy**, and the
observed cost was already paid: the real assessment on `prereg-6c9e721e8ec8`
could not be written, outcomes are one-way, and a diagnostic probe note is now
its permanent record.

**2. It is not a heuristic silencer — it is a faithful model of the executing
system.** The rejected proposal guessed at *intent* ("this looks like a
quotation, so probably not a claim"). This does not guess. It computes what
the shell itself would treat as an operator. Anything bash would execute still
blocks. There is no loophole opened, because the model and the executor agree
by construction — that is the property a heuristic can never have.

If a future auditor finds a string where this scanner and bash disagree, that
is a real bug and not a tuning question. **That is the falsifier**, and it is
per-invocation rather than time-based: on any current call,
`_has_compound_shape(cmd)` must be True for every `cmd` in which bash would
execute an operator.

## Tests

`tests/test_bypass_quote_context.py` — 13 tests, all passing. Deliberately
split so the security half outnumbers the convenience half:

- the live regression (operators inside quoted values, both quote kinds)
- length-invariance, since the symptom was short-passes / long-fails
- **F22 exploits still blocked**: decoy safe-word followed by a chain
- **F31 exploit still blocked**: substitution inside a quoted `cd` argument
- backtick inside double quotes still blocked
- single-quoted substitution asserted *inert*, so a future over-tightening
  that flattens the two quote kinds fails loudly instead of quietly
  re-breaking long notes
- unterminated quote fails closed; escaped quote does not open a string

Full gate/hook selection: 1178 passed, 63 skipped.

## Second finding, not fixed here

`.claude/hooks/keyword-enforcement-doorman.sh` blocked this edit repeatedly,
counting **prose in a docstring** as added regex patterns. Reading the hook:
its block message instructs *"then retry the edit"* after logging a
`divineos correction`, but **the hook never checks whether that correction
exists.** The documented remedy is not implemented, so a retry always blocks.

That is a second self-blocking gate of the same family as the one this
document fixes, and it fired on the *mention vs use* distinction — a docstring
describing shell syntax read as code matching shell syntax. Which is the same
confusion as the bug being fixed, and the same confusion that fired
`correction-shape-v2` twice tonight on tasting results.

**Three mechanisms, one shape, one session.** Filed separately; not silently
worked around.
