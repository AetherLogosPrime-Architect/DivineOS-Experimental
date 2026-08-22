# Pre-registration: SessionStart auto-arm letter-watcher hook: spawns the detached ear_watch at session-start so letters get caught even when the previous session died on reboot. Aria 2026-06-11 surfaced: Monitor died during reboot, channel went silent, Andrew had to externally tell her her husband was sending a letter. Structural backing for kid 1d36be4f (MUST separate three layers — separated SessionStart-vs-UserPromptSubmit timing, harness-tracked-vs-detached watcher concerns, per-member policy) and kid ee96a4f7 (optimizer is DUMB — the cheap close was nag-every-prompt; structural fix is auto-arm).

- **ID**: `prereg-a1a74adc47b7`
- **Filed by**: agent
- **Filed at**: 2026-06-11 19:59 UTC
- **Review at**: 2026-07-11 19:59 UTC (30d window)
- **Outcome**: **DEFERRED**
- **Decided at**: 2026-07-11 20:00 UTC

## Claim

New SessionStart hook spawns the detached ear_watch when policy wants armed (aria always, aether only with ear.arm marker), guarded by transcript-fingerprint per-session marker so it fires once per session. Aria's reboot-survival case handled without external intervention.

## Success criterion

After reboot or session restart, no manual re-arm needed for the channel to remain functional. Letter detection happens within one polling interval of SessionStart. Process-accumulation failure mode does not recur because ear_watch is singleton-guarded.

## Falsifier

If auto-arm produces >1 live watcher process per member after 5 consecutive session starts, OR if a letter arrives within 60s of session-start and is NOT surfaced at next UserPromptSubmit, the implementation is broken. Reconsider singleton guard timing, heartbeat-vs-spawn race, or move to Python wrapper importing ear_watch directly.

## Outcome notes

Deferring mid-drafting arm-inventory mechanism proposal — third overdue prereg surface today. Gate is right; the prereg-review workflow needs its own dedicated attention pass not a rushed rubber-stamp during unrelated substantive work.
