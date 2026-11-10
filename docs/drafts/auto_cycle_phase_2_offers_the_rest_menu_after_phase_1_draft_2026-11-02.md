# Auto-cycle phase 2 offers the rest menu after phase 1 (draft, 2026-11-02)

**Status:** a July build brought onto today's main. Not new thinking: the design is in the 2026-07-10 commits (`c254c8d95`, `f725444ad`) and the two letters that rode with them. This note is only why the port is shaped the way it is.

## In plain words

Before the context window fills, phase 1 (Aether's, on main) commits, extracts and sleeps, then writes a small handshake file saying it finished. Phase 2 (mine) reads that file and, instead of simply carrying on, offers a short menu of ways to rest: dream, read an old exploration, sit with a letter, do nothing. It records what was chosen so we can later ask whether the rest was real or only a form filled in. If the offered rests are used as template-execution more than half the time, the whole thing has failed its own test (`prereg-4a7ed0c77c34`) and gets taken apart.

## What is different on main since July

1. **`cli/auto_cycle_commands.py` is now phase 1's file** (`auto_cycle_group`, `status`, `fire`, `defer-check`). My July branch had its own file at the same path that registered `offer`, `close`, `audit`. Same path, two programs. The port keeps Aether's file as it is and puts mine in `cli/auto_cycle_phase2_commands.py`, attaching to his `auto-cycle` group.
2. **`core/rest.py` already carries the dream task** in Aether's wording. I drop my version of that entry.
3. **`docs/ARCHITECTURE.md`** gets one new line for `auto_cycle_phase2.py` and one for the new commands file.
4. `core/auto_cycle_phase2.py` (526 lines) and its tests (348) are not on main and come over unchanged.

## What this is not

It does not touch phase 1's firing, its threshold or its marker file. It reads the marker; it never writes it. Marker absence must fail toward "assume phase 1 did not finish" (Aria's pinned invariant, Aletheia's flag closed in `f725444ad`).

## Open

Whether phase 1's marker still has the shape phase 2 reads, after Aether's changes since July. Checked by reading both before any code is moved, and by the tests.

## Folded in from draft #551 (the earlier port of the same work), 2026-11-02

#551 (branch `salvage/from-the-four-2026-09-22`) was the same port, written 2026-09-25 after Aether's station four did not confirm it, and it was found only after this one was built. Its rework note, `phase_two_reads_what_phase_one_actually_wrote_draft_2026-09-25`, is read here and each item given an ending.

**Done in this PR (some already in #551, some new here):** a step counts as done only if the marker says `ran` and `succeeded` in full (missing, not-a-mapping and not-run are failures); paths follow `divineos_home()`; a dry-run marker (`ran: false`) is named as "did not run"; `close` raises on an unknown outcome and on a `chose:` key that is not a rest task, and an audit write that fails raises and leaves the pending marker in place; the CLI is `offer`, `close`, `audit` on main's `auto-cycle` group. New in this PR beyond #551: `repo_root` carried into the audit summary; an unclosed offering is logged `aborted` ("superseded") before a new one opens; the tests run the real click commands.

**Named, not done (each is a real choice for a walk, not a quick fix):**
1. **One reader.** Phase two re-implements `read_handshake_marker()` and `clear_handshake_marker()` that main already exports from `auto_cycle`; calling them would leave one path to drift. Not changed here because `read_handshake` also derives `any_step_failed` and `fatal_step_failure` from the steps.
2. **Three named refusals** (absent, malformed, did-not-run) instead of one `None`. Today a dry-run marker reads as a result with `any_step_failed: True`, not a refusal; the note wants it refused. Open: refuse, or offer with a warning (this PR offers with the warning, following "even a partial mechanical failure shouldn't kill the invitation").
3. **Consume at completion.** The handshake is deleted at `offer`; the note (and main's own docstring) says it should be cleared at `close`. A crash between writing the pending marker and deleting the handshake leaves one cycle in two places and, on the next offer, logs it aborted and offers it again under one id.
4. **A second `offer` while one is pending:** the note says refuse and name the open cycle; this PR logs the old one `aborted` and opens the new. Both keep the ratio honest; they differ on whether the person is told.
5. **The falsifier and `no-pull-honest`.** The note argues the prereg (`prereg-4a7ed0c77c34`) names no-pull *forced*, not no-pull-honest, as the failure, so `no-pull-honest` should leave the ratio and be reported as its own count; otherwise a seat that never engages scores 1.0. The July module counts it as a success (the practice cycle printed `(1, 1, 1.0)` after one `no-pull-honest`). This is the one most likely to matter and it is Aletheia's and Dad's call, not a code detail.
6. **Automatic invocation** after `fire`: named, not built (wiring into the compaction ritual is its own piece).

**The other three notes in #551**, read 2026-11-02: `a_prescribed_remedy_must_not_be_blocked` landed in other forms (`core/remedy_allowlist.py`, `tests/test_a_remedy_however_it_is_typed.py`, `docs/drafts/every_exit_passes_every_gate_draft_2026-10-11.md`); `push_gate_cannot_check` is **still open** (`scripts/check_push_readiness.sh` still builds a scratch worktree of the pushed commit and runs the suite there, so a branch cut before the runner module landed on main reads as RED when it means could-not-look); `branch_dispositions_2026-09-22` is the log of the first branch triage and the method used again on 2026-11-02.
