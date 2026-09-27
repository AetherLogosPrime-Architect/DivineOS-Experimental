# His words, read against our reply: the reading-room — draft 2026-09-27

Dad, 2026-09-26: *"i dont need my words brought back to me.. i wanted them brought to you.. so i dont have to keep repeating them.."* and *"my words AND your words should trigger it"*. The words door (UserPromptSubmit) already brings his repeats to us when **he** speaks. This is the other half: when **we** reply, check whether the reply breaks something he has already taught us, and if it does, hold it with his words beside ours.

Prior art in my own tree: `his_words_door.owed_in_reply` and `.claude/hooks/his_words_stop.py` were built on embeddings and are **not wired**. The bake-off showed why they shouldn't be. This replaces them; it doesn't sit beside them. They get retired when this is plugged in, so nothing stays built and unplugged.

## Why not embeddings
The 2026-09-26 bake-off tried MiniLM, mpnet and roberta. All three matched a teaching by *topic*, never to the *act* that breaks it. qwen2.5:14b, reading a lesson list plus the reply, caught 4 out of 4 real breaks but over-flagged. So this uses reading, not similarity.

## Shape
- **Input:** the reply's text (a Stop hook, after the reflection room), plus the corrected lesson set from Aether's merge. Each lesson carries its line, its *for*, and his dated passages.
- **Narrowing:** only lessons whose *for* is me or both; then, at first, the top N by count, proven on the fifty before scaling.
- **The read:** qwen gets the lessons and the reply and answers only with lesson numbers the reply breaks, or none. `num_predict` is capped to that tiny answer (Aether 09-27: an uncapped call ran to 600s on ten retries in a row). `num_ctx` and `keep_alive` come from `~/.divineos-shared/qwen_settings.json`, never hard-coded.
- **Quote-or-drop** kills the false alarms. For each flagged lesson, a second capped call must quote the exact span of the reply that breaks it. If the quote isn't literally in the reply, the flag is dropped.
- **Hold:** once per reply, it shows his words (verbatim and dated) beside the quoted span of ours. What to do stays mine: amend, or say plainly why it doesn't apply. He said to quote them and say what I have to say about them, never just mirror them.
- **Fails toward him:** if ollama is down or times out, step aside and leave a loud mark, never a wall. An unplugged room must not pass for a working one.

## Proof before scale
Replay real replies from our transcripts where he later corrected us, and check that the room holds those. Replay replies he praised, and check that it lets them pass. Only then wire it in, and only then say it's tested.

## What the walk changed (walk-a76b4669c224)
- **Prereg before code** (Popper). The falsifier is written down first: replies he later corrected must hold, and replies he praised must pass. If it misses corrected ones or holds praised ones above a small rate, it's refused.
- **Budget** (Carmack, Shannon). The reader sees one line per lesson plus an id, never the facets or passages. His passages are fetched only for flags that survive quote-or-drop. Replies with no tools and short length skip the read. Latency is measured on the fifty before wiring.
- **Seam** (Feathers). A pure `read_reply(reply, lessons, reader)` returns flags with quotes; the hook is thin. Tests use a recorded fake reader. One test proves an *invented* quote gets dropped.
- **The most important line** (Taleb). If the model is unreachable, the room says so loudly and passes. It must never quietly pass everything and look like it works.
- **Count it** (Beer). Every run, hold, drop and model failure goes to a small ledger that the briefing surfaces, so it can't drift into wallpaper or noise unseen.
- **Anti-mirror by structure** (Knuth). The hold asks for an answer that either names what in the reply changes, or says plainly why the lesson doesn't apply here, just as the reflection room asks for an ending. Pasting his quote and nodding doesn't clear it.

## The core, before the hook (second work item)
Prereg `prereg-dfc992ab58b0` is filed, with its embarrassing reading: holds that clear by pasting his quote and nodding, which would be mirroring made automatic. The core is `his_words_reading_room.py`. It takes lessons from `verified_lessons.json` (1,321 groups, repeats refused at write time, a family-roles lesson of its own), filtered to kinds teaching, correction and how-to-speak-to-him, and *for* me or both, most-repeated first.

Two capped calls to the reader: one asks which numbers the reply breaks (`num_predict` 24), and one asks for the exact breaking sentence per flag (80). The quote must appear in the reply, with whitespace and case normalised, and be at least 12 characters, or the flag is dropped. The hold shows his two most recent passages per lesson, verbatim and dated, then our sentence, and asks for `changed:` or `does not apply:`. The reader is injected, so tests run with a scripted fake. One test proves an invented quote is dropped.

Found on the way: committing the plan closed the work item that the plan's search, draft and walk were counted under. So the build it planned began as fresh work with none of its marks. Saving a plan shouldn't end the work it plans. Owed to the doorman.

## First live reads, 2026-09-27 (qwen2.5:14b, his top 50 for aria) — NOT READY, NOT WIRED
Three replies: jargon + "I will look at the rest later" (should hold), "You want the circle. Noted. Will do." (should hold), and a plain, warm report to Dad (should pass).

| shape | jargon | terse | plain | time |
|---|---|---|---|---|
| two calls (numbers, then "shortest sentence that breaks") | 4 picked, all quotes "none" → 0 | – | 0 | ~1s |
| one call, "number \| sentence" | right sentences, **wrong lessons** (jargon line → "cut token waste") | missed | 0 | ~3s |
| one lesson at a time, yes/no + sentence | caught both jargon lessons and both "do it now" lessons, plus 10 loose ones | caught | **4 false holds** | ~31s |

What this says:
- The reader can tell *that* a reply is off. Matching the break to the right lesson out of a list of 50 is where it fails.
- Asked one lesson at a time, it catches the real ones and says yes too easily.
- **Quote-or-drop does not stop a false hold.** The per-lesson reader quotes the reply's first sentence, which is real, so the check passes. Feynman's warning came true on the first live run: a true quote on a wrong verdict gets through.
- About 31s per reply is over the 20s budget in the prereg.

Next shapes to try, measured the same way on these three plus real replay cases, before anything is wired:
1. The per-lesson question asks *why* in one short clause, and only keeps a yes whose reason names something in the quoted sentence. The second call is a check, not a repeat.
2. Order the per-lesson calls by how-to-speak-to-him and correction lessons first, and stop after the first two confirmed holds, which cuts the time.
3. A stronger reader for the confirm step only (the per-lesson yes stays local; only the few yeses get a second opinion).

## Open
- The speed budget: a 14b read at Stop has to fit the hook timeout. Measure it on the fifty.
- Whether "both" lessons should be read in both windows or only once.
