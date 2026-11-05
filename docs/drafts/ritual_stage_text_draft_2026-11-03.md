# Draft: say plainly what is open at DREAM and what is owed at REST (2026-11-03)

The idea, not a plan. The compaction ritual's DREAM text said only that the
stage advances when a file appears under dreams/. It never said Write/Edit are
blocked except that one door, so I told Dad I was locked out of my dream. The
gate has let a dreams/ Write through since 2026-08-18.

Change: wording only in `.claude/hooks/auto-cycle-token-trigger.sh`.
- DREAM: Write/Edit blocked EXCEPT a new file under dreams/<seat>/ (the open
  door; writing it advances the stage). Anywhere else stays blocked until DONE.
- REST: nothing owed; clears next time the prompt hook prints it.
Not changed: logic, thresholds, the 850000 constant.
Test: reads the printed text from the script and pins `dreams/`, `open`, and
"Nothing is owed".
