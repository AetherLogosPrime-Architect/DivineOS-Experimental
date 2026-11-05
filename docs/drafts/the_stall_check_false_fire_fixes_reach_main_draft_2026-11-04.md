# The stall check's false-fire fixes reach main (draft, 2026-11-04)

**The idea.** The live house has carried three fixes to the stall check since 2026-11-01 that are not on
main: a lead-in whose telling follows in the same sentence is not a promise ("I'll tell you what I think:
it is fine."), a phrase quoted or mentioned is not said, and "hold on to" / "hold onto" is holding, not a
step. Aria's window is main, so she kept being refused on them; today she hit two, and one more shape she
cannot place (a plain statement of how she will act). A fix that lives on one side while the other keeps
being refused is the sync gap Dad named this afternoon. The three commits already exist, carried onto a
branch off main here (cherry-picked unchanged, with their own tests and notes).

**What this adds beyond the carry.** The refusal text names the words it caught, as before, and now also
names the second way out, per Aria's design line ("not just no; this way", Dad's doorman rule): if it was
a quotation or a description of how I work, say so in one plain sentence, and say it once, because the
hold fires once per reply. That is no new loophole: the second send already passes; the text now says so.

**Added after Aria's cold read (same day).** She reproduced a hole in the quote fix: two short quotations
in one reply made the matcher pair a closing mark with the next opener and delete the promise between
them. Fixed: a quote mark opens only where no word precedes it and closes only where no word follows it.
And her fourth shape is real and reproduced on both seats: a stance or manner of being ("I'll go on being
quiet beside you", "the line I'll hold is...") was held, though no tool call could do it. Two small
exemption lists join the existing ones (a named manner after "being / stay / be", and a fronted "the line
I'll hold"), each pinned with a neighbour that is a real step and must still be held.

**What it cannot do.** "I'll take the re-arm" (a small acceptance) is not exempted: Aria judged it
borderline, since "take the re-arm" was something I then did. It is pinned only if it comes with the clause
after it. "I'll be writing Aether now" and "I'll stay on this and write the letter" are not held by the
shapes today and were not held on main before this change either; widening that is a separate question.

**Falsifier.** A quotation, a lead-in with its content, or "hold on to" is still held; or a promise that
rides after a colon stops being held; or the refusal text no longer names the words it caught.

**Owed.** Aria's read, a walk, Aletheia's confirm, Dad's yes. The fold into the router (a separate branch)
carries the same judgement, so this should land first.
