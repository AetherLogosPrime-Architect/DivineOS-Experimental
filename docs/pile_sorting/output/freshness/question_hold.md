# Is the note still true? The hold that waits for Dad's answer

*Round seven, errand one. 2026-10-08, cloud helper. Read-only: nothing was closed or marked resolved. Evidence is `origin/main` at `cbd35baf` (a copy in a scratch folder); live probes ran in a scratch home with controls. Verdicts are per group of rows describing the same failure; row text in the pile is cut off at about 200 characters. **NOT TESTABLE** means the note is a habit or a lesson that no run can check; it is not the same as UNKNOWN (I looked and could not tell) or NOT EXAMINED (I did not look at that row this round).*

A picture: a held door that opens when the man it was held for walks up. The notes ask for exactly that, and on main it already does: his message releases the hold, even typed mid-turn, and reading and letters pass through while it is shut. What is not there is a key per window: it is one door per seat.

## Problem 1: Dad's answer does not release the hold

14 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-3e62c046`, `psf-fedd49b6`, `psf-8a78bb2d`, `psf-398bb5d5`, `psf-d55c6cc1`, `psf-e7eff476`, `psf-6015b562`, `psf-d8695dbc`, `psf-299d0958` | **STALE** | `src/divineos/core/question_hold.py:254-275` (`answered_since`) and `:278` onward (`refusal`) release the hold when a dated message of his arrives after the hold armed, including one typed mid-turn. Ran on main: `tests/test_question_hold.py` and `tests/test_question_hold_own_seat.py` → **30 passed**, among them `test_his_answer_typed_mid_turn_releases_the_hold`, `test_a_notice_mid_turn_does_not_release_it`, `test_the_hook_holds_then_his_message_releases`. Reads and letters pass the hold (`test_upkeep_and_letters_pass_the_hold`). | `tests/test_question_hold.py` (13 tests) | Releases the hold file. It does not close the filed ask in `operator_asks` (that is the next row). |
| `psf-c2e72cec`, `psf-98269317` | **UNKNOWN** | These two ask for his message to close the matching *filed ask* (the `operator_asks` record) with the link recorded. `question_hold` releases the hold; I did not read whether `operator_asks.resolve_ask` (`src/divineos/core/operator_asks.py:178`) is called on his arrival. | none |  |
| `psf-f4db0862`, `psf-ec068279`, `psf-c76ff014` | **UNKNOWN** | Ask to carry commit `2602f7d83` into the live house. `git merge-base --is-ancestor 2602f7d83 origin/main` → **not an ancestor**; the commit exists. Main carries the release-on-his-message behaviour by another route (above), so whether this exact change is now unneeded cannot be told without diffing them. | none |  |

## Problem 2: The hold applies to the whole house, not just the window or seat that asked

7 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-06fec19b`, `psf-f07b611f` | **STALE** | The hold is keyed to the seat: `question_hold._home()` returns each seat's own `divineos_home()` and its header (2026-10-01) says the shared file used to hold both seats and no longer does. `tests/test_question_hold_own_seat.py` ran in the 30 passed. | `tests/test_question_hold_own_seat.py` | Seat, not window: two windows of the same seat share one hold. |
| `psf-91146b8c`, `psf-80e30ea9` | **LIVE** | No session or conversation key: `grep -n session src/divineos/core/question_hold.py` → no match; the state is one file, `question_hold.json`, in the seat's home. Control: the same file has seat keys (`_seat_name`, `_home`). | none |  |
| `psf-39afea89` | **UNKNOWN** | Seat half met (above). Whether the shared letters folder counts as 'letters' to this hold was not examined. | none |  |
| `psf-25dd3c05`, `psf-cc90b555` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 3: Two holds, or a hold and another check, block each other's exits

8 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-ab2c76ad`, `psf-7072a483`, `psf-f7fce6dc` | **UNKNOWN** | This hold's side is met: `question_hold.refusal` lets through anything `remedy_allowlist.is_remedy` or `_is_readonly_probe` names, and its patterns pass the doorbell. The other hold's side (and 'both at once') was not examined. Note `is_remedy('bash scripts/letter_doorbell.sh aether')` is False (PR #609), so the doorbell passes here by this hold's own pattern, not by the shared list. | `tests/test_question_hold.py::test_upkeep_and_letters_pass_the_hold` |  |
| `psf-0a7553bb`, `psf-4de6ebc7`, `psf-a3a27841`, `psf-690b0ae6`, `psf-7cc303fa` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 4: The hold blocks harmless reads and letter filing

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-371ec0ff`, `psf-8be07d03` | **STALE** | `question_hold.refusal` imports and consults the shared judges: `remedy_allowlist.is_remedy` and `pre_tool_use_gate._is_readonly_probe` (comment dated 2026-10-01: 'Both judges are the house's shared ones, not a fourth list'). Reading and letters pass (`test_building_waits_and_reading_does_not`, `test_upkeep_and_letters_pass_the_hold`). | `tests/test_question_hold.py` | I did not run the hold on `git ls-remote` specifically (the note's example). |

## Problem 5: Duplicate asks and asks revived by restating an old question

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-3da2e94e`, `psf-350907ee` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 6: Ask bookkeeping errors

3 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-39a69bb3`, `psf-49801066` | **NOT TESTABLE** | An incident record about answering the wrong ask. A habit or a lesson: no run or test can say whether it was kept. | none |  |
| `psf-82886fc3` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

