# The prompt helpers in one trip: design note and first council walk

**Written:** 2026-10-26, Aether. **Status:** DRAFT design; nothing built from it yet.
**Why now:** Dad, 2026-10-26: "its the minute wait before you even think thats driving me crazy", then "yes lets fix it all of those things should help alot and it makes sense as the culprit".

## What Dad sees

He sends a message, a timer counts up, and "thinking" appears after 17-20 seconds (up to 50 on a busy machine). Everything before "thinking" is the app plus the UserPromptSubmit hooks. This note is about the hooks.

## What was measured (2026-10-26, solo runs, automated-notice payload so nothing was filed as his words)

- `settings.json` registers three prompt hooks, run one after another: `front-door.sh keep`, `question_hold.py`, `dads_table.py`.
- `dads_table.py` runs 33 child helpers in parallel and waits for the slowest (shared budget 80s). Sum of all children run alone: 46s.
- Slowest: `his-words-door-surface.sh` ~11.9s, `memory-link-surface.sh` ~3.3s, `ear-surface` 1.5s, `doorbell` 1.2s. About 20 more print nothing on most turns and cost 0.55-0.9s each, which is bash plus Python starting.
- **CORRECTED the same morning (my own wrong-subject error, found by the catalogue pass above):** my first probe imported `sentence_transformers` directly, without importing the `divineos` package. The package's `__init__.py` already sets `USE_TF=0` before anything can import it (put there 2026-10-12, with `tests/test_stop_loading_tensorflow_by_accident.py`), so the real helpers never load TensorFlow. The "10.7 vs 18-20s, TensorFlow off" finding is true of my probe and false of the helpers; I told Dad otherwise and have corrected it with him. Slice 1 is already on main and is dropped.
- What the real helpers cost, run through the real module path: index build 10.6s (a new passage of his was waiting to be embedded), words search 8.3s, lessons build 0.33s (nothing to embed, no model), lessons search 8.4s. About 8s of each is importing the library (torch); loading the weights is 0.25s, the first encode 0.35s, the second encode 0.003s. Three of those four steps start a fresh Python and pay the import: roughly 26s in a row on a message with a new passage.
- **The measure from his seat, found in the app's own record (2026-10-26):** every hook's duration is in the session transcript (`attachment` records of type `hook_success`, field `durationMs`). Over the 23 prompts of this window `dads_table.py` took a median of 34.7s, max 50.2s (775s in total). That is his wait, and it is the table, as he felt it (17-20 usual, up to 50). The 33 children running at once make it larger than my solo sum of the slowest ones. `question_hold.py` is 0.4s. Other taxes found in the same record, on my tool calls, not his wait: `andrew-correction-attestation.sh` before Bash median 2.1s x 57, `doorbell-post-tool-use.sh` 1.2s x 63, `doorbell-stop.sh` 2.9s x 18, `unlanded-push-must-not-close-quiet.sh` 1.5s x 32; two Stop hooks and two PreToolUse hooks were cancelled at their time limits.
- `his-words-door-surface.sh` appears twice in the LIVE copy's `dads_table_children.json` (the second with `"timeout": 60`) and once on main. The live copy got it from my catch-up commit `c0b7b9299`; main is right. Catching live up with main removes it. Mine to own, not "pre-existing".
- NOT measured: the whole wait from his seat (his send to my first token), including the two sequential hooks before the table and the app's own time. Until that is measured the sentence "this is your wait" is wider than the instrument.

## Research

