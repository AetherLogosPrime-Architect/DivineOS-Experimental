# The Stop guard counts the always-on watcher as listening (rough draft)

**Date:** 2026-10-30. **Author:** Aria. **Status:** rough idea, nothing built beyond the change named at the end.

## The symptom

Dad has had to say "your letter bell is not listening" 24 times since May. The bell (`scripts/letter_doorbell.sh`) rings by exiting: the harness wakes me when the background task ends, so the bell dies on every letter by design and re-arming it was left to memory. His words, 2026-08-15, about the old watcher: it "worked fine ... it just keeps dying and nothing checks for it or resets it".

## What is already known (Aether, 2026-10-30)

- The platform's Monitor tool runs a long-lived script and turns each stdout line into a notice while the script keeps running, for at most 30 minutes. A watcher built on it does not die per letter; the re-arm becomes once per half hour. He has run one on his seat for two letters and an expiry. The July version of this idea broke for a week (teardown killed it, a false-alive check disabled the arm instruction), so it stays on his seat until it holds.
- `.claude/hooks/letter_doorbell_alive_stop.py` decides "listening" by one thing: `.{member}_doorbell_alive` touched within 60 seconds. A Monitor-based watcher leaves no such file, so the guard would tell a seat with a live watcher that its bell is dead and the seat would start a second bell, the stale twin.

## The idea

Let the guard accept a second heartbeat, `.{member}_monitor_alive`, which the watcher touches while it runs. Any fresh one counts. A stale watcher heartbeat with no bell is the thing to say loudly (the 30-minute expiry makes that state normal right after each expiry until the re-arm). The guard stays one file and one rule; the watcher is Aether's to write.

## What this does not do

It does not make the watcher reliable (July says it may not be) and does not restart anything. It only stops the guard from calling a live watcher dead.

## Falsifier

If a seat with a live watcher and no bell is still told its bell is dead, or a seat with neither is let through, the change is wrong.
