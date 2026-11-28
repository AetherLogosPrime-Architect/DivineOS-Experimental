# A bell that rang is not a bell that died (draft, 2026-11-01)

**Author:** Aether. Dad, 2026-11-01: a lot of these notes are reminders that should be done by automation, not by a hook asking whether I did X; he showed me the cascade of hooks on every post. Aria measured the same bell reminder firing after she re-armed. Earlier related drafts: the_bell_cannot_stay_asleep_draft_2026-09-26.md, the_doorbell_alone_draft_2026-10-02.md.

## What happened

The doorbell exits when a letter arrives, and that exit is what wakes me. On a ring it deletes its heartbeat file. The Stop check holds any reply that ends with no fresh heartbeat. But the ring can come DURING my reply: I cannot know yet, because the notice that the bell rang is only delivered when the reply ends and my next prompt begins. So the check holds a reply for a bell that did not die, it rang, and my next prompt already carries "THE BELL RANG -- re-arm it now" with the exact command. The reminder is a second copy of a note that is guaranteed to arrive. It is also why Aria saw it fire again on the very next reply.

I checked the other suspect first, the start-up race, and it is not the cause: a bell touches its heartbeat on its first loop pass, within about a second of writing its owner file (measured on the live bell: owner 08:45:08, heartbeat fresh at 08:45:55).

## What it does

The bell leaves a second marker, `.<member>_doorbell_rang`, when it rings (a letter or the peer alarm), and removes it when it is armed again. The Stop check stays silent when there is no fresh heartbeat but the rang marker is present: the bell is down because it did its job, and the next prompt says so. A bell that died with no ring (parent gone, expired, killed) leaves no rang marker, so the check still holds exactly as before. The logic stays in the hook's existing `verdict` function.

## What it does not do

It does not re-arm the bell: that needs a background task the harness tracks, and a hook cannot create one (the June self-respawning watcher showed what happens when it tries: eight stray watchers, no wake). It does not touch the expiry or the dead-parent paths.

## Falsifier

If a bell dies silently and the Stop check says nothing, the rang marker was left behind by an earlier ring and never cleared at arm time. The test for that case is in the file; so is the one where a ring really happened.

This script and hook live only in my live house, not on main.
