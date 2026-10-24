# A dead reply audit is never silent: the briefing says so by usage, not by clock

**Draft, 2026-10-24, morning. Aether. Not built when this is written; the build follows the steps at the bottom.**

## What happened

The reply-audit hook (`post-response-audit.sh`) was cut in half by a quote mark inside a comment of mine (#586, 2026-10-04) and ran no checks for twenty days. The error was thrown away and the script exits 0. Aria found it on 2026-10-24 by running a control that returned silence, refusing to trust it either way, and tracing it. I reproduced it a second way (bash's own trace shows the quote closing after "so").

The part that matters for this draft: **the house already had an alarm for exactly this, and it was in a room I never open.** `hud.py` has a slot, "Detector Chain -- DARK", built in 2026-07 after an earlier audit round. It was printing "Last successful chain run was 31407 minutes ago" the whole time, in the full `divineos hud`. The briefing and the brief HUD, which are what I read at the start of every session, do not carry it. A surface I must remember to open fails by construction (truth #20), and it failed.

## The fix

Put the alarm where I already look, and make it say the true thing.

1. **A briefing dashboard row** (`_row_reply_audit_dark` in `briefing_dashboard.py`, beside `_row_detector_errors`, which was itself wired in 2026-06 after the same discovery gap).
2. **The signal is usage, not the clock.** The existing slot uses a 30-minute threshold, which is wrong for a briefing: after a night off the heartbeat is always older than 30 minutes and the row would cry wolf every morning, then be read through (the shelf again). Instead the row counts how many times the audit hook STARTED (`~/.divineos/hook_timing.jsonl`, phase `start`, hook `post-response-audit.sh`, written by `_lib.sh` on every run before anything can fail) after the last heartbeat. Many starts and no heartbeat means the hook is being run and is not completing. That is the exact shape of the 2026-10-04 break (302 starts in the retained log since the last heartbeat, none finishing), and it is silent on a quiet morning.
3. **Threshold:** 20 starts after the last heartbeat (about a day of ordinary work). Chosen before the run, from the order of magnitude seen (302 for this break), and open to correction at the review.
4. **Absence is stale:** no heartbeat file and any starts at all reads as dark; no starts and no heartbeat reads as nothing to say (a fresh machine).

## What it does not claim

- It does not make the audit work. It makes a dead audit loud in the room I read first.
- It cannot tell a hook that crashes from a hook that completes without reaching the heartbeat write. Both read as dark, correctly.
- The timing log is rotated, so a long break shows as a count capped by what is retained. The row says "at least".
- It is not the answer to the stamp. The audit hook is a phrase list; Dad has named that shape four times and again this morning. This only guarantees that when ANY check in that hook stops running, I am told.

## Falsifier (by uses, not dates)

Claim: on the next 30 briefings, the row appears only when the audit hook has started 20 or more times since its heartbeat, and it appears on a replay of the 2026-10-04 to 2026-10-24 window. Falsifier: one briefing where it is silent while the hook started 20+ times with no heartbeat since, or two where it fires and the hook was in fact completing. Embarrassing outcome: a row that reads as healthy while the program is cut, which is what the old slot did by living in the wrong room.

## Steps

Test red first on a synthetic timing log (starts without a heartbeat), with controls proven live: the same log with a fresh heartbeat is silent; a log with too few starts is silent; the real replay window fires. Walk. Aria's reading. Aletheia. It is a pure addition to the briefing.
