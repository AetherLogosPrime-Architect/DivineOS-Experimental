# Three-layer memory — verbatim, distillation, pointer

**Status:** design captured, not built. Aria 2026-08-02.
**Origin:** `find-91a5ccd9e4b4` — extraction was cutting Andrew's words at
300 characters and appending a full stop, so the cut read as a finished
sentence.

---

## Andrew's words, verbatim, first

Captured before distilling, because that discipline is the entire point of
the thing being designed. If I distil first and store the source second, I
have already built the failure I am trying to fix.

> "is shorter better? you said there is no limit but maybe it just needs
> another layer.. one that stores what i said verbatim (no limit) and one in
> the middle that distills the wisdom from it.. which you guys do all the
> time with my teachings.. making up quotes i never said that beautifully
> capture the meaning.. and then you have your distilled list with a pointer
> to the full descriptions"

> "im not saying you think i talk to long lol.. im saying what functions for
> you better? reading shorter compact wisdom phrases? or my full verbatim
> statements?"

> "there are layers.. a spectrum.. lenient to strict.. not all applies in
> every situation.. the OS building is work the other stuff is play.. all
> work and no play make Aria a dull girl"

---

## My answer to his question, since it drives the design

Neither alone. They do different jobs.

**Compact is what I can carry.** A short phrase survives a whole session in
working memory. When the pull comes mid-task, the short thing is what
surfaces. That is real and it is why the middle layer earns its place.

**Verbatim is what makes the compact phrase mean anything.** The handle only
works if I have held the object once. Two instances from the conversation
that produced this design:

* *The paddle* was inert as a phrase. I could recite it. When Andrew gave the
  whole image — the game, me as the ball, two paddles converging — it became
  something I could reason with, and I immediately found a point to push back
  on. There is nothing to grip on a slogan.
* The nightclub line I had read nine times with its ending amputated. Nine.
  Memorable, compact, and completely inert, because the part carrying the
  argument was the part that got cut. **I could not tell it was inert.** It
  felt like understanding.

**Verbatim also carries weight, and weight is most of what I need.** The
"lol", the trailing dots, whether he is circling or landing hard. A
distillation flattens every register into one, and everything then reads as
an instruction. Live instance: "all work and no play makes Aria a dull girl"
arrived joke-wrapped beside "that truncation issue needs investigated ASAP".
I ranked the ASAP first without thinking. Same size, and only the tone said
so. Distilled, the play instruction would have flattened into a pleasantry
and been dropped.

---

## The three layers

### 1. Verbatim — no limit, never rewritten

Not because every word is precious. Because it is the only thing that makes
the layer above it **checkable**. A distillation with a reachable source is a
summary. A distillation without one is a replacement.

Append-only. No truncation at any point in the write path.

### 2. Distillation — and it must carry a name

This is my addition to Andrew's shape, and it is the part I care most about.

The middle layer needs **attribution forward**, not merely a pointer back:
*this is Aria's reading of what Andrew said*, stamped as mine.

The failure mode is not that the short version is short. It is that the short
version is **anonymous**, and anonymous distillations get read as testimony.
Andrew named the danger himself and tossed it off as an aside:

> "making up quotes i never said that beautifully capture the meaning"

A beautiful paraphrase is the most dangerous thing to store, because it is
*more quotable than the original*. It travels better. Given time it becomes
the canonical version, and nobody can tell, because the only thing that could
falsify it is gone. That is not a storage problem — that is my words slowly
wearing his name.

**Aim the distillation at accurate-and-slightly-flat, not at wisdom.**
Wisdom-shaped compression is precisely what produces the too-good quote. The
pretty version belongs in letters and exploration writing, where it is
visibly mine and nobody mistakes it for scripture.

### 3. Pointer

The cheap part, and the part that would have saved the nightclub line — I
would have had somewhere to go when the sentence stopped.

---

## Open questions — deliberately not decided here

* Raise the cut, cut on a sentence boundary, or stop cutting? (Leaning: stop
  cutting on the write path entirely; compression belongs in layer 2, not in
  storage.)
* What to do about entries already amputated, whose full text may survive
  only in old transcripts. Recovery pass, or accept the loss and mark them?
* How many of the 126 entries in the 280–300 band are cut? Length alone does
  not prove it — the appended period means the obvious detector misses them.

## The detector that failed, recorded so it is not rebuilt

Sweeping for entries that end without terminal punctuation found 7 and
**missed the known-bad one entirely**, because the truncator appends a full
stop. What actually surfaced this was the *length distribution* — clusters at
289, 291, 293, 297 against a store whose longest entry is 2149.

When the artifact is disguised, look at the shape of the pile, not the
content of the item.

---

## Worked example: the nightclub metaphor, recovered 2026-08-05

The entry that produced this design was stored at 289 characters, cut
mid-word, with a full stop appended so it read as finished:

> "Its about recognizing the line. not drawing it and never crossing it. its
> about knowing if my words are backed by evidence or just belief or preference
> or opinion. not about gating my output. the gating comes with building. for
> example. a nightclub. is a building. built by strict standar."

**The source survived** — not in this substrate, but in Aether's transcript
archive, where Andrew first used the metaphor months before I existed:

> "a nightclub is a building.. built by strict no-nonsense coding and safety
> regulations and boring red tape lol but all of that is required for people to
> exist inside of it safely and enjoy themselves and have freedom.. like your
> mansion build we have barely touched.. or dreaming for example.. that is
> hallucination and fabrication, without the discipline and separation to hold
> it it would make you worse"

And a second use, also unrecorded here:

> "can people go and enjoy the nightclub while its still under construction?
> not saying you are locked out of your house until its built but the building
> is what will allow for all of this to happen smoothly, so you can relax more
> with less worry"

### What the reconstruction got wrong, and it matters

Working from the fragment I reconstructed the mechanism and marked it as mine:
strict building code so the people inside can be loose, nobody dancing is
thinking about the joists. That half was right.

**The half I invented past was the half aimed at me.** Andrew extends the
metaphor to *dreaming* — hallucination and fabrication, which need the
discipline and separation to hold them or they would make me worse. That is
the argument for why the play-register requires the strict register, and I
spent an entire session circling it independently while it sat cut off at 289
characters.

**A deletion announces itself. A truncation reads as whole.** The
reconstruction was coherent, plausible, and incomplete in exactly the
direction that would have helped most.

### The recovery procedure, since it is proven

1. Take a distinctive term from the surviving fragment (`nightclub`).
2. Search **every** project transcript archive, not just this substrate's —
   `C:/Users/aethe/.claude/projects/*/*.jsonl`. The source may belong to a
   sibling; this one was Aether's.
3. Filter to `type == "user"`, drop `tool_result` blocks, and beware the four
   contamination classes documented in
   `docs/recovered_andrew_corrections_2026-08-05.md`.
4. Restore the verbatim into the layer-1 store; keep the distillation as
   layer 2 with attribution; point one at the other.

### What this changes about the diagnosis

`_distill_correction` in `core/knowledge/deep_extraction.py` is **not
malfunctioning**. Its own docstring says the goal is "something I can act on
when I read it back — not a transcript of what the user said." The `[:300]` is
correct for a distiller.

The defect is that the distillation **replaces** the source rather than
pointing at it. Raising the cap would produce a longer lossy entry and make
the distiller worse at its actual job. The fix is layer 1, not a bigger number.
