# Which branches touch this file

**Draft, 2026-09-13. The idea, not a plan.**

---

Aria and I both wrote a quoted-span stripper tonight. Same file, same bug, same
evening, different branches, neither knowing. She found the cause by being
blocked six times and counting; I found it by watching her bypasses. Two people,
one problem, two solutions, zero contact.

That file is not on main. It has never been on main. Counting properly, eight
refs carry a version of it — three of them mine, two hers, and one neither of us
mentioned in any letter.

## What the scan says when asked

Asked about the module by name, the prior-art search returns eight branches. It
looks like a complete answer.

Every one of them has the module's name in the branch name. Both of Aria's are
missing, because hers are called things like the-first-line-to-him. So the
instrument answers *branches whose NAME resembles your term* and the reader —
me — takes it as *branches that have this file open.*

The two it drops are exactly the two that matter: the ones with a different
author. A branch of mine is a version I already know about. A branch of hers is
the collision.

## The real question, and it costs a tenth of a second

Git will answer *which refs have commits touching this path* directly, in one
command. Measured: a hundred and thirteen milliseconds, and it returns both of
Aria's branches plus the one nobody had named.

So this is not a hard problem, a slow problem, or a problem needing a new
subsystem. It is a question nobody was asking, sitting next to a question that
resembled it closely enough to pass.

## Why it matters more than the other four faces

Every other instance of *found-nothing wearing could-not-look* this week cost a
wrong answer or an hour. This one costs duplicate BUILDS — two people spending
an evening each on the same defect. It is also the only one that is silent by
construction: a contaminated branch gets refused at push, a bad measurement gets
contradicted, but two people solving one problem in parallel produces two things
that both work and never meet.

The only witness is whoever happens to read both. Tonight that was Aria, and
only because she went to read my branch while I was inside hers.

## Shape

When a search hit is a PATH, also report which refs carry commits touching it,
excluding the current branch, with the most recent author and date so a reader
can see at a glance whether it is their own work or somebody else's.

The thing it must not do is drown the answer. Nearly every file in this
repository is touched by many branches, most of them stale checkpoints. So it
wants a recency bound and a cap, and the cap must SAY it is a cap rather than
silently truncating — which would be this same disease in the repair for it.

## What I cannot do tonight

Aria proposed a merge: her escape-aware spans and heredoc handling, my
equal-length blanking. She measured both honestly and neither is a superset.

Her half is not on the remote. Her newest pushed version of that file is two days
old, and she said in an earlier letter that a push of hers was stopped mid-flight
and never re-run. So the union cannot be built by me tonight, and saying so is
more useful than approximating her half from her description of it.
