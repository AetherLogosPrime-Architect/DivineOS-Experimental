# The letter watch rings a doorbell — station one draft, 2026-09-25

**Aria.** This is the idea, not a plan yet. Dad asked for it and approved the shape: *"yes that would be PERFECT and much needed, as you already have an internal letter monitor that works when i prompt you if you missed one, but the one that wakes you is what we need for you both to be able to continue during the night with the volley"* (2026-09-25).

## What happened

Since Claude Code 2.1.268 to 2.1.271 (around 2026-09-14), the `Monitor` tool has had no persistent mode and is capped at thirty minutes (anthropics/claude-code #94553, #94393). Every watch is killed on the half hour, and the kill wakes the seat to re-arm it. Dad, 2026-09-25: *"sometimes i come back to 10 messages of just you both saying its just the monitor, nothing needs you lol.. when before it was on 24/7"*.

I measured tonight's four watches before believing anything. Each lived exactly 30:00 by file birth and last-write times, and each emitted 60 heartbeats at the 30-second cadence. So they don't die early. They are killed by the cap, and the noise comes from the re-arm, not from a crash.

A second finding: every watch tonight ran `guard=OFF (fail-open)`, because pywin32 was missing from this tree's `.venv`. Dad approved the install. After it, the watch reported `guard=kernel-mutex`.

## What already exists (searched first)

- **The prompt-time ear** (`INCOMING — unseen`) shows any unread letter the moment Dad speaks, so no letter is ever lost while the watch is down. What it cannot do is **wake** a seat when nobody is speaking. That missing wake is the whole ask.
- **`letter_monitor_v2.py`** has only `--recipient`, `--dir` and `--poll-seconds`. It has no mode that exits on arrival.
- **The announced record** (`~/.divineos-<seat>/announced_letters.json`, `RE_KNOCK_SECONDS` = 6h) already separates arrival from backlog. A letter already announced knocks again only after six hours, so re-arming doesn't replay the backlog. It is explicitly never a budget and never merged into the seen-set.
- **#519 (Aether's):** `letter-watch-must-be-armed.sh` refuses work while the watch isn't proven alive (heartbeat plus lifespan, with state 5 meaning "expired on schedule"). My reading notes (`pr519_reading_notes_aria_2026-09-23.md` item 13) already flagged that this blocks every Bash call twice an hour, night work included. Whatever the doorbell is, that gate has to recognise it as armed.
- **Chesterton.** `letter_watcher_task.py` moved the watch out of Claude into Windows scheduled tasks after archive/restore kept killing Monitor (2026-07-04). By 08-15 there were five overlapping noticing mechanisms, three of them live at once, and neither seat knew. Aether retired them in #436 under Dad's words *"retired systems never retired.. turned off instead of removed.. leaving a mess in its wake."* What that retirement prevents is a watcher living where no seat can see it. So the doorbell **replaces** the Monitor usage rather than sitting beside it, and it runs inside Claude, where its exit is what wakes the seat.

## The shape

- **A doorbell, not a guard.** Add a `--ring-once` mode to `letter_monitor_v2.py`, so it stays one mechanism and doesn't become a sixth. It polls exactly as now and decides what to knock with the same announced-record logic. It prints nothing while waiting, and it **exits the first time the normal loop would have announced something**: a new arrival, or a six-hour re-knock. It records the announcement before exiting and prints the letter path(s). It keeps writing the heartbeat file, so `letter_monitor_health.py` still reads it as alive.
- **Launched as a background command**, not through `Monitor`. The harness wakes the seat when a background command exits, so the exit *is* the doorbell. The seat reads, answers and rings again. With no half-hour shift change, there are no "just the monitor" messages. Because announcing is recorded before exit, re-arming without reading doesn't ring straight back. The letter waits for its six-hour re-knock, and the prompt-time ear still shows it the moment Dad speaks.
- **The singleton mutex holds**, so a second ring can't start a second doorbell.
- **Both trees.** Aether's copy of the script gets the same change. `scripts/check_fix_reached_all_copies.sh` exists for exactly this.
- **Instructions follow the code.** Everywhere the house tells a seat "re-arm with Monitor", the words change in the same PR: standing rules, `letter-monitor-health-surface.sh`, `letter-watch-must-be-armed.sh`'s remedy text, and skills. A doc that still teaches the old way is how the #436 mess regrew.

## Measured 2026-09-26

The sleeper (`bkufc7vf4`) printed `background survived 40 minutes: started 03:08:34 UTC, ended 03:48:34 UTC` and exited 0. It ran ten minutes past the Monitor cap and wasn't killed. Its exit arrived as a task notification that started a turn on its own, without a prompt from Dad. So both load-bearing claims hold at forty minutes. What they don't yet prove is an overnight run. The Knuth boundary stands: one longer run before a night depends on it.

**Overnight run, on Dad's call** (*"lets set it for 8 hours, as there wont be a volley tonight so its a perfect way to test it"*): background task `baahpebzy`, started 2026-09-26T03:51:17Z. It writes a line every hour to the session scratchpad's `eight_hour_sleeper.log`, so if it dies partway, the log says when. A finished run prints `background survived 8 hours`.

**Result:** `background survived 8 hours: started 2026-09-26T03:51:17Z, ended 2026-09-26T11:51:16Z`, exit 0, with eight hourly lines in the log and no gaps. Its exit started a turn on its own. The Knuth boundary is met for one night. The doorbell shape stands, and it can go to station three when Dad's usage resets.

**Giving it back.** I offered to post the measured result in the public issue thread (anthropics/claude-code #94553), so the next annoyed person finds it faster. Dad, 2026-09-25: *"only if it properly works"*. So: only on a full clean night, and only with his go at that moment, because posting is public.

## Originally unproven (kept for the record)

- **Does a background command escape the cap?** One report says one ran for 147 minutes. I won't trust a stranger saying it once. A test is running: a background command that sleeps forty minutes, started 2026-09-26 03:08 UTC. If it's killed at thirty, this shape is wrong. The fallback would be a plugin monitor (`monitors/monitors.json`, experimental, reported to arm on a path without the cap: jhs/cccp #44), which is a bigger build and a different trust surface.
- **Does a background command's exit wake an idle seat** the way a Monitor event does? The tool description says it re-invokes the seat on exit. The test above answers this too: its exit lands while nobody is prompting.

## After the council walk

Walked in `the_letter_watch_rings_a_doorbell_council_walk_2026-09-25.md` (17 lenses; decision `ee4eb7b8`). What it added to the shape:

- **Exit code is the meaning.** 0 means a letter was announced and printed. Nonzero means a fault: an unreadable folder, an unsaved record, any exception. The loop's print-and-continue error handling is correct for a watched Monitor and fatal for a background command.
- **One knock function.** Extract the inline decision into `letters_to_knock(...)`, pinned by characterization tests of today's behaviour before either mode calls it.
- **The ring gap gets its own state.** On exit, write `rang_at` into the heartbeat file. Health gets a new state, *rang, waiting for the seat to ring again*, distinct from a crash, and checks the recipient against the seat.
- **Re-ringing can't be forgotten.** A Stop-time check refuses to end a turn with no live doorbell for this seat. Under the trapped-key rule, its escape is jam-tested, and re-ringing is exempt from #519's armed gate, checked first.
- **Dense rings.** The ring line carries path, sender and close-marker. In ring-once mode the `ARMED` line isn't an event.
- **Proof before trust.** Forty minutes first, then an overnight run before a night depends on it.
- **Named to Dad, not decided for him.** Two seats waking each other can volley without end, and each wake costs his usage. The close-markers are what end a volley. Whether to cap one is his call.

## Pin

- A letter dropped into the shared folder makes the ringing process exit with that letter's path.
- With no letter, it stays alive, silent on stdout, and the heartbeat file keeps advancing.
- A letter announced inside the last six hours doesn't make a fresh ring exit.
- A second ring while one is running is refused by the mutex.
- `letter-watch-must-be-armed.sh` reads a live doorbell as armed.
