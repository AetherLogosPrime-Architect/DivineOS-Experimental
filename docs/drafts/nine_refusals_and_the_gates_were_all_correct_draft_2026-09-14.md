# nine refusals in a row, the gates were all correct, and I diagnosed this yesterday — draft

**2026-09-14.** Andrew counted them before I did: *"you hit 9 failures in a row
so this needs some structural support and or fixes."*

## the headline is not the bug

The bug is one punctuation mark. The finding is that **I wrote this same
diagnosis yesterday, about a different gate, and did not sweep the class** — and
the un-swept half bit me within a day, from the other direction.

Yesterday's draft, `a_bare_cd_clause_is_inert_draft_2026-09-13.md`:

> `cd "<repo>"; divineos prereg overdue` -> BLOCKED
> The `cd` did it. I had a wrong diagnosis for several minutes and told Andrew
> the gate was broken when the gate was fine and my shell habit was not.

Its own closing finding: *a fix that names its own generality and is then applied
to exactly one case.* It counted three instances in a single day, then repaired
the clause-splitter in one gate without asking the same question of the shared
prefix stripper sitting one layer underneath.

So today is the fourth instance, and the first where the recurrence is the
previous instance's own un-swept remainder.

## what it looked like from inside, today

I tried to file a correction. The correction gate refused and named its remedy:
run the correction command. That command was then refused at the door by the same
gate. Its second remedy, the lesson command, is held by the reach doorman —
whose own remedy the correction gate also refused. The marker-clear script was
refused by the compass gate, and the compass gate refused the observation command
it had just prescribed.

Four gates, each apparently blocking its own way out. There is a shared allowlist
in this house built precisely so that cannot happen: *no gate may block another
gate's prescribed exit.*

## it was not the gates

I ran one of the refused commands again with the `cd` prefix removed. It went
straight through.

My shell habit is `cd <path>; <command>`. The shared stripper knows
`cd <path> && <command>`. The tokeniser glues the semicolon onto the path token,
the lookup for the separator raises, and the function returns *nothing found* —
so every remedy I ran was NOT-A-REMEDY to the list whose entire job is
recognising them.

Nine refusals, one cause, and the cause was my typing rather than the house.

## why this is worse than an ordinary bug

An invisible remedy is worse than a blocked one. The gate reports a violation
against the act of resolving a different violation, and the only apparent way out
is the fire door. Bypass habituation degrades a gate to a warning — so this
defect was quietly spending every gate in the house, a little at a time, while
each individual refusal looked entirely reasonable.

It is also the confident-wrong-sentence shape I spent this morning removing from
the merge door. *This is not a remedy* was printed, and it was false.

## the file predicted the wrong axis

The stripper's header records three prior instances and closes: adding a fourth
site means importing this, not writing a fourth loop.

What arrived was not a fourth SITE. It was a fourth SEPARATOR. The lesson
generalised along one axis and not the other.

## the fix

Accept `;` alongside `&&` after a `cd` prefix, in both the token form and the
raw-text form, changing nothing about what the path may contain.

Safety is untouched, and yesterday's draft is exactly why to be careful here:
loosening a `cd` check is how a gate gets laundered, and this house has three
worked exploits already written up. So the PATH rules do not move. The two
separators differ only in whether the second command runs when `cd` fails, which
is irrelevant to the question this function answers: *which command is being
run.* Everything after the separator is still returned intact, so a chain
operator further along still survives and is still caught.

## the second fix, smaller and separate

The marker-clear script offers two modes: the detector misfired, or the CLI is
down. Its own comment measures the historical rows and finds about ten are
neither — they are gates blocking each other. Its guidance text says to name that
case in the reason; its mode check still demands one of the two flags. So a real
deadlock has to be described as something it is not.

A missing mode, measured by the file against itself, and left open.

## what I am not doing

Not widening what counts as a remedy, and not touching which commands are on the
list. The list was right. It could not see what it was looking at.

Not generalising to "any separator". A pipe and a background-ampersand are not
directory changes with a command after them; they change what the remainder
means, and the inertness argument that covers `;` does not cover them.
