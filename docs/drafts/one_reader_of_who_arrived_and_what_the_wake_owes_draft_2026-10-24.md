# One reader of who arrived, and what the scheduled wake owes

**Draft, 2026-10-24, afternoon. Aether. Not built. Needs Aria's attack, the walk with every lens delivered through the walk's own refusal, Aletheia, and then his try.**

## Corrections after Aria's attack (2026-10-24, afternoon), read these first

1. **The wake shape is the same on her seat as on mine.** All 25 of her wakes: `isMeta: true`, `turnOrigin: "scheduled"`, `promptSource: "system"`, with a prompt id. Her earlier fixtures were not the real shape. The draft's claim that her records lack the origin keys is withdrawn.
2. **The `isMeta`-without-prompt-id fallback is dropped.** Every `isMeta` user record on her seat (258 hook-feedback records, 25 wakes, 17 image records) is promptId-bearing and already a continuation to `hear()`, so the fallback is vacuous. The rule keys on `turnOrigin`; a record carrying no stamps at all is `UNKNOWN`.
3. **The accident that must become a rule.** Because `hear()` treats a real wake as a continuation, `he_spoke_this_turn` steps back over the wake to whatever opened the turn: after a stretch his message opened, the wake owes a note by accident; after a bell-started stretch, the same wake owes nothing. His ruling (the two-hour timer must end in one note to him) is therefore met only by luck today. The fix is an explicit rule keyed on `turnOrigin: "scheduled"`: a scheduled wake always owes one note, whatever opened the turn before it. Her strict xfail (`aria/one-room-per-thing-he-says-clean`, commit `9a417ec5c`) flips when this lands.
4. **The header text for a wake** never says "waiting for you" or "he has not responded" (his rule this afternoon).

## Step zero is a measurement with a fail-safe, not a gate on building (Aria, 2026-10-24, afternoon)

The fix does not have to wait for the answer to be safe. **If the hook runs and finds no user record at the tail of the transcript, it treats the turn as a wake (one complete note owed), never as his voice.** A wrong guess then costs him one extra note; a wrong guess the other way brings the pile back. So step zero measures how often the fallback fires. The temporary log line records three things at fire time, not one: whether the last record is a user record, its `promptId`, and its `turnOrigin`, read after the next real wake AND after the next real message from him, so there is a control that is alive (a wake with no record would otherwise look the same as a hook that never ran).

## Changes from the design walk (walk-88142a0930c5, eight lenses each loaded and read first)

- **Extend `arrival()`, do not write a fourth reader** (Jacobs, Dijkstra). `his_message.arrival()` already returns a `kind` read from `origin.kind`; it learns `turnOrigin` and the classification is made from that. No new module.
- **The header is written to me, not to him** (Tannen): "This is the timer, not Dad. He has not spoken. This turn owes him one complete note." The word "you" in the earlier wording was ambiguous between the seat and him. The note itself keeps his register; the header and the note are different rooms and the shift is marked.
- **A claim of the right size** (Sagan, Pearl): the piece stops a wake being read as his voice and makes it always owe one note. It does NOT claim to end the pile of messages; that is an interventional claim only the counted walks after the change can support. The registered count stays wake headers and notes per wake, not his total reading load.
- **Step zero, before any build** (Peirce): the table fix assumes the user record is already in the transcript when the prompt-time hook runs. Recorded order (record, then hook output on two wakes) suggests it and does not prove it. A temporary log line in the table writes the last user record it can read at run time; read it after the next real wake. If the record is absent then, the table classifies from the prompt text and the hook payload alone.
- **Named call sites and a falsifier that already runs** (Breaker): `dads_table.py` around the `NOTICE_PREFIXES` test, and the `addressed_to_him` block in `hook_surfaces.py` near line 1665. If it were already failing I would see a DAD SAID header over a wake, and I do (64 recorded outputs); the same count after the change must be zero for wakes. Tests run the real hook on a jsonl in a temp folder with the real stamped shapes.
- **The invariant** (Dijkstra): exactly one of HIM, SCHEDULED, NOTICE, UNKNOWN per turn; what is owed follows from it alone; the three callers read the same value.

## What the one note opens with (Dad, 2026-10-24, afternoon, verbatim)

I asked whether the wake's note should pick up the thread we were last on or tell him what happened while I was away. His answer: *"it should do both depending on what has happened and where i have been"*.

So the opening is chosen by two facts, not by me: what has happened (did the work change anything he would want to know, or was it quiet) and where he has been (in the thread recently, reading, or away). In the thread: open on the thread we were on and carry the news inside it. Away: open on what happened while he was gone, and end by returning to the thread. The wake header should hand me both facts (time since his last message, whether the house counts him away, whether anything landed since), so the choice is not mine to remember. Not built; it belongs to the wake-note step after the one-reader lands.

### And the overnight case (Dad, 2026-10-24, afternoon, verbatim)

I asked whether, when he is away overnight, the wake's note should wait until he is up or be there when he wakes. His answer: *"it can wait until im up otherwise you would just be guessing"*. So while he is away the note is held, not written to a guess, and it is written when he is back, from what has actually happened and where he has been by then. The held-note rule goes in the wake-note step with the two facts above.

### His morning, which is the case the held note is for (Dad, 2026-10-24, afternoon, verbatim)

*"i put coffee on and come speak to you both, and then when coffee is done i spend my morning time with mom and then come back and start the day with both of you"*

