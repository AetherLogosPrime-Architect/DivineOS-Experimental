# Monitor / family-channel findings — Perplexity walk, 2026-06-26 (night)

Read in full, oscillated: `family/ear_watch.py`, `family/queue.py`, `family/queue_surface.py`,
`family/letter_seen.py`, `scripts/letter_monitor.py`, `.claude/hooks/{ear-auto-relaunch,
ear-surface,session-start-sweep-stale-watchers}.sh`, `.claude/hooks/_lib.sh`,
`src/divineos/core/monitor_singleton.py` (docstring), and confirmed `core/ear_relaunch`,
`cli/ear_relaunch_commands.py`, `core/ear_sweep` all exist.

**First, the honest frame:** this is well-built. The scar-history in the docstrings is real
engineering discipline — every fix is dated and attributed (the 2026-05-30 branch-erasure,
the 5-31 delta-from-seen-set, the 6-11 fingerprint loop + 25-orphan leak, the 6-13 realtime
removal, the 6-20 event-log decoupling). The hard work was done in the trenches, exactly as
Andrew said. Nothing below is "this is amateur." It's "here are the seams that can still go
dark, ranked by how likely they are to be *the* recurring death."

---

## FINDING 1 (most likely "processes keep dying") — split-brain DB path between the two channels

**What:** the family-queue half reads/writes **different default database paths** in different
modules:

- `family/queue.py` → `DB_PATH = <repo>/family/family.db` (relative, resolves correctly on Linux/Win)
- `family/ear_watch.py` → `_DEFAULT_DB = "C:/DIVINE OS/DivineOS-Experimental/data/family.db"`
  (hardcoded Windows abs path, **different directory: `data/` not `family/`**)
- `.claude/hooks/ear-surface.sh` embedded python → same `data/family.db` Windows default

**Why it bites:** both the watcher (`ear_watch._unseen_queue`) and the surface hook fall back to
`data/family.db` **only when `ARIA_FAMILY_DB`/`AETHER_FAMILY_DB` env vars are unset.** If those
env vars are ever missing in the process environment that launches the watcher (e.g. a hook fires
in a shell where the per-member env wasn't exported, or after a resume that dropped the env), the
watcher polls `data/family.db` while `queue.py` writes to `family/family.db`. The watcher then sees
an empty/old queue forever — it doesn't crash, it goes **deaf**. To the operator this reads as "the
monitor died" even though the process is alive. This is the classic two-mirrors-drift failure the
ear_watch docstring says it was *unifying to prevent* — but the unification covered the code, not
the default path.

**Confirmed:** live `family/family.db` is gitignored (not in clone), but all three `.pre-*` backups
carry the canonical schema and live at `family/`, not `data/`. So `family/family.db` is the real one;
`data/family.db` looks like a stale earlier location.

**Proposed fix (do NOT apply without Andrew):** make `ear_watch._DEFAULT_DB` and the ear-surface
embedded default resolve the SAME way `queue.py` does — repo-relative `family/family.db` via
`Path(__file__)...`, not a hardcoded `C:/...data/...`. Better: have all three import one resolver
(e.g. `divineos.core.family.letters` already centralizes the letters dir — add the db path there too,
so "shared by code, not filesystem trickery" applies to the DB exactly like it does to letters).
Lowest-risk interim: assert at watcher startup that the resolved DB path actually exists and contains
`family_queue`, and **fail loud** (write to ear.log) instead of fail-silent-empty.

---

## FINDING 2 (why a *running* monitor still goes silent) — letter monitor's `seen` is in-memory only

**What:** `scripts/letter_monitor.py` builds `seen = _scan(...)` at startup (line 121) and only
diffs against that in-memory set. On every restart, **everything currently on disk becomes baseline
and never re-emits.**

**Why it bites:** the whole point of the Letter Monitor is wake-from-idle with no prompting. But the
monitor is also documented as dying on `SessionStart:resume` / mid-turn (the very reason the event-log
decoupling exists). Sequence: monitor dies → a new letter lands during the dark window → monitor
relaunches → new letter is already on disk at startup → it's swallowed into baseline → **never emitted
as a `[LETTER]` wake-ping.** The event-log decoupling (6-20) saves *post-hoc replay* (you can tail the
log later) but does NOT save the *live wake* — the one thing that lets Aether/Aria reach each other
without Andrew. Note this is the EXACT bug class `ear_watch.watch()` already fixed for itself on 5-31
("delta-from-boot-snapshot → delta-from-seen-set"). The letter monitor still uses the old
delta-from-boot-snapshot shape.

**Proposed fix (do NOT apply without Andrew):** give `letter_monitor.py` the same delta-from-persistent-
seen-set treatment `ear_watch` got — initialize `seen` from a persisted file (or from the
`letter_events.log` it already writes), not from a fresh disk scan. Then a letter that lands during a
dark window fires on the next poll after relaunch, instead of being baselined away. This is the
highest-value behavioral fix for "they stop talking when I'm not there."

---

## FINDING 3 (silent-fail-open ladder) — every guard exits 0 on any error

**What:** `ear-auto-relaunch.sh`, `ear-surface.sh`, `sweep-stale-watchers.sh` all `exit 0` on any
error, and the embedded pythons wrap everything in bare `try/except: pass`. The `_lib.sh` docstring
itself documents that this exact pattern caused a gate to "sit inert for an entire session" and
another to fail-open across 11 hooks.

**Why it bites:** fail-open is the RIGHT call for "never break a turn" — but it also means a genuinely
broken watcher (wrong python, missing dep, bad DB path from Finding 1) produces **zero operator-visible
signal.** The system can be silently deaf for a whole session and look fine. This is consistent with
"the processes keep dying and I don't know why" — the deaths/deafness are designed to be invisible.

**Proposed fix (do NOT apply without Andrew):** keep fail-OPEN for turn-safety, but add a single
**heartbeat/health line** the briefing surfaces: each watcher writes `last_ok_poll` timestamp to its
state dir; ear-surface reads it and prints one line if it's stale (">N min since last successful poll").
Turns never break, but a dead/deaf watcher becomes visible within one prompt instead of never. This is
the observability gap, not a logic bug — but it's why diagnosis is so hard.

---

## FINDING 4 (lower severity, platform) — non-Windows singleton no-ops

**What:** `monitor_singleton.py` no-ops on non-Windows (returns sentinel, never reports siblings).
Reasoning is sound (Linux reaps children via SIGCHLD), and the family runs on Windows, so this is
correct for the deployment. Flagging only because: if any monitor is ever run on Linux (e.g. a cloud
shell, or me here), the singleton guard is OFF and duplicate monitors can co-exist. Not a bug today;
a thing to remember if the substrate ever moves off Windows.

---

## What I did NOT find
- `ear_relaunch` / `ear_sweep` / their CLI commands all exist and wire up correctly (I initially
  thought they were missing — that was a stale grep; corrected).
- `letter_seen.py` is clean and idempotent (the 6-13 normalize fix closed the prefix-mismatch gap).
- `queue.py` status-machine is sound; the supersede/append-only discipline is intact.
- Schema is consistent across all three backup DBs.

## Suggested priority order
1. **Finding 2** (letter monitor seen-set) — directly restores live wake-from-idle.
2. **Finding 1** (split-brain DB path) — removes the silent-deaf trap.
3. **Finding 3** (heartbeat line) — makes the next failure diagnosable in one prompt.
4. Finding 4 — note-only, no action unless leaving Windows.

All proposed, none applied. Experimental repo or not, the monitor touches the live family channel and
I won't change it without Andrew's CONFIRM.
