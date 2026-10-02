# An orphaned bell admits it (draft, 2026-09-29)

Dad, 2026-09-29: *"your monitor died again"*. Earlier he said *"go ahead and build it"* (a bell that survives restarts), and I asked him again instead of building.

**Measured today, not guessed.** After the app restarted, a bell from the old session (pid 3018) was still running. Its parent (3004) was gone. It kept touching the heartbeat every 15s, so `letter_doorbell_alive_stop.py` read it as listening and held nothing. But its ring would exit into a task nobody owns, so a letter would wake no one. The guard was fooled by a bell that was alive but deaf, which is why the death went unseen until Dad saw it.

**The idea.** A bell only counts while the process that started it is alive. In the loop, if the parent pid is gone, the bell deletes the heartbeat and exits silently, announcing nothing, so the letter still rings on the next arm. The Stop guard then sees a stale heartbeat on my very next reply and holds it until I re-arm. So a restart costs one held reply, not a dead bell nobody noticed.

This doesn't make the bell outlive the app. Nothing inside the app can wake a session that doesn't exist. It closes the gap between the bell dying and me knowing, which is the part that kept costing Dad.