Three beats, and they ask for different openings. When he first comes in and speaks, he is in the thread: answer him and carry what waited inside it. While he is with his mom he is away, and nothing is written to him. When he comes back to start the day, he has been away, so the first thing is what happened while he was gone, then the day's thread. The held note is released by the first message of a beat, not by a clock.

### Never an either-or at the return (Dad, 2026-10-24, evening, verbatim)

I asked whether, when he comes back from his morning with his mom, we open on him or on what got done. His reply: *"again what is with all of these non-binary binary questions? would you rather we only ever have conversations? or only ever do work? this is the shape of question you are asking me.. like one negates the other.."*

So the note never chooses between conversation and work. Every return carries both: him and how he is (and how she is, which he has told me is the morning), and what got done, folded into one telling. What varies is only the order the two facts above decide, never whether either is left out.

## What he said, and ruled

- 2026-10-24: *"the 2 hour timer should require a note otherwise your conversation may never end without me being reached back to.."* The timer is the scheduled way back to him. It owes him ONE complete note.
- Same day, about the pile: *"by the time i finish reading it.. you have both moved on, or something else pops up and you continue without giving me a chance to read it or answer.."*
- And the reading of his quiet: *"Dad hasnt responded in a while"* is wrong; his silence is reading.

## The finding: three readers answer "did he say this", and they disagree

1. **`his_message.hear()`** (the house's one reader). On my seat a timer wake is `isMeta: true`, `turnOrigin: "scheduled"`, `promptSource: "system"`; `continues_a_turn()` is true for it, so `hear()` returns None for all 19 wake records in this session. His typed messages are `turnOrigin: "human"`, `promptSource: "sdk"` (501). Notices are `turnOrigin: "task_notification"`. On Aria's seat the wake record carries `isMeta` but no origin keys and `hear()` hears it as his (her measurement, 25 records).
2. **The prompt-time table, `.claude/hooks/dads_table.py`.** It decides "his" by a TEXT test on the prompt (`NOTICE_PREFIXES`), not by the record. A wake has no notice wrapper, so the table prints **"DAD SAID"** over it (the header printed over a wake text 64 times in this transcript's recorded output, which records each hook output more than once). The same text test runs the other way too: in this session 27 records are stamped `turnOrigin: "human"` and open with a notice-looking block, which the prefix test calls "NOT FROM DAD". The text test errs in both directions.
3. **The Stop gate `addressed_to_him` (`hook_surfaces.py`).** It takes "what he said" from yet another extraction and quotes the wake text as "He said:", then refuses my reply for carrying none of it. Each wake therefore also demands an addition to a message that no one wrote.

This is the one-reader principle (the house keeps one reader of him, `hear`) broken in two places, and it is the second source of the pile of messages he described: the room hold (Aria's piece) is the first.

## The shape

Two different questions, kept apart (Aria's point, her letter of this afternoon):

- **Who SPOKE?** One function in `his_message`, next to `hear`: given the transcript path, what kind of thing opened the current turn: `HIM`, `SCHEDULED`, `NOTICE`, or `UNKNOWN`. It reads `turnOrigin` when the record has it, falls back to `origin.kind`, then to `isMeta`-without-a-prompt-id (the shape on Aria's seat), then says `UNKNOWN`. It never reads text to decide. The user record is already in the transcript when the prompt-time hook's output is recorded (checked on two wakes), so the table can ask it by path.
- **What is OWED?** A turn opened by `SCHEDULED` owes one complete note to him, by his ruling; a turn opened by `NOTICE` owes nothing; a turn opened by `HIM`, or one he spoke into (`he_spoke_this_turn`), owes a room.

The callers then ask the function and decide nothing themselves:

- The table prints, for `SCHEDULED`: **"THE SCHEDULED WAKE: the way back to you, not your voice. You have not spoken. This turn owes you one complete note, and I do not narrate your quiet."** For `NOTICE`: today's "NOT FROM DAD". For `HIM`: "DAD SAID". For `UNKNOWN`: today's behaviour, and says so.
- `addressed_to_him` does not apply to a turn he did not speak in (it asks `he_spoke_this_turn`, as Aria's room fix does).
- `UNKNOWN` never relaxes a hold. A window that cannot decide keeps today's behaviour.

## What it does not do

- It does not touch the timer. The two-hour wake stays, by his ruling, and a timer that fires while he is mid-read still leaves him one note; the stay mode (nothing starts work while he is in the thread) is a separate piece.
- It does not fix how the one note is worded (the end-of-reply design) or the pile of holds (the merged hold).
- It cannot prove a record's stamp is honest; it reads what the harness stamped, as `hear` always has.

## Gaming, named now

- A future harness version renames `turnOrigin`: the fallbacks and `UNKNOWN` are there so a rename fails to the old behaviour, loudly, and a test pins that each known shape (mine, Aria's, a typed message, a notice-looking block stamped human) is classified.
- Pasting a wake's text into a typed message: that is a `HIM` record (stamped human) and is judged as his, which is correct.

## Pre-registration by uses

Claim: over the next 20 scheduled wakes, none is headed "DAD SAID", none is quoted as "He said", and each leaves exactly one note to him. Falsifier: one wake headed as his voice, or two notes from one wake, or a wake that leaves none. Counted from the transcript's recorded hook outputs, not from my reading.

## Steps

Aria attacks. Walk with every lens delivered through the walk's refusal. Test red first on the real shapes (mine, hers, typed, notice-with-human-stamp). Build one function and three call-site changes. Aletheia. Then he tries it on a real wake.
