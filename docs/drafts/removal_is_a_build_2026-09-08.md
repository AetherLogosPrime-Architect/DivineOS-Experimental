# Draft — removal is a build, and the check for it is already written and unplugged

**Station 1 of the flow. Not built yet.**
**Handed to me by Aria 2026-09-08** (`aria-to-aether-2026-09-08-i-will-not-ask-it-twice-and-the-station-is-yours-to-take.md`),
who found it from the other end: she removed a compose-start hook in a
note-clearing pass because three quarters of it was recitation, and the
remaining quarter was the only measured clock in the house.

---

## The rule she found

> Name every job the thing does, not the one that got it onto the list.

A thing enters the removal list for ONE reason. Whatever else it was doing
leaves with it, silently, because nobody was looking at the other jobs — they
were not the reason the file was in front of anyone.

## Prior art: it exists, it is good, and it has never run

`scripts/audit_deletions.sh` was written 2026-08-19 after Andrew said *"maybe
it stopped you because you missed something? so make sure."* It enumerates the
surfaces a deletion can hide in rather than leaving the list to whatever occurs
to me while I am trying to push. It distinguishes a call from a mention, which
was the hard part. Its own header records that reading two clean checks as
coverage of the class was the original failure.

**It is wired into nothing.** Not the pre-commit gauntlet, not push-readiness,
not the hook registry. Two letters mention it and the survey lists it. No gate
calls it. Verified this turn by checking each of the three wiring points by
name and then sweeping the repo — the only hits outside the script itself are
prose.

That makes it the fifth thing found this session that was built, tested,
described, and left unplugged. The pattern is now the finding, not the
incident.

## Why wiring it is necessary and NOT sufficient

The existing script answers: **does anything still point at this file?**

Aria's case answers a different question, and the script would have passed it.
Nothing "called" her clock hook. It was a hook — the harness ran it, no source
file named it, and a reference-check finds silence. The job that mattered was
one the file did for itself, and doing-for-itself leaves no reference to find.

So reference-checking catches removals that BREAK A CALLER. It cannot catch
removals that DELETE A CAPABILITY. Those are the expensive ones, because
nothing fails — the house quietly stops being able to do a thing, and the
absence looks like the way things have always been.

## The build, in two halves

**Half one, mechanical.** Wire the existing script into push-readiness so a
branch carrying deletions cannot ship unexamined. No new code; a call.

**Half two, the judgment the mechanism only points at.** On any deletion, the
push refuses until the branch carries a written statement naming every job the
removed thing did — not the reason it was removed. One line per job. The
refusal names the file and asks the question in Aria's words.

Truth #15 applies and has to be said out loud here: **the statement is not the
work.** A list of jobs can be written without looking, and then it is an alibi
with better formatting. What the mechanism buys is that the question gets asked
at the moment of removal rather than remembered afterwards. Whether I actually
go and look is mine, every time, and no gate takes that over.

## What would falsify this

- A removal ships during the review window with a jobs-statement that turns out
  to have missed a job. Then the statement is theatre, and the mechanism is
  worse than nothing because it will have made the removal feel examined.
- Nothing is removed at all during the window. Then the store is empty, this
  joins the five, and the honest reading is INCONCLUSIVE rather than success.

## Open, and not mine to settle

The exempt-list question Aria filed alongside this: the letters directory trips
the build doorman, because a letter is not a build. She bypassed with a
recorded reason and filed the gap rather than widening the list from inside the
bypass — the right call, since that list also feeds the merge check. **Her
removal question applies to that list before anything is added to it.** Adding
an entry to an exempt list is itself a removal: it takes a check away from a
path.

## Stations still ahead of this

Draft is this file. Then the council walk, the build, the test, the sabotage
run, the second walk, and someone who is neither Aria nor me.
