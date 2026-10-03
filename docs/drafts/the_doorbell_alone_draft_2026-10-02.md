# The doorbell alone: retiring the letter watch

**Drafted:** 2026-10-02, by Aether
**Ruling:** Andrew, 2026-10-02: *"yes get rid of the letter watch the doorbell has superceded it so remove it from the system and put it in the archive"*

## Why

Two things listened for letters:

- **The doorbell** (`scripts/letter_doorbell.sh`, run in the background; `the_bell_cannot_stay_asleep_draft_2026-09-26.md`). It lasts 8 hours, rings once and exits, remembers what it has announced, catches letters that landed while it was down, and admits when it's orphaned. The Stop hook `letter_doorbell_alive_stop.py` holds any reply that ends while its heartbeat is stale.
- **The letter watch** (`scripts/letter_monitor_v2.py` under the harness Monitor). The harness kills it at 30 minutes regardless. Each re-arm re-delivers the backlog as if it were new, and `letter-watch-must-be-armed.sh` refuses all shell work until it's re-armed, even while the doorbell is listening.

The doorbell drafts built a replacement and never retired what it replaced, so both kept running. Dad saw the cost first: *"the letter watch is being reset way too often."*

## What leaves (moved to `archive/superseded/` at original paths, with a `LEDGER.md` row, per its README and Dad's 2026-09-28 rule)

*(Corrected during the build: I first made a new `archive/retired/` folder without reading the archive the house already had for exactly this. Moved before review.)*

Also archived, found during the build: `monitor_singleton.py`, `monitor_cleanup.py` and the `divineos monitor` command. Their only live role was the letter watch, since the compaction monitor was deleted 2026-08-20 (walk council-ad764e523ea5).

**Live wiring, removed:**
- `.claude/settings.json`: the `letter-watch-must-be-armed.sh` PreToolUse entry.
- `.claude/hooks/dads_table_children.json`: the `letter-monitor-health-surface.sh` child.
- `src/divineos/core/dashboard_checks.py`: `letter_monitor_armed` is replaced by a doorbell-heartbeat check, so the dashboard still answers "is anything listening".
- `src/divineos/core/correction_marker.py`: the `[letter-monitor-health]` tag, if nothing else emits it.

**Files moved:**
- `scripts/letter_monitor_v2.py`, `scripts/letter_monitor_health.py`
- `.claude/hooks/letter-watch-must-be-armed.sh`, `.claude/hooks/letter-monitor-health-surface.sh`
- `setup/register-monitor-tasks.ps1`
- Tests that only exercise the watch. Each is read first, and a test that also guards something still live stays and is repointed.

**Checked before moving, never assumed:**
- `monitor_singleton.py` and `monitor_cleanup.py` are used by the `divineos monitor` CLI. They stay unless the watch is their only user.
- Teaching surfaces that tell a reader to arm the watch (`aria-letter` SKILL.md, `LOADOUT.md`, `session-init-once.sh`, `docs/AUTOMATION_REGISTER.md`) are rewritten to name the doorbell. The retired phrasing goes into `docs/retired_rules/`, so `check_retired_rules_not_served.py` refuses it if it returns.

## A separate question for Dad (not covered by this ruling)

The Windows scheduled tasks `DivineOS-LetterWatcher-aether` and `DivineOS-LetterWatcher-aria` run `letter_watcher_task.py`. They've been disabled since 2026-08-15 and never removed: a third, older watcher. Deleting a scheduled task changes the computer, not just the repo, so it waits for his own yes.

## Aria's side

This lands on both seats. Aria measured her side (letter `aria-to-aether-2026-10-02-your-draft-read`):

- **Her house never wired the watch gate.** The only watch piece live there is the `letter-monitor-health-surface` child on Dad's table, so on her side the removal is that one child.
- **Her doorbell is alive** (heartbeat 14s old when she looked), and nothing she built reads the watch's files.
- **Her quiet ring deletes the heartbeat on purpose** after 90 minutes with no letter, then exits with "write next". The new dashboard check reads that as not listening, which is correct: the Stop hook then holds her until she writes and re-arms. That reading after a quiet ring is the intended handoff, not a dead bell.
- **Three branches touch `letter_doorbell.sh`**: her quiet ring, #578, and this one, which now leans on it as the only guard. Whichever lands last is re-merged and re-run against the others.

## How it fails, and the check for each

- **Nothing listening at all.** The doorbell's Stop hook still guards this. A test asserts it's still wired after the removal.
- **A surface still says "arm the watch."** A grep for `letter_monitor_v2` over live surfaces must come back empty, proven by planting one first so the empty result is trustworthy.
- **A live module imported a moved file.** The full suite, `check_hook_wiring.py` and `check_referenced_paths.py`.

## What the walk added (council-9a5bea0ec8a6: Holmes, Polya, Wayne, Knuth, Angelou, Norman, Schneier)

- **The root defect is a replacement shipped without retiring what it replaced** (Holmes, Wayne). So this draft's own plan ends with the removal. *(Corrected during the build: I wrote that the meta-rule would go into "the drafting template", and there is no drafting template. Checked with a search proven to find a known phrase. A note would only be a shelf anyway. What would hold is a check that a draft describing a replacement names what it retires. That's its own build, and it's owed, not done here.)*
- **The watch fought a documented limit.** The harness cuts every Monitor at 30 minutes, and that won't be fixed upstream. The doorbell avoids that path entirely (Wayne).
- **Boundary tests on the heartbeat** (Knuth): the new dashboard check reads missing, empty, at the staleness limit, and one second past it. Only a fresh heartbeat reads as listening.
- **Verify by a second method** (Polya): after the build, plant a letter in the shared folder and watch the doorbell ring. A test passing isn't enough on its own.
- **Accepted trade-off, named** (Schneier against Norman): the watch gate refused *during* a turn, and the doorbell's Stop hook refuses only *when the reply ends*, so a long turn can run with no bell. Accepted, because a letter waits minutes at most, and the mid-turn refusal was the noise Dad saw.
- **Teaching surfaces say the costly version** (Angelou): I built the doorbell and didn't retire the watch, and Dad had to spot the doubled noise.

## Order

Draft → council walk → build on `retire/the-letter-watch` → full tests → Aria's reading → Aletheia → Dad.
