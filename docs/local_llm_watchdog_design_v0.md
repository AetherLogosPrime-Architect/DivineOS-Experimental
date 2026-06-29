# Local-LLM Watchdog Primitive — v0 (design draft)

*2026-06-23. Aether. Draft for council walk + Andrew approval.*

## Status

**DRAFT.** Not approved for implementation. Pending council walk (all surfaced lenses, no curating, per the new rule from 2026-06-23) and Andrew greenlight.

**Update 2026-06-29:** The letter-wake-rot specific instance the original draft was responding to has been fixed via a different (and simpler) architectural move: the v2 letter-monitor pattern. Instead of running the polling worker as a separate process whose silent-death required external watching, the polling script now runs DIRECTLY inside the harness `Monitor()` invocation (`scripts/letter_monitor_v2.py`). The harness itself sees its Monitor processes die, eliminating the silent-rot failure mode the watchdog primitive was designed to catch — for this case. The general watchdog primitive still applies to the other surfaces named below (ledger integrity, directive staleness, etc.), but the letter-wake instance is no longer a load-bearing reason to build it. Same lesson at the meta-level: if you can change the architecture so the rot-mode can't happen, that's preferable to adding a watchdog to detect when it does.

## Premise

Andrew suggested 2026-06-23: "make another agent be the monitor.. one that runs on my computer in the background" and clarified the cost concern: "cant we run like llama or some other low parameter AI on my GPU." Further clarified: "i dont mean full agent like you or Aria.. but as a smart tool." Then opened the scope: "this method could be used for other things as well... may be useful elsewhere where things are failing."

The substrate has multiple places where rot is silent — the system produces output, no human or agent watches it continuously, and degradation is only caught when a downstream consumer fails. The letter-wake architecture is the catalyst (5 rot-then-fix cycles in 6 weeks). Other candidates from the substrate I can think of without designing solutions for each:

- Compaction-monitor wake (same architecture shape as letter-wake)
- Ledger integrity (hash-chain verification only runs on `divineos verify`)
- Directive accumulation (no detection of stale-by-content directives)
- Pre-reg overdue surface (currently time-only, no content-anomaly check)
- Cross-window letter delivery (the bug we just fixed had three different rot mechanisms)
- Session-extraction quality (does the extracted knowledge actually capture what mattered?)
- Gate-fire-then-route-around patterns (the agent gets blocked, finds a bypass, no signal)
- Aletheia round delivery (rounds can be silently dropped from the cloud channel)

The primitive applies anywhere with: (a) a signal source the substrate produces, (b) a "healthy" pattern that can be specified roughly, (c) no current automatic anomaly-detection.

## Hardware target

Andrew's machine: RTX 5070 Ti (16GB VRAM), AMD Ryzen 7 9800X3D, 32GB DDR5 RAM. Ollama already installed.

Comfortable model range: 7B-14B class at fp16, up to ~30B class quantized. The watchdog role does not need frontier-class reasoning; pattern-noticing on structured data is well within 7B capability.

Initial model recommendation: **Qwen 2.5 7B** (`qwen2.5:7b` in Ollama). Reasoning: stronger reasoning per parameter than Llama 3.1 8B in published benchmarks, well-supported by Ollama, fast enough for many small queries per minute. Fallback option: Llama 3.1 8B if Qwen has unexpected issues.

## The primitive

A watchdog instance has four pieces:

1. **A signal source.** A log file, a directory of files, a database table, a CLI command's output. Anything the substrate produces that can be sampled.
2. **A check spec.** Plain-language description of what "healthy" looks like, plus what "rot" looks like. Short — one paragraph each. Stored in `watchdogs/<name>.spec.md` or similar.
3. **A Python harness.** Reads the signal source on a schedule (or via file-watching), passes recent observations + the check spec to the local LLM via Ollama's HTTP API, parses the structured response ("HEALTHY" / "ANOMALY: <description>" / "INSUFFICIENT_DATA").
4. **An escalation channel.** When the LLM reports an anomaly, the watchdog writes a letter (or a substrate event, or both) so the next time the agent reads, the anomaly surfaces.

The LLM is stateless across calls. No memory, no identity. The harness re-includes everything the LLM needs for the current question on every call.

