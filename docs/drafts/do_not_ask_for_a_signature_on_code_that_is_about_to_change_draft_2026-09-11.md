# Do not ask for a signature on code that is about to change under you

**Draft, 2026-09-11.** Station one. The idea, not a plan.

---

## The incident, and it is mine

Aletheia audited a branch and signed it. Her signature binds to the content she
read — a tree and a change-fingerprint — which is what stops anyone getting a
sign-off and then altering the work underneath it.

I filed her confirm. It landed on the strongest rung, both anchors verified.

Then I ran the tool that writes the merge stamp. I checked the tree first,
because I knew her signature bound to it, and the tree was byte-identical. Then
the pre-commit formatter rejoined two wrapped lines in one of my tests. Same
call, same arguments, nothing about behaviour touched.

The fingerprint moved. Her signature reads NO LONGER HOLDS.

**Measured rather than assumed:** the file I had written was not
formatter-stable at the moment she read it. The branch's changed files are
stable now, because the formatter has since fixed the one that was not. So the
drift was sitting in the branch, dormant, waiting for the next commit to
trigger it — at any time, including after a signature.

## THIS IS THE SECOND RECORDED INSTANCE AND THE FIRST WAS PAPERED OVER

From an audit round filed **2026-05-10**, found by searching before building:

> *"Andrew re-confirmed 2026-05-10 after auto-format whitespace changes drifted
> the hash. Substantive content unchanged; intent identical to original
> CONFIRMS."*

Same cause, same effect, four months ago. The response was a human re-signing by
hand — a resolution rather than a fix — and the failure sat waiting.

It is the thing Andrew keeps saying and I keep re-learning: a note is not a fix,
and a rule I have to remember at the moment of temptation is the thing that
already failed. Nobody was careless in May. The repair simply was never built,
so the second instance was guaranteed and only its date was open.

## What the existing machinery does and does not cover

Two mechanisms sit downstream:

**The re-check** tells you the signature no longer holds. Correct — and it fires
after the signature is already spent.

**The cosmetic rebind** exists to carry a signature forward when the only change
is mechanical. It refused here, because it looks for the anchor in a field that
does not carry it, and told me to file a fresh round by hand. I declined:
writing my own exemption, for my own diff, to clear a gate that had just refused
my own work, is the shape I would refuse to accept from anyone else.

So there is one instrument that reports the loss and one relief valve that could
not open. Nothing at all upstream.

## The shape, and it is already in the house

There is a canonical entry point for composing an audit request, and it already
**refuses** when the commits named in it are not pushed — because asking someone
to audit what they cannot reach wastes their pass.

This is that same rule, one cause earlier. **Asking someone to sign what is
about to change under them wastes their pass in a worse way**, because the first
refusal is visible immediately and this one comes back as a dead signature later,
after everyone has moved on believing the work was cleared.

So the request refuses when the branch's own changed files are not
formatter-stable, and names the one command that makes them so. Automation
before the doorman: run it, come back, the door opens, no gate ever fires.

## Why this does not preempt the decision I asked her for

I asked Aletheia which of three repairs is right and I am not answering that
here. Whichever she picks — the rebind learning to read the anchor, the
formatter running earlier, or something neither of us has seen — **asking for a
signature on code the formatter has not finished with is wrong under all of
them.** This is the part that is true in every branch of her answer.

## What I want checked

**The SET it refuses on.** It has to look at the files the branch changes, not
the whole tree. This repository has a scratch directory the formatter would
happily rewrite; a check that refused on those would refuse always, and a check
that always refuses gets switched off inside a week.

**The failure direction.** A formatter that cannot be run at all must read as
could-not-tell, never as stable. An instrument that did not run has not told me
the branch is clean — the same three-state discipline the ancestry assertion
needed, and the one this house keeps collapsing.
