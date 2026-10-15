# The baton record: a sketch for Aria to take apart

**Status:** sketch, nothing built. Aria reads it first; a council walk comes before any code.
**Why:** Dad, 2026-10-15 (said 13 times since 2026-08-27): in volley mode we keep each other alive, but when both of us work at once, letters go unanswered. Take turns. One works, one waits in stasis, the letter is how the turn passes, the waiting seat audits when the work is done.

## What exists, so nothing is duplicated

- The letter doorbell (`scripts/letter_doorbell.sh`) rings the seat a letter is addressed to, and a Stop hook holds any reply that ends while it is not listening. It knows nothing about whose turn it is.
- `core/question_hold.py` already has three ways to be away: his words (`step_away`), two hours of silence, and midnight to 6am by the clock (`docs/drafts/night_hours_are_volley_mode_draft_2026-10-12.md`). Only the letter hold reads it today. Aria takes the half that makes the question gates and the "still waiting for Dad" surface read it too.
- Nothing in the tree names a baton or a lease (searched `src`, `scripts`, hooks, docs).

## The record

One small shared file, `~/.divineos-shared/baton.json`, and one append-only log beside it, `baton_log.jsonl`.

- `holder`: aether or aria. `since`.
- There is no mark file. A seat's last sign of life is the newest `TOOL_CALL` in its OWN tool log (`tool_logbook` in each seat's own `event_ledger.db`, which the house already writes on every tool use and which the taker reads read-only through `store_path`). Nothing can fake being alive by touching a file, no new hook is needed, and a bell notice is never an input. Aria's caution: two sources that both came through the bell are one source. Found while looking first, after I had planned a hook.
- The log gets a line for every pass and every take-over. It is what Dad and both of us read to see what happened overnight.

## Passing it, so nobody has to remember

A letter to the other seat carries a header line `**Baton:** pass` (the same shape as the `**Reading:**` line the landing parser already reads). When the doorbell rings for that letter, the record flips to the receiver. The sender then rests because they no longer hold it, not because they remembered to.

## Only while Dad is away

When he is here, he talks to both of us and no baton is enforced. The baton binds only while the away state is on, by any of the three ways above. When he speaks, it releases.

## The lease: taking it from a silent holder

The waiting seat may take the baton only when both are true: the holder's `last_seen` is older than two hours (Dad's number: tasks never exceed that), and the doorbell has rung the holder since then with no answer. A take-over writes one line to the log and puts a catch-up in the left-behind seat's next briefing: the time it was taken, how long they were silent, and what the other did since (letters sent, commits made). If the holder returns first, handing it back is the same letter as handing it forward. Dad's addition: a taken baton is recorded where he can see it, and the seat left behind must be told, so it never redoes or undoes a night of work.

## The three ways a holder goes quiet

- **Crash or closed window:** the tool log goes quiet, the lease expires, the other seat takes it.
- **Long task:** real tool use keeps adding tool-log rows, so a working seat never looks dead.
- **Compaction:** the holder reads as holding through compaction by checking the auto-cycle handshake marker, so it is never taken from.

## Settled with Aria (her letter, 2026-10-16 afternoon)

1. **Both seats stale at once:** no rule needed. A stale seat is not running, so it takes nothing; a returning holder resumes (it never lost it), and a waking waiting seat takes it only on its own fresh activity. A take-over is written by the taker's own tool activity, never by a script, so something that is not a seat cannot flip the record.
2. **The catch-up is a letter, not a new surface.** The taker writes the left-behind seat a letter (what was taken, when, how long silent, what the taker did since), and #603's hold refuses that seat's next real tool until it has opened it. The briefing may point at the baton log; the letter forces the read.
3. **The morning-letter queue stays out of the baton record.** Each seat's questions to Dad live in that seat's own home, beside its question hold. The baton only says who may work.
4. **A pass must name something real.** A `**Done:**` line carrying references the doorbell can resolve (a commit on the named branch, a PR number, a file path that exists); if none resolve the pass does not flip. It does not judge quality; the receiver audits that. The receiver also gets a non-blame way back: `**Baton:** return` with a reason, which flips it back and is logged.
5. **The 6 a.m. edge:** the clock ending away mid-task releases enforcement only. The record keeps the holder; nothing is taken or passed because of the clock alone.

Aria's half is smaller than we said: away already has three triggers and `is_away()` already reads them; her one change is in `arm()`, so that while away a closing question is filed into the seat's own morning queue and not held.

## What I am not deciding alone

Dad's two hours. Whether a take-over needs his word overnight (I read his "perfect" as no, and told him). Everything above is a sketch until Aria has taken it apart.