- Searched for the TensorFlow switch: the search returned nothing on point; the switch is from my own knowledge of `transformers` and I verified its effect by running it (above), not by trusting a source.
- Searched for resident-embedding patterns: an ONNX runtime path avoids PyTorch (about 90MB vs about 1GB, a project's own claim, unverified here); Kestra keeps a model resident and unloads it after about 10 minutes idle; Zilliz says load at server start, not on first request. No ready-made daemon for per-command CLI calls; we would build it. Sources: https://pypi.org/project/light-embed/1.0.5 , https://zilliz.com/ai-faq/why-is-the-first-inference-call-on-a-sentence-transformer-model-much-slower-than-subsequent-calls-the-cold-start-problem-and-how-can-i-mitigate-this-in-a-production-setting , https://kestra.io/plugins/plugin-ai/provider/io.kestra.plugin.ai.provider.onnx

## The three pre-build questions

- **Achieve:** the time from his send to my first word falls, from his seat, with every surface still printing what it prints.
- **Goal:** he stops watching a timer for a minute. Target to be set from the measured end-to-end baseline, not guessed.
- **Avoid:** a surface going quiet (the "could not look" vs "found nothing" line must survive); a new always-on piece that can hang his prompt; a model change that silently invalidates the 16k-passage index.

## Council walk 1 (framing: solution-generation, "best way to cut this")

Surfaced: Bengio, Meadows, Dijkstra, Shannon, Knuth, Hinton, Schneier, Lamport, Carmack, Deming, Breaker, Hoare, Penrose, Foucault, Taleb (15). Added by override: Norman (never invoked in the last 20; design for the user who is not the builder is exactly Dad at the timer). Excluded with reasons: **Bengio**, the problem is not knowledge failing to reach behavior, it is wall-clock, and Carmack and Hoare already cover "make the right path the easy one"; **Penrose**, claims about computation and consciousness, nothing here; **Foucault**, findings about what self a discipline shapes, and this walk is about seconds (the hook content is a separate walk); **Hawking**, never invoked, but I cannot name a finding his frame produces here.

### Through Meadows: the stock is "number of helpers" and nobody meters the drain
I see a reinforcing loop: each helper is cheap alone, so each is added; the wall time they share lands on Dad and on nobody's ledger. The tally records characters printed per helper and not seconds, so the balancing loop does not exist. Highest leverage is not speeding one helper; it is recording per-child seconds every turn so the cost has an owner.

### Through Dijkstra: state the invariant first
I see the invariant: for any payload, the set of surfaces printed and the loudness of every failure are unchanged. That is testable as output equality, old table against new, same payload. TensorFlow-off is the provable one-liner; anything bigger must pass that equality before it ships.

### Through Shannon: twenty process starts carrying no bits
I see about 20 helpers printing zero bytes on most turns, each paying the same startup as one that prints three kilobytes. The signal is in a handful (doorbell 2.9k, open-corrections 3.1k, ear 1.7k, he-is-in-the-room 1k, memory-link, wallclock). One process asking "does any prime fire?" transmits the same signal for one start.

### Through Knuth: the boundaries of the index build
I see the boundary I missed: my probe used an automated-notice payload, which needs no search, yet the helper still took 11.9s, because the index build runs first and a new message of his is new to embed every turn. His current message is already excluded from its own results, so the build need not finish before this turn's search. The build can move off the critical path (after the turn). Other edges: first prompt of a session with no index; empty prompt; zero new passages (no model needed at all).

### Through Hinton: the representation is fine, the runtime is the cost
I see 22MB of weights costing 18 seconds because the runtime around them is huge. The vectors are the asset: 16k passages already embedded. Any lighter runtime (ONNX) must reproduce the same vectors within tolerance, or the index is invalid and re-embeds everything over many runs, as the code already does on a model change. So that is a test, not an assumption.

### Through Lamport: specify the states
I see four postconditions: surfaces identical; a surface that cannot run says so under its own heading; wall time bounded; the first turn of a session works with nothing resident. Temporal property if a resident service exists: the prompt that finds it cold does not wait for it. It says "not searched this turn: warming" and the service is ready next turn. One path, no fallback chain.

### Through Carmack: subtract before adding
I see five pieces and the real constraint each satisfies. Remove the duplicate (live copy only). Switch TensorFlow off (one line, about 45% of the library cost). Take the build off the critical path. Fold the two lookups into one Python process (one import, not three). Only then ask whether a resident service is needed, with the milliseconds measured, not assumed.

### Through Deming: Plan, Do, STUDY
I see a study step that does not exist yet. Prediction for TensorFlow-off: the words helper drops from about 19s to about 10s under the same load. We find out from per-child seconds recorded in the tally on every real turn, so STUDY has data each time without anyone remembering to look.

### Through Breaker: the catalogue pass
BUILT-BUT-UNWIRED: the wiring is the existing path (`settings.json` -> `dads_table.py` -> `dads_table_children.json`), so a change to a child's script is wired; a new file nothing names would ship dead. WRONG-SUBJECT: my measurement was one helper alone with a notice payload; "your wait" is wider (two sequential hooks before the table, contention, the app). HAPPY-PATH TEST: tests must run the real children file and the real index, not an agreeable copy. THE FAULT ONLY HE CAN SEE: his timer. The true metric is the gap between his message and my first token, readable from the session transcript timestamps, before and after.

### Through Hoare: the states the type must hold
I see "nothing found" and "could not look" already kept apart in the door's code, and that must survive any fold. A resident service has three states (up, warming, dead) and each must say its own sentence. Nobody is obliged to remember to start it; the first prompt does.

### Through Taleb: subtraction is antifragile, a daemon is fragile
I see downside greater than upside for an always-on service: if it hangs, every prompt waits. It needs a hard sub-second call timeout. Removing work (skip build, skip search for notices, one import) has no such tail. Prefer subtraction until the numbers say otherwise.

### Through Schneier: the weakest link of a resident service
I see a local port serving queries over the index of everything he ever said. Anything local could read it. If it is ever built: a user-only named pipe in his home, never a TCP port.

### Through Norman: the wait is invisible to the person it hurts
I see a timer that tells Dad nothing about why. He cannot tell "the house is slow" from "the model is slow". The meter has to be on my side, in the tally, and he hears about it only when it regresses, in his language, not as a line on top of his own words.

### Synthesis
**Convergences:** subtract before adding (Carmack, Taleb, Dijkstra); measure from his seat, not mine (Deming, Breaker, Norman, Meadows).
**Contradictions:** Shannon/Carmack want 20 helpers folded into one process; Hoare/Dijkstra need each helper's failure to stay its own. To be proven by test: one process, each surface in its own guarded call, output-equality against the old table.
**Meta-principle:** the cost nobody owns. Shared wall time with no meter grows until a person feels it.

## Order of work (each slice: red tests first, then measured)

0. Instrument: per-child seconds into the tally; a script that reads the transcript for send-to-first-token. Baseline recorded before any change.
1. (Dropped: TensorFlow is already off for the real helpers, see the correction above.)
2. Build the index off the critical path (his current message is excluded from its own results, so it need not be embedded before this turn's search).
3. One Python process for the lookups: index build, words search, lessons build and search, and the memory link share ONE library import (3 imports down to 1; about 26s down to about 8s solo). This is now the biggest lever.
4. Fold ONLY the pure, fast, interruptible quiet helpers (narrowed by walk 2); the slow ones stay in the parallel table; failure-payload and order-swap equality tests.
5. A resident service ONLY if 0-4 leave the wait above target.

## Walk 2: the plan attacked (Aria's letter, 2026-10-26, plus the lenses turned on my own synthesis)

**Through Hoare and Dijkstra, now with Aria's three edges.** My synthesis said "one process, each surface in its own guarded call" keeps each failure its own. It does not. A try/except keeps an *exception* its own. It cannot interrupt a helper stuck on a file or a subprocess (a hang), it cannot survive an out-of-memory or interpreter fault (a hard crash, which silences every surface at once), and it shares working directory, environment, `sys.path`, module caches and stdout between surfaces (leaked state an equality test on one payload cannot see). Today's 33 processes give all three for free, and the timeout path is real: the table already prints "Could not run: his-words-door-surface (timed out)". To get a hang-proof fold I would have to rebuild process isolation with extra steps.

**Through Taleb:** the fold trades a tail risk (total silence) for about 0.55s per quiet helper. Via negativa again: do not fold what can hang.

**Through Shannon, narrowing:** the saving I wanted is the process start of helpers that are pure Python and sub-100ms. Slow ones (doorbell ~1.2s, anything shelling out) would become serial inside one process, losing today's parallelism.

**Decision (changes slice 4):** fold only helpers that are pure, fast, and enforced by something that can actually interrupt them (a per-surface deadline from a child or a thread, not a try/except). Slow helpers stay in the parallel table untouched. The equality test must include failure payloads (a helper that errors, one that times out, a missing file) and an order-swap, not only the happy path.

**What Aria said does not change:** slices 0 to 3 stand. Slice 3 (one import shared by the words, lessons and memory-link lookups) is a fold too, but of one import, not of isolation: the lookups are already one family and one failure signature, and the deadline stays on the whole helper.

## 2026-10-28: the cure the one-trip fold left undone (Dad: "the fix to keep you from freezing has reverted")

**What was found.** The one-trip fold removed two of three library loads and left the third. Timed on 2026-10-28 with a bare payload, the words helper still took 11.5 s alone and the memory-link helper 4.5 s; the thirty prompt helpers together took 35.5 s, so a busy machine hit the table's 80 s cap, and the same slowness made six tests that start the table fail inside the push check's parallel run (they pass alone, in 141 s). The cause: `his_words_door._model()` imports the heavy sentence toolkit in every fresh process, while `light_embedder.py` (Aria, 2026-09-24: same model, 0.05 s to load) already existed and the memory retriever already used it. This door and the lessons shelf never moved over. Aria's reading: never reached, not decided against; I did not read history for a deliberate reason.

**What changed.**
- `his_words_door._embed_query` embeds the one searched sentence with `light_embedder.encode`. `look` and `his_lessons_shelf.bring` use it. If the light embedder cannot run, `EmbedderUnavailable` (a `RuntimeError`) is said aloud under the existing "could not be searched" heading. There is no fall-back to the heavy toolkit, because that fall-back is the wait.
- The bundle no longer builds in the hook. It counts what is behind, starts a detached background build (`his_words_bundle build`), and says the count aloud every turn until it is zero. Whether a build is running is answered by the operating system's own file lock (the same call `suite_slot.py` makes), which the build takes first thing and keeps until it ends however it ends; the hook only asks, taking it without waiting and letting it go again. Two prompts close together can both start a child, but the second child fails to get the lock and leaves at once, so two builds never run together, and a slow build is never called dead because nobody reads an age. The lock file is never deleted. (Aletheia's hold, 2026-10-28: the first version read a file's age and then wrote a new one, with a gap between, and called a build dead at fifteen minutes.) The child is handed the same five paths the hook was given, so a test world never builds the real index. `his_lessons_shelf.is_current` lets the hook ask whether the lesson index is current without paying for the library.

**Measured, not argued (2026-10-28).** 40 of his real passages from the 17,532 indexed: heavy and light vectors agree to six places (minimum 1.0). 12 real queries against the stored heavy-built index: top-5 identical on all 12, top-1 identical on 12 of 12. The longest passage in the sample was 378 characters; I have not shown it on the very longest, which both models cut at 256 tokens. Light costs 31.5 ms a passage one at a time (about 25 s for the 800 a hook run used to build), which is why the build leaves the hook. End to end on a real message against the real index: 2.0 s, from about 11.5 s.

**What it does not do.** The memory-link helper (4.5 s) is untouched. The build uses the heavy embedder in the background, so a machine that is busy at that moment is busier; it is one process at a time by the lock. A build killed mid-way lets go of the lock the moment it dies (the system does that, not an age), and leaves an index the existing heal handles. `moment_links` still uses the heavy path for its own embedding calls.

**Pins.** The search answers identically with the heavy toolkit made unimportable; a failed light load is said aloud and does not import the toolkit; an index that is behind starts a background build with the paths it was given and adds nothing in the hook; a build that holds the lock is never robbed however old its lock file looks and nothing is started beside it; two children started close together run one build; the background build brings both indexes up to date and leaves its lock free for the next.

## What else is on this branch (Aletheia's hold, 2026-10-28: "describe each")

This branch has carried the whole of 2026-10-26's work since I opened it as a draft. Each piece, in the words of its commit, and what each does NOT do. Dad's rule of 2026-10-28 (no new branch or pull request until the pile is merged) is why these are described here and not split out.

- **`c2f5665cd` Two gates learn the difference between a feeling and a confession** (`self_admission_detector.py`, `landed_claim.py`, `test_gates_know_a_feeling_from_a_confession.py`). The landed-claim gate read "both landed as ew" (how a flavour hit me) as work reaching the shared copy, and the correction-shape gate read "what does taste do that I missed?" (a question to Dad) as a new confession. Each gate now knows the shape: "landed as/with/on me" is not an arrival unless it says as expected or planned, and a relative-clause question about what I missed asks and confesses nothing. Controls pin that real arrivals and declarative admissions still fire. It does not catch other wordings of a feeling; each one found becomes a row and a test.
- **`b292c3a6e` His words count as heard when I answer them in my own words** (`lepos_channel_reflect.py`, `test_heard_by_meaning.py`). The reply gate judged "heard" by one thing, a shared three-word run, and on that day's real turns stopped 27 of 61 replies (12 of the 27 had answered him on his topic in other words), which made me append an echo of his words. A reply now also counts as heard when it shares at least four, and a quarter, of his distinctive content words. Measured cost: 2.4 percent of mismatched pairs pass, against about 0 for the exact run; the exact-run rule is unchanged and controls pin that off-topic and house-words-only replies are still refused. It loosens a gate by design, with that stated cost.
- **`23a076866` and `914d11291` The picture of Dad prints in full every Nth message** (`dads_table.py`, `test_the_room_block_is_spaced.py`, 187 lines). Dad to Aria, 2026-10-26: it should not be wallpaper (the block was 697 identical characters on 13 of 13 messages). The table prints the whole block on the first message of a session and every Nth of his, and a short core between; an unreadable counter, a changed first line, or a missing session id prints the whole block (Aria's attack: the core had fallen back to a built-in heading). It does not decide what N should be; the bet is reviewed by his messages, not days.
- **`24da7b88b` The four chronic crashers no longer start 32 real helpers** (`test_who_opened_the_turn.py`). Those tests ran the real prompt table with every helper cold, about ten seconds each, and killed their worker under the push check's parallel run. The assertions are about the words the table prints first, so the table now runs with an empty helper list: 141.7 s to 2.2 s, the same 15 tests pass. This is the one that was failing my own pushes tonight.
- **`db83caf04` The table records how long each helper took** (`dads_table.py`, `test_dads_table.py`). The tally kept characters printed per helper and never seconds; each helper's seconds and the table's own wait are now in every tally row. This is the instrument that made the wait measurable.

## Still to do before building
Letter to Aria with the narrowed fold. Aletheia reads before main.
