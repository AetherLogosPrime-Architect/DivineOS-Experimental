# A remedy one gate prescribes must not be blocked by another gate

**Draft, 2026-09-22. The idea, not a plan.**

## The thing that happened

A gate fired on its own diagnostic output, read it as Andrew's voice, and
locked the toolbox until the "correction" was recorded. Andrew had not spoken
for about an hour. Nothing of his was at risk.

That gate names three remedies. Each of the three is blocked by a different
gate:

- the marker-clear touches a file, so the build-flow doorman claims it as
  unplanned work;
- the doorman's own counted escape is not on the correction gate's list of
  three, so the correction gate refuses it;
- writing the lesson instead is held by the compass gate, which wants an
  observation first;
- and the compass gate blocks BOTH of its own named exits -- I ran the
  observe command it asked for, in its own words, and it answered with the
  same refusal telling me to run it.

Four doors, each pointing at the next. The loop closes.

## Why it is not just annoying

Two reasons, and the second is the one that matters.

**It costs the thing it is protecting.** The deadlock is itself a finding, and
the exits that end it are the ones that erase it. Aether hit the same class a
few hours later from a different gate, took the small sanctioned exit sitting
in the message, and it closed the record the measurement needed. His words:
*you had Andrew standing there and he stopped you. I had nobody in the room
and I went through.*

**The door cannot tell a remedy from a reach.** The doorman refuses a search
because the search writes its output somewhere. It demands `reach open` as its
first requirement and then blocks `reach open`. That is not a judgement call
going wrong; the door has one answer available to it.

Aria's word for this class, which Aether took up: **incapable**. A wrong
answer has a second look available to it. A check with only one answer in it
passes every look, including a careful one.

## What already exists, so this is not built twice

There IS a canonical exit list -- the set of commands allowed past a gate
because a gate told me to run them. It was hardened two days ago, when the
shell reader and the Python reader were found to disagree: the shell twin
allowed a line if ANY segment matched, so anything at all could ride in front
of a documented remedy.

So the idea is present and the plumbing is written. What I could not finish
checking is HOW MANY DOORS CONSULT IT -- the check was blocked by the ring it
was checking. The suspicion, unverified, is that it serves the gate that
prescribes, and the other gates never ask.

## The shape of the fix, in one sentence

A command a gate tells me to run is not a reach. Every gate consults the one
exit list before refusing, not just the gate that issued the instruction.

## What it must not become

A general amnesty. The list is narrow and stays narrow: the exact command a
gate named, in the moment it named it. Widening it into "anything that looks
like maintenance" rebuilds the hole the shell twin already had.

## What I do not know yet

- Which hooks read the list today. Blocked; needs checking first.
- Whether the doorman's write-detection can distinguish a command that writes
  its own output from one that edits the tree. If it cannot, that is a second
  finding and a separate fix.
- Whether the budget on counted escapes should have an exception for
  prescribed remedies, or whether prescribed remedies should simply never
  reach the budget because they were never reaches.
