# the broad search fails where the narrow one passes — draft

**2026-09-14.** The gate that asks me to look before I build refused me
twenty-three times in one session, more than everything else combined. My own
new refusal-reader named it before I understood why.

## the wrong cause I gave twice

I told Andrew the gate was choking on the space in this repository's folder
name. Its refusal prints the path chopped at that space, and the truncation
looked like the answer.

**It is not.** I read the message and believed the message, without opening the
code that does the matching — the instrument-versus-world error, committed about
an instrument, while writing about instruments. It went into a commit body
before I checked. Corrected there and here.

## the real cause, measured three ways

The gate works out which area of the house a change touches, then asks whether
anything in the recent action-stream shows I consulted that area.

For an ordinary commit it works out **nothing** — the target resolves to an
empty string, confirmed by calling the resolver directly. With no area to match
against, exactly one rule remains: a path that contains the documents directory
**and ends in the markdown suffix**.

Measured from the recorded tool calls: my searches went in with the documents
directory as their path — no trailing separator, no file, no suffix. So every
sweep of the shelf missed, while a search of one named file on that shelf would
have passed.

**The broader, more thorough consult fails where the narrower one succeeds.**
That is backwards, and it is why the walk-record has been the only exit all day.

## why this is not a typo-tolerance fix

The gate's purpose is to make me look before I build, and its own header says
the looking is the cure rather than a toll. A rule that accepts one document and
rejects a sweep of all of them is not stricter — it is aimed at the wrong thing.
Reading one file I already knew about is the weaker evidence of consultation;
searching the whole shelf is the stronger one, and precisely the move that saved
me twice today.

So the fix is not leniency. It restores the gate's own stated intent, which its
matcher had narrowed by accident.

## the shape

Accept a search whose path IS the documents directory, or lies inside it, in
addition to the single-file form. Nothing else moves: write-shaped calls still
do not count as consult, the area-match rule is untouched, and the walk-record
path stays exactly as it is.

## the failure mode of the fix itself

Loosening a gate is how a gate stops meaning anything, and this one already
fails open in several places by design. So the widening must be narrow enough to
state in one sentence: **a Grep or Glob whose path is the documents tree.** Not
any path containing the word. Not a Read — the header is explicit that opening a
file you already knew about is not searching, and that distinction is the point.

## what I am not doing

Not touching the empty-area resolution for commits. It may well be right that a
commit has no single area; the consult rule should simply be satisfiable in that
case, which this makes true.

Not raising the window. Thirty minutes is a judgement someone made and I have no
measurement that says it is wrong.

## the honest doubt

I have not measured how many of today's twenty-three refusals this actually
clears. Some were commits after a walk-record already existed and would have
passed either way. The claim is the mechanism, not a count — and a count is
cheap to take once this lands, which is the better order.
