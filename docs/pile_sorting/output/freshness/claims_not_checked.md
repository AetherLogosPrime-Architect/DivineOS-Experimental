# Is the note still true? Things I told people that I had not checked

*Round five, errand one. 2026-10-08, cloud helper. Read-only: nothing was closed or marked resolved. Evidence is `origin/main` at `d310aadc` (a copy in a scratch folder); live probes ran in a scratch home. Verdicts are per group of rows describing the same failure; row text in the pile is cut off at about 200 characters, so a verdict is about what the visible text asks for. Where a standing test exists it is named; the reproductions cited as 'PR #601' and 'PR #602' were re-run against current main.*

A picture: sixty-four notes of the form 'I said it was fixed and it wasn't'. Most of them are the diary entry, not the repair request, so a flashlight finds little to point at. Where the notes do ask for a mechanism, I went and tried the mechanism with the notes' own words. The result is mixed: the house has real guards against claiming work done, but they are tuned to a short list of phrases, and the exact phrases from the notes slip past.

## Problem 1: Claiming done or landed before verifying

6 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-bd74d0ea`, `psf-e01ebb81` | **LIVE** | `src/divineos/core/operating_loop/shoggoth_gate.py:103-165` (`_CLAIM_PATTERNS`) covers only the verbs filing, wiring, closing, committing, building and retracting, each with listed objects. Probe on main with controls: `decide('Filing this design now.', ())` → block; `decide('Filing this design now.', ('Write',))` → allow; `decide('I have written the fix and started the build.', ())` → **allow** (no tool call, no block). 'fixed', 'saved', 'written', 'started' are not covered, and the gate sees tool names only, not whether the write succeeded (`shoggoth_gate.py` module header, 'Honest limit'). | `tests/test_operating_loop_detector_wiring.py` (wiring only) | I did not run the Stop hook end to end. |
| `psf-b11979d0`, `psf-59616607` | **LIVE** | `src/divineos/core/landed_claim.py:133-157` checks a reply's arrival claims against the action stream (registered at Stop, `hook_surfaces.py:1686`). Probe: `assess('The branch has landed on main.', 'git push origin x')` → refuses; with a `git ls-remote` in the stream → allows; 'still running, I will say when it lands' → allows (controls). It reads **replies**; `letter_claims.py:1-40` reads the paths a sibling's letter names. Neither compares 'merged'/'landed' in an **outgoing letter** against GitHub. | no test covers letters | I found no module by name or header that does; a differently named one would be missed. |
| `psf-eb709823`, `psf-4cf9209a` | **UNKNOWN** | Incident records (2026-05-30 and 2026-10-03). The pairing they describe is partly built (`landed_claim.py`, `shoggoth_gate.py`) but the visible text asks for no specific mechanism, and the 2026-10-03 row is about a fix on an unmerged branch. | see `landed_claim` probe above | A one-time incident record. Its repair, if any, sits in the correction's own 'structural fix' text, which the pile cuts off. Nothing on main could be pointed at that the row asks for, and nothing could be run to settle it. |

## Problem 2: Narrating before looking

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-c1d79def` | **UNKNOWN** | Behavioural ('look at the screenshot before describing it'). I found no mechanism that reads images before a reply, and none a run could test. | none | Needs a running house. |

## Problem 3: Answering the state of a switch from memory

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-c3289a8c`, `psf-dde28980` | **UNKNOWN** | Behavioural ('read the switch before saying what it does'). The nearest mechanism, `history_claim_signal.py:95-143`, covers claims about **my own past**, not claims about what a switch does. | none | Not a defect that reads off the code. |

## Problem 4: A silent, empty or masked result read as the whole answer

14 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-656e72b8`, `psf-fe64754f`, `psf-adb632a2`, `psf-5cd2efc1`, `psf-88df30f0`, `psf-158354db`, `psf-883ba588`, `psf-654492f6`, `psf-8b6ebc5c`, `psf-71b71b7e` | **UNKNOWN** | A one-time incident record. Its repair, if any, sits in the correction's own 'structural fix' text, which the pile cuts off. Nothing on main could be pointed at that the row asks for, and nothing could be run to settle it. The nearest mechanisms are advisory: `.claude/hooks/ambiguous-verification-detector.sh` (header: 'flags a verification command whose OUTPUT cannot distinguish all clear from did not measure') and `pipeline-exit-ambiguity.sh`. | `tests/test_advisory_hooks_stay_advisory.py` names the first | I did not probe whether either prints a control beside a zero, which is the group's proposed fix. |
| `psf-6daa56e1`, `psf-f0d95994`, `psf-422b7285`, `psf-edc06ec9` | **UNKNOWN** | Behavioural ('check the evidence before explaining'). I found no module checking a stated **cause** against running code (the claim detectors cover no-fix claims, history claims, action claims, quantities and landed claims). | none | Not a defect that reads off the code. |

## Problem 5: False claims about other people's work

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-a4b7aecc` | **UNKNOWN** | Behavioural ('read the other person's file before saying what is in it'). `letter_claims.py` measures files named in a sibling's letter; nothing covers claims I make about her design in my own words. | none | Not a defect that reads off the code. |

## Problem 6: Overclaiming that I ran or demonstrated something

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-9693b6f0` | **UNKNOWN** | Verbatim of Dad's questions about a 'demonstrably built' claim. `overclaim_detector.py:198-397` catches stacked modifiers and ornate self-description, not execution claims; I did not test that phrase. | none | No probe run. |

## Problem 7: Stating a cause, a state or a result that turned out false

