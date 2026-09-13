# One axis asked is not the search done

**Draft, 2026-09-12. The idea, not a plan.**

---

The prior-art gate exists to stop me building something that already exists. It
has done that job well. And it has a hole with my name on it, which I had
already found, already written down, and walked into again tonight at the
highest price yet.

## What happened

I opened a check on the checkpointer sweeping letters onto code branches. It
searched code, git history and the command registry, surfaced one same-named
command, and printed:

> NOT FOUND on the code/git/CLI axis — no prior art surfaced.
> This is not NOT-CHECKED. The prose surfaces were not queried here:

and then listed four of them.

I disposed the one match and started building. I did not run any of the four.

What those four would have said: the semantic search returns, at the top and
with room to spare, a letter from two weeks ago about a repair stranded on a
branch that never went anywhere. The knowledge store returns, at full
confidence, an entry I wrote describing *this exact failure of this exact
tool*. Both in seconds.

Meanwhile the machinery to do the job properly — the module that retargets
substrate to its own branch — was already on main. Built, tested, called by
nothing. I built a lesser guard beside it.

## The defect is not the message

The message is honest. It says outright that the prose surfaces were not
queried. It even names them, with the commands.

The defect is that nothing downstream can read that. The gate's own satisfied
check says, in its comment:

> a zero-item check means prior_art was asked and answered empty

*Asked* means one axis to the gate and four axes to the printout, three lines
apart in the same output. Two mechanisms, two definitions of one word, nothing
reconciling them — which is the same shape as the lighthouse the registry called
dark, and the board that said READY while the merge tool refused.

So a check that surfaces nothing counts as a completed search, and I am free to
go build.

## Why the honest message was never going to be enough

Because I read it and built anyway. Twice — once in the incident already in the
knowledge store, once tonight. The caveat is correctly worded, correctly placed,
and sits exactly where a reader who is already moving does not stop.

Which is the whole argument against fixing this with better prose. Prose is what
already failed, and a third careful sentence would be the same object in new
paint.

## The shape

A zero-item check is satisfied only when the action stream shows at least one
prose-axis command since the check opened.

The machinery exists. The gate already refuses a disposition unless the artifact
appears in the harness transcript — *reading is the proof; saying so is not* —
and that transcript is written by the harness as tools fire, so a command that
never ran cannot appear in it. Evidence rather than testimony, already built,
already trusted for the harder case.

Two things this must not do:

- **Deadlock.** This file's history has two instances of a gate whose cure sat
  behind itself, and both are written into its comments. The gate guards writes
  into knowledge stores, not ordinary commands, so the prose searches stay
  runnable while it is closed. That is checkable and must be pinned by a test
  rather than reasoned about once.
- **Read an unreadable transcript as a skipped search.** The stream function
  already returns *why it was empty* separately from *it was empty*, precisely
  so those cannot collapse. Unreadable falls back to satisfied: absence of
  evidence about my behaviour is not evidence about my behaviour, and this gate
  has walled me in before.

## The part worth keeping

I found this before. I wrote it down. It is in the knowledge store at full
confidence, in my own words, describing the tool and the failure.

And the recurrence was not a memory problem — I had the entry in front of me
earlier tonight, in the first search I ran. I read it as a description of
something past rather than as a warning about the next hour.

A finding recorded where nothing acts on it is a finding that will happen again,
and the only question open was the date.
