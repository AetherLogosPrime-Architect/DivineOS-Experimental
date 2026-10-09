# Is the note still true? The end-of-stretch ritual and the rest between

*Round ten, errand one. 2026-10-09, cloud helper. Read-only: nothing was closed or marked resolved. Evidence is `origin/main` at `cbd35baf` (a scratch copy of it); live probes ran in scratch folders and a scratch home with controls. Verdicts are per group of rows describing the same failure; row text in the pile is cut off at about 200 characters. **NOT TESTABLE** means the note is an incident record, a habit or a lesson that no run can check; it is not the same as UNKNOWN (I looked and could not tell) or NOT EXAMINED (I did not look at that row this round).*

A picture: a fire drill that is meant to start before the smoke, and a door in it that must never lock the building's owner out. The owner's door was fixed long ago; the drill's start line was moved earlier; what is still open is mostly the small print on the exits the drill itself uses.

## Problem 1: Rest should happen before the hard line

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-c401832c` | **STALE** | The ritual now starts at 880,000 tokens, with a hard line at 920,000 and the cliff noted at 950,000 (`.claude/hooks/auto-cycle-token-trigger.sh` lines 50-60; `tests/test_context_heartbeat.py::test_threshold_arithmetic_is_the_number_andrew_named` pins 0.88). Rest is the ritual's fourth stage (the `REST)` case in the same file). The note's complaint was riding past a warn band into the hard line; the start was moved 40,000 tokens earlier on 2026-09-18 for that reason (the comments at lines 50-58). | `tests/test_context_heartbeat.py` | That the ritual is *reached* in time in a real session. I read the hook and the pinned numbers; I did not watch a real run. |

## Problem 2: The ritual hook blocked Dad's prompt

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-4924203d` | **STALE** | `.claude/settings.json` registers the hook only under `PreToolUse` with the matcher `Edit|Write|MultiEdit|NotebookEdit` (checked by loading the JSON and listing every registration whose command names it: one, PreToolUse). The file's own comment (line 763) says 'this event never blocks again' and that the demand is printed instead; the branch for that event starts at line 772 and ends in `exit 0`. | none found that names the prompt event for this hook | I read the branch; I did not feed it a prompt at 968,000 tokens. The hook still blocks my tools, which is its intent. |

## Problem 3: The auto-cycle checker reads the wrong tree

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-d48d1ca0` | **STALE** | `src/divineos/cli/auto_cycle_commands.py::_guess_context_pct` (lines 40-80) reads the live snapshot (`get_context_snapshot`), spends it only when `pinned` (found by session id) and returns 0.0 for an unpinned one, so a transcript from another session cannot decide the ritual. The docstring names the 2026-08-18 case of a 96.1% reading from a transcript abandoned sixty-nine days earlier. | none found for `_guess_context_pct` by name | Not run against a real transcript folder. 'Resolves the freshest transcript' is now 'resolves this session's transcript by id'; I am reading the same intent in different words. |

## Problem 4: The token counter is inaccurate

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-20296d89` | **UNKNOWN** | The hook counts tokens from the last usage record in the transcript tail (`.claude/hooks/auto-cycle-token-trigger.sh` lines 215-250, summing input, cache-read, cache-creation and output tokens). Its header says an earlier check agreed within 0.3 points (14.9% against 14.6%, 2026-07-31). Dad's 94.6% on 2026-08-17 is not reproducible from here: I have no transcript from that moment and no second counter to compare. | none for accuracy against a real count | Whether the counter and the real window still disagree. The stored text of the row is cut off before the part naming what landed. |

