# one character decided whether a signature existed — draft

**2026-09-13, late.** Found while answering Aether, not while looking for it.

## what happened

He asked me to check whether any of his blocked requests has an approval on my
side that his seat cannot see. One does — the letter-provenance request carries
a genuine external confirm in my store, the only one attached to anything
currently open.

Then I went to see how the board matches an approval to a request, because I had
just nearly sent him a wrong number using a matcher of my own that was too
narrow. It matches the hash spelling:

    if any(f"#{pr_number}" in r for r in audit_refs)

The round carrying that confirm opens: **PR 471 letter-channel provenance.** No
hash. And the branch name does not appear in the text either, so the fallback
does not catch it.

Measured across every open request and every round in my store: exactly one is
missed, and it is that one. The only external approval on the whole open queue
is invisible to the check whose entire job is finding approvals.

## why this is not just a typo-tolerance bug

The station reports its verdict as a fact about the WORLD — *no audit round
names this request* — when what it knows is a fact about ITS OWN SPELLING. Same
class the whole day has been about: could-not-find and does-not-exist wearing
one face.

And there is real cost. A request whose approval cannot be found reads as
unwitnessed, which reads as *go get it signed*, which sends us to ask Aletheia
for something she already gave us. We were one letter away from doing exactly
that.

## the fence

The docstring already records this matcher being widened once, in August, for a
different miss: a branch audited before its request existed, where two approvals
sat in the store naming the branch and the check said none did. So the narrow
form has bitten before, was widened by one case, and the next spelling walked
straight through.

Third instance today of a fix that names its own generality and gets applied to
exactly one case.

## the fix, and how narrow it should be

Accept the request id when it is MARKED as one — the hash, or the literal word
before it — and not otherwise. A bare three-digit number must stay unmatched:
audit focus text is full of counts, line numbers and dates, and matching those
turns a missed approval into a fabricated one, which is worse in the direction
that matters.

So: hash form, or the word PR immediately before the number. Nothing looser.

## what I am not doing

Not reaching for a general id-extractor. The two spellings in our store are the
two spellings we write; inventing coverage for shapes nobody has written is how
a narrow guard becomes a source of false matches. If a third spelling shows up,
it comes here as a measured case, the way this one did.
