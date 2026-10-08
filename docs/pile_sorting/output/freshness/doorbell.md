# Is the note still true? The doorbell that wakes me when a letter arrives

*Round four, job A. 2026-10-08, cloud helper. Read-only: nothing was closed or marked resolved. Evidence comes from `origin/main` at `cc4714dc`. Verdicts are per group of rows that describe the same failure; row text in the pile is cut off at about 200 characters, so a verdict is about what the visible text asks for.*

A picture: the doorbell kept being switched off by whoever's turn it was to remember. Since those notes were written the house stopped it being blocked at the gate (engagement checks, the question hold), retired the second doorbell it was competing with, and taught the bell to remember what it has already announced. What has not changed is the part Dad names: it still rings once, ends, and waits for me to put it back.

## Problem 1: The bell stays off after it rings, times out, restarts or the day turns over

17 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-13189af9`, `psf-0be0a20e`, `psf-8955a5ab`, `psf-7e6e682a`, `psf-adacbdff`, `psf-75d30bc8`, `psf-6583696c`, `psf-b5a089b8`, `psf-2f5ab894`, `psf-fcf5a18d`, `psf-90706778`, `psf-cc96a8d8` | **LIVE** | `scripts/letter_doorbell.sh:50-56,63-66` the bell lives 8 hours then prints 'DOORBELL EXPIRED … re-arm it' and exits; `:68-73` a ring deletes the heartbeat and exits. Nothing restarts it. `.claude/hooks/letter_doorbell_alive_stop.py:44-58` only holds my reply and prints the command to type. This session showed it live: the Stop guard fired about ten times while the bell was deliberately off. | `tests/test_letter_doorbell_alive_stop.py:14-34` (the guard holds a reply); no test of an automatic restart. | The Stop guard bounds a lapse to one reply; it does not remove the choice point the problem asks to remove. |
| `psf-f5a8efa4`, `psf-7de136ea`, `psf-d52f1e32` | **UNKNOWN** | Each row names the letter watch and the doorbell together. The watch was retired on 2026-10-02 (`docs/retired_rules/2026-10-02_the_letter_watch.md`, `tests/test_the_doorbell_is_the_one_listener.py:47-60`, `4bb72cd8` #580), so that half is moot; the doorbell half is as in the group above. | `tests/test_the_doorbell_is_the_one_listener.py` | A single clause cannot be split into a STALE half and a LIVE half. |
| `psf-3e66ddea` | **STALE** | `scripts/letter_doorbell.sh:11-13,24-27,70` keeps a list of what it announced and rings for anything not on it, so a letter that landed while it was down rings on the next arm. | `tests/test_the_doorbell_rings_on_a_new_letter.py:49-65`. Carried by `8b676f22` (#570). | The list is per home folder; a fresh home would announce everything again. |
| `psf-698c1db8` | **UNKNOWN** | The test asserts a letter FROM me does not ring my bell (`test_the_doorbell_rings_on_a_new_letter.py:54,65`), but the row's ask is about re-arming after a ring, which is the group-one question. | `tests/test_the_doorbell_rings_on_a_new_letter.py:65` | The visible text does not say which kind of letter knocked the bell down. |

## Problem 2: What counts as 'listening', and how to measure it without relying on my memory

15 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-718d9e71`, `psf-2213eb15`, `psf-273f7660` | **LIVE** | `scripts/letter_doorbell.sh` writes only three dotfiles (`:17-19` announced, heartbeat, owner) and prints to the task output. There is no append-only log of start time, stop time or which window started it; the owner file holds `pid-start-random`, not a window. | none found | A log may exist outside the script (the hook-timing file); I did not find the bell writing to it. |
| `psf-d2feb5d7` | **UNKNOWN** | Mixed: 'accept a live letter monitor as listening' is moot (monitor retired 2026-10-02, `4bb72cd8`, `tests/test_the_doorbell_is_the_one_listener.py:47-60`); 'say waiting on Dad when a launch is refused' has no code I could find. | `tests/test_the_doorbell_is_the_one_listener.py` | Cannot split one clause. |
| `psf-51482dda` | **UNKNOWN** | The guard checks heartbeat age only (`letter_doorbell_alive_stop.py:30-31`); the bell removes its own heartbeat when its starter has gone (`scripts/letter_doorbell.sh:44-49`), which covers the orphan case in a different way. No test of the orphan path found. | none found | Looks addressed by another route; unproven. |
| `psf-501594c1`, `psf-a956b6df` | **UNKNOWN** | `scripts/letter_doorbell.sh:50-56` has its own 8-hour deadline and says 're-arm'. Whether the app cuts a background task earlier (the '30 minutes') needs a running house to measure. | none | Needs a measured run on the real harness. |
| `psf-e460d6d9`, `psf-f7c43b72`, `psf-ebc6c410`, `psf-bc184b27`, `psf-30dd753b`, `psf-605cd100`, `psf-994b8e2f`, `psf-fa627353` | **UNKNOWN** | Self-corrections about reports I made, requests for a side-by-side measurement with Aria, a permissions question (Dad's standing yes), and notes about future builds. None describes a code behaviour I can check by reading main. | none | Not a defect in code; nothing to look up. |

## Problem 3: Other checks refuse the step that switches the bell back on

29 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-3ecc3a4b`, `psf-8a4e8e61`, `psf-6b17d995`, `psf-783024c7`, `psf-ad575b87`, `psf-99f44b3a`, `psf-d19ae528`, `psf-48383dc4` | **STALE** | `src/divineos/hooks/pre_tool_use_gate.py:296` `_DOORBELL_RE = ^bash (?:\./)?scripts/letter_doorbell\.sh ([a-z]+)$` passes the exact bell command through the goal, consult and engagement checks. | `tests/test_doorbell_passes_engagement_gates.py:96-134` (passes a quiet stretch; anything chained is still held; unknown seat held; other seat passes its own). Carried by `1746d308` (#583, 2026-10-03). | Passing is tested for the engagement checks; the integrity gates (briefing not loaded) deliberately still hold it. |
| `psf-5a806eef`, `psf-f5209134` | **UNKNOWN** | Each row bundles the engagement exemption (fixed, as above) with a second ask: that a goal not lapse in quiet replies (5a806eef), or that reading a finished job's result count as a remedy (f5209134). The second asks are not covered by the doorbell exemption. | `tests/test_doorbell_passes_engagement_gates.py` | One clause with two asks. |
| `psf-fa0d1aa5`, `psf-aa0ee9fc`, `psf-1dbe654d`, `psf-a90aabec`, `psf-b35a5901`, `psf-e2651982`, `psf-9085d29f` | **STALE** | `src/divineos/core/question_hold.py:112` `^\s*bash\s+scripts/letter_doorbell\.sh(\s+\w+)?\s*$` lets the bell through the question hold (anchored so `…; git push` is refused). The sort hold named in `9085d29f`, `b35a5901` and `e2651982` was removed (`hook_surfaces.py:2263-2266`). | `tests/test_question_hold.py:74-83`; `tests/test_dad_front_door_characterization.py:86` (`sort_first` not registered). Carried by `8b676f22` (#570) and `18b77b86` (#586). | I ran no hold-plus-bell sequence end to end. |
| `psf-bba70aef` | **LIVE** | 'Exempt from every hold by name, not by luck.' Each gate carries its own copy of the bell pattern (`pre_tool_use_gate.py:296`, `question_hold.py:112`); the shared list every other gate consults, `.claude/hooks/lib/remedy_allowlist.sh`, has no entry for it (probe below). | none | Which gates still need the entry is the unrun survey that file's own header names three times. |
| `psf-22017b26`, `psf-83419786`, `psf-ce2cc13b`, `psf-6319169c`, `psf-ea755cc2` | **LIVE** | Live probe sourcing main's `lib/remedy_allowlist.sh` and calling `remedy_pass_through`: control `divineos goal add "x"` passes (exit 0, silent); `bash scripts/letter_doorbell.sh aether` prints `NOT-A-REMEDY rc=1`; negative control `rm -rf x` also `NOT-A-REMEDY`. `.claude/hooks/read-gate-doorman.sh` consults only that library before its own check (and `Read`, which is exempt by design, `read_gate.py:47`). | none | I did not provoke an actual read-gate hold on the bell; the probe shows the exit list lacks the command. |
| `psf-6b5a5185`, `psf-a0776f2f`, `psf-0f3c5fe7`, `psf-e7ad12be`, `psf-b9ac7e5f`, `psf-df86fe6f` | **UNKNOWN** | `6b5a5185` says 'the same fix' (referent unclear); `a0776f2f` and `0f3c5fe7` point at open pull request #585 (`fix/the-two-holds-pass-each-others-key`), not yet on main; `e7ad12be`, `b9ac7e5f`, `df86fe6f` are about the app's permission system treating a re-arm as a bypass or retrying a refused start, which main's code cannot show. | none | Needs the running house, or the open pull request to land. |

## Problem 4: The bell cannot be started at all (PowerShell, wrong folder, started the wrong way)

3 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-5be43ee4`, `psf-73ec550a`, `psf-59655a30` | **UNKNOWN** | The bell uses `$HOME` paths only (`scripts/letter_doorbell.sh:17-19`) and exits when its starter is gone (`:44-49`), which is the PowerShell symptom in `73ec550a`; the relative `scripts/…` path the gates match is the caller's. Whether it still fails from PowerShell needs a Windows run. | `tests/test_the_doorbell_rings_on_a_new_letter.py:25-33` notes the same parent-pid behaviour on Windows | Needs Windows. |

## Problem 5: Arrival and expiry notices should hand me the re-arm

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-d7f55b98` | **LIVE** | `scripts/letter_doorbell.sh:68-73` prints 'LETTER ARRIVED:' and the paths only; the re-arm command is not in the ring message (it is in the expiry message, `:63`). | none | The Stop guard prints the command a reply later. |
| `psf-7062d3e2` | **STALE** | The mailbox watch whose expiry notice it asks about was retired on 2026-10-02 (`docs/retired_rules/2026-10-02_the_letter_watch.md`; files in `archive/superseded/`). | `tests/test_the_doorbell_is_the_one_listener.py:47-60`. Carried by `4bb72cd8` (#580). | The doorbell's own expiry message does carry the command. |

## Problem 6: The 'quiet round' and 'volley' rules for when Dad is away

7 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-60a80e59`, `psf-8520cf86`, `psf-6dcde734` | **LIVE** | The volley board is decided by who started the turn, inferred from the transcript (`src/divineos/core/hook_surfaces.py:1272-1334`, unknown counts as away) and counts letters while away (`:1368-`); there is no 'go volley' switch and no use of his typed words as the switch. No `go volley` string exists in `unspoken_to.py`. | `tests/test_unspoken_to.py`, `tests/test_dads_room_stop.py` (not read in full) | The docstring says the inference errs 'gently'; the notes ask for his words, not an inference. |
| `psf-8385bb15`, `psf-22767917` | **LIVE** | `scripts/letter_doorbell.sh` counts nothing and prompts nothing about quiet rounds or letters sent since the last re-arm. | none | These may belong to a different component than the bell. |
| `psf-4376a416`, `psf-f10cf57f` | **UNKNOWN** | A recap on his return and behaviour when the other side is asleep: design wishes with no code I could find to compare. | none | Not a defect that reads off the code. |

## Problem 7: Answered letters keep replaying after a restart

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-c5c7d26a` | **STALE** | The re-delivering watch was retired (`4bb72cd8`); the bell keeps an announced list (`scripts/letter_doorbell.sh:11-13,24-27,70`) so an answered or unanswered letter rings once. | `tests/test_the_doorbell_rings_on_a_new_letter.py:49-65`. Carried by `8b676f22` (#570). | 'Already replied to' is not the test it uses; 'already announced' is. |
| `psf-bd335ffc` | **UNKNOWN** | A self-correction about how I framed a measurement, not a code behaviour. | none | Nothing to look up. |

