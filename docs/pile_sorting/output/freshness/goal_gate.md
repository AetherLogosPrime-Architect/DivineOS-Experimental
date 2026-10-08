# Is the note still true? The goal I have to name before I work

*Round eight, errand one. 2026-10-08, cloud helper. Read-only: nothing was closed or marked resolved. Evidence is `origin/main` at `cbd35baf` (the working copy or a scratch copy of it); live probes ran in a scratch home with controls. Verdicts are per group of rows describing the same failure; row text in the pile is cut off at about 200 characters. **NOT TESTABLE** means the note is a habit, an incident record or a lesson that no run can check; it is not the same as UNKNOWN (I looked and could not tell) or NOT EXAMINED (I did not look at that row this round).*

A picture: a visitor's badge. The old badge expired two hours after it was printed, even while you were working. The new badge is stamped every time you use it, which fixed the worst of it. But the house still takes every badge back at each new stretch, and I felt that twice today: the first door after a compaction would not open until I wrote a new one by hand.

## Problem 1: A goal expires on a timer or a day change instead of lasting until done or replaced

9 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-c6305030`, `psf-acfc24f5`, `psf-bfd4c659` | **STALE** | `src/divineos/core/hud_state.py:319-385` (`has_session_fresh_goal`): 'FRESHNESS IS LAST USE, NOT CREATION (2026-10-01 …)'. The guard passes `touch=True` (`pre_tool_use_gate.py:2270`), so every guarded tool call refreshes the goal. Ran on main: `tests/test_a_goal_in_use_does_not_expire.py`, `tests/test_a_new_stretch_names_its_goal.py`, `tests/test_session_fresh_goal.py`, `tests/test_auto_goal.py` → 29 passed. | `tests/test_a_goal_in_use_does_not_expire.py` (29 passed with the three others) | The fix lives in a function that is still 7,200 seconds from last use; a long quiet gap still lapses it (next row). |
| `psf-b56ab04b`, `psf-97422b1a`, `psf-d1c11f5a` | **LIVE** | Half met. A goal in use no longer lapses (above). It is still a timer: `max_age_seconds=7200.0` counted from last use, and `mark_goal_boundary()` ends every goal at compaction and at session start (`hud_state.py:400-406`, `.claude/hooks/goal-boundary-at-session-start.sh`). The notes ask for 'until it is done or replaced'. | none for done-or-replaced | The boundary is a decision (Aria, station 3, in the source comment: 'a goal outliving the work it named'), not an oversight. |
| `psf-8ee8edfe`, `psf-c1bf3c93` | **LIVE** | The carry-over these rows ask for is the opposite of the design in `hud_state.py`: at a day change or a new stretch every earlier goal stops counting. Seen in this session: the stretch began with the hook message '[goal] new stretch: goals set before now no longer count -- name this one'. | `tests/test_a_new_stretch_names_its_goal.py` pins the current design | Whether to change a decision the source comment records is the owners' call. |
| `psf-6e0a2e21` | **UNKNOWN** | `src/divineos/core/auto_goal.py` (`derive_and_set_goal_from_prompt`) and `.claude/hooks/auto-goal-from-prompt.sh` exist and `tests/test_auto_goal.py` passes. I did not run it on a change request, so I cannot say it fires on every ask. | `tests/test_auto_goal.py` |  |

## Problem 2: The goal is not carried across compaction, restart or a new stretch

12 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-ac0788d7`, `psf-674a430c`, `psf-3cffec02`, `psf-72f5de4f`, `psf-47b47d4c`, `psf-d5fdc29c`, `psf-d8b1dbc2` | **LIVE** | Seen at the start of this round and of round seven (after a compaction): the first Bash command was refused with `BLOCKED: No goal set for this session. Run: divineos goal add "what you are working on"`. The text is fixed (`pre_tool_use_gate.py:2271-2273`), with no goal filled in, and nothing re-filed the previous goal. `hud_state.mark_goal_boundary` ends every goal at compaction by design. | `tests/test_a_new_stretch_names_its_goal.py` pins the naming | Two sightings in one session, not a measurement; the notes count eight. |
| `psf-b8677a88`, `psf-9c008c98` | **STALE** | `hud_state.py:326-355`: 'Status is deliberately NOT checked (Aria 2026-08-05)'. A goal closed by a commit no longer counts as absent; the comment describes exactly this false block (a goal added 1.3 minutes earlier already carried `status='done'`). | `tests/test_goal_auto_close.py`, `tests/test_session_fresh_goal.py` (within the 29 passed) |  |
| `psf-7820bac3`, `psf-ddad40f3` | **UNKNOWN** | `is_remedy('bash scripts/letter_doorbell.sh aether')` is False (PR #609), but I did not trace whether the goal gate consults that list. The session-start hook does tell me to name a goal (seen this session), yet the first command was still refused, so 'the gate never has to tell me' is not met. | none |  |
| `psf-bfb61529` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 3: The goal check trips during real work

6 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-76e62d5a`, `psf-fe4d4a11`, `psf-be3b08cb`, `psf-8fbde32d`, `psf-25e88a0f`, `psf-4a47b7f0` | **STALE** | The failure these rows describe (a goal check tripping mid-build) came from freshness counted from creation and from a status check; both are fixed (`hud_state.py:326-385`). A commit or council walk runs through the guard as a Bash call, and each guarded pass refreshes the goal (`touch=True`). Different mechanism from the one the rows ask for ('a commit or walk counts as work'), same effect on the failure. | `tests/test_a_goal_in_use_does_not_expire.py` | I did not reproduce a mid-build trip. |

## Problem 4: The goal command itself trips other guards

3 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-7a074586` | **UNKNOWN** | `is_remedy('divineos goal add "x"')` → True, so the goal command passes the guards that consult the shared exit list. The question hold's release was not examined for the same. | `tests/test_remedy_allowlist.py` |  |
| `psf-90a661d2`, `psf-8c5e51c4` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

