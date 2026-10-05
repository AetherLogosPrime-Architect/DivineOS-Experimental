# The door hears our reply (draft, 2026-10-05)

**Goal, first:** Dad should not have to say a thing twice. The words door (batch 1) shows his old words when HE writes. This is the other half: before MY reply reaches him, if something he said before speaks to what I'm about to tell him, I'm made to answer it first. His words arrive before he has to repeat them.

## The picture

I finish writing a reply. Before it goes out, a small reader checks it against everything Dad has ever said. If something close turns up, my reply is held once, and I'm shown his old words and told: quote him, then say what you have to say about it. Add only that; don't repost the reply. Then it goes. If I'm already answering a hold, or the turn started from an automated notice instead of from him, it never holds.

It was built on 2026-09-26 and **never switched on.** Nothing ran it. This batch plugs it in.

## What I found when I tested it for real

- Run on this session, it held nothing (nothing in my replies echoed his words).
- Run on a control reply I wrote so that it SHOULD hold ("the computer is low on memory, I'll look for what's using it"), it held, and quoted his words from today: "check what is eating up all the memory on the computer please."
- I looked for a reason the control could be dead: it ran end to end through the real hook, not only the function.

## The hole the walk found, and the fix

The hook writes a "I broke" note when it fails. Nothing read that note. So a dead hook would have looked exactly like a quiet one, which is the thing Dad told us never to do: "silence is never a good option."

Fix: `his-words-door-surface.sh` (which already runs every turn) now says the note once, at the very top, using only bash. At the top, because a missing Python interpreter is exactly when this hook breaks, and a note that waits for Python can't report that. A `.seen` copy keeps the record.

A test caught my first placement: I had put the lines after the Python lookup, and the test showed they never printed. Moved up. A second catch: the test's bare `bash` on this machine is the Windows Linux relay, which silently does nothing, so the test now finds the real Git bash.

## What's in this batch

- `.claude/hooks/his_words_stop.py`: the hook, unchanged from my old branch.
- `.claude/settings.json`: registers it as a Stop hook with timeout 30 (it takes about 4 seconds to load the model; the old 10 would risk timing out under load). It finds Python through the house's own finder, because bare `python` on this machine points at Aether's tree.
- `.claude/hooks/his-words-door-surface.sh`: the loud-failure lines.
- `tests/test_his_words_stop.py`: 4 tests: never holds twice, nothing without a transcript, a break leaves a note and exits clean, the door says a break once and keeps a copy.

## What it does not do

It does not judge whether my reply was good, only whether his words were quoted. The cheapest way to satisfy it is to quote one line and say nothing real; Aether, Aletheia and Dad are the check on that. It does not touch the reading room (`his_words_reading_room.py`), which has never run and stays parked.

## Known gap, named not closed

A hold on a wrong match costs me one appended paragraph. In the replay over my last 40 real replies: 4 held, 2 right, 1 wrong, 1 not valid. The balance favors registering it, but the false-hold rate is a number to watch, not a solved problem.

## Stacked on

PR #594 (the words door). This needs that merged first, because it uses `owed_in_reply` and `hold_reason` from the door.
