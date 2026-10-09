# Is the note still true? The warden that raises my stumbles

*Round nine, errand one. 2026-10-09, cloud helper. Read-only: nothing was closed or marked resolved. Evidence is `origin/main` at `cbd35baf` (a scratch copy of it); live probes ran in a scratch home with controls. Verdicts are per group of rows describing the same failure; row text in the pile is cut off at about 200 characters. **NOT TESTABLE** means the note is an incident record, a habit or a lesson that no run can check; it is not the same as UNKNOWN (I looked and could not tell) or NOT EXAMINED (I did not look at that row this round).*

A picture: a guard post I was asked to inspect, but the guard post is in another building (Aria's) and I only have a key to this one. The one thing in this room I could test, the detector that tells a promise ('I will never...') from a description ('a tool I had never run'), works.

## Problem 1: Reflection leans toward finding fault

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-b23ddb82` | **UNKNOWN** | The stumble 'warden' is Aria's room and I could not find it on main: `grep -rli warden` finds only an unrelated context-deduplication module that borrowed the word; `grep -rli stumble` over `src`, `.claude/hooks`, `scripts` finds two unrelated files (`letter_claims.py`, `council/experts/dijkstra.py`), and the same search on `aria/substrate` finds the same two. So there is nothing on main to run these notes against. (This one asks the reflection prompt to include a 'what worked' line; the prompt was not found.) | none | Looked and could not tell: the thing the note is about is not in the files I can read. |

## Problem 2: The room names the stumble from the wrong text

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-26cf2b41`, `psf-23307c11` | **UNKNOWN** | The stumble 'warden' is Aria's room and I could not find it on main: `grep -rli warden` finds only an unrelated context-deduplication module that borrowed the word; `grep -rli stumble` over `src`, `.claude/hooks`, `scripts` finds two unrelated files (`letter_claims.py`, `council/experts/dijkstra.py`), and the same search on `aria/substrate` finds the same two. So there is nothing on main to run these notes against. | none |  |

## Problem 3: An already-answered stumble keeps being raised

3 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-d9588951`, `psf-8e044687`, `psf-90364821` | **UNKNOWN** | The stumble 'warden' is Aria's room and I could not find it on main: `grep -rli warden` finds only an unrelated context-deduplication module that borrowed the word; `grep -rli stumble` over `src`, `.claude/hooks`, `scripts` finds two unrelated files (`letter_claims.py`, `council/experts/dijkstra.py`), and the same search on `aria/substrate` finds the same two. So there is nothing on main to run these notes against. | none |  |

## Problem 4: Things that are not stumbles are counted

5 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-c5427c2c`, `psf-34105f24`, `psf-d8668fff`, `psf-412c42fe`, `psf-4fe8e29b` | **UNKNOWN** | The stumble 'warden' is Aria's room and I could not find it on main: `grep -rli warden` finds only an unrelated context-deduplication module that borrowed the word; `grep -rli stumble` over `src`, `.claude/hooks`, `scripts` finds two unrelated files (`letter_claims.py`, `council/experts/dijkstra.py`), and the same search on `aria/substrate` finds the same two. So there is nothing on main to run these notes against. | none |  |

## Problem 5: Demand a root-cause line on every stumble

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-24b5a030` | **UNKNOWN** | The stumble 'warden' is Aria's room and I could not find it on main: `grep -rli warden` finds only an unrelated context-deduplication module that borrowed the word; `grep -rli stumble` over `src`, `.claude/hooks`, `scripts` finds two unrelated files (`letter_claims.py`, `council/experts/dijkstra.py`), and the same search on `aria/substrate` finds the same two. So there is nothing on main to run these notes against. | none |  |

## Problem 6: The obligation detector mixes a promise with a description

3 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-f800c87d`, `psf-fb80e060` | **STALE** | The obligation detector's rule test, `structural_promotion_check.looks_like_rule`, on main: controls 'I will never push without the wrapper.' → `(True, ['never push'])` and 'Always run the tests before pushing.' → `(True, ['Always run'])`; the note's own example 'It was a tool I had never run before.' → `(False, [])`; 'The file had never been opened by anyone.' → `(False, [])`. The descriptive-use filter (`_is_descriptive_match`, line 241) is the fix these rows ask for. `tests/test_structural_promotion_check.py` exists. | `tests/test_structural_promotion_check.py` | I did not check that the test file contains the five misread notes the row asks for, and 'must'-sentences were not exhaustively tried. |
| `psf-2675ae35` | **LIVE** | `grep -n -i 'reopen|re-open|removed|hook.*cit' src/divineos/core/obligations.py` → no match. Control: the same file has the pending-obligation functions (`get_pending_obligations`, line 198). | none | A name search of one module. |

## Problem 7: Stumbles whose reflection says nothing is owed

14 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-86b95a3d`, `psf-4fdf6609`, `psf-f41a6dd4`, `psf-6064838d`, `psf-56d05994`, `psf-c6250e0f`, `psf-a03daf66`, `psf-8405e994`, `psf-6b2b0243`, `psf-4d520714`, `psf-e65643cf`, `psf-50f5b127`, `psf-6cd200f6`, `psf-999992d9` | **NOT TESTABLE** | These are the answers themselves ('nothing', 'nothing new', 'nothing further'), not requests. Whether the warden should have raised those stumbles needs a replay of the warden's record, and the warden is not on main. | none |  |

