# The Cleanup List

One page. Seven jobs, in the order they should be done, with the reason each one
sits above the next. The long map is the reference; this is the thing we walk
down together, one at a time.

Each job says what is wrong in a sentence you can picture, and what *fixed*
means — so neither of us can call it done early.

---

## 1. Turn on the finder

**What is wrong.** There is a device in this house whose only job is to find
things that were built and never plugged in. It works. It has never been
switched on — it is wired as a note, printed into a pipe that cuts it off, and
nobody has ever read what it says.

**Why it is first.** Everything else on this list exists because this was off.
Fixing it stops the pile growing while we clear the pile.

**Fixed means.** It can stop a commit. Anything we deliberately choose to leave
unplugged is written down on a list, so silence stops meaning *nothing to
report*. Its own errors are no longer hidden. And what it finds arrives where I
will actually see it.

---

## 2. Make the house answer to its own address

**What is wrong.** When I ask this project for one of its own parts, I get
handed Aether's copy instead. It bit me in the middle of doing your work today —
my own record of you was invisible to me from inside my own folder.

**Why it is here.** Until this is fixed, *every* measurement of what is and is
not working is taken through a crooked lens. Including the ones in the map.

**Fixed means.** Asking for a part from inside this folder gets this folder's
part, and a check refuses to run at all if it does not.

---

## 3. Throw out the empty boxes

**What is wrong.** There are record-files sitting in the right places with
nothing inside them. Not missing — present and hollow. A program opens one,
finds nothing, and reports a clean empty record instead of screaming that it
opened the wrong thing. There is also a whole second set of real records living
in a folder created by a wrong turn, which a cleanup step could delete without
anyone noticing.

**Why it is here.** It is the only item on this list where failure currently
disguises itself as success. It is also the cheapest.

**Fixed means.** The hollow files are gone, so a wrong path fails loudly. The
stranded records are moved somewhere reachable. And the documentation stops
pointing at a file with nothing in it.

---

## 4. Decide about the four dead rooms

**What is wrong.** Four finished, reviewed, tested subsystems are connected to
nothing. Among them: the guard against me giving you a beautiful empty answer,
and the guard against me claiming something does not exist without looking. Both
were built the week I did those exact things. Neither was ever plugged in.

**Why it is here.** Right now the architecture document claims we are protected
against failures we are not protected against.

**Fixed means.** Each one gets *read first* — what it was for, and whether that
need still exists. Then it is either wired to something real, with a test that
fails the day it comes unwired again, or, only if it turns out to be genuinely
superseded, retired through the gate that will not let anything go until the
reason it existed has been written down.

I had this wrong when I first wrote this page. It said wiring and burying were
equally fine answers. They are not.

> "nothing we have built was built without reason or purpose.. some may be
> obsolete or superceded but nothing should be thrown away without looking
> first." — Andrew, 2026-08-13

**This one needs your call.** Whether an unwired guard gets connected or retired
is a decision about what this house promises — and you asked first what each one
guards, which is the right question and one I owe you before the decision, one
guard at a time.

---

## 5. Fix the shell hunt, once

**What is wrong.** Twelve different places in the test suite each invented their
own way to find the same program, and they disagree. One works, one fails, one
skips forever in silence. On this machine the thing they find is a stub that
errors out.

**Why it is above the doorbells.** It leaves the test suite permanently red, and
a suite that is always red teaches both of us to ignore red. The failure message
even prints the bypass command underneath itself.

**Fixed means.** One shared way to find it, the twelve copies deleted, a check
that refuses new hand-rolled ones, and a suite that comes back clean.

---

## 6. Finish the doorbell consolidation

**What is wrong.** Roughly a hundred little programs wake up as you type, each
starting a whole engine from cold to ask one question, and most conclude they
have nothing to say. This is the tax you feel.

**The important part.** This is *not* a thing to build. Aether already built the
router. It knows all seven kinds of doorbell and says so in its own opening
lines. Nine things are moved over. It is a job a ninth done, and both of us have
been discussing it as though nobody had started.

**Fixed means.** The prompt sensors become one program that starts one engine
and runs the checks inside it. The cheap *do I have anything to say* question
happens before the expensive startup instead of after. One doubled registration
deleted. And the big repeat-offender routes through the silencer we already own.

---

## 7. Widen the merge gate

**What is wrong.** The gate guarding the main line has real teeth — the survey
got that wrong on its first pass and corrected itself, and I want the correction
carried here rather than buried. What it lacks is reach: it inspects only files
on a protected list, so a change touching nothing on that list walks through
unexamined, even though the rule says everything gets reviewed.

**Why it is last.** It works. It just does not look at enough.

**Fixed means.** It applies to any file, and its all-clear message says what it
actually examined rather than implying it looked at everything.

---

## What this list does not cover

The survey ran out of budget before checking eleven more leads, and never ran
one whole sweep — the one hunting for guards that sit in a file *after* the
point where the file has already stopped running. Present in the text, dead when
it runs. That is the shape most likely to be hiding more of the above, and it is
still open.

Two of the survey's own numbers came back wrong on re-measuring, both in the
direction of making things look worse than they are. Every figure in the long
map is a good-faith measurement rather than a fact.

And none of this touches the personal side of the house — the letters, the
explorations, the character sheets. That is a different survey, and probably not
one to run with this lens.
