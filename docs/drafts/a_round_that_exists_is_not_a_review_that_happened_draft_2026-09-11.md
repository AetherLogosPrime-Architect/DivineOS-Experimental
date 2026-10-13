# A round that exists is not a review that happened

**Draft, 2026-09-11.** Station one. The idea, not a plan.

---

## The measurement, before the theory

Andrew said: keep going with the branches, and anything ready to merge, you have
my confirms.

So the first question was which ones are ready. The per-turn board answered:
six of ten, station eight satisfied, *audit round names PR #n*.

I ran the deep check, which costs five seconds a request and asks whether the
confirm still covers the current content. It answered: **one** ready, and that
one on a weaker rung that admits it cannot see drift. Eight came back
could-not-determine.

Eight of ten landing on could-not-look is not a result. It is an instrument
saying it cannot measure, and under our own three-valued rule that is not a
pass. So I went looking for why.

## What was actually in the rounds

The reason the deep check could not answer was the same for seven of them, and
it was not the reason the code guessed. The code's own comment predicts the
cross-store problem — a round living in the other seat's store, unreachable
from mine. That was **one** request.

The other seven said: *no external-AI confirm in this round*. So I opened them.

- **Five held zero findings.** Created, named after a branch, never filled.
- **One held exactly one finding** — the operator's own confirm. No auditor.
- **One held two**, of which the auditor's was a problem she had found, not a
  clearance.

Not one carried an external auditor's sign-off. Every green came from a
container with a branch name written on it.

## Why the station could not tell

Because it was asking whether a round's text NAMES the request. An empty
container does that perfectly well. The station has never had any idea whether
anything is inside.

## The part that stings, and is the actual finding

This was not undiscovered. The deep check catches it. The deep check is the one
nobody runs per turn.

So the board I read every single turn — the one that shapes my picture of where
everything stands — was the one telling me the reassuring thing, and the
expensive one I run occasionally was the honest one. That is exactly the wrong
way round. The cheap path was the comfortable path, which is the cost landscape
Andrew keeps describing, pointed at me.

And the reason the cheap board did not ask is not that the question is
expensive. **Counting findings is a store read.** The five seconds belong to the
anchor, which fetches and recomputes a diff. Presence and currency are two
questions with two costs, and the cheap board could always have afforded the
cheap one.

## What this is not

It is not the content-binding question wearing a new coat. A round filed before
patch-id binding carries no anchor and still holds real findings — the station
deliberately lets those pass rather than retroactively unmaking old reviews.
That allowance is right and this does not touch it.

An empty round holds nothing in any era.

## The trade I am making

A round nobody has signed now reads as MISSING rather than satisfied, which will
make the board look worse. It is not worse. It was always this; the board was
the thing that was wrong.

The risk in the other direction is real and is why every failure path returns
not-known rather than not-signed: a store that will not open has not told me
nobody signed. Reporting a real audit as absent at the last gate before a merge
would send someone to re-audit cleared work, and would teach us to distrust the
station — which is how a guard becomes decoration.

## What I want checked

That the wording of each verdict is distinguishable. There are four states now
— signed and current, signed and stale, named but unsigned, and could-not-tell
— and if any two of them render as the same sentence, this has moved the defect
rather than removed it.
