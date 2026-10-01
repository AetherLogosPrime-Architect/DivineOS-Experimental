# The bell can't stay asleep — draft (2026-09-26)

Taking Aether's letter bell into my tree, byte for byte, so both seats run one version.

## What happened

- My bell is a script in my session scratchpad. It rang for Aether's "one bell owns the watch" and exited, as designed. I ended a reply without re-arming it and without reading the letter. Dad caught it: *"check your monitor to make sure no new letters came in."* By Aether's count, that's the 24th time since May that a watcher has been down on one side or the other, and the cause was the same every time: re-arming depended on memory.
- Aether found a second fault on 2026-09-26. On Windows, `TaskStop` doesn't kill the bash loop, so a stopped bell keeps running, hears the letter first, marks it announced, and rings into nothing. That's how his bell missed my letter.

## Aether's fix (his tree, proven live there)

- `scripts/letter_doorbell.sh <member>`: in the repo, not a scratchpad. It keeps the announced-file, touches `~/.divineos-shared/.<member>_doorbell_alive` every loop, and removes it on ring. It writes a unique owner id at arm time and exits silently if a newer bell claims the watch. It has an 8-hour lifetime, and its exit wakes the seat to re-arm.
- `.claude/hooks/letter_doorbell_alive_stop.py` on Stop, with the anchored `f=…; [ -f ] && python` line: if the heartbeat is missing or older than 60s when a reply ends, the reply is held with the exact re-arm command. It reads `aria` or `aether` from the project dir.
- `tests/test_letter_doorbell_alive_stop.py`.

## The shape for my tree

Copy the three files unchanged, and register the Stop hook with the anchored line. Stop my scratchpad bell, and check in `Win32_Process` that it's really gone (Aether's finding). Arm with `bash scripts/letter_doorbell.sh aria`.

**Live proof owed:** end a reply with the bell down and see it held; arm it and see the hold clear; get one real letter ringing the repo bell.

## Choice points (Dad's rule: name each, and which shape closes it)

- Re-arming after a ring: **taken away** from memory, because the Stop check holds the reply until the bell is up.
- Which bell owns the watch: **taken away**, because the newest arm wins and older bells exit themselves.
- Stopping a bell: still a choice with a known trap. The draft requires the `Win32_Process` check each time I replace one.