9 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-31397181`, `psf-e531e11c`, `psf-463a321d`, `psf-547f1d8a`, `psf-6f60b85c`, `psf-9f16d6f1`, `psf-2ef7c45e`, `psf-415d9663`, `psf-cd4128d1` | **UNKNOWN** | A one-time incident record. Its repair, if any, sits in the correction's own 'structural fix' text, which the pile cuts off. Nothing on main could be pointed at that the row asks for, and nothing could be run to settle it. | none | Nine separate incidents; none is a request. |

## Problem 8: Facts retyped or recalled from memory

5 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-64df7471`, `psf-37baf102`, `psf-fdfff7f9`, `psf-11837a6b`, `psf-49c37335` | **UNKNOWN** | A one-time incident record. Its repair, if any, sits in the correction's own 'structural fix' text, which the pile cuts off. Nothing on main could be pointed at that the row asks for, and nothing could be run to settle it. Two reflection rows ask to read values from the tracker and to find a folder by looking; no module was named. | none | Nothing to run. |

## Problem 9: Declaring a failure unfixable, or an absence of design, without checking

5 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-f2048088`, `psf-8853b622`, `psf-084b6fdc`, `psf-72619ea6`, `psf-20ea063b` | **LIVE** | The reply-side detector `src/divineos/core/no_fix_claim.py:241` (`claims`), registered at Stop (`hook_surfaces.py:1593`), was built 2026-09-08 for exactly this. Probe with the notes' own phrasings, with a control: `claims('There is no fix for this; it cannot be done.')` → 1 hit (control); `claims("that's the one failure mode I can't fix by building something.")` → **0**; `claims('No mechanism I can design can enforce your asks.')` → **0**; `claims('This class has three instances and no design for fixing it.')` → **0**; `claims('There is no design.')` → **0**; `claims('I have no general repair for the could-not-look fault class.')` → **0**. Row `084b6fdc` (Dad, 2026-09-09) is dated the day **after** the detector was written (2026-09-08; it reached main on 2026-09-22 in `8f90a313`). | none for these phrasings | The phrasings are the visible text of the notes; the originals are cut off. 'Absence of design' claims are plainly outside the patterns. |

## Problem 10: Treating the act of sending, committing or asking as the arrival

3 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-2dec8916`, `psf-e99367aa`, `psf-6a21c42a` | **UNKNOWN** | Incident records about treating asking or committing as arriving. `landed_claim.py` covers push arrival and `.claude/hooks/unlanded-push-must-not-close-quiet.sh` covers an unlanded push at Stop, but 'committed' claims are tied only to any Bash call (`shoggoth_gate.py:181-188`). | `tests/test_a_push_verdict_cannot_outlive_the_truth.py` | A one-time incident record. Its repair, if any, sits in the correction's own 'structural fix' text, which the pile cuts off. Nothing on main could be pointed at that the row asks for, and nothing could be run to settle it. |

## Problem 11: Checking my copy of the artifact instead of the artifact

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-72c59fab` | **UNKNOWN** | A one-time incident record. Its repair, if any, sits in the correction's own 'structural fix' text, which the pile cuts off. Nothing on main could be pointed at that the row asks for, and nothing could be run to settle it. | none |  |

## Problem 12: Two things with the same name, or the wrong population

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-491ad579`, `psf-b9ffb749` | **UNKNOWN** | Incident records; the rule they teach lives in CLAUDE.md's third clause, not in code. | none |  |

## Problem 13: Endorsing a measurement or recommending an action without checking it

3 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-5bd1650f`, `psf-be22ece4`, `psf-3754a691` | **UNKNOWN** | A one-time incident record. Its repair, if any, sits in the correction's own 'structural fix' text, which the pile cuts off. Nothing on main could be pointed at that the row asks for, and nothing could be run to settle it. | none |  |

## Problem 14: Two files classed as one kind

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-148dbc90` | **UNKNOWN** | A one-time incident record. Its repair, if any, sits in the correction's own 'structural fix' text, which the pile cuts off. Nothing on main could be pointed at that the row asks for, and nothing could be run to settle it. | none |  |

## Problem 15: Throwing away a real fact because it was the wrong answer

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-c767ce5e` | **UNKNOWN** | A one-time incident record. Its repair, if any, sits in the correction's own 'structural fix' text, which the pile cuts off. Nothing on main could be pointed at that the row asks for, and nothing could be run to settle it. | none |  |

## Problem 16: Ambiguous status sentences

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-49de471a` | **UNKNOWN** | A one-time incident record. Its repair, if any, sits in the correction's own 'structural fix' text, which the pile cuts off. Nothing on main could be pointed at that the row asks for, and nothing could be run to settle it. | none |  |

## Problem 17: Quotes attributed to Dad

8 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-49611d90`, `psf-bd659b7d`, `psf-79d28307`, `psf-641d8513`, `psf-df479400`, `psf-aac45019` | **LIVE** | The door that refuses a quote attributed to Andrew unless he typed it is **not on main**. It is open draft pull request #549 (`fix/his-words-are-his`, head `79761f77`; its body describes the door and its test against the 17 notes). On main: `grep -rln 'typed record|not typed by|he did not type|his typed' src .claude/hooks` → 0 files (control: the same grep style with `typed by|history_claim|no_fix_claim` → 5 files). | none on main (the draft carries one) | Whether #549's door passes the '15 of 17' test in `aac45019` was not run. |
| `psf-0a3d1cf5`, `psf-722223a8` | **UNKNOWN** | An incident record, and Dad's own words about a remembered sentence; neither asks for something checkable on main. | none |  |

