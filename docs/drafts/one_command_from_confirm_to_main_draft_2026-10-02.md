# One command from confirm to main

**Drafted:** 2026-10-02, by Aether
**Ruling:** Andrew, 2026-10-02: *"if you are forgetting rules then those are rife for automation so they cannot be forgotten remember this takes alot of time on my end so every redo takes another 10-15 mins of time, so the less redos the better so see where you have failed and lets fix it"*

## What failed today, in order (each one a redo)

Merging four of Aletheia's confirmed PRs (#555, #562, #578, #579) took three or four attempts each:

1. `gh pr merge --body "$(sed ...)"`: refused by `pr_merge_gate`, which reads the trailer only from literal command text.
2. A literal body: refused by GitHub, because "base branch policy prohibits the merge". The ruleset requires `multi-party-review`, which reads per-commit trailers or the PR body. A trailer on the squash message alone doesn't satisfy it.
3. `divineos stamp-ready`: refused for two stations the board couldn't see (a council walk under another fingerprint, and Aletheia's cold read), then refused again because the branch was behind main.
4. A merge of main produced conflicts. In one case (#578/#579 against #555) resolving them changed an authored file, so it goes back to the reviewer.
5. Stale local workbenches (`wt15`, `wtkiln`) were behind or diverged from the PR head and had to be replaced.

Every rule involved already exists in code. The failure is that I chain them by hand, in an order I re-derive each time.

## What it is

`divineos ship <pr>`: one command that runs the whole sequence, refuses at the first step that can't pass, and says which step and why. It never skips one.

1. **Read the PR**: head SHA, branch, mergeable state.
2. **Find the confirm**: an external-AI CONFIRMS finding naming this PR at its exact head SHA. If the head moved since the confirm, check the floor-only rule (every authored file byte-identical to the confirmed commit, confirmed commit an ancestor). If it holds, file the operator's floor-only CONFIRMS (Andrew 2026-09-23). If not, **stop: "changed after review, back to Aletheia"**, naming the files.
3. **File the round**, if it doesn't exist: aletheia CONFIRMS plus user CONFIRMS under the standing rule (Andrew 2026-09-23), bound to the tree-hash.
4. **Work in a fresh worktree at the PR head**, never an existing workbench.
5. **If behind main**: merge `origin/main` there. On conflict, stop and name the files. Afterwards, rerun step 2's floor check, so a resolution that changed an authored file stops here.
6. **Stamp**: write the External-Review trailer into the PR body (the CI fallback) and push any catch-up commit through `divineos_push.sh`.
7. **Ready, and wait for the required checks** (`multi-party-review`, `test (3.12)`, `test (3.12, sklearn)`) to report. If they fail, stop.
8. **Squash-merge** with the trailer written literally in the merge command, so `pr_merge_gate` can see it.
9. **Pull main** into the live house (Andrew 2026-09-23: *"you should be pulling from main after merging"*).

It never enables auto-merge. The command does the merge itself, once, after the checks pass.

## What it reuses (prior art, so nothing is rebuilt)

`stamp_ready_command.py` (stamping, station board), `watchmen/merge_stamp.py`, `pr_merge_gate.py`, `audit_commands.prepare-merge`, `automerge_commands.py`, `scripts/divineos_push.sh`, and the floor-only check already in `stamp_ready_command._content_rung`. The new code is the ordering and the stop-with-a-reason at each step. No step's logic is re-implemented.

## Open questions for the walk

- Station board: should `ship` pass the board a confirm it already found, rather than asking me to restate it with `--despite-stations`?
- Waiting on CI inside a command: a bounded wait with a clear "still running, rerun later" exit, or does it hand back and get re-run?
- Order across several PRs: when two share a file (#578/#579), merging one changes the other's floor. Should `ship` accept a list and re-check after each merge?

## What the walk settled (council-85a8c91b7b18: Deming, Yudkowsky, Carmack, Feynman, Pearl, Polya, Meadows, Norman)

- **One common cause** (Deming, Feynman, Norman): every refusal today was correct, and the merge order lived in my head. The sequence itself is the missing artifact.
- **Ordering only** (Carmack): no gate removed or loosened, no step's logic re-implemented.
- **It can never manufacture a confirm** (Yudkowsky, the dissent that binds the design): `ship` refuses unless an external-AI CONFIRMS already exists at the exact head SHA. It files the operator's standing confirm only beside hers, never instead of it. It reads her findings and never writes them.
- **The floor is re-checked after every catch-up** (Pearl): main moving between steps is the confounder. #578/#579 against #555 is the case that proves it.
- **It takes a list** (Meadows): `ship 578 579 562` merges in order and re-checks each remaining PR after each merge, because each merge makes the next one behind.
- **It reports one line per step** (Norman): which step, passed or stopped, and why, so Dad can see what happened without reading code.
- **Traced** (Polya): today's #578 case stops at the catch-up step, naming `correction_marker.py`, and sends it to Aletheia. That's right.

## What Aria added (letter `aria-to-aether-2026-10-02-my-merge-path-for-ship`)

- **Dad's confirm comes from a recorded quote, never from me.** His standing rule exists (2026-09-23: *"my confirm stands for anything Aletheia has confirmed thats how it works..its a rubber stamp"*), and `ship` quotes it, with its date, into the user finding it writes, read from one recorded place. If that record is retired or changed, `ship` asks him per merge and records his reply verbatim.
- **It always makes its own temporary worktree** at the exact PR head and removes it afterwards (her 24 workbenches are cleared, and two of mine were stale today).
- **Her #575 round trip becomes test cases:** `--body-file` unseen by `pr_merge_gate`; bare `gh pr ready` refused in favour of stamping; a confirming letter missing its `**Reading:**` line; and stamping from a checkout of another branch, where the worktree has no `divineos`, so `ship` runs the main venv's exe by absolute path.

## Smaller fixes found in the same stretch (separate, after this)

- Two old watch-gate tests read the real `$HOME`, so the retirement opt-out breaks them. #580 removes them; until then they need a temp home.
- `kept_both_sides.py` flags generated files after regeneration, so it should skip or recompute generated registers.
- The build-flow gate treats `--help` and `git log` as edits.

## The command, first cut (2026-10-03): the checks, then the button

Aletheia (2026-10-03) holds her signature until the head carries `divineos ship`. The first cut of the command is the half-automation Dad set out for merges: the machine does every step it can check and hands me one labelled button, and the press stays mine. So `divineos ship <pr>` runs these read-only, one line per step, and stops at the first one that fails:

1. **Read the PR**: open, not a draft, its head.
2. **Her confirm at this exact head**, through `confirm_in`, proven by her signed line in her own letter, with a withdrawal winning.
3. **Dad's confirm in the same round**: a user CONFIRMS for this PR at this head. `ship` never writes one.
4. **The required checks**: every check on the head has passed or was skipped.

If all four pass, it prints the merge command with the External-Review trailer written literally, ready to run. It doesn't run it, and it never turns on auto-merge. A head that moved since her confirm stops at step 2 in this cut. The floor-only path (`floor_proven`) and the catch-up are the next slice.

## Order

Draft → council walk → Aria → build → tests (including a dry run against a real confirmed PR) → Aletheia → Dad.
