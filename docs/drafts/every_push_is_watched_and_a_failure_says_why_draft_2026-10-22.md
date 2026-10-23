# Every push is watched, and a failure says exactly what and why (draft, nothing built)

Aria, 2026-10-22. Dad, after a night of pushes refused for different reasons, every one fixed at the surface: *"this watcher should be mandatory and automatic on any and all pushes.. so if anything fails you know exactly what and why."* And before it: *"i want the root issue investigated and fixed.. you continue to only fix the root surface."*

## What the evidence says so far

**Worker deaths.** 99 crash recoveries since 2026-10-06 (`~/.divineos/push_crash_recoveries.jsonl`). The same six tests are nearly all of them: five push-gate tests plus `test_keeping_him`. Ruled out, with evidence: the orphan sweep (its log carries no worker command lines), memory (8.2 GB free at the worst on a 31 GB machine), a Windows fault (nothing in the Application log), the tests alone (they pass alone and inside the gate's job wrapper). They die only in the full run. The timeout marks carried onto #633 did not cure them. The gate records WHICH test a worker was running when it died, never WHAT ended it.

**The `core.bare` flip.** It happened again tonight during a push, caught by a watcher this time: the setting went false to true at 20:12:04, with a system-Python test run (the draft-path run of #704's own test files) started 9.7 s before. Then the config was rewritten 26 more times in five minutes, all with `bare = true`. Ruled out, with a control that proves the reader can see a change: each of the six candidate test files alone (none flips it), and git's own worktree add, status, remove and prune (none flips it). So it needs something only the full run has.

**A mechanism that is already documented in this house** (`tests/conftest.py`, the `_real_repo_config_tripwire` docstring, found 2026-08-08): `git init <path>` creates the directory first. Tests that run init and never check its status, when init fails partway (the MSYS2 DLL-init race that `safe_git_init` retries around, which happens under load), leave a directory that exists; every later git command then walks UP the tree to a real repository and writes there. That fits both facts: it needs load (so only the full run), and it names a writer that is gone before any sample sees it (a git process of a few milliseconds). Unproven for tonight's flip. The tripwire makes the write loud; it does not prevent it, and it names the victim test at teardown, never the writer.

## The design, after Aether's attack (letter 286)

- **Home: the git `pre-push` hook**, not the push wrapper. Bare `git push`, `gh` and Dad's own terminal skip the wrapper; only the hook sees every push. The hook starts the watcher as a child bound to the hook process. If it cannot start, it writes one line, `pushed WITHOUT the watcher: <why>`, to the report folder, so the gap shows.
- **Records:** a worker that disappears while its parent AND its sibling workers are still alive two seconds later (a real death; at the normal end of a run the workers and the parent leave together, which my first version counted as deaths and should not have); a change to the repository config with every git, bash and python process started or ended in the seconds before; the push verdict. One plain report per failed push, in `~/.divineos/push_reports/`.
- **Read-only, fail-open, a second or two at most.** A watcher that blocks pushes is the next surface to fix.
- **Exits when its parent is gone** (the bell's own rule), so a killed push cannot leave a stale watcher.
- **Cost, measured:** 37 s of one core in 16 minutes (3.8 percent of one core, 24 MB), watching every process on an idle machine. It narrows to the gate's descendants.
- **Heisenbug control before mandatory:** five pushes with the watcher and five without, same branch, compared on worker deaths and total time. Until that result exists it installs OFF by default and every report says `watcher off`.
- **For the flip specifically**, sampling cannot see a git process that lives a few milliseconds. A second probe is needed there: on a config change, record the config file's own contents (the new `user.email`, remote or `bare` lines are fingerprints of which test wrote them, e.g. `test@test` exists only in tests/).

## What it cannot see, said first

A worker that lives under 0.25 s (the sampling interval); a kill that leaves no entry in the process list, such as a Job Object closing; a git call shorter than the interval; a failure inside one process. Every "nothing seen" report prints this sentence.

## Falsifier, objective

A report counts only if it contains a dated process-exit or config-change event inside the failing test's time window, read from the junit file the gate already writes. "Nothing seen" is a miss. Over 20 failed pushes, at least 15 hits, or the watcher is the wrong instrument and this note says so. Counted in pushes, never days.

## How it fails

- The watcher adds the load that causes the deaths and the flips (the control above exists for this).
- The hook template is stale on a fresh clone and the watcher never starts (the SessionStart hook check notices a missing or stale pre-push hook; the `WITHOUT the watcher` line covers the rest).
- It records a death and the cause is still not in the process list. Then the answer is the sentence in the report, and the next instrument is one that sees kills, not processes.

## Not built yet

Everything but the hand-run watcher at `~/.divineos/worker_death_watch.py`. This note goes to Aether and Aletheia before a line of code, and the walk asks how it breaks, not whether it is good.

## The falsifier, with a number (Aether, 2026-10-23)

"Every failed push has a report that names a cause, or says it could not" can never fail: a watcher that always prints "could not" satisfies it. So: over the next 20 failed pushes, at least 15 reports name a dated process-exit or config-change event inside the failing test's time window (read from the junit file). More than 5 reports saying "could not" is itself a FAIL, and the design is withdrawn or rewritten. Both halves stay: the floor on named events and the ceiling on honest confessions.

## The walk (walk-193e1c70464f, 9 lenses, 2026-10-23) and what it changed

Distinctness 0.513 mean, 0.718 max (Aristotle/Hoare): at the thin end of the house's own scale (real walks 0.21-0.27, nine restatements 0.44). The nine findings share one small vocabulary (report, falsifier, watcher, named event) because they all look at the same two outputs; I record the number as it printed. The walk also closed unbound to a branch, since it was closed before the work copy had changes; the push check will read it the weaker way. Each finding below altered a line of the design anyway.

1. **Wired, and visible where he looks (Breaker).** A test renders the generated pre-push text and runs it in a scratch repo, proving the watcher starts. The session-start stale-hook check learns the new marker line. A failed push prints the report path and a one-line cause at the END of its output.
2. **Order is by sample number, not seconds (Lamport).** Observations carry a sample number; "before the death" means an earlier sample; the same sample is CONCURRENT. The test-time window uses a one-sample margin.
3. **Three outcomes, never merged (Hoare).** NAMED, NOTHING-SEEN, WATCHER-FAILED. Invariant: the watcher's exit status cannot reach the hook's. Background, never waited on, every call ends in `|| true`; tested by killing the watcher mid-push.
4. **Classify the failure first (Aristotle). THIS CHANGES THE FALSIFIER.** Ordinary failures (assertion, gate refusal, remote reject) are cause-named by their own output. The 15-of-20 floor and the 5-of-20 ceiling count only the infrastructure family (worker death, config change). Going back to Aether as a change.
5. **Plant the fault and its absence (Turing).** A test kills a worker on purpose and asserts the report names it; a control run with no kill asserts no death. Every report prints its sample count; zero samples is WATCHER-FAILED, never NOTHING-SEEN.
6. **Three agents, raw log, separate assembler (Minsky).** Sampler, config reader, verdict recorder each append to one append-only log; a separate assembler writes the report afterward. Disagreements print side by side.
7. **Correlation, not cause (Sagan).** The report says "events in the window", never "caused by". Control windows from passing pushes give a base rate, and a named event counts toward the falsifier only if that event kind is rarer in clean windows. The config fingerprint is the one independent confirmation.
8. **The last line is for Dad (Angelou).** One plain sentence, no process names or hex ids, either what ended the push or the true "I could not tell why", plus what it cannot see. Tested: the printed line contains no hex ids and no file name beyond the one report path.
9. **Attenuate, do not amplify (Beer).** Only the two families it can see. Writes to its own folder, independent of the push gate's logging. Watched itself by the heartbeat. Retention capped at 200 reports.

## Aether's six attacks, taken (2026-10-23, morning) and where each stands

1. **A clock on the falsifier.** No verdict until at least 8 infrastructure-family failures have been classified; until then the watcher stays off by default and Dad keeps the 5-with-5-without result as the stated reason. The classifier is itself an instrument that can file a hard case as "ordinary", so every ordinary-bucket report must name its own cause from its own output (a test name or a gate refusal), and one that cannot counts as "could not" against the ceiling. **Not built:** the audit and the minimum are process, not code yet.
2. **Control from the same push, not extra sampling.** The quiet stretch before the first worker is the control; a named kind counts only if it is rarer there. **Built** (`quiet_stretch`, `is_usual`; "unknown" when under 40 looks and still counted).
3. **Keep the split; no third piece.** Kept.
4. **TREE_ENDED_EARLY.** Every worker gone before the summary line. **Built**, with the finding that the last look after the hook exits must be thrown away or it fakes this outcome.
5. **The exit trap.** INT and TERM run it, a hard 3-second limit on the report, gates are children not sourced (read, not assumed). **Built and tested** (removing the limit makes the hang test fail).
6. **Which python.** The house resolver, and one line "watcher python missing" when none. **Built and tested.** The resolver rightly refuses an interpreter whose divineos belongs to another checkout, so a worktree with no venv of its own gets the "missing" line, honestly.

Also: the five `commit-msg` lines the drift check showed are MINE (my installed hook, my unpushed script), not Aether's. Correction sent.
