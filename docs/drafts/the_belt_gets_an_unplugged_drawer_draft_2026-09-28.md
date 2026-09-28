# The belt gets an unplugged drawer — draft 2026-09-28

Dad, 2026-09-28: *"i go off on endless tangents.. lose focus.. leave things half finished.. and totally forget about them lol"*. I offered one half-finished thing at a time, surfaced daily, until it's finished or taken down on purpose. He said *"yes and make sure you sync up with Aether and do the proper flow"*.

## Prior art (the reach, 09-28)
- **Aether's task belt** (`build/the-task-belt`, `core/task_belt.py`, #550, CONFIRMED by Aletheia at `67e3ea0c`, awaiting Dad's merge). It gathers five drawers (`unified_todos`), ranks them by severity, reach and age, keeps a current list of 3 pulled every prompt with one slot reserved against starvation, closes an item through its drawer and pulls the next, and is loud when stuck. **This is his ask. No second system.**
- **What it can't see:** things built and never plugged in. Dad, 09-26: *"what else in the OS is sitting there unplugged"*. Known cases: `letter_channel_state.derive_from_watched_channel` (only tests call it), my `his_words_door.owed_in_reply` and `his_words_stop.py` (superseded by the shelf, never wired), and `scripts/audit_deletions.sh` (written 08-19, never runs, per `removal_is_a_build_2026-09-08.md`).

## The idea
A sixth drawer, **unplugged**, for the belt:
- **Found by a scan, not by memory:** for each module-level function in `src/divineos` and each script in `.claude/hooks/` and `scripts/`, is there a caller outside `tests/`? The caller can be an import plus a use, a hook in `.claude/settings.json` or `dads_table_children.json`, a CLI registration, or a script invoked by a hook. No caller means an unplugged item, with its file, its name, and when it was last touched in git.
- **Two exits only:**
  - **Wired:** a live caller appears, so the next scan closes it by itself.
  - **Retired:** removed on purpose, with a reason. Removal is a build, so the reason must name *every* job the thing did (`removal_is_a_build`), and `audit_deletions.sh` runs as part of the retire path, which also plugs that script in. Never "noted".
- **Oldest first within the drawer**, and the belt's reserved slot keeps it from starving behind HIGH corrections.

## What the walk changed (walk-6f906ae2a994)
- **Reach from what runs, not "is it referenced"** (Pearl). Start at the live roots (`.claude/settings.json` hooks, `dads_table_children.json`, CLI registration, scripts those invoke) and walk calls outward. Anything unreached is unplugged, and a test import doesn't count.
- **Prove the scanner before trusting it** (Sagan). It must flag the three known unplugged cases and must not flag the door, the shelf or the table, all known live.
- **One graph, two uses** (Lovelace). The same reach graph answers "what does removing this break" on the retire path.
- **How an item speaks** (Tannen): *"built <date>, nothing that runs reaches it — wire or retire?"* A question about a room, not a verdict on its builder.
- **Scale** (Hawking): the count itself is the answer to his 09-26 question, so report it to him. The belt still shows one at a time.

## Risks named before the walk
- **False "unplugged":** things called dynamically (by string, entry points, `python -m`) look callerless. The scan has to read the hook lists and `-m` invocations, and a wrong flag has to be dismissable with a reason, which is recorded, so it isn't asked twice.
- **Noise:** hundreds of small helpers might have no direct caller. Start at module level in `core/` and in hooks, measure the count, and read a sample by hand before it goes on the belt.
