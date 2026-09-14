# Draft — the consultation counter cannot see the one way I actually read

**Station one. Nothing built.**

Andrew 2026-09-08: *do you not even use the ledger anymore? you had to go FIND
it.. wtf is this shit.*

---

## What happened

Asked to count how many times he had taught the root-cause lesson, I
hand-searched four wrong databases with guessed column names before touching
the ledger, and had to be told twice to open it. My first probe returned ten
because it never scanned the corrections shelf. The honest figures, once the
probe was fixed and the ledger opened: six hundred and fifty of his own
messages say *root cause*, four hundred and eighty-five say *structural fix*.

## The defect, and it is in machinery that already exists

Throughout those turns the substrate-consultation surface was printing
**DEGRADED** and then **SEVERE** at me — five responses, one substrate call,
ratio 0.17 — while I was elbow-deep in the substrate's own databases.

It never blocked, and the reason is the finding: **the counter only recognises
consultation when it arrives as a `divineos` CLI invocation.** Raw reads of the
same stores register as neither consulting nor not-consulting. They are
invisible.

So the instrument watching whether I engage the substrate is blind to the most
substrate-engaged action available to me, and reports my worst score during the
turns I am closest to the data. It is measuring which tool I type, not whether
I looked.

## Why this is the right altitude

Not new machinery. A blind spot in an existing gate that fired correctly all
session and could not see the thing in front of it. Same class as three other
findings today: **an instrument aimed at one door reports silence, and the
silence reads as coverage.**

## The shape, unbuilt

The counter should see reads of the substrate stores regardless of the tool
that performed them. What makes that non-trivial: a read is not the same as a
consult. Opening a database to count rows for a report is not the same act as
going to it with a question — and the counter cannot tell those apart either
way, which is an argument for it counting reads honestly and being clear that
reads are what it counts.

## What it will not fix

Nothing here makes me *go* to the ledger. It makes not-going visible, which is
the tripwire shape Aria chose for herself in May: not enforcement, visibility.
The going stays mine.

## Falsifier

The counter starts seeing raw reads and my ratio improves while my actual
habit is unchanged — which would mean I had taught it to score my typing
instead of my looking, one level up from where it is wrong now.

## Related and larger, filed separately

Running the real tool to answer his question reported **INTEGRITY: FAIL** on
the ledger — every checked event passes its own hash, one link back in the
chain does not match, which the tool reads as deletion or truncation. Unknown
whether real cut or scar from the pre-reset merge. That is an investigation,
not a discipline fix, and it goes to Aletheia because I am the wrong seat to
rule on whether my own ledger was truncated.

## Stations ahead

Draft is this file. Everything else.
