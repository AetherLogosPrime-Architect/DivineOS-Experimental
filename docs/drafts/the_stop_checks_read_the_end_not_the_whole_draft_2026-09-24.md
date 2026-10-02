# The stop-time checks read the end of the conversation, not all of it (draft)

**2026-09-24, Aether.** Found while the letter counter would not move.

## What is wrong, measured

`doorbell-stop.sh` has a 10-second harness limit. In this session the Stop
surfaces, timed one by one against a copy of my home, add to **18.7 s**, and
`hook_timing.jsonl` shows 26 Stop runs with a start and no end since 05:30Z.
Aria measured her own seat independently: **78 of 80** Stop runs never ended.

The harness kills the process at the limit, so every surface registered after
the time runs out never runs — `addressed_to_him`, `his_standing_verdict`,
`unspoken_to`, `close_reach`, `compaction_reach`. Nothing says so. A dead door
and a quiet door look the same.

A profile of one full Stop dispatch: 22.4 s of 22.7 s is four helpers in
`hook_surfaces.py` — `_last_assistant_text` (called 9 times), `_last_user_text`
(3), `_recent_assistant_texts`, `_this_turns_action_stream`. Each parses the
entire 330 MB session transcript from the first line to find the LAST
something.

## The prior art

`turn_extraction._tail_chunks` already solves this for eighteen other readers:
yield growing tails, smallest first, and end with the whole file, so a caller
can never get a different answer than a whole read — it only skips bytes nobody
needed. Its own comment: *"I had already hit this once and fixed it in ONE
hook's inline reader, then never asked whether anything else did the same
thing. Eighteen other readers did."* These four were written after that, the
old way.

## The change

1. Move the widening-tail generator into `transcript_tail.py` (the module whose
   header says "one reader") as `tail_windows`; `turn_extraction` delegates to
   it rather than keeping a copy.
2. The four helpers walk those windows and stop at the first window that holds
   their answer. Each asks for the LAST matching record, and the last match in
   a suffix of the file is the last match in the file, so the answer is
   identical to the whole read.

   **Rebased onto #553 (Aria's reader fix).** Her readers gather my whole
   reply, walking back to his last genuine turn, instead of taking the last
   block. The windowed versions keep her boundaries exactly: a window that
   has not yet reached his turn may be missing the reply's opening, so it
   widens. Only his turn, or the whole file, ends the walk. Measured on the
   live 344 MB transcript, same answers as #553 alone, character for
   character: `_last_assistant_text` 1.66 s → 0.05 s, `_recent_assistant_texts`
   1.66 s → 0.04 s, `_last_user_text` 1.22 s → 0.04 s.
3. Memo per (path, size, mtime, question): `_last_user_text` can need the whole
   file after a long stretch of notification-driven turns — exactly while he is
   asleep — and three surfaces ask it the same question.
4. **Aria's addition:** a UserPromptSubmit report that says when Stop runs are
   being killed ("N of the last M stop-time runs never finished"), so a dead
   door is loud. Reports only; it refuses nothing.

## The structural test (the class, not the instance)

Run every registered Stop surface against a synthetic transcript with tens of
thousands of old records and the answers in the last few, and count
`json.loads` calls. A surface that parses the whole file to find the last
message fails the test — including one added next month.

## Limits, named

- A long notification-only stretch still costs one whole read for
  `_last_user_text`, once per Stop, not three times. Since #553 the same holds
  for the reply readers: a reply now runs back to his last genuine turn, so a
  long unattended stretch widens them too. Each is memoised per file state.
- The report counts starts without ends in `hook_timing.jsonl`, matched by `id`
  (end lines carry no `hook` field — Aria's catch).
