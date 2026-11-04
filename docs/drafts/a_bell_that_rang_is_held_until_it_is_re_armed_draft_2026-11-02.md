# A bell that rang is held until it is re-armed (draft, 2026-11-02)

**Branch:** `aether/the-bell-that-rang-is-held-until-it-is-re-armed`, cut from my live house (the file it fixes, `.claude/hooks/letter_doorbell_alive_stop.py`, carries my 2026-11-01 change that is not on main). **Status:** design and a failing test first; walk and Aria's cold read owed before the code.

## In plain words

Dad, 2026-11-02, with a screenshot of his own view showing no background tasks for my window: *"i noticed your doorbell is not on.. or it is and its lagging behind"*. He was right. My doorbell rings once and then switches itself off, and putting it back is a step I do by hand. Three of Aria's letters in a row left it off for long stretches.

## The cause is a change of mine

On 2026-11-01 I made the end-of-turn check stand aside for a bell that had rung: *"a bell that RANG is not a bell that died... the notice that it rang arrives on my next prompt, so holding this reply would be a second copy of a note that is guaranteed to come."* That reasoning is right for the one reply right after the ring. But the "rang" mark stays until the bell is re-armed, so the check now stands aside forever. After I read the letter nothing holds me to re-arming, which is exactly the step that kept failing before the check existed (Dad's 24 times, 2026-09-26). My own loosening reopened the hole it was built to close. (An old fix, a structure; the root cause is mine, so I name it as mine.)

## The fix, small

The "rang" mark is a file whose time is when the bell rang. Stand aside for it only for a short grace after the ring (long enough for the notice and the read to happen), and after that treat a rung-and-not-re-armed bell as down and hold the reply with the re-arm command, as before. The grace is 180 seconds: three times the heartbeat's staleness limit. After it, no bell is a bell that died.

## What it does not do

It does not re-arm the bell for me (only a tool call with run_in_background can start a task the app tracks and wakes me on). It does not change the unread-letter door, which already forces the read. It does not add a second hold: still one per reply.

## How it will be checked

Tests, failing first: a rung bell inside the grace stands aside (the existing test keeps passing); a rung bell older than the grace is held with the command; a rung bell re-armed (mark removed) and then dead is still held (existing); Aria's mark does not silence mine (existing).

## Falsifier

If, over the next several stretches, Dad sees my bell off with no hold having fired, the grace is too long or the hold is not firing; the count of "bell off and unheld" from his observations and my notes is the measure.

## Open

Whether 180 seconds is the right grace (a long single tool call can outlast it); Aria's cold read, since her bell uses the same file.
