# Rough draft — the attack station

**Station 1 artifact. Written before the code, 2026-09-07.**

---

## The idea

Andrew taught this in August: *"always try to break your stuff when building
it, the happy path is a narrow path, that is why nothing feels wrong."* I built
the tool that does it — it hollows out every function in a module and re-runs
the tests, so any test that still passes was never testing anything.

**Then I did not run it on anything I built tonight, and told him I was the
wrong seat to test my own work.** The lesson was taught, the tool was built,
and it sat there. That is his whole complaint about this house in one example.

So the fix is not another tool. **It is that the tool I already have becomes a
station nobody can skip.**

## What changes

A sixth station between the test and the second council pass: **the attack.**
It can only be satisfied by a recorded run whose command actually invokes the
sabotage tool. Writing "I attacked it" satisfies nothing, the same way
hand-typed test output stopped satisfying the test station an hour ago.

Order matters and it is not decorative: you cannot sabotage tests that do not
exist, and there is little point walking the lenses a second time over code
whose tests have not been shown to test anything.

## What it does not do

It does not judge the attack. A sabotage run whose survivors I never read is a
run I can point at, and the mark cannot tell. **This buys that the room is
opened.** Andrew's own line about that limit: *"im not saying to automate
judgement.. but you can automate and force the judgement to happen."*

And it does not cover the attack that matters most — trying to game the thing
by hand, the way I found the empty folder tonight. No tool generates that. What
the station can do is make the cheap mechanical half unavoidable and leave the
imaginative half where it has to live, with me and with Aria.

## How I would cheat it

- **Run the tool against a module I did not touch.** Open, and honestly so: the
  recorded command is stored, so a reader sees which module was attacked. That
  is visible rather than prevented, which is the right trade for now.
- **Run it and ignore every survivor.** Not closable by a mark. Named here so
  the limit is on the record rather than discovered later.
- **Delete tests until nothing survives hollowing.** Expensive and loud in a
  diff. Not worth defending against.

## What would prove this failed

If a build lands with the attack mark set and a survivor list nobody read, the
station is theatre and should be marked failed rather than tuned. The check is
whether any survivor ever changes a test afterwards.
