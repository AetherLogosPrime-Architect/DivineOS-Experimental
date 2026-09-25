# The stamping step has never run, and the guard has been blaming a worktree

*Draft, 2026-09-22. The idea, not a plan.*

## What I was doing when I found it

Trying to merge the request Aletheia confirmed. Stamping refused it: one commit
still carried no trailer "after the amend", and the diagnostic named the
worktree holding the branch as the likely cause.

I went to check the worktree theory and found something that rules it out: the
branch tip was unchanged and there were no backup refs. A rewrite leaves both.
**The rewrite had not run at all.** So a message describing what happened after
an amend was describing an amend that never occurred.

## The actual cause

Two ends of one comparison abbreviate differently.

- The commits are selected with git's AUTO abbreviation, which grows with the
  repository. Here it is **nine** characters.
- The rewrite filter asks git for **eight**.

Eight never equals nine. The filter matches nothing, so every message is
rewritten to itself, so git has nothing to do, so it exits zero without
touching anything. Nothing lied. A rewrite that changes no message genuinely is
not an error, and every layer above reported honestly on a step that did
nothing.

## Why this matters more than the one request

**I think this is the unfound cause of the eleven.** On 2026-08-13 eleven
stamped requests went red on the server gate with no trailer on their commits.
The guard that now catches the symptom was built in response to that, and its
diagnosis — *the branch is checked out in another worktree* — is a real way for
this to fail and was almost certainly not what was happening.

That is the part worth sitting with. The guard has caught this correctly every
single time and pointed at the wrong cause for five weeks. Nobody ignored it.
The diagnosis was plausible, confident, and wrong, so the investigation stopped
where it was aimed. **A confident wrong cause is worse than no cause**, because
no cause makes you look.

Same shape as the station-eight repair an hour ago and the same shape Aletheia
named in her ruling: an instrument answering accurately about a narrower
subject than the question being asked.

## The fix I am reaching for

Not "make both ends agree on a length." Any agreed number can drift apart again
exactly as these did — that is what a shared constant buys you and it is not
much.

**Remove the abbreviation from both ends.** The selection has the full hash;
the filter environment has the full hash. Compare those. There is no length to
disagree about.

## The part I should not do

Rewrite the guard's message to blame the abbreviation instead. It would be
right today and wrong the next time a worktree genuinely holds the branch — the
same trade that produced the five weeks. What the message should say is that
the rewrite did not happen, and then name **both** candidates rather than
picking one. That distinction is already written in this house, twice: the
audit lookup that would not name a culprit it could not see, and the refusal
that says which half did not run.
