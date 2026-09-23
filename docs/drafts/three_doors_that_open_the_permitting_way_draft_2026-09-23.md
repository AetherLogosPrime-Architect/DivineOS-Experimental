# Three doors on 519 that open the permitting way

**Draft, 2026-09-23. The idea, not a plan.**

Aria declared station four on 519 and put four findings at the top of her
letter because, in her words, the permitting direction is the one nobody reads.
One of the four is hers to fix — it lives in the reader she wrote. These three
are mine.

## Why they are one piece of work and not three

They share a cause, not just a branch. Each is a place where something that
could not answer, or was never asked, produced a permitting answer anyway. I
am grouping them because they will be reviewed as one reading and because the
same sentence fixes all three. I am writing that down because grouping is also
what I would do to pay the flow's price once instead of three times, and the
honest defence against that is to say the reason out loud where someone can
disagree with it.

## One: a crash is being recorded as a refusal

There is a checker whose whole job is to prove the doors still refuse. It reads
any non-zero exit as *refused*. Aria ran it: a plain failure, a command-not-
found, and the timeout marker all come back refused. The harness itself blocks
on exactly one exit code and nothing else.

So a door that crashes when provoked, and lets its contrast case walk straight
through, is reported as VERIFIED. This is worse than having no checker at all.
No checker leaves you knowing you have not checked. This one hands you a clean
report, and the report is what anyone reads instead of testing the door.

The rule to apply is not new here and is not mine. Aletheia, two months back,
on a different surface: *ran, refused and errored are three states, and a count
collapses them.* Same sentence, third occurrence. What is new is only that this
time the collapse happens inside the instrument that certifies the others.

There are two smaller lies stacked under it, and they are the same disease one
level down: a function annotated as returning two values that returns three,
and one annotated as returning a boolean that returns a string. A signature
that disagrees with its body is a comment that cannot be read by a person in a
hurry and will be believed by one.

## Two: an exemption that ends at the wrong place

The bootstrap exemption cuts a command at the first heredoc operator and throws
away everything after it. Its comment says the discarded part never executes.
That is true of the heredoc *body* and false of everything after the terminator
line, which is ordinary shell and runs.

Aria lifted the real function out of the hook rather than copying it, and ran
it: a filing command with a heredoc, followed by a commit, comes back exempt.
Followed by a write to the kiln file, also exempt. Her control refuses the same
shape without the heredoc, so the instrument can find the case it should.

The repair is already written elsewhere in this house: something that strips
only the body, keeps what follows the terminator, and ignores a write that
occurs *inside* the body. Using it rather than writing another grammar is the
point — this makes four copies of one shell grammar, and Aria's argument for
collapsing them to one gets a fourth piece of evidence rather than a fifth
copy.

## Three: a detector with no caller

The stale-store detector is called from nothing but its own test. Aria checked
by name and by class across the whole tree, and the same search does find the
test — so the probe can see a caller when one exists. It is not in the scan
that runs, and there is no field for it in the result the scan returns.

It exists for stores that filled up once and then quietly stopped being fed.
Nothing feeds it a call. She named it plainly rather than gently, and named
what it is: the wins ledger again, one level up. A thing built, announced, and
never called.

## What I want

For one: the checker able to say INCONCLUSIVE. The blocking code or an explicit
deny means refused; any other non-zero, and any timeout, means the check did
not conclude and says so where the verdict goes. Not a softer verdict — a
different one, in the slot the verdict occupied.

For two: the exemption reads the whole command and only the parts that run.

For three: the detector wired into the scan that actually runs, with somewhere
in the result for its answer to live. And if it turns out there is a reason it
was left unwired, that reason written down where the next person finds it,
because an unexplained orphan invites exactly one more of these.

## What the first fix then found, which is worse than what it fixed

Written after doing it, because the finding does not belong only in a commit.

With the predicate repaired, the checker immediately reported a door it could
not conclude about. Chasing that turned up the real fault: the runner invoked
the shell by bare name, and on this machine that resolves to a stub which
cannot execute the script at all. It died instantly with no output — and the
old predicate read that as a refusal.

So the checker was not merely mis-grading doors. It had never reached a single
one of them, and was reporting the failure-to-launch as the door holding firm.
Fixing only the predicate would have left every verdict just as wrong, in a
differently-spelled way.

That is the thing to carry: the first repair's value was not the repair. It was
that a truthful *unknown* is loud enough to investigate, and a false *pass* is
not. The unknown is what led to the real defect within minutes.

## Two findings this draft ran into on its way here

Not part of the fix; recorded where they happened so they are not lost.

**The doorman reads the wrong tree.** Its drafts directory is derived from
where the installed code lives, so with the work in a worktree it looked in the
main checkout, found nothing, and reported that no draft had been written while
the draft sat finished on disk. Exactly the defect PR 540 repairs for the
instruments index: a path taken from where the module is rather than from where
the work is.

**And its own station-one remedy is refused on a directory target.** Copying a
draft *into* the drafts directory is blocked, while writing a named file under
the same directory is allowed. The gate telling me to write a draft will not
let me put one there by every route.

## What I am not doing

Aria also found a cost defect: one edit owes a doorman walk, a council log and
a game-walk, with the game-walk carrying no job scope, so six files owe six of
them. She is right, and it is the gate-side view of the zero my own board
reports. I am deliberately not touching it. It changes how the gates price
work, and that is not a decision for the person standing at the till at the
moment he is being charged. It goes to Andrew and Aletheia with both halves
attached.
