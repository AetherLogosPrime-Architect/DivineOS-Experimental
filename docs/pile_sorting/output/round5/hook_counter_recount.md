# Re-counting the hook scripts with the house's own counter

*Round five, errand four. 2026-10-08, cloud helper. Read-only: the counter (`src/divineos/core/hook_layer.py`) was not changed.*

**A picture.** A head-count at a door, on a clipboard that only recognises people who say their name out loud. Ten people walk in using hand signals and are written down as strangers. Two people are ticked "known" only because someone joked about their names on the wall. The count of strangers is therefore ten too high and the "known" list is two too long.

## The recount

Run on `origin/main` at `d310aadc` with the counter's own function (`hook_layer.inventory`), the same as `divineos hook-layer show`:

| Measure | Counter says |
|---|---|
| Registrations | 77 across 7 harness events |
| Shell files | 145 (21,761 lines) |
| Embedding python | 26 files (5,847 lines) |
| **Detached from the OS** | **45 files (5,862 lines)** |

These match the round-four figures (45 and 5,862), so nothing has moved on main since.

## Which of the ten still call the main system by a path the counter cannot see

The plan expected 35 detached scripts. Ten of the 45 call the OS, all in the same way: `python -m divineos.<package>.<module>`. The counter looks for `from divineos`, `import divineos`, or `divineos <word>` (`hook_layer.py:62-63`). The text `-m divineos.hooks.front_door_hook` contains `divineos.` and so matches none of them.

Each row below was checked by reading the script's non-comment lines for the `-m` call, and by confirming the module file exists on main.

| Script | Lines | Calls | Module on main? |
|---|---:|---|---|
| `session-init-once.sh` | 311 | `divineos.core.hook_context_merge` | yes |
| `andrew-past-writing-surface.sh` | 63 | `divineos.core.andrew_past_writing_surface` | yes |
| `require-goal.sh` | 47 | `divineos.hooks.pre_tool_use_gate` | yes |
| `his-state-is-his-to-say.sh` | 43 | `divineos.hooks.his_state_claim_hook` | yes |
| `his-voice-ends-the-turn.sh` | 42 | `divineos.hooks.his_voice_hook` | yes |
| `run-tests.sh` | 35 | `divineos.hooks.targeted_tests` | yes |
| `session-checkpoint.sh` | 34 | `divineos.hooks.post_tool_use_checkpoint` | yes |
| `shoggoth-gate.sh` | 32 | `divineos.core.operating_loop.shoggoth_gate` | yes |
| `front-door.sh` | 27 | `divineos.hooks.front_door_hook` | yes |
| `stop-distancing-intercept.sh` | 18 | `divineos.hooks.distancing_intercept_hook` | yes |

The ten total 652 lines. Taking them out leaves **35 scripts and 5,210 lines**, which is the plan's number. I did **not** run each module to prove it executes; I proved the call is written in the script and the target file is there.

## The counter's mistake runs the other way too

Of the 100 scripts the counter calls "attached", five are attached **only because a comment** contains `divineos <word>` (no non-comment line matches):

| Script | What it actually does |
|---|---|
| `pre-tool-bypass-rate-scan.sh` | calls `python -m divineos.hooks.bypass_rate_hook` (a real call the counter reaches only by luck of a comment) |
| `stop-response-scope-intercept.sh` | calls `python -m divineos.hooks.response_scope_intercept_hook` (same) |
| `lepos-channel-reflect.sh` | builds a `divineos lepos-channel reflect` command in python (a real call, same luck) |
| `continuity-frame-prime.sh` | inline python using only the standard library; **no OS call** |
| `log-session-end.sh` | sources `_lib.sh` and exits 0; **no OS call** |

So the counter is wrong in both directions: ten false "detached", two false "attached" (the last two rows), and three right answers for the wrong reason.

Two smaller things it cannot see: it reads only `*.sh`, and the hooks folder also holds six `.py` files (for example `detect_andrew_build_request.py`, which carries the logic that `detect-andrew-build-request.sh` merely routes to, and imports nothing from the OS). And two scripts run a `scripts/*.py` by path (`merge-question-wrong-instrument.sh` runs `scripts/merge_preview.py`; `post-merge-doc-fix.sh` runs `scripts/check_doc_counts.py`); neither of those imports `divineos`, so their "detached" label is correct.

## Does the counter need fixing, and why

**Yes, I think so, because its purpose is the migration to-do list.** The measure is quoted as "the judgment is still in shell" and the next migration is sized from it. As it stands that list is 10 scripts too long, and it sends someone to migrate files that already point at the OS. The cost is small and the first sign is already visible: the plan's own figure (35) disagreed with the counter's (45) and it took a recount to see why.

What a fix would have to do, as a proposal only:

1. Count a script as calling the OS when a **non-comment** line has `-m divineos`, `from divineos`, `import divineos`, or `divineos <word>`. That removes the ten false "detached" and the two false "attached".
2. Keep a control that must stay detached (for example a script with no OS call at all) so a loosened pattern cannot make everything attached.
3. Give `.py` files in the hooks folder the same treatment, or say plainly that they are out of scope.

What I did not decide: whether a script that calls the OS only to get an interpreter (`find_divineos_python`) counts as calling it. Today it does not match the pattern either.

## What this could not do

- It did not execute any hook, so "calls the OS" means "has the call written in non-comment lines", not "the call succeeds".
- Counts are from `origin/main` at `d310aadc`; the branch this file sits on is older.
