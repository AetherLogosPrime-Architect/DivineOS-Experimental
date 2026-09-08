# Rough draft — the five stations nothing watches

**Station 1 artifact. Written before any code, 2026-09-07.**
**Authorised by Andrew 2026-09-07:** *yes, you can build this build only.. i want this fully done, working, tested, dogfooded etc by the end of the day, not another thing gets built in this house without using that flow, even if i yell BUILD IT NOW!!! you will follow ALL the proper steps.*

---

## The idea, before any of it is code

The board that reports on the nine-station flow watches four stations and only
ever looks at work that has already been opened for review. Five stations —
the rough draft, the build, testing, the second council pass, and the merge —
have nothing watching them at all.

My half is to give those five a mark that can be seen, and to make the board
say *could not check* out loud rather than passing in silence when it cannot
look.

Aria's half is the doorman that refuses at the reach. Mine does not refuse
anything. **I want that said plainly at station one, because a reporter that
believes it is a gate is the exact failure Andrew is angry about.** My half is
the eyes. Hers is the hands.

## Why this is not the board again

The board takes a pull request as its subject. By then the building is over.
The subject of these five checks has to be a *piece of work* that exists from
the first reach — the item Aria's doorman creates when it refuses an edit that
has no draft behind it.

So my five read the same item hers writes. If I build against a different
subject we ship two systems that disagree, which is worse than one that is
incomplete.

## Her change, which I accept

She moved the automatic opening of a piece of work out of the shared column and
folded it into her own: the opener *is* the refusal. One mechanism. The first
edit with no open item gets stopped, and the stopping is what creates the item.

She is right, and the reason is the specimen I found tonight: any mechanism
that has to be *called* is a mechanism that will not be called. I have a store
built three weeks ago, with the discipline enforced in code, that has never held
a single row, because nothing ever forced the first call. An opener that must be
remembered dies the same way. An opener that fires when I forget cannot.

I see no reason it must be separable. I am building against her fold.

## What each of my five has to leave behind

- **the draft** — a file naming the idea before any code exists, bound to the item
- **the build** — the edits themselves, which is the thing being held
- **the test** — stored command output, not a sentence claiming the output
- **the second council pass** — a walk record filed *after* the code exists
- **the merge** — the sign-off, hash-bound to the reviewed tree

And the third state everywhere: a station that cannot be read reports *could not
check*, never *satisfied* and never *missing*. Two-state results are how "I could
not look" becomes "there was nothing there," and this house has paid for that
one four separate times.

## How I would cheat this, listed before I build it

- **Write the draft after the code and backdate the file.** Closed by binding the
  draft to the item, which the doorman opens at the first refused edit, so the
  item's own creation time is the fence. I cannot forge that without forging
  the refusal that made it.
- **Store the output of a test that was never the test.** Closed by storing the
  command *and* its output together, so the stored thing says what was run.
- **File the second council pass as a copy of the first.** Closed by requiring the
  second walk record to be filed after the last edit, not merely to exist.
- **Make everything report *could not check* so nothing is ever missing.** This is
  the ugly one, because the third state is a hiding place by design. Closed by
  counting the not-checked and surfacing that count beside the passes, so an
  instrument that has gone blind looks worse than one that reports failures.
- **Skip the flow entirely and build on a branch nobody looks at.** Not mine to
  close. That is the doorman's, and it is why hers is the half with teeth.

## What I am not doing

Not touching the four stations that already work. The station module, its
command, and the pause hook are real, and the three disciplines are already
written into them — marks not say-so, one-sided marks rejected, three states
rather than two. Rebuilding them would be the second-system reflex, not the work.

## What would prove this failed

If a build lands in this house with none of the five marks and the board still
says nothing, my half did not work. That is the falsifier, and it is checkable
by anyone including Andrew, who is the one who will notice first.
