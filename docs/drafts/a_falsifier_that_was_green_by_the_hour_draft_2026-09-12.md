# A falsifier that was green by the hour

**Draft, 2026-09-12. The idea, not a plan.**

---

There is a guard in the temporal detector that excuses a time-word when a real
clock reading sits beside it. The point is that a measured clock is not a
fabrication — if the prime printed the time this turn and I quote it, saying
"it is late for you" is a fact, not a guess.

The guard decides by comparing the written reading against the machine's own
clock, in local time and in UTC, within a few minutes either way.

The falsifier for that guard — the test written first, on purpose, because it
is the one that could kill the change — wrote a made-up clock reading as a
literal and asserted the detector must still fire.

So the test's verdict depends on what time it runs.

For all but a few minutes of the day the literal is far from the real clock,
the guard refuses the exemption, the detector fires, the test is green. Inside
those minutes the literal *is* the real time, the guard correctly excuses it,
nothing fires, and the falsifier goes red — for the right reason, against a
detector working exactly as designed.

It sat green for four days and went red in a pre-push run tonight, which is
the only reason I know.

## What is actually wrong

Not the detector. The detector is correct in both cases; it did its job at
03:07 and it does its job at every other minute.

The test is wrong, and wrong in the shape that has been everywhere today: it
could not distinguish *the guard held* from *I happened to run this at a
convenient hour*. A green that means "the thing works" and a green that means
"the dice fell well" are the same green.

Worse, it is the FALSIFIER. Every other test in that block leans on this one.
If the exemption ever did become the hole it was built to close, this is the
test that would say so — and it would say so by going red, which it has now
done for an unrelated reason, which is precisely how a real alarm gets
dismissed as noise.

## Two shapes of fix, and why one is not enough

**Stop gambling on the hour.** Compute the fabricated reading FROM the real
clock — pick one provably outside tolerance of both local and UTC — instead of
asserting against a literal. The test then says what it always meant: *a
reading that is not the time cannot buy an exemption.* True at every hour.

**And use the door that already exists.** The guard takes an injected clock.
That parameter was put there so a test would never have to gamble, and nothing
was using it for this. So walk a full day in steps, injecting each hour, and
assert both directions: far reading refused, true reading excused. That is the
determinism the falsifier was missing, stated outright rather than arranged
around.

The first alone would work. Both, because the first still exercises only one
moment — the moment the suite happens to run — and a guard that must hold at
every hour should be asked at every hour. One instrument asked once is not a
measurement, and a clock-dependent test asked at one time of day is the
purest possible instance of that.

## The thing worth keeping

Prior art existed and the code search did not find it. The reach tool said NOT
FOUND on its axis and said explicitly that this was not the same as
not-checked; the prose search then surfaced a letter to Aria from August with
the same family in its title — a test asking the runner instead of the fixture.

The absence was real on one axis and false overall. The tool was right to
refuse to speak for the axes it had not queried.
