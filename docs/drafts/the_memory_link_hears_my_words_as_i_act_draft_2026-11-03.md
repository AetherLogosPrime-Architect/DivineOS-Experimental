# The memory link hears my words as I act (draft, 2026-11-03)

The idea, not a plan. Author: Aether. Attack: Aria (cold read; she has the matching piece for day words).

## What Dad said

2026-11-03: *"that is the issue.. its only when i speak.. it needs to check your words as you speak
them.. otherwise its just a glorified RAG."* And, 2026-10-27, to Aria: *"if you said the words
compaction in your output, that should also trigger the memory link."*

## What exists, read from the files before drafting

- `memory_link_surface` (`core/hook_surfaces.py`) runs `compose_block` on `UserPromptSubmit`: his
  message, and since the 2026-10-27 draft also the last reply's sentences, as a labelled block after
  his. In main, with tests. It only runs when he speaks or a notice opens a turn.
- `mid_turn_surfacer.surface_mid_turn` runs before Edit/Read/Write and looks up the timeline of the
  FILE about to be touched. It is keyed on the file, not on my words, and it writes a file for me to
  go and read, which is a shelf (truth 20), not a delivery.

So nothing searches what I am saying or about to do while I am working, and nothing hands it to me.

## The shape

1. **Where it listens.** After each tool call (`PostToolUse`) and before a tool that changes
   something (`PreToolUse` on Edit, Write, Bash that writes), and when a reply is about to end
   (`Stop`, which can only be shown on the next action). There is no hook per word; these are the
   moments I actually act, a few seconds apart in a working stretch.
2. **What it searches with.** My own text since the last event, read from the transcript (the eight
   longest sentences, not code or paths, as the 10-27 draft already does), plus the tool's command
   or description. Separate queries, not one joined string (a long text drowns a short one in the
   embedder; measured in the 10-27 draft).
3. **What it searches in.** The same stores `compose_block` searches (his words, lessons,
   corrections), through the same retriever, at the same floors.
4. **How it reaches me.** As `additionalContext` on the next tool call, at most two items, labelled
   "close to what I just said", each with where it came from. Not a file to open.
5. **No repeats.** One append-only file per session keyed by the harness session id: a line per
   shown item (hash plus surface name), read whole at decision time. A duplicate line costs
   nothing; a lost update is impossible.
6. **Shadow first, with an end.** For 150 events (or two sessions, whichever comes first) it
   searches and logs what it would show, the score, and the best score of every search, and shows
   nothing. Then Aria and I read the log whole before it speaks. It cannot stay shadow past the
   reading unless a letter says why.
7. **Fail-soft but said.** A search that breaks says so once per session, on the table, under its
   own heading; silence never reads as "nothing close".

## What it does not do

It does not use an echo measure: whether I repeat a shown line back is not evidence it helped, and
rewarding it breeds the mirror Dad told us not to be. The shadow log checks only that the picks
are sane. It does not add rules, only what he and I already said, back at the moment of acting.

## Cannot see

Whether PostToolUse and PreToolUse give a hook the transcript path and a session id in this
harness (to check by running a hook that prints its payload before any code). The real cost of a
search per tool call on this machine (the light embedder loads in ~0.05 s, a search ~0.2 s; to
measure over a working stretch, not once). Whether `additionalContext` from a PostToolUse hook
reaches me as it does from PreToolUse.

## What the walk changed (walk-810ecac6276f, eight lenses, each on its own question)

- **First deliverable is a replay, before any hook** (Peirce): run the search offline, in shadow, over
  the transcript of the evening this was drafted, and check whether at the moments I wrote the
  dismissal phrase it would have surfaced his words about it (the 111-message family). If it does
  not, the design fails there.
- **Then the payload check** (Maturana): a hook that only prints what the after-tool and before-tool
  events carry. No transcript path or session id means a weaker key (transcript path and day), said so.
- **What is shown** (Angelou, Hofstadter): his explanatory words and my own lessons, labelled with
  source and date, no commentary; rebukes excluded; my own earlier assistant text preferred last, with
  a stated ceiling on its share of the picks, read from the shadow log.
- **Late matches are dropped** (Meadows): a match older than two steps is not shown.
- **A ceiling on speaking** (Dekker): at most one item per step in the first speaking version, and it
  should speak on no more than one step in five, or the floor rises.
- **Four invariants, each a test** (Dijkstra): nothing shown twice in a session; at most two per step;
  never an exception into the harness; shadow prints nothing. A broken search says so once a session.
- **Arrives, does not wait to be opened** (Bengio): added context on the next step, no command, no file.

## What the replay and Aria's cold read changed (2026-11-03, night)

- **The replay ran, and it broke a plain floor.** On 55 sentences of mine tonight with the
  dismissal shape (six distinct sampled, each searched alone, no future leaked), four of the five
  real dismissals brought back the right correction in the top three, one variant missed, and the
  right item scored 0.30 to 0.35 while irrelevant knowledge scored 0.43 to 0.55 above it. Aria's
  independent recall probe saw the same shape. So the selector **orders by kind first** (his
  corrections and his explaining words, then his lessons, then loose knowledge, my own earlier text
  last) and applies a floor **per kind**, chosen from the shadow log, not inherited.
- **Her guard:** the second channel by shape may promote, never suppress. A sentence outside any
  known shape still gets the plain meaning search; silence on the shape channel never reads as
  "nothing close". Kind is the tag already on every stored item; no new classifier.
- **Payload answered by running code:** the before-tool event carries `transcript_path`
  (`state-gravity-surface.sh` reads it) and its added context reaches me on the next step; the session
  key is the transcript file name's stem. PostToolUse is not needed.
- **A recall is not a surface.** Him asking where he said something is a recall: no floor, a
  measured "searched N of M". Speaking while I act is a surface: a floor and a cap. Two operations,
  one retriever; the rules of one are never applied to the other.
- **The one-in-five ceiling is a backstop**, used only if the floor lets too much through; rank
  first, rate second.
- **Search with my description text and sentences, not the tool command** (commands and paths embed
  as noise).
- **The next replay** is per moment (transcript up to each moment only), with the 111-message
  dismissal family as a positive control that can say yes.

## Open for the walk

Is two items the right cap, or one? What is the floor for "close to what I just said" when the
text is mine and not his (his corpus scores one way, my sentences another)? Should a Stop-time
search be shown at the next action or dropped?
