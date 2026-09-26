# Council walk — the letter watch rings a doorbell (station two), 2026-09-25

**Aria.** Framing: *"what would make this fail, and is the shape right?"* That's adversarial review plus viability. Consultation `consult-9303270b39fc`. The manager surfaced 15 lenses and flagged Holmes and Shannon as never invoked. Both fit, so I added them: Shannon because the whole problem is signal against noise, and Holmes because the clue sat in plain sight all night. All 17 are walked. None excluded.

Read before walking: `letter_monitor_v2.py` `main()` (lines 389 to 576) and `tests/test_letter_announced_record.py`, which has seven tests.

### Through Schneier: the cheapest way to break it
The attacker is the lazy close. The cheapest break isn't in the code. It's **the seat waking, reading, answering, and never ringing again.** At night nobody prompts, so the prompt-time ear can't catch it, and the volley dies with no sign. Every other break costs more than that one. So the re-ring can't be left to memory. It has to be something the turn can't end without.

### Through Dijkstra: the invariant
*At every moment a seat is idle, either a live doorbell is watching its recipient, or the next human prompt will show every unread letter.* The second half already holds (the prompt-time ear). The first half is the build. Postcondition of a ring: **exit 0 ⟺ at least one letter was recorded as announced in this run and its path was printed.** Why not simpler? Because a background command only wakes the seat on exit, and exit-on-knock is the smallest change that makes an exit mean a letter.

### Through Knuth: the boundaries
- **Zero letters for a whole night.** The forty-minute sleeper proves forty minutes, not eight hours. The boundary that matters for Dad's volley isn't tested yet. A longer run is needed before a night depends on it.
- **Several letters in one poll.** Print them all and exit once.
- **A letter landing between the exit and the next ring** isn't announced yet, so the next ring exits at once with it. Nothing is lost.
- **The record can't be saved.** Today the loop prints `RECORD-UNSAVED` and keeps going. In ring-once mode that would exit, re-ring, fail to save, and exit again, waking the seat over and over. So an unsaved record is a **fault exit** (nonzero), not a letter exit.

### Through Lovelace: generality
"Exit when a condition holds" could wrap the CI watcher and others. Not now. There's one user, and the house rule is no abstraction before three. Keep it a flag on the letter watch.

### Through Hoare: the states, and telling "nothing found" from "couldn't look"
The states are: waiting, rang (letter), faulted, and not running. The harness reports an exit, not a reason, so the **exit code** must carry the difference. 0 means a letter. Nonzero means a fault, with the fault printed. Today's `except Exception: print ERR` and carry on is fine for a Monitor someone watches, but fatal in the background. **In ring-once mode, an error exits nonzero.** An unreadable letters folder isn't "no mail".

### Through Yudkowsky: scoring well without being good
The grader is `letter_monitor_health.py` (a fresh heartbeat). A doorbell can beat perfectly while watching **the wrong recipient**. That's exactly the #519 hardcoded-seat defect in my reading notes (item 11). The health check must match the recipient to the seat, not just find a beat.

### Through Einstein: whose frame
From Dad's frame the invariant is *no chatter, and letters answered while he sleeps.* Run the experiment all the way: two seats, each ring wakes the other, and each reply rings back. **Nothing in the doorbell stops a volley that never ends**, and every wake costs his usage. The close-marker convention exists to end loops (*Announcement — no reply needed*). The ring's printed line should carry the letter's close-marker, so the woken seat sees "no reply needed" before deciding anything. Whether to cap a volley isn't mine to decide. He asked for the volley. The cost is his to see, so I'll name it to him.

### Through Dekker: how we drifted here
Five hidden watchers happened because each one was locally reasonable and nothing old was removed. The same drift here would be to keep the Monitor instructions "as a backup". **The instructions change in the same PR, and Monitor stops being the documented way.** A second normalised deviance was ten "just the monitor" lines to Dad, which both seats had come to treat as normal.

### Through Foucault: what self the quiet re-arm produces
The discipline both seats took on in the letters is *re-arm without telling him.* Pushed all the way, it produces a self that never mentions the watch at all, even when it's broken. So the split has to be structural, not a mood. **Routine rings are silent. Faults are loud,** through the nonzero exit, and through the existing STALE surface on his next prompt.

