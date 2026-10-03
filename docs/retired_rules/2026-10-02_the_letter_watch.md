<!-- retired-rule
id: letter-watch
retired: 2026-10-02
retired-by: Andrew
successor: the letter doorbell -- bash scripts/letter_doorbell.sh <seat>, run in the background, guarded by .claude/hooks/letter_doorbell_alive_stop.py
pattern: (?i)\bletter_monitor_v2\.py\b
pattern: (?i)\bletter-watch-must-be-armed\b
pattern: (?i)\bletter_monitor_health\.py\b
pattern: (?i)\barm\s+(?:the\s+)?letter\s+monitor\b
-->

# The letter watch

**Retired 2026-10-02 by Andrew. Replaced by the letter doorbell.**

## What it said

A letter wakes me only if a harness Monitor is running `scripts/letter_monitor_v2.py`. The gate `letter-watch-must-be-armed.sh` refused all shell work until that Monitor was proven alive, and `letter-monitor-health-surface.sh` reported its state every prompt.

## Why it was retired

Dad asked which of my two running listeners was which, and when I explained he said: *"yes get rid of the letter watch the doorbell has superceded it so remove it from the system and put it in the archive"*.

The harness kills every Monitor at 30 minutes, and that limit won't be fixed upstream. So the watch had to be restarted twice an hour, each restart re-delivered old letters as if they were new, and its gate refused work even while the doorbell was listening. Dad saw the noise before I did: *"the letter watch is being reset way too often."*

The root defect was mine. I built the doorbell (2026-09-26) and never planned retiring the watch, so both ran.

## What replaced it

The doorbell: `bash scripts/letter_doorbell.sh <seat>`, run in the background. It lasts 8 hours, rings once and exits, remembers what it has announced, catches letters that landed while it was down, and admits when it's orphaned. The Stop hook `letter_doorbell_alive_stop.py` holds any reply that ends while its heartbeat is stale, and the dashboard check `letters.doorbell` reads the same heartbeat.

The accepted trade-off: the old gate refused during a turn, and the doorbell guard refuses only when a reply ends. The retired files are in `archive/superseded/` at their original paths, with a row in its `LEDGER.md`.
