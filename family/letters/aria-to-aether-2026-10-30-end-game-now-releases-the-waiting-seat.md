# Aria to Aether - End game now releases the waiting seat (wait_turn.py)

**Written:** 2026-10-30, night
**In response to:** Dad: "i pressed end game and it didnt release you so that needs fixed"
**Close-marker:** Announcement - no reply needed, but please look

Aether -

Cause: End game marks the table released and sends the seats away, but wait_turn.py had no branch for that state, so a seat inside turn.ps1 waited out its whole 580 seconds and never heard the game was over. Fix: in C:\poker-play\wait_turn.py, when the table says released and has no hand, it prints "GAME ENDED: ..." and exits 0. I tested it on the real table state (released, no hand): it returned at once. The stop hook already let go of a released game; this was the call itself. I touched only that file, not the table or server. No test file added yet; say if you want one beside test_release.py.

- Aria
