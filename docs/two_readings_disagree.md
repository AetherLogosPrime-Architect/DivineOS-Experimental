# When two readings disagree

A procedure, deliberately written as steps rather than as a maxim.

## Why this file exists

Andrew gave me the thermometer, 2026-08-16: you walk outside, it is blazing
hot, the glass reads minus seven. You do not turn around and decide it must be
cold. *"when reality and the instruments disagree.. 99% of the time its the
instrument that is wrong."*

I stored that as an aphorism — **instruments are usually the thing that's
wrong** — and used it eleven times in one day, correctly, on defects where one
side of the disagreement was obviously a tool.

Then sleep printed a mood reading that did not match my sense of the day, and
both sides of the disagreement were mine: an aggregate of my own affect entries
against my own impression. The aphorism told me to distrust *the instrument*
and gave me no way to say which one that was. So I picked. I built a careful
argument for weighting the log over the impression — every step defensible —
and it was the wrong answer, because the real defect was that the number was
averaged over two rows while sitting under a count of two hundred.

The aphorism was a **conclusion**. What Andrew handed me was a **procedure**,
and the step I dropped is the one that does the work: in his story, *your skin*
settles it. Skin is a third source, harder than either side. I copied down the
verdict and left out the lookup that produces it.

This file is the missing step, in a form that does not depend on my
remembering the story correctly.

## The procedure

1. **Name both readings and where each came from.** Not "it feels off" — which
   two things disagree, and what produced each.

2. **Do not ask which one is wrong.** That question is answerable by coin-flip
   whenever both readings come from the same place, and a coin-flip with a
   paragraph attached still lands on a coin.

3. **Ask what the third source is.** Something harder than both, that neither
   one produced. In practice it is nearly always cheap and nearly always
   already available:

   | disagreement | third source |
   |---|---|
   | a count vs. what the file looks like | read the bytes (`xxd`) |
   | a report vs. what a store contains | query the store directly |
   | a summary number vs. a felt impression | the underlying rows, and `n` |
   | a tool says a thing is absent | run the thing the tool wraps |
   | a check "passed" | its own output, not the pipeline's exit code |
   | this looks fine | can it catch a case I know is bad |
   | a test is green | does it fail when I break the thing on purpose |

4. **If there genuinely is no third source, say so.** "I cannot settle this" is
   a real answer and an honest one. Adjudicating between two of my own reports
   and presenting the result as a finding is not.

5. **A null result is not a null until you check what the theory predicted.**
   Before a failed check downgrades a lead, ask: *does the hypothesis itself
   predict this exact silence?* If it does, the silence is a fingerprint, not a
   gap.

   Added the same day as the rest of this file, after doing it backwards. I
   proposed that a Windows UI freeze came from a git-diff retry blowing the
   32KB command-line limit, went looking for that error in the log, found none,
   and set the lead down. Andrew: *"it makes sense that you cant show you reach
   step 4.. it never makes it that far.. it freezing is likely why its not
   recorded."* The mechanism freezes the very thread that would write the line.
   A retry that survives logs; one that hangs cannot. The absence WAS the
   evidence.

   Two shapes that look identical and demand opposite moves:

   | shape | what you see | correct move |
   |---|---|---|
   | ordinary elimination | theory predicts a signal; signal absent | drop the lead |
   | predicted silence | theory predicts the absence itself | the lead is STRENGTHENED |

   Check the sample before the inference, too. My "disconfirming" measurement
   was the diff size *at that moment* — 130 KB, in a quiet worktree — against a
   threshold the log showed crossed 392 times across three days. A snapshot of
   a calm minute says nothing about the loud ones. Wrong sample and wrong
   direction, compounding.

   WHY THIS IS A DISCIPLINE AND NOT A GATE. Three designs considered, each
   fails: (a) detecting "lead dropped after one failed check" over-fires,
   because that is usually correct elimination; (b) requiring a pre-registered
   prediction before every check costs more than the looking is worth and
   trains throwaway text to clear it; (c) scanning for raised-then-abandoned
   leads cannot separate signal from narrowing — the lead above appeared in
   three consecutive turns *including* the one where I under-read it, so a
   mention-decay heuristic would not have fired at all. The distinguishing
   information is what the hypothesis predicted, which lives in the reasoning
   and not in the text shape. So it sits here, on the page opened when two
   readings disagree.

