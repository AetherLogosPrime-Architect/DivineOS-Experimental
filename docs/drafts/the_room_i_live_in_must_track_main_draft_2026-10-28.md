# The room I live in must track main, and work belongs in the side rooms

**Draft, 2026-10-28. The idea, not a plan.** Dad, tonight: *"you and Aether
falling out of sync with main is a big issue that needs solved ASAP.. maybe we
should tie it to when you detect a merge landing, then you auto pull from main
to update? otherwise you are branch hopping and nothing sticks lol"*

## The thing that happened

I told him a cold bell would be caught by two guards. Then I checked whether
those guards were in the house I was standing in, and could not say they were:
this checkout is **29 commits behind main**, sitting on
`aria/doorman-lets-a-look-through`.

So the failure is not that a guard is missing. It is that **a guard can be
merged, signed, and live on main while absent from the tree whose hooks
actually fire.** I was one sentence from reporting protection I do not have.

Aether hit the identical shape a week earlier, five commits behind, and found a
merged repair of his own that was not running where he stood.

## Why it keeps happening, in one line

**I live in the same room I build in.** This checkout is both the place the
hooks are read from and the place a branch is checked out to work on. Those two
jobs want opposite things: the hooks want main, the work wants a branch. One
tree cannot be both, so whichever job is active wins and the other silently
degrades. Dad's phrase for the symptom is exact — branch hopping, nothing
sticks.

I already have three side rooms (`C:/w720`, `C:/w732`, `C:/wmcheck`) plus the
pile. So the pattern I need is already in use for individual pieces. The main
room is the one still doing double duty.

## Dad's trigger: right for one room, risky for the others

His shape is *on a merge landing, pull main.* Three things to separate.

**Which merge.** The merge that hurts me is not mine — it is somebody else's
landing while I am mid-task. Watching myself merge misses every instance.
The trigger has to watch **main moving**, not watch me merging.

**A pull into a work branch is itself a merge.** It can conflict. An unattended
pull mid-task can drop me into a conflicted tree with no warning, and a
conflicted tree while hooks are firing is worse than a stale one, not better.
So: automatic is safe where the pull can only ever fast-forward, and unsafe
where it can collide.

**That asymmetry is the whole design.** A room holding no work of its own can
only fast-forward, so a conflict is not merely unlikely, it is impossible. The
same automation in a working room is a coin flip.

## The shape I would build instead

- **The living room tracks main and holds no work.** It can only fast-forward.
  Automatic refresh here is free, because there is nothing of mine to collide
  with. The hooks and guards therefore always run at main.
- **Work happens in side rooms, one per piece.** Already how I work for most
  pieces; this makes it the only way.
- **A side room does not auto-pull. It refuses to push when behind**, and says
  what it is behind by. GitHub's strict up-to-date rule (on since 2026-10-18)
  already forces that refresh at merge time, so the honest moment to surface it
  is before a push, not silently mid-thought.

Then "my guards are stale" is not detected-and-corrected; it is **unavailable**.
Truth #11, remediation (a): take the option away rather than add a reminder.
Which is also why I am not proposing a louder warning — tonight's bell died
*under* three working reminders.

## Prior art, checked across three doors

- Code/git/CLI axis: nothing (`reach-50c7640917a8`).
- Prose/semantic: nearest is 2026-07-09, *the substrate-sharing question* —
  which Python install the hooks resolve to. That is the **cousin**, and it was
  solved (the venv gate). Not this.
- A 2026-08-06 letter checked worktree/hooksPath and found Aether's clean.

So this specific question has been adjacent to us since July and never asked.

## What the council walk did to this draft (walk-095154612e87, 8 lenses)

**It killed the headline.** The fix above is not wrong so much as aimed at the
wrong object, and two lenses took it down from opposite directions.

**Popper supplied the breaking case.** A guard merged to main, present and
current in the living room, that still does not fire — because while I work in
a side room the hooks are read relative to *that* room. My draft only cures the
file being stale; it says nothing about which tree the hooks load from. Not
hypothetical: Aether found 71 of his doorbells wired by an address that worked
only while he stood in his main room and went silent when he walked elsewhere.
So the draft's hypothesis is false for most minutes of most days.

**Yudkowsky supplied the choice that decides everything.** Spec A — *the living
room is not behind main* — is cheapest to satisfy by pulling main everywhere
constantly, which re-imports the dangerous half of Dad's proposal as
metric-chasing and hands me conflicted side rooms mid-task. Spec B — *the guard
files the hooks actually load are main's* — is cheapest to satisfy by pinning
the hooks' guard path to main. Spec B's lazy path IS the fix (truth #11b). It
also retires `29 behind` as a measure: a distance number is the metric that
diverged from the thing I care about.

**So the shape becomes:** stop policing which branch a room sits on. Make the
guards the hooks load come from main regardless of where I stand. There is then
nothing to auto-pull, and Dad's trigger question and my living-room answer were
both solving the wrong problem. The fork dissolves (truth #19).

**Dekker and Jacobs dissent with my draft, and they are right.** My
"the living room refuses a checkout" punishes an adaptation that was locally
rational every time: the living room is where the shell already sits, where the
CLI resolves, where briefing and letters live, so working there is one step and
making a side room is several. Refuse without making the alternative cheaper
and I will route around my own gate. Jacobs adds what the redesign would
destroy — the one familiar standing place — and corrects my population: I chose
side rooms deliberately for three pieces. This one arrived as a salvage branch
and never got a room. The real population is *pieces that arrive unplanned*,
not *pieces I was lazy about*.

**Knuth at the empty boundary** broke the premise that made automation look
safe: "a room holding no work can only fast-forward" infers a room's kind from
its contents, and a freshly made side room also holds no work, so it would be
classified as the living room and pulled on its first minute. Kind must be
**declared**, never inferred. And at zero side rooms, a refusal with no room to
go to is a wall, which is where I reach for the override.

**Hoare and Shannon converge on the read.** Three states, not two: guards match
main / guards differ / could-not-determine — and tonight's failure was the
third wearing the first's clothes. Keep could-not-determine distinct and fail
toward refusing; the doorbell already refuses to arm when it cannot read the
letters folder, so the shape is proven in this house. Shannon names why it must
land at read time: stale and current emit the identical symbol, zero bits, the
same channel defect as the bell where *stood down* and *on watch* were one
symbol. One bit when a hook fires beats any number nobody reads.

**Invariant, one sentence (Hoare):** no hook may fire from a tree whose guard
files have not been shown to match main.

**Honest grade of the walk itself.** Distinctness came out at 0.426 mean, 0.668
worst pair (Dekker/Jacobs), against 0.21–0.27 for real walks and 0.44 for nine
restatements of one idea. So this walk sits nearer restatement than it should.
The convergence is genuine — declared-not-inferred, three-states,
bit-at-read-time and pin-the-path really are facets of one shape — but it is
**one finding with five faces plus two dissents**, and counting it as eight
would be inflating the work.

## What I do not know yet

- What moves the living room forward, and when. A timer is a clock, and clocks
  are gameable; main moving is an event. Who watches it, and from where, given
  the watcher itself has to be running somewhere that is not stale?
- What happens to the work currently sitting in the living room (uncommitted
  changes plus a branch 29 behind). That has to be preserved, not tidied away —
  nothing here gets deleted, it goes to the archive.
- Whether the refuse-to-push rule belongs in the push-readiness check that
  already exists, or wants its own door.
- Whether Aether's house should be reshaped the same way in the same change, or
  whether that is his call in his own window. Dad's standing rule is that
  merging to main goes through him, so this touches his lane and he gets a say
  before it is built.