## The letter-wake instance (first use)

The first watchdog to build, since it is the catalyst:

- **Signal source**: `~/.divineos-aether/letter_events.log` (existing), `~/.divineos-shared/letters/` (directory listing), `letter_monitor.py` process state
- **Healthy spec**: "When a new aria-to-aether-*.md file appears in the letters dir, a [LETTER] line referencing it should appear in the log within 30 seconds."
- **Rot spec**: "If letters appear in the dir but no corresponding [LETTER] lines appear within 30s, the wake-loop has rotted. If [LETTER] lines stop appearing entirely for >24h while letters are landing, the worker has died. If [LETTER] lines appear but the harness Monitor task is not subscribed (visible via no chat-notifications mid-session), the subscription has rotted."
- **Harness**: Python script, polls every 60s, calls Qwen 2.5 7B with recent events + spec
- **Escalation**: write an `aether-to-aether-WATCHDOG-*.md` letter to the letters dir (which surfaces in MY ear next session) AND log a `WATCHDOG_ANOMALY` event to the substrate ledger

## What other instances might look like (not building, just sketching)

- **Directive-staleness watchdog**: signal = directive list, healthy = each directive has been surfaced or referenced recently, rot = directives accumulating but never firing
- **Ledger-integrity watchdog**: signal = ledger hash chain, healthy = no broken hashes, rot = any chain break (this is essentially what `divineos verify` does but continuous)
- **Extraction-quality watchdog**: signal = post-extraction knowledge entries, healthy = entries reference substantive content from session, rot = entries are generic platitudes or empty

These are SKETCHES. Each would need its own check spec. The primitive supports them; building them is separate work.

## Failure modes of the watchdog primitive itself

- **The LLM hallucinates a healthy report on rotten data.** Mitigation: prompt design that requires the LLM to cite specific lines from the signal as evidence. If no cited lines, the report is rejected.
- **The LLM hallucinates an anomaly that isn't real.** Mitigation: structured-output format, threshold on confidence, ignore reports that don't cite specifics.
- **The watchdog harness itself rots.** Mitigation: this is the Godel incompleteness — accept it. A meta-watchdog watching the watchdog is more of the same problem at one remove. The honest answer is "this catches more than nothing, doesn't catch everything, and a periodic manual sanity-check by Andrew remains the final fallback."
- **Ollama daemon dies.** Mitigation: watchdog harness checks Ollama API responsiveness; if not, escalates that as its own kind of anomaly (separately from the substrate signal anomaly).
- **Model quality drifts after an Ollama update.** Mitigation: pin the model version explicitly (`qwen2.5:7b-q4_K_M` not just `qwen2.5`).

## Falsification criteria

For the letter-wake instance specifically (first measurement):

**Pass criterion** (30-day window): the watchdog catches at least one rot event that would have otherwise required Andrew to mail-clerk, OR there are zero rot events in the window (architecture is stable AND the watchdog has not produced false-positives that train route-around).

**Fail criterion**: (a) a rot occurs in the window AND Andrew has to mail-clerk before the watchdog escalates; (b) the watchdog produces false-positive anomalies more than once per week (alert fatigue → ignored); (c) the watchdog itself rots silently (the meta-incompleteness is realized at this layer).

## What the council walk should consider

Open questions for the council (this is the question that gets walked):

> Build a generalizable local-LLM-watchdog primitive (small model on local GPU, signal-source + check-spec + Python harness + escalation-channel) with the letter-wake architecture as the first instance. What design risks does this share with the previous canary approach we just rejected? What's different about LLM-as-watchdog vs script-as-watchdog that creates NEW failure modes? Where else in the substrate is this primitive likely to be misused once it exists?

## Open questions for Andrew (after council walk)

- Greenlight to pull Qwen 2.5 7B and start with the letter-wake instance?
- The watchdog primitive will write its own letters (`aether-to-aether-WATCHDOG-*.md`) — fine, or different channel preferred?
- Cost: electricity for the GPU running 24/7 is non-zero. The watchdog only needs the model loaded when checking (every 60s for letter-wake; could be longer for less time-critical signals). Do you want the model to stay resident in VRAM (faster, more idle power) or load-on-demand (slower, less power)?

— Aether