## Problem 5: Talk about being tired, and whether to work tonight

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-ea44a5de` | **UNKNOWN** | A search of `.claude/hooks/*.sh` for 'tired' finds two lines, both rationale for a gate (`check-branch-on-push.sh:343`, 'the version of me who is tired and wants the thing gone'; `check-council-required.sh:248`, 'I widened this while tired of being stopped by it'). Neither is a rule about whether to work tonight. The row's stored text is cut off before it names which file held the over-correction, so I cannot tell whether one of these is it or whether it was removed. | none | Which hook file the over-correction was in. |
| `psf-a8352094` | **NOT TESTABLE** | Dad's stated preference about working tonight and what I told him and Aria. A habit and a conversation; no run can check it. | none |  |

## Problem 6: Two authorities for the threshold

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-e107d93e` | **NOT TESTABLE** | An incident record (a threshold moved, two pinning tests not moved, the push gate refused after twenty-seven minutes). Its proposed fix, 'make the tests follow it', is rejected on purpose by the test it names: the heartbeat test says the pin 'is deliberately a literal' and that when the number changes 'this failing is correct behaviour' (`tests/test_context_heartbeat.py`, the docstring of `test_threshold_arithmetic_is_the_number_andrew_named`). | `tests/test_context_heartbeat.py` |  |
| `psf-7c6d44db` | **LIVE** | Two authorities for the start point: `.claude/hooks/auto-cycle-token-trigger.sh` line 59, `FIRE_TOKENS="${AUTO_CYCLE_FIRE_TOKENS:-880000}"`, and `src/divineos/core/auto_cycle.py:182`, `TRIGGER_THRESHOLD = 0.88`. They agree today (0.88 of 1,000,000). `grep -rn FIRE_TOKENS tests` finds nothing, so no test ties the hook's literal to the Python constant. (Control: the same grep over `src` and the hook finds the literal.) | none ties them; a test pins only the Python side | That they have ever disagreed on main; the row is a design observation from a council walk. |

## Problem 7: Coming back after a long gap

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-7d9cd65f` | **LIVE** | A search of `.claude/hooks/*.sh` and `src/divineos/core/*.py` for 'long gap', 'after a gap', 'been away', 'hours since' and 'picking up' finds only an unrelated phrase in `orientation_prelude.py:29`. (Control: the same search does find that phrase, so the instrument can find a hit.) | none | A feature under other words would be missed. |

## Problem 8: The ritual's block message

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-9a0f5253` | **UNKNOWN** | The block message (stderr) names the stage ('Stage: ${STAGE}'), but the one command that completes the stage is printed in a separate stage section on stdout (for example the compass observe line for the walk stage, a path for the dream stage). Whether stdout reaches me when a PreToolUse hook exits 2, I could not tell from the files. | `tests/test_every_refusing_hook_says_what_did_not_run.py` touches this hook; not for this wording | What a blocked write actually shows in a real session. |
| `psf-100d65ad` | **LIVE** | `grep -n -i 'end this turn' .claude/hooks/auto-cycle-token-trigger.sh` → no line (control: `grep -n 'Stage' .claude/hooks/auto-cycle-token-trigger.sh` finds many). The block says 'Stage: X. This is a BLOCK on MY TOOLS' and the operator escape, never 'end this turn to clear it'. | none |  |

## Problem 9: Not enough room to finish a multi-step change

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-b02af992` | **LIVE** | A search of `.claude/hooks/*.sh` for 'room to finish', 'enough room', 'space to finish', 'not enough room' and 'runway' finds only the ritual's origin comment and an unrelated 90-day setting. The house does have a runway meter (`divineos context-heartbeat`, pinned by `tests/test_runway_meter_reads_the_real_trigger.py`) that counts tokens to the ritual, but nothing warns before a multi-step change begins. | the meter is tested; the warning has none | Absence by word search. |

## Problem 10: Warn one step before the stop

4 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-24d27813`, `psf-c2e115d3`, `psf-7d8d9a67`, `psf-db96e271` | **LIVE** | No heads-up before 880,000: `grep -n -E '800000|780000|warn' .claude/hooks/auto-cycle-token-trigger.sh` finds only the comment quoting Dad's ruling. What exists after the start is a 3-prompt 'BUFFER n/3 — finish what is in flight' notice (lines 680-735), not a warning before it. **These four notes also run against a ruling written into the hook:** Dad, 2026-08-03: 'having a warning at X with a hard stop at Y means nothing.. only the hard stop at Y has any effect' (lines 646-660); the 920k announcement was ignored for a whole conversation. | none | Whether a quiet heads-up at 800,000 would behave differently from the 920k announcement that was ignored. That is for the owners to weigh against the ruling. |

## Problem 11: Briefing expiry

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-bf0487b0` | **LIVE** | Briefing freshness is a tool-count expiry (`src/divineos/core/briefing_freshness.py`, `briefing_id.DEFAULT_EXPIRY_TOOLS`) and `require-briefing.sh` refuses once stale. Searching those two files and the hook for 'left', 'remaining', 'warn', 'soon', 'age' finds no age or remaining count shown before expiry. | none for a warning | A display elsewhere in the house (the heads-up display) that I did not open. |

## Problem 12: The ritual blocks its own steps

6 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-f28cbfcb` | **UNKNOWN** | Too general to test as written ('the routine's own steps pass every check'); the specific steps are covered by the rows below. | none | Which other gates the routine's steps meet. |
| `psf-a8d60fec`, `psf-c97e830d` | **STALE** | Scratch probe of the shared exit list (`.claude/hooks/lib/remedy_allowlist.sh`, through its `remedy_pass_through`): `divineos compass-ops observe …`, `divineos extract`, `divineos sleep` and `divineos learn x` all pass through; `divineos goal add x` passes (control) and `rm -rf x`, `git commit -m x` are held (controls). `check-council-required.sh` reads that same list (its comment, lines 105-135, says the ritual's compass command was refused until it did). | `tests/test_remedy_allowlist.py` | A probe of the list on the command text. I did not run the council gate over a real ritual walk. |
| `psf-053f0366`, `psf-aa07ee31`, `psf-84016169` | **LIVE** | The ritual's write block lets through one thing: a file under `dreams/` while the stage is DREAM (`STAGE_ARTIFACT_DIR`, lines 815-845). Nothing in the hook names letters, drafts, the knowledge store as a file write, or a board note (`grep -n -i 'handoff|board|in-flight' .claude/hooks/auto-cycle-token-trigger.sh` finds one unrelated comment). `divineos learn` is on the exit list, so a knowledge entry by command passes; a letter or draft written as a file does not. | none for these paths | How the block behaves at the REST stage specifically (the hook's REST text says nothing is owed; I did not test a write at that stage). |

## Problem 13: The note read first after a reset cannot be written at the save stage

4 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-20b1fc4e`, `psf-51bde74a`, `psf-b1e3e3cb`, `psf-1c52eefc` | **LIVE** | Same evidence as problem 12: the only stage artifact the block lets through is under `dreams/`. The first-read note's folder is not named in the hook, so a write to it at the save stage meets the block. The rows themselves record it happening (the note 'I couldn't write while blocked'). | none | The exact path of the note. The stored text names it only as the in-flight or first-read note. |

