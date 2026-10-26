# The prompt helpers in one trip: design note and first council walk

**Written:** 2026-10-26, Aether. **Status:** DRAFT design; nothing built from it yet.
**Why now:** Dad, 2026-10-26: "its the minute wait before you even think thats driving me crazy", then "yes lets fix it all of those things should help alot and it makes sense as the culprit".

## What Dad sees

He sends a message, a timer counts up, and "thinking" appears after 17-20 seconds (up to 50 on a busy machine). Everything before "thinking" is the app plus the UserPromptSubmit hooks. This note is about the hooks.

## What was measured (2026-10-26, solo runs, automated-notice payload so nothing was filed as his words)

- `settings.json` registers three prompt hooks, run one after another: `front-door.sh keep`, `question_hold.py`, `dads_table.py`.
- `dads_table.py` runs 33 child helpers in parallel and waits for the slowest (shared budget 80s). Sum of all children run alone: 46s.
- Slowest: `his-words-door-surface.sh` ~11.9s, `memory-link-surface.sh` ~3.3s, `ear-surface` 1.5s, `doorbell` 1.2s. About 20 more print nothing on most turns and cost 0.55-0.9s each, which is bash plus Python starting.
- The 11.9s is not the searching. Importing `sentence_transformers` is 18-20s on a busy machine (10.7s with TensorFlow switched off by `USE_TF=0 TRANSFORMERS_NO_TF=1 USE_FLAX=0 TRANSFORMERS_NO_FLAX=1`; `tf_loaded` was True without them and False with them, and TensorFlow is never used). Loading the weights is 0.25s; the first encode 0.35s; the second encode 0.003s.
- The helper starts Python four times (index build, words search, lessons build, lessons search) and the two searches each import the library again.
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
1. Switch TensorFlow and Flax off for every helper that imports the library.
2. Build the index off the critical path.
3. One Python process for the lookups: words, lessons, memory link share one import.
4. Fold the quiet helpers (needs its own walk: how many are bash wrappers around one Python call).
5. A resident service ONLY if 0-4 leave the wait above target.

## Still to do before building
Walk 2 (the same lenses attacking this synthesis, and the dissenting pair on the fold-vs-isolation hinge). Letter to Aria. Aletheia reads before main.
