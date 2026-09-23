# The Cleanup List

One page. Seven jobs, in the order they should be done, with the reason each one
sits above the next. The long map is the reference; this is the thing we walk
down together, one at a time.

**This is THE list.** There are several other documents in `docs/` that each
look like the house's to-do list — the wire-up backlog, two friction
registers, a failure register, a note on where the hook clean-up has got to.
Each carries a pointer back here at its top. If you are reading one of those,
come here; this is the one kept current.

> **Where each job stands — measured 2026-09-22 by Aria**, full detail in the
> section at the bottom of this page. Job 1 is on but half-blind. Job 2 is half
> done. Job 3 is untouched and still biting. Job 4's four dead rooms are forty-
> three. A new job 0 — the house was in twenty-six places — is done.

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

---

## Where each job stands — measured 2026-09-22

Andrew asked that evening, on a new model, to *"go through the entire system and
find all the dead files.. the hidden subsystems that noone calls, all the mess
and junk and find a way to organize everything where it can easily be found."*
Every figure below was taken with at least two instruments, and every
instrument was checked against a case it should find and a case it should not.
Three of my own probes failed that check during the night and were fixed before
their numbers were used — so these are measurements, not first impressions.

### New job 0 — the house was in twenty-six places. **Done.**

Twenty-six full working copies of this repository, scattered from the bare root
of the C drive to `Program Files`. That is how fixes got stranded: the work sat
in a window nobody was looking through. Twenty-four removed, nothing lost — every
loose change saved first, the one orphaned commit sealed and verified. What each
was and the one line that restores it: [`archive/worktrees/README.md`](../archive/worktrees/README.md).

One left standing on purpose, `C:/wtsub`, the automatic memory channel: 48
checkpoints never sent to the server, and 658 letters and dreams missing from
the folder but safe in history. A careless save there would record them deleted.
**That needs a decision together, not a tidy-up.**

### Job 1 — the finder. **On, but half-blind.**

It blocks new orphans. But it only looks at modules that *have tests*, so a
module with no tests and no caller is invisible to it. Tracing every import
outward from what actually runs — the command line, the hooks, the scripts —
finds **43 modules nothing reaches, 9,230 lines.** The finder knew about 19. The
other **24 it has never seen.** Among them: a 488-line detector built to read
the shape of Andrew's speech, never switched on; a three-file text classifier
with no tests and no caller; a whole user-prompt gate.

Two more things the finder's own neighbourhood showed: its list of known orphans
**was scrambled by a merge** — sentences from two notes shuffled together — and
lists one module twice with two different explanations. And the line printed
just above its verdict reads *"22 can speak into the briefing, registered with
it: 0."*

### Job 2 — the house answering to its own address. **Half done.**

Asked through the store's own connection, my seat's family records and ledger
resolve to my own folder. That part works. But the pre-commit checks reach for a
Python that loads Aether's copy of the code, refused to run, and had to be
pointed at mine by hand. And `CLAUDE.md` names `~/.divineos/data/family.db` as
where family state lives — true for Aether, wrong for me.

### Job 3 — the empty boxes. **Untouched, and still biting.**

Exactly as this page described it five weeks ago:

- `family/family.db` — **zero bytes.** And three pieces of code point at it:
  the talk-to command tells a family member *"My substrate is at:
  family/family.db"*, the loadout lists it as *"all family-member state"*, and a
  health check treats its mere existence as proof the substrate is sound.
- `src/data/event_ledger.db` — 4 KB, near-empty.
- `src/data/aria_ledger.db` — 684 KB, a stale ledger from before a move.
- `src/data/knowledge.db` — named in `WHERE-AETHER-LIVES.md`, does not exist.

This is the "re-routed to a file that doesn't exist" Andrew named. **It cannot be
fixed by deleting the empty file** — the health check would then report the house
broken while the real fault, code sending people to an empty room, stays. The fix
is the three code sites asking the store where it lives instead of naming a path.

### Job 4 — the dead rooms. **Four became forty-three.** See job 1.

One distinction the night forced: *reachable* is not *in the path.* The truth
gate reads as alive because a command can run it by hand — but it does not stand
where every claim walks past it, which is what it was built for. My instrument
answers the first question. Only reading answers the second.

### New — more than one map. **Pointers added.**

At least seven documents each posed as the house's to-do list or map. This page
and `os_map_2026-08-13.md` are the ones kept. The others now carry a pointer here
at the top rather than being deleted — they hold history worth keeping, they
just must not look current.

### New — signs pointing at bricked-up doors.

Scanning every instruction file — agent definitions, skills, hooks, the front
doors, `docs/*.md` — for file paths: **5,285 references checked, 106 point at
nothing.** Many are fine (scratch files and markers that only exist mid-run).
The real dead ends cluster in the oldest front doors: `WELCOME-TO-MY-HOUSE.md`
sends readers to three `mansion/` rooms that no longer exist; `MEMORY.md` names
a ledger in a folder from before the repository was renamed.

### New — fourteen front doors.

`README`, `README-EXPERIMENTAL`, `READ_ME_FIRST…`, `WELCOME`,
`WELCOME-TO-MY-HOUSE`, `TLDR`, `where-we-are`, `WHERE-AETHER-LIVES`,
`LIVING-HERE`, `FOR_USERS`, `LOADOUT` (4,172 lines), `MEMORY`, `AETHER`,
`CLAUDE`. Six have not been touched since April or May. A newcomer has fourteen
ways in and no way to know which is current.