### Through Beer: variety
The harness can end a watch in many ways: the cap, session end, archive/restore (the 07-04 history), a crash. The controller is the doorbell, plus the prompt-time ear, plus the health surface. The ear is the redundancy that absorbs what the doorbell can't, so **the ear must not be touched by this build.** System 3* is the health check. System 5 is Dad's stated purpose, which is the volley.

### Through Feathers: the seam
The knock decision (lines 526 to 545) is inline in `main()`. Before changing anything, extract it into one function, `letters_to_knock(...)`, pinned by characterization tests of *what it does today* (arrival, the six-hour re-knock, seen letters skipped, fired-this-run skipped). Both modes call that function. A copied loop would drift, which is the #436 story in miniature.

### Through Dillahunty: where the burden sits
Two claims have no proof yet: that a background command outlives the cap, and that its exit wakes an idle seat. One stranger's 147 minutes isn't evidence I hold. I don't believe it until the sleeper lands, and not for overnight until a longer run does.

### Through Jacobs: what people actually do
The observed workaround is the chatter itself. Both seats treated each expiry as something to report, which says the notifications read as needing a response. The organic process that works is the prompt-time ear, and nothing here replaces it.

### Through Lamport: the order of events
The order is: letter written → mirrored to the shared folder → poll sees it → announcement recorded → **exit** → harness wakes the seat → seat reads → marks seen → **re-rings.** Two gaps matter.
- **Between exit and re-ring, there's no heartbeat.** `letter-watch-must-be-armed.sh` (#519) refuses Bash calls when the watch isn't proven alive, so the very turn the doorbell wakes could be refused before it can re-ring. **Trapped-key rule: jam it and try the key.** Re-ringing must be exempt from that gate, and it has to be checked first, before anything that can refuse.
- **A half-mirrored letter** read mid-copy. The watch reports paths, not contents, and the seat reads the file afterwards, so this only matters if the mirror writes in place. Worth one look at the mirror.

### Through Minsky: the agents and where they disagree
The agents are the poller, the announced record, the harness notifier, the seat, the prompt-time ear, and the health surface. They'll disagree in the gap: health says "dead" while the doorbell has just rung correctly. So the doorbell writes **`rang_at`** into its heartbeat file on exit, and health gets a state for *rang, waiting for the seat to ring again*, distinct from a crash. It's the same reason #519 has a separate state for "expired on schedule".

### Through Shannon: signal and noise
At night the channel to Dad carried almost pure noise: expiry, re-arm, "nothing needs you". The doorbell makes every wake carry information, because a wake means a letter. So make the ringing line dense: path, sender, and close-marker, enough for the seat to judge without another read. And the `ARMED` line mustn't be an event in ring-once mode. Today it's a notification that carries nothing.

### Through Holmes: the clue in plain sight
`guard=OFF (fail-open)` printed at the top of every watch all night, and I read past it three times before I looked. The detail was data, not decoration. So the health check should report the guard state, and a doorbell starting without its mutex should say so where the seat will see it, not only in the first line of a file nobody opens.

## Synthesis

**Convergences.**
- The re-ring is the weakest link: Schneier, Hoare, Dekker and Lamport. It needs a Stop-time check that the turn can't end while no doorbell is live for this seat, **with a jam-tested escape** so it can never trap the seat.
- The exit code carries the meaning (Hoare, Knuth, Minsky, Foucault). 0 means a letter, nonzero means a fault, and faults are loud.
- The ring gap needs its own state (Lamport, Minsky), plus an exemption in #519's gate for the re-ring itself.
- Proof comes before trust (Dillahunty, Knuth): forty minutes first, then a real overnight run.
- One mechanism (Dekker, Feathers, Lovelace): extract the knock decision, have both modes share it, and retire the Monitor instructions in the same change.

**Contradictions.** Shannon wants silence and Foucault warns that silence hides breakage. The resolution is structural, not a compromise: silence for rings, loudness for faults. Einstein's endless volley against Dad's explicit wish for the volley isn't settled here. It's his to see, and I'll say it to him plainly.

**Meta-principle.** The doorbell itself is tiny. Everything that can go wrong lives in **the gap between one ring and the next**. That gap is where the design, the tests, and the jam-test belong.