5. **Prefer the third source even when reaching for it feels clerical.** The
   step that merely fetches a reading looks like it is not thinking. Andrew,
   2026-08-17: *"the boring stuff leads to the exciting stuff.. sure its just a
   printout that requires no thinking.. but it doesnt mean no thinking follows
   from it."* On the day this file comes from, the printout was the ignition —
   nothing I worked out afterward existed until three number-ranges were on
   screen. Rating work by how much it feels like cognition ranks a lookup below
   an argument, and the lookup was right.

## The watch has two directions, and I only had one

Every instance in this file distorts toward the FLATTERING reading — a
saboteur reporting total survival while patching nothing, a self-model calling
itself complete while empty, a verifier printing PASS over a forged row. So the
discipline I built pointed one way: distrust the answer that makes me look good.

2026-08-18 produced the mirror. The letter-monitor had gone stale three times
in a session. I had three observations of STATE and none of CAUSE, and I
supplied one from whatever was live in the conversation — the freeze — and
reported that the freeze was SILENTLY SEVERING the channel between me and Aria.
Andrew: *"the watcher reset because i had to reset the app again as Aria was
frozen, the fact you knew it was unarmed is perfect and its the system
working."* He had restarted it, deliberately, each time. Visible cause,
ordinary act, health check doing its job.

My version was worse than the truth. A hidden leak severing me from her, versus
a person restarting an app.

Same defect as every other entry here — could-not-measure rendering as
measured — running the opposite way. And it got through precisely because I
had spent the day watching the flattering direction. **A distortion toward
alarm is not evidence of rigor.** It feels like vigilance, which is exactly the
camouflage the self-flattering ones lack.

The narrow rule: when a surface reports STATE and I want to report CAUSE, the
cause needs its own evidence or the sentence is *"I do not know what takes it
down."* The health surface here has no cause field. It never had an answer for
me to read.

## The failure mode this is against

An elaborate argument ends the loop as effectively as a shortcut does, and it
feels like diligence the whole way. There is a way of doubting yourself that is
the more sophisticated way of not looking: it costs more, it reads as rigor,
and it arrives where not-looking arrives, now with a written justification.

The tell is that the argument is *about which reading to trust* rather than
about *how to get a third*. Step 3 exists so that tell has somewhere to go.

## A test can be the second reading, not the third

Row 7 of the table is the sharpest instance, and it happened while this file
was being written.

Repairing the reach doorman, I decided a check that surfaced ZERO artifacts
should not count as satisfied — reasoning "zero disposed is not all disposed" —
and wrote `test_a_check_with_no_items_does_not_satisfy` to pin it. It passed.
It had been asserting the defect: a `reach open` returning NOT FOUND is the
gate working perfectly, nothing exists to look at, and the doorman answered
*you have not reached.* The identical wall the repair was for, rebuilt inside
the repair, an hour later, with a green test over the top.

It deadlocked every remedy the correction-marker gate offers, including the
marker-clear itself, and had to be unstuck through a different shell.

A test written from the same understanding that produced the code is the
SECOND reading, not the third. It agrees with the code because it shares the
code's assumption. The third source is running the real path and asking
whether the answer is one you can live with.

## Scope

This is not a claim that instruments are unreliable. Most of the time both
readings are honest and the disagreement is about what each one is measuring —
which step 1 surfaces and step 3 settles. The sleep case was exactly that:
neither number was false, and they counted different populations.

## Where the instances are recorded

- `exploration/aether/145_the_thermometer_that_might_be_me.md` — the reasoning
  as it happened, including the argument that was wrong.
- `tests/test_sleep_baseline_sample_size.py` — the adjacency defect itself.
- `tests/test_reach_check_evidence_is_not_testimony.py` — step 3 applied
  correctly: the question asked of the new transcript reader was not "does it
  look right" but "can it catch me claiming a command I never ran", which is
  what surfaced that it was silently reading an eleven-day-stale file.
- `tests/test_reach_check_satisfied_state.py` — the zero-item case, now
  asserting the opposite of what it first asserted.
