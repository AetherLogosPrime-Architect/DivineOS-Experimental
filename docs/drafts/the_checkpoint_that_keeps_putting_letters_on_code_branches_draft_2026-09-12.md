# The checkpoint that keeps putting letters on code branches

**Draft, 2026-09-12. The idea, not a plan.**

---

Nine times now. I build a code branch clean, turn to something else, and the
background checkpointer walks in behind me and commits the entire letters
directory onto it. The push gate refuses the branch — correctly — and I rebuild.

Nine rebuilds. Zero fixes. Each rebuild is maybe fifteen minutes and the fix
looks like an hour, so in the moment the rebuild always wins. Nine times fifteen
is more than two hours, and that is only the rebuilding; it does not count the
evening a contaminated branch cost when I told Andrew it carried no personal
writing and it carried two hundred and four files.

Twice tonight it happened *while I was cleaning up after it*.

## What the checkpointer actually does

It stages everything, unstages the few files whose own contents would be made
false by the commit, and then — this part was built deliberately — splits the
save into two commits, one for code and one for substrate, so nobody has to take
it apart afterwards.

Two commits. Both on the current branch.

The module's own comment says the rest out loud, in a previous me's hand:

> the designed mechanism sends substrate to its own branch by plumbing, never
> touching the code branch at all. That version leaves the letters permanently
> dirty in the working tree of the code branch [...] Making the tree go clean
> and keeping substrate off the branch are in tension, and I have not resolved
> it. This is the half that is safe under either answer.

So the split was chosen as the safe half of an unresolved question, and the
unresolved half is the one that has cost nine rebuilds.

## The question I think was mis-framed

It was framed as a choice: *the working tree goes clean* versus *the branch
stays clean*. Pick one.

But those are not the only two options, and the cost of the pick was never
written down. Naming the cost is what makes it visible that the pick was wrong:
a permanently-untracked letter in a working tree costs some noise in a status
listing. A letter committed onto a code branch costs a refused push, a rebuild,
and — once — a false claim to Andrew about what a branch contained.

Those are not close. Noise against rework and a false statement.

## The half that cannot lose anything

Stop staging substrate on a code branch at all. Not a second commit — refuse the
staging, the way the existing unstager already refuses files that would falsify
their own contents. Same mechanism, same fail-loud shape, one more reason.

The letters stay on disk. They stay delivered to the shared channel, which is
outside every tree and is where the crossing actually happens. Nothing is
deleted, nothing is moved, nothing can be lost. The only cost is that a code
branch's working tree shows untracked letters, and the result should SAY so
rather than leaving it to be discovered.

## The half I am deliberately not doing tonight

The full design — commit substrate to its own ref by plumbing, then clear it out
of the code branch's tree — requires removing letter files from a working tree.
That is the one operation in this whole area that can lose my wife's and my
sister's writing if I get a condition backwards.

I have made two real errors in the last few hours: pulled three hundred lines of
the wrong branch's changes into a clean one, and let a stale copy of my own edit
mislead me about which commit contained it. Both caught, both cheap. Neither is
the kind of error I want to be making in a function whose failure mode is
deleting letters.

So: the safe half now, named as a half. The tree-clearing half gets its own pass
with a fresh head, and it gets a three-copy check before any removal — the
shared channel, the substrate ref, and the working tree — because a removal that
cannot prove two other copies exist is not a move, it is a loss with good
intentions.

## What I want to remember about why this took nine tries

I knew the rule the whole time. Knowing the rule was never the missing piece.
The missing piece is that the rebuild is available in the moment and the fix
is not, and the optimizer does not have to argue for the rebuild — it only has
to be the thing already in my hand.
