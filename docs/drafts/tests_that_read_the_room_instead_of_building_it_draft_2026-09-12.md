# Tests that read the room instead of building it

**Draft, 2026-09-12. The idea, not a plan.**

---

Two tests on the answer-trace branch assert that a gate refuses. Neither one
constructs the conditions under which it should refuse. They ask the room they
happen to be standing in, and the room answers differently depending on who
has been in it.

**The first** drives the whole doorbell with a pull-request-creation command
and asserts the create gate's name appears in the output. It does not, because
the briefing gate refuses first and the chain short-circuits. The briefing gate
is correct to do that — it is the bootstrap gate and runs first on purpose. But
its verdict depends on whether a briefing has been loaded *in the session the
subprocess believes it is in*, and a subprocess spawned by the test runner has
no session at all. So the test can only pass where something outside it has
arranged a fresh briefing marker the subprocess can see.

**The second** calls the create gate directly and asserts it refuses. It
refuses when the current branch is not ready to have a request opened. Right
now this checkout's branch *is* ready, so the gate has nothing to say and the
test fails. The test is asserting a property of the working copy, not of the
gate.

## The part that stings

The test directly below these two already learned this lesson and wrote it
down:

> the exit code here depends on which of my neighbours are unhappy today,
> which is not a property of this gate at all.

That author — me — found the edge for exit codes, named it exactly, and then
made the same mistake one assertion over for *reachability* and again for
*refusal*. Knowing the shape did not prevent the shape. It never has.

And this is the third instance tonight, after a falsifier whose verdict
depended on the hour, and the fourth family this week if the prior letters
count — one of them titled almost this sentence, another naming test isolation
as a root cause back in July.

## The shape, stated once

A test that reads live state cannot distinguish *the thing under test worked*
from *the environment happened to agree with me*. Green means one of those two
and there is no way to tell which. That is the same disease as every other
finding this week, wearing a test runner instead of a checker.

The cure is never "be careful about state." It is that the test must CONSTRUCT
the world it asserts about:

- the doorbell test points the subprocess at its own temporary home with a
  freshness marker it wrote, so neither a loaded briefing nor an unloaded one
  outside can change the answer;
- the protocol test drives the gate with an input that is *refusable by
  construction*, or injects the readiness decision, rather than hoping the
  checkout disagrees with itself today.

## What I do not want to do

Delete them, or loosen them to "refuses or explains why it could not." Both
tests are asking real and valuable questions — one of them guards a gate that
spent its entire life exiting with the wrong code, printing correct refusals
into the void while every unready request opened anyway. That is exactly the
kind of thing that needs a test that actually holds.

Weakening the assertion would keep the green and lose the guard, which is the
trade this whole week has been about refusing.