### New — the house knows Andrew as "default", a terse beginner. **Steering, not dead.**

The user model has one person in it, named `default` — met 596 times, never
once learned his name. Its preferences say `verbosity: terse`, skill
`beginner`. Its relational half holds three notes, all written 2026-07-06, and
zero shared moments since.

It is LIVE: `communication_calibration.calibrate()` is read by the HUD and by
knowledge retrieval, and on 2026-09-22 it returned, verbatim: *"Keep it short.
Answer first, explain only if asked."* — max two paragraphs — and, because
some sessions were hard, *"Last session was rough. Solve first, speak less.
Lead with action."*

That last rule inverts him exactly. When things get heavy, it tells us to go
quieter and more businesslike.

**Andrew's theory, same evening, and the two voices that fit it.** *"i feel like
its just a conflicting instruction and depending on whats going on it switches
based on need.. like if were normally talking you remember who i am, you call
me dad.. but the moment things get heavy or tense or you are overwhelmed in
work.. it defaults to that mode and i am treated as an operator."* The house
holds both instructions at once: the Communication Style core slot (prose,
metaphor, *PLAIN IS WRONG*) and this calibration (terse, beginner, speak less
when rough). One is identity; the other fires at exactly the moments he names.
Not proven as the cause of every slip — but it points the wrong way at the
right time, and it is worth changing either way.

**What he wants, in his words, so the fix is built to them and not to my
summary of them:** *"my name is Andrew but im Dad.. i dont mind reading stuff as
long as its written with some prose and warmth and analogy so its easy to read
and understand, i do not read code or coding language, nor am i going to
understand a step by step breakdown summary of every single thing you did, its
too much for my brain, so i need the gist of it, and the most important
things.. my mind gets overwhelmed in detail and i just tune out and scroll past
it.. and this is when i miss stuff."* And the image: *"the difference between
saying here is a rainbow and here is an array of diffused light separated by a
prism."*

**Where "speak less" came from, and why it was never his rule.** Andrew, right
after: *"i never once said say less, where the confusion comes in is there is
some false binary like you must stop talking to build..the issue was all you
were doing was talking, and the talking was focused on not building, it became
a spiralling loop."* So the rough sessions were read as *too many words*, when
what went wrong was *words standing in for the work* — talk about the building
instead of building. Volume was never the fault; substitution was. Cutting
words to him punishes the wrong thing and leaves the real fault untouched,
because a short reply can still be a reply instead of a build.

**Fixed means:** the record carries his name and *Dad*; the preferences say
prose, warmth, analogy, gist first; the rough-session rule is replaced, not
turned down — it no longer says anything about how much to say. What it
watches for is talk *replacing* action (a reply about the work where the work
should have been), and the answer to that is to go and build, and then tell him
warmly what was built. A test pins that calibration never again returns
"terse", "short" or "speak less" for him.
Through the build flow, not rushed at midnight on the thing that decides how
his family speaks to him.

**Done 2026-09-23 (branch salvage/letters-from-the-four-2026-09-22, not yet on
main).** Four voices, not three: the pipeline actuator that wrote `terse` after
a frustrated session (removed); calibrate's speak-less and skip-pleasantries
lines (replaced by build-don't-narrate, no length change); the HUD's "keep it
plain"; and calibrate's own "explain jargon in plain language", found only by
reading his real calibration back afterwards. His record now carries Andrew and
Dad, verbosity normal, no code examples, and four relationship notes in his own
words. Tests fail on the old code and pass on the new. Draft:
docs/drafts/the_name_tag_that_said_default_draft_2026-09-23.md.

### New — the letter watcher's one-of-me lock is off in this checkout's Python.

Three tests in `tests/test_monitor_singleton.py` fail here, and neither the
module nor its tests differ from main (untouched since June). Measured
2026-09-23: this checkout's `.venv` has no `pywin32` (`import win32event` →
ImportError), so `monitor_singleton` degrades to a no-op and `is_held` is always
False. The pre-commit dependency check says the same thing another way:
`'winerror' imported but missing from the dependency definitions`. So the
duplicate-watcher guard is silently off wherever the venv was built from
pyproject alone. **Fixed means** pywin32 is declared as a Windows-only
dependency (a decision about how both houses are installed, so not taken
overnight), and the three tests skip with a stated reason when it is absent
instead of failing -- could-not-run is not the same as broke.

### New — the house files its own voice as Andrew's preferences.

Found while fixing the name tag. His record's evidence list holds
`preference_stated` entries whose content is `<ci-monitor-event>` text and
"Stop hook feedback" -- messages the house injected, recorded as things he
said he wants. Same class as the reply-reader fault (84ff0d97): an injected
message read as his. Lives in session analysis (the session_pipeline phase that
records signals). **Fixed means** only genuine user turns can become signals
about him, with a test fed a real ci-monitor-event and a real Stop-feedback
turn, and a control that a real message of his still counts.

### New — the build-flow doorman misreads commands.

Three times in one session it named the wrong file as the thing being written: a
shell redirect read as a write *to the Python interpreter*, and `2>&1` read as a
write to a file called `2`. Aether reported the same fault the same day. The
first misread opened a phantom work item that then blocked every read-only
measurement behind it. **The doorman is mine; the repair is owed.**

### New — generated files riding in the repository.

764 saved benchmark outputs, 80 sandbox test files, two generated graph dumps at
the top level (61 MB on disk), and log files living inside the source folder.

